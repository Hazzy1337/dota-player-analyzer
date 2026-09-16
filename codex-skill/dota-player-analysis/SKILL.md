---
name: dota-player-analysis
description: Analyze one or more Dota 2 players from Dotabuff/OpenDota links, Steam32 IDs, or Steam64 IDs; calculate recent form, heroes, deaths, sessions, streaks, roles, consistency, and evidence-based recommendations; generate Russian or English PDF reports and comparison reports. Use for requests such as "проанализируй мой Dotabuff", "посмотри игрока", "разбери последние 45 дней", "сравни игроков", "что мне улучшить в Dota", or "сделай анализ Dotabuff".
---

# Dota Player Analysis

## Workflow

1. Extract every supplied player identifier. Accept Dotabuff/OpenDota URLs, Steam32, and Steam64.
2. Infer the report language from the user's message: use `ru` for Russian and `en` for English.
3. Select the period:
   - Default to `--days 45`.
   - For “за полтора месяца”, use `--days 45`.
   - For “последние N матчей”, use `--matches N` and do not also pass `--days`.
   - Preserve explicit `--from` and `--to` dates.
4. Run the bundled launcher from the repository root:

   ```powershell
   python "<skill-dir>\scripts\analyze.py" analyze <player> --days 45 --language ru
   ```

5. For two or more players, run `compare` and pass all identifiers.
6. Inspect the CLI exit code and generated `analysis.json`. Do not summarize a failed or empty run as successful.
7. Check `data_quality`, source warnings, sample sizes, and every inferred field before describing conclusions.
8. Return a short chat summary and link the generated PDF. Keep detailed analytics inside the PDF.

## Hard rules

- Never invent a statistic, source field, role, item timing, death timing, MMR change, or objective event.
- Render missing fields as `N/A` or “Not available from source.”
- Call an indirect conclusion “estimated” or “inferred”.
- Never mix career statistics with selected-period statistics.
- Do not make strong hero/time/session claims below the confidence thresholds stored in the report.
- Do not claim that one compared player is universally better based on WR alone.
- Treat Dotabuff blocking as a data-quality limitation. Allow the analyzer's OpenDota fallback to complete the report.
- Always produce a PDF for a successful analysis or comparison.

## Output

Respond concisely in the user's language:

```text
Готово.

За последние 45 дней:
<matches> матчей
<wins>–<losses>
<winrate>% WR

Главные проблемы:
1. <evidence-based leak>
2. ...

Главные сильные стороны:
1. <evidence-based strength>
2. ...

Полный разбор:
[PDF]
```

Read [references/methodology.md](references/methodology.md) only when explaining confidence, missing telemetry, or the scoring methodology.
