# Dota Player Analyzer

A resilient Python CLI that combines Dotabuff and OpenDota data, calculates evidence-based player trends, and produces reproducible PDF reports with explicit data-quality limits.

[Русская версия](README_RU.md)

## What it does

- accepts a Dotabuff/OpenDota URL, Steam32 ID, or Steam64 ID
- collects recent matches with cache, retry, timeout, backoff, and rate limiting
- falls back from Dotabuff to OpenDota when Cloudflare or availability blocks collection
- optionally enriches data through Steam Web API
- calculates hero form, known roles, deaths, sessions, fatigue, streaks, tilt signals, time-of-day results, consistency, and trends
- exports normalized JSON, CSV, charts, and a PDF report
- keeps replay-only or unavailable metrics as `N/A` instead of inventing them

## Architecture

```text
CLI
  -> source adapters (Dotabuff / OpenDota / Steam)
  -> normalized match model
  -> analytics and session engine
  -> evidence-based recommendations
  -> JSON / CSV / chart / PDF reporting
```

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Usage

```powershell
.\.venv\Scripts\python -m dota_analyzer analyze 336235516 --days 45
.\.venv\Scripts\python -m dota_analyzer analyze https://www.dotabuff.com/players/336235516
.\.venv\Scripts\python -m dota_analyzer compare 336235516 138712363 --days 45
```

Useful diagnostic options include `--verbose`, `--save-raw`, `--no-cache`, `--cache-ttl-hours`, `--enrich-limit`, and `--browser-fallback`.

## Optional environment variables

Copy `.env.example` and provide keys only when needed:

- `OPENDOTA_API_KEY`
- `STEAM_WEB_API_KEY`
- `DOTA_ANALYZER_CACHE_TTL_HOURS`
- `DOTA_ANALYZER_TIMEZONE`

The analyzer works without API keys, subject to public rate limits.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

Tests use a small synthetic Dotabuff-like HTML fixture and do not require a live account.

## Data quality and privacy

- Source failures and fallbacks are recorded in report data quality notes.
- Raw pages, cache files, player exports, and generated personal reports are ignored by Git.
- Do not commit API keys or reports containing another person's match history without permission.
- Dotabuff and OpenDota remain independent services with their own availability and terms.

## Codex skill

`codex-skill/dota-player-analysis` contains the reusable Codex skill package that drives the same analyzer and reporting methodology.

## Author

Sergej Gordeev (Paluch)

## License

No license is granted at this time. The source is publicly visible for portfolio and review purposes. Contact the author before reuse or redistribution.
