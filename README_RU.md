# Dota Player Analyzer

Локальный Python-инструмент для анализа игроков Dota 2 по Dotabuff/OpenDota и генерации PDF. Он принимает Dotabuff/OpenDota URL, Steam32 или Steam64, сохраняет нормализованные данные и строит рекомендации только из доступных метрик.

## Источники и ограничения

- Dotabuff — первый источник. Клиент поддерживает профиль, matches pagination, heroes/activity pages, cache, retry, timeout, backoff, rate limiting и сохранение raw HTML.
- Dotabuff может отвечать `403`/Cloudflare. Тогда инструмент явно переключается на OpenDota и записывает это в `Data Quality`.
- OpenDota используется для fallback и ограниченного match enrichment. Инструмент работает без API key; ключ повышает доступный лимит.
- Steam Web API опционален и используется только при наличии `STEAM_WEB_API_KEY`.
- Playwright — опциональный fallback (`pip install -e .[browser]`, `playwright install chromium`, затем `--browser-fallback`), не единственный способ получения данных.

## Установка

```powershell
cd P:\dota-player-analyzer
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## CLI

```powershell
.\.venv\Scripts\python -m dota_analyzer analyze https://ru.dotabuff.com/players/336235516
.\.venv\Scripts\python -m dota_analyzer analyze 336235516 --days 45
.\.venv\Scripts\python -m dota_analyzer analyze 336235516 --matches 200
.\.venv\Scripts\python -m dota_analyzer analyze 336235516 --from 2026-07-01 --to 2026-08-15
.\.venv\Scripts\python -m dota_analyzer compare 336235516 138712363 --days 45
```

Диагностика: `--verbose`, `--save-raw`, `--no-cache`, `--cache-ttl-hours`, `--enrich-limit`, `--browser-fallback`.

Результат каждого игрока:

- `output/<account_id>/analysis.json`
- `output/<account_id>/matches.csv`
- `output/<account_id>/Dota2_Analysis_<name>_<date>.pdf`

Comparison сохраняется в `output/comparison/`.

## Аналитика

Рассчитываются overview, герои, известные роли, deaths buckets/correlation, сессии (gap <90 минут), fatigue, streaks/tilt, время суток, дни недели, party/solo при наличии, сторона, длительность, consistency, тренд, evidence-based leaks и Next 100 Ranked Plan. Недоступные replay-level метрики остаются `N/A`; косвенные skill scores помечаются estimated.

## Тесты

```powershell
.\.venv\Scripts\python -m pytest -q
```

Парсер тестируется на сохранённом HTML fixture, а не только на живом Dotabuff.
