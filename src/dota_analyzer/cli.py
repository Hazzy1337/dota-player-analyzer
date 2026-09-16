from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .service import AnalyzerService


def _date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dota-analyzer", description="Evidence-based Dotabuff/OpenDota player analyzer")
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    period = common.add_mutually_exclusive_group()
    period.add_argument("--days", type=int, default=45)
    period.add_argument("--matches", type=int)
    common.add_argument("--from", dest="from_date", type=_date)
    common.add_argument("--to", dest="to_date", type=_date)
    common.add_argument("--output", type=Path, default=Path("output"))
    common.add_argument("--cache-dir", type=Path, default=Path("cache"))
    common.add_argument("--cache-ttl-hours", type=int, default=24)
    common.add_argument("--enrich-limit", type=int, default=20)
    common.add_argument("--language", choices=("ru", "en"), default="ru")
    common.add_argument("--save-raw", action="store_true")
    common.add_argument("--browser-fallback", action="store_true", help="Use optional Playwright after Dotabuff HTTP blocking")
    common.add_argument("--no-cache", action="store_true")
    common.add_argument("--verbose", action="store_true")
    analyze = sub.add_parser("analyze", parents=[common])
    analyze.add_argument("player")
    analyze.add_argument("--compare-with-previous", action="store_true")
    compare = sub.add_parser("compare", parents=[common])
    compare.add_argument("players", nargs="+")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.command == "compare" and len(args.players) < 2:
        raise SystemExit("compare requires at least two players")
    settings = Settings(cache_dir=args.cache_dir, output_dir=args.output, cache_ttl_hours=args.cache_ttl_hours, enrich_limit=max(0, args.enrich_limit), browser_fallback=args.browser_fallback)
    service = AnalyzerService(settings, use_cache=not args.no_cache, save_raw=args.save_raw)
    kwargs = {"days": args.days, "matches_limit": args.matches, "from_date": args.from_date, "to_date": args.to_date, "language": args.language}
    if args.command == "analyze":
        kwargs["compare_with_previous"] = args.compare_with_previous
    try:
        result = service.analyze(args.player, **kwargs) if args.command == "analyze" else service.compare(args.players, **kwargs)
    except Exception as exc:
        logging.getLogger(__name__).exception("Analysis failed")
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    finally:
        service.close()
    if args.command == "analyze":
        overview = result["overview"]
        if args.language == "ru":
            print(f"Готово. {overview['matches']} матчей, {overview['wins']}–{overview['losses']}, WR {overview['winrate']}%")
            print("Главные проблемы:")
        else:
            print(f"Done. {overview['matches']} matches, {overview['wins']}–{overview['losses']}, {overview['winrate']}% WR")
            print("Main issues:")
        for index, leak in enumerate(result["top_leaks"], start=1):
            print(f"{index}. {leak['title']}")
        print(f"PDF: {result['files']['report_pdf']}")
    else:
        if args.language == "ru":
            print(f"Готово. Сравнено игроков: {len(result['players'])}")
        else:
            print(f"Done. Players compared: {len(result['players'])}")
        print(f"PDF: {result['files']['report_pdf']}")
    return 0
