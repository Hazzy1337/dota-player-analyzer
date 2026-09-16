from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Player

NAVY = colors.HexColor("#173A63")
BLUE = colors.HexColor("#2F679D")
LIGHT_BLUE = colors.HexColor("#EAF1F8")
PALE_BLUE = colors.HexColor("#F5F8FB")
TEXT = colors.HexColor("#1A1F26")
MUTED = colors.HexColor("#5D6672")
GREEN = colors.HexColor("#2D7658")
PALE_GREEN = colors.HexColor("#E9F4EE")
RED = colors.HexColor("#A84742")
PALE_RED = colors.HexColor("#F9ECEB")
AMBER = colors.HexColor("#A56A1D")
LINE = colors.HexColor("#B9C4D0")
WHITE = colors.white


def _fonts() -> tuple[str, str]:
    regular_path = font_manager.findfont("DejaVu Sans")
    bold_path = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
    if "DotaReport" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DotaReport", regular_path))
        pdfmetrics.registerFont(TTFont("DotaReportBold", bold_path))
    return "DotaReport", "DotaReportBold"


def _styles() -> dict[str, ParagraphStyle]:
    regular, bold = _fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("CoachTitle", parent=base["Title"], fontName=bold, fontSize=22, leading=26, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6),
        "subtitle": ParagraphStyle("CoachSubtitle", parent=base["BodyText"], fontName=regular, fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8),
        "h1": ParagraphStyle("CoachH1", parent=base["Heading1"], fontName=bold, fontSize=15, leading=19, textColor=BLUE, spaceBefore=7, spaceAfter=5, keepWithNext=True),
        "h2": ParagraphStyle("CoachH2", parent=base["Heading2"], fontName=bold, fontSize=11, leading=14, textColor=NAVY, spaceBefore=5, spaceAfter=3, keepWithNext=True),
        "body": ParagraphStyle("CoachBody", parent=base["BodyText"], fontName=regular, fontSize=9.2, leading=13.3, textColor=TEXT, spaceAfter=4),
        "body_bold": ParagraphStyle("CoachBodyBold", parent=base["BodyText"], fontName=bold, fontSize=9.2, leading=13.3, textColor=TEXT, spaceAfter=4),
        "small": ParagraphStyle("CoachSmall", parent=base["BodyText"], fontName=regular, fontSize=7.5, leading=10.2, textColor=MUTED, spaceAfter=2),
        "score": ParagraphStyle("CoachScore", parent=base["Title"], fontName=bold, fontSize=27, leading=29, textColor=NAVY, alignment=TA_CENTER),
        "score_label": ParagraphStyle("CoachScoreLabel", parent=base["BodyText"], fontName=bold, fontSize=10, leading=13, textColor=NAVY, alignment=TA_CENTER),
        "card": ParagraphStyle("CoachCard", parent=base["BodyText"], fontName=regular, fontSize=8.7, leading=12.2, textColor=TEXT, spaceAfter=0),
        "card_title": ParagraphStyle("CoachCardTitle", parent=base["BodyText"], fontName=bold, fontSize=9.5, leading=12.5, textColor=NAVY, spaceAfter=2),
        "number": ParagraphStyle("CoachNumber", parent=base["BodyText"], fontName=bold, fontSize=14, leading=16, textColor=WHITE, alignment=TA_CENTER),
    }


def _page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5DDE6"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.setFont("DotaReport", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.5 * mm, "Dota Player Analyzer • coaching report")
    canvas.drawRightString(A4[0] - 18 * mm, 8.5 * mm, f"{doc.page}")
    canvas.restoreState()


def _fmt(value: Any, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value}{suffix}"


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(value) if value is not None else "N/A", style)


def _table(rows: list[list[Any]], widths: list[float] | None = None, *, header: bool = True, compact: bool = True) -> Table:
    styles = _styles()
    cooked = [[cell if isinstance(cell, Paragraph) else _p(cell, styles["small"] if compact else styles["body"]) for cell in row] for row in rows]
    table = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3 if compact else 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 if compact else 5),
        ("BACKGROUND", (0, 1 if header else 0), (-1, -1), WHITE),
    ]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE), ("FONTNAME", (0, 0), (-1, 0), "DotaReportBold"), ("TEXTCOLOR", (0, 0), (-1, 0), NAVY)])
    table.setStyle(TableStyle(commands))
    return table


def _metric_cards(overview: dict[str, Any], language: str) -> Table:
    styles = _styles()
    values = [
        (_fmt(overview["matches"]), "Матчи" if language == "ru" else "Matches"),
        (f"{overview['wins']}–{overview['losses']}", "Победы–поражения" if language == "ru" else "Wins–losses"),
        (_fmt(overview["winrate"], "%"), "Winrate"),
        (_fmt(overview["kda"]), "KDA"),
        (_fmt(overview["deaths"]), "Смерти / матч" if language == "ru" else "Deaths / game"),
    ]
    cells = []
    for value, label in values:
        cells.append([_p(value, styles["score_label"]), _p(label, styles["small"])])
    table = Table([cells], colWidths=[32 * mm] * 5)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return table


def _rating_card(analysis: dict[str, Any], language: str) -> Table:
    styles = _styles()
    rating = analysis["overall_rating"]
    left = [_p(_fmt(rating["score"], "/10"), styles["score"]), _p(rating["label"], styles["score_label"]), _p(f"Confidence: {rating['confidence']}", styles["small"])]
    right_title = "Вердикт" if language == "ru" else "Verdict"
    right = [_p(right_title, styles["card_title"]), _p(analysis["coach_summary"], styles["body"]), _p(rating["explanation"], styles["small"])]
    table = Table([[left, right]], colWidths=[43 * mm, 119 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), LIGHT_BLUE), ("BACKGROUND", (1, 0), (1, 0), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.8, BLUE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return table


def _action_card(index: int, leak: dict[str, Any], language: str) -> Table:
    styles = _styles()
    meta = f"Impact: {leak['impact']} • Confidence: {leak['confidence']}"
    body = [
        _p(leak["title"], styles["card_title"]),
        _p(leak["explanation"], styles["card"]),
        _p(("Действие: " if language == "ru" else "Action: ") + leak["action"], styles["body_bold"]),
        _p(meta, styles["small"]),
    ]
    table = Table([[_p(index, styles["number"]), body]], colWidths=[13 * mm, 149 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), RED if index == 1 else BLUE), ("BACKGROUND", (1, 0), (1, 0), PALE_RED if index == 1 else PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return table


def _bullet_paragraph(index: int, text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"<b>{index}.</b> {text}", styles["body"])


def render_player_pdf(player: Player, analysis: dict[str, Any], output_dir: Path, language: str = "ru") -> Path:
    styles = _styles()

    def tr(ru: str, en: str) -> str:
        return ru if language == "ru" else en

    safe_name = re.sub(r"[^\w.-]+", "_", player.name or str(player.account_id), flags=re.UNICODE).strip("_")
    path = output_dir / f"Dota2_Analysis_{safe_name}_{date.today().isoformat()}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=14 * mm, bottomMargin=17 * mm, title=f"Dota 2 Coaching Analysis — {player.name}")
    o = analysis["overview"]
    story: list[Any] = []

    # Page 1: verdict first.
    story.append(Paragraph(tr(f"{player.name} — РАЗБОР ИГРОКА DOTA 2", f"{player.name} — DOTA 2 PLAYER REVIEW"), styles["title"]))
    story.append(Paragraph(tr(f"ID {player.account_id} • период {o.get('from', 'N/A')[:10]} — {o.get('to', 'N/A')[:10]} • только матчи выбранного периода", f"ID {player.account_id} • {o.get('from', 'N/A')[:10]} — {o.get('to', 'N/A')[:10]} • selected-period matches only"), styles["subtitle"]))
    story.append(_metric_cards(o, language))
    story.append(Spacer(1, 5 * mm))
    story.append(_rating_card(analysis, language))
    story.append(Paragraph(tr("Три главных рычага для роста winrate", "Three biggest win-rate levers"), styles["h1"]))
    for index, leak in enumerate(analysis["top_leaks"][:3], start=1):
        story.append(_action_card(index, leak, language))
        story.append(Spacer(1, 2.2 * mm))
    story.append(PageBreak())

    # Page 2: portrait and explanations.
    story.append(Paragraph(tr("1. Портрет игрока", "1. Player profile"), styles["h1"]))
    story.append(Paragraph(analysis["coach_summary"], styles["body"]))
    story.append(Paragraph(tr("Сильные стороны", "Strengths"), styles["h1"]))
    for index, strength in enumerate(analysis["strengths"], start=1):
        story.append(_bullet_paragraph(index, strength, styles))
    story.append(Paragraph(tr("Слабые стороны — простым языком", "Weaknesses in plain language"), styles["h1"]))
    for index, leak in enumerate(analysis["top_leaks"][:4], start=1):
        story.append(KeepTogether([Paragraph(f"{index}. {leak['title']}", styles["h2"]), Paragraph(leak["explanation"], styles["body"]), Paragraph(f"<b>{tr('Почему это важно', 'Why it matters')}:</b> {leak['evidence']}", styles["small"])]))
    story.append(Paragraph(tr("Оценка аспектов", "Aspect ratings"), styles["h1"]))
    score_rows = [[tr("Аспект", "Aspect"), tr("Оценка", "Score"), tr("Что означает", "Meaning"), tr("Уверенность", "Confidence")]]
    for row in analysis["rating_breakdown"]:
        score_rows.append([row["name"], _fmt(row["score"], "/10"), row["explanation"], row["confidence"]])
    story.append(_table(score_rows, [42 * mm, 22 * mm, 76 * mm, 23 * mm]))
    story.append(Paragraph(tr("Важно: оценки с косвенными данными описывают текущую форму, а не врождённый уровень навыка.", "Important: ratings based on indirect data describe current form, not innate skill."), styles["small"]))
    story.append(PageBreak())

    # Page 3: only evidence that changes decisions.
    story.append(Paragraph(tr("2. Что именно влияет на твой winrate", "2. What actually affects your win rate"), styles["h1"]))
    story.append(Paragraph(tr("Смерти и цена ошибки", "Deaths and the cost of mistakes"), styles["h2"]))
    story.append(Paragraph(tr(f"В победах ты умираешь в среднем {_fmt(analysis['deaths']['wins'])} раза, в поражениях — {_fmt(analysis['deaths']['losses'])}. Ниже не просто KDA: таблица показывает, как меняется результат матча при разном количестве смертей.", f"You average {_fmt(analysis['deaths']['wins'])} deaths in wins and {_fmt(analysis['deaths']['losses'])} in losses. This is not merely KDA: the table shows how match outcomes change across death ranges."), styles["body"]))
    story.append(_table([[tr("Смерти", "Deaths"), tr("Матчи", "Matches"), "WR", tr("Надёжность", "Confidence")]] + [[row["name"], row["matches"], _fmt(row["winrate"], "%"), row["confidence"]] for row in analysis["deaths"]["buckets"]], [35 * mm, 35 * mm, 35 * mm, 57 * mm]))

    story.append(Paragraph(tr("Пул героев", "Hero pool"), styles["h2"]))
    hero_rows = [[tr("Герой", "Hero"), tr("Матчи", "Matches"), "W–L", "WR", "KDA", tr("Вывод", "Read")]]
    for hero in analysis["heroes"][:8]:
        if hero["matches"] < 5:
            read = tr("мало данных", "small sample")
        elif o["winrate"] is not None and hero["winrate"] >= o["winrate"] + 4:
            read = tr("рабочий", "proven")
        elif o["winrate"] is not None and hero["winrate"] <= o["winrate"] - 8:
            read = tr("проверить", "review")
        else:
            read = tr("нейтрально", "neutral")
        hero_rows.append([hero["name"], hero["matches"], f"{hero['wins']}–{hero['losses']}", _fmt(hero["winrate"], "%"), _fmt(hero["kda"]), read])
    story.append(_table(hero_rows, [42 * mm, 20 * mm, 20 * mm, 21 * mm, 20 * mm, 39 * mm]))

    story.append(Paragraph(tr("Когда и насколько долго ты играешь", "When and how long you play"), styles["h2"]))
    time_rows = [row for row in analysis["time_of_day"] if row["matches"] >= 10]
    duration_rows = [row for row in analysis["duration"] if row["matches"] >= 10]
    combined = []
    if time_rows:
        best = max(time_rows, key=lambda row: row["winrate"] if row["winrate"] is not None else -1)
        worst = min(time_rows, key=lambda row: row["winrate"] if row["winrate"] is not None else 101)
        combined.extend([[tr("Лучшее время", "Best time"), best["name"], best["matches"], _fmt(best["winrate"], "%"), _fmt(best["deaths"])] , [tr("Худшее время", "Worst time"), worst["name"], worst["matches"], _fmt(worst["winrate"], "%"), _fmt(worst["deaths"])]] )
    if duration_rows:
        best_duration = max(duration_rows, key=lambda row: row["winrate"] if row["winrate"] is not None else -1)
        worst_duration = min(duration_rows, key=lambda row: row["winrate"] if row["winrate"] is not None else 101)
        combined.extend([[tr("Лучшая длительность", "Best duration"), best_duration["name"] + " min", best_duration["matches"], _fmt(best_duration["winrate"], "%"), _fmt(best_duration["deaths"])], [tr("Худшая длительность", "Worst duration"), worst_duration["name"] + " min", worst_duration["matches"], _fmt(worst_duration["winrate"], "%"), _fmt(worst_duration["deaths"])]] )
    if combined:
        story.append(_table([[tr("Срез", "Slice"), tr("Группа", "Group"), tr("Матчи", "Matches"), "WR", tr("Смерти", "Deaths")]] + combined, [43 * mm, 33 * mm, 27 * mm, 27 * mm, 32 * mm]))
        story.append(Paragraph(tr("Время суток указано в настроенной локальной временной зоне. Это корреляция: используй её как эксперимент на 25 игр, а не как абсолютную истину.", "Time of day uses the configured local timezone. This is correlation: use it as a 25-game experiment, not an absolute truth."), styles["small"]))

    story.append(Paragraph(tr("Динамика формы", "Form trend"), styles["h2"]))
    trend_rows = [[tr("Часть периода", "Period segment"), tr("Матчи", "Matches"), "WR", tr("Смерти", "Deaths"), "KDA"]]
    for row in analysis["trend"]["segments"]:
        trend_rows.append([row["segment"], row["matches"], _fmt(row["winrate"], "%"), _fmt(row["deaths"]), _fmt(row["kda"])])
    story.append(_table(trend_rows, [43 * mm, 30 * mm, 30 * mm, 30 * mm, 29 * mm]))
    story.append(Paragraph(tr(f"Итог по динамике: {analysis['trend']['direction']}. Смысл этого блока — увидеть повторяемость результата, а не переоценить один удачный день.", f"Trend verdict: {analysis['trend']['direction']}. This section is meant to show repeatability, not overvalue one good day."), styles["body"]))
    story.append(PageBreak())

    # Page 4: executable plan.
    story.append(Paragraph(tr("3. Практический план улучшения", "3. Practical improvement plan"), styles["h1"]))
    story.append(Paragraph(tr("Следующие 30 ranked — один простой эксперимент", "The next 30 ranked games — one simple experiment"), styles["h2"]))
    plan = analysis["next_30_games_plan"]
    plan_rows = [
        [tr("Главный фокус", "Main focus"), plan["main_focus"]],
        [tr("Цель по смертям", "Death target"), _fmt(plan["death_target"], " или меньше" if language == "ru" else " or fewer")],
        [tr("Ranked-пул", "Ranked pool"), ", ".join(plan["ranked_pool"]) or "N/A"],
        [tr("Лимит сессии", "Session limit"), tr(f"не больше {plan['session_limit']} игр", f"no more than {plan['session_limit']} games")],
        ["Stop-loss", tr(f"пауза после {plan['stop_loss']} поражений подряд", f"pause after {plan['stop_loss']} consecutive losses")],
        [tr("Неудачное окно", "Avoid window"), plan["avoid_time"] or tr("не подтверждено", "not confirmed")],
        [tr("Обязательный review", "Mandatory review"), plan["mandatory_review"]],
        [tr("Контрольная точка", "Checkpoint"), plan["checkpoint"]],
    ]
    story.append(_table([[tr("Правило", "Rule"), tr("Что делать", "What to do")]] + plan_rows, [48 * mm, 114 * mm], compact=False))

    story.append(Paragraph(tr("Чек-лист после каждого поражения", "Checklist after every loss"), styles["h2"]))
    checklist = [
        tr("Какая первая моя смерть реально изменила темп матча?", "Which of my deaths first changed the tempo of the match?"),
        tr("Что я видел на карте за 20 секунд до неё?", "What information did I have 20 seconds before it?"),
        tr("Была ли у команды конкретная цель: tower, Roshan, farm или reset?", "Did the team have a concrete goal: tower, Roshan, farm, or reset?"),
        tr("После 40-й минуты: был ли buyback и зачем я вошёл в опасную зону?", "After minute 40: did I have buyback, and why did I enter a dangerous area?"),
        tr("Был ли выбранный герой частью основного ranked-пула?", "Was the selected hero part of the main ranked pool?"),
    ]
    for index, item in enumerate(checklist, start=1):
        story.append(_bullet_paragraph(index, item, styles))

    story.append(Paragraph(tr("Что оставить и что изменить", "What to keep and what to change"), styles["h2"]))
    keep = "<br/>".join(f"• {item}" for item in analysis["what_to_keep"])
    stop = "<br/>".join(f"• {item}" for item in analysis["what_to_stop"])
    keep_stop = Table([[_p(tr("ОСТАВИТЬ", "KEEP"), styles["card_title"]), _p(tr("СДЕЛАТЬ / ОГРАНИЧИТЬ", "DO / LIMIT"), styles["card_title"])], [_p(keep, styles["card"]), _p(stop, styles["card"])]], colWidths=[81 * mm, 81 * mm])
    keep_stop.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), PALE_GREEN), ("BACKGROUND", (1, 0), (1, -1), PALE_RED), ("TEXTCOLOR", (0, 0), (0, 0), GREEN), ("TEXTCOLOR", (1, 0), (1, 0), RED), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(keep_stop)

    story.append(Paragraph(tr("Качество данных и ограничения", "Data quality and limitations"), styles["h2"]))
    quality = analysis["data_quality"]
    story.append(Paragraph(tr(f"Источник: {quality['primary_source']}; матчей в срезе: {o['matches']}; детально обогащено: {quality['opendota_enriched']}; без подробной телеметрии: {quality['missing_detailed_telemetry']}. Уверенность общей выборки: {quality['confidence']}.", f"Source: {quality['primary_source']}; period matches: {o['matches']}; detailed enrichment: {quality['opendota_enriched']}; missing detailed telemetry: {quality['missing_detailed_telemetry']}. Overall sample confidence: {quality['confidence']}."), styles["small"]))
    for warning in quality["warnings"]:
        story.append(Paragraph(f"Warning: {warning}", styles["small"]))
    story.append(Paragraph(tr("Career-статистика не смешивалась с выбранным периодом. Роли, lane, GPM/XPM, item timings, net-worth conversion и replay-level macro не оцениваются как факт, если источник их не предоставил.", "Career statistics were not mixed with the selected period. Roles, lane, GPM/XPM, item timings, net-worth conversion, and replay-level macro are not rated as facts when the source did not provide them."), styles["small"]))

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return path


def render_comparison_pdf(comparison: dict[str, Any], output_dir: Path, language: str = "ru") -> Path:
    styles = _styles()

    def tr(ru: str, en: str) -> str:
        return ru if language == "ru" else en

    path = output_dir / f"Dota2_Comparison_{date.today().isoformat()}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=15 * mm, bottomMargin=17 * mm, title="Dota 2 Player Comparison")
    story: list[Any] = [Paragraph(tr("СРАВНЕНИЕ ИГРОКОВ DOTA 2", "DOTA 2 PLAYER COMPARISON"), styles["title"]), Paragraph(tr("Сравниваются отдельные аспекты и доступные выборки, а не определяется «кто лучше вообще».", "Individual aspects and available samples are compared; this does not decide who is universally better."), styles["subtitle"])]
    rows = [[tr("Игрок", "Player"), tr("Матчи", "Matches"), "WR", "KDA", tr("Смерти", "Deaths"), "GPM", tr("Роль", "Role"), tr("Стабильность", "Consistency")]]
    for item in comparison["players"]:
        player = item["player"]
        rows.append([player.get("name") or player["account_id"], item["matches"], _fmt(item["winrate"], "%"), _fmt(item["kda"]), _fmt(item["deaths"]), _fmt(item["gpm"]), item["main_role"] or "N/A", _fmt(item["consistency"], "/10")])
    story.append(_table(rows, [31 * mm, 20 * mm, 20 * mm, 19 * mm, 21 * mm, 20 * mm, 24 * mm, 27 * mm]))
    story.append(Paragraph(tr("Как использовать сравнение", "How to use this comparison"), styles["h1"]))
    story.append(Paragraph(tr("Смотри на различия в дисциплине, стабильности, пуле и поведении в сессиях. Один WR без учёта роли, героев и размера выборки не является итоговой оценкой игрока.", "Focus on differences in discipline, consistency, hero pool, and session behavior. A single WR without role, hero, and sample context is not an overall player rating."), styles["body"]))
    for item in comparison["players"]:
        story.append(Paragraph(str(item["player"].get("name") or item["player"]["account_id"]), styles["h2"]))
        story.append(Paragraph(f"Archetype: {item['archetype']}. Hero pool: {item['hero_pool']}. Session fatigue delta: {_fmt(item['session_fatigue_delta'], ' pp')}. Role sample: {item['role_known_sample']}.", styles["body"]))
    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return path
