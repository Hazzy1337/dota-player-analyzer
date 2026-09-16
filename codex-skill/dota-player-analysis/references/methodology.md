# Methodology

- Use `<5` matches as insufficient, `5–9` as low confidence, `10–19` as medium, and `20+` as high for grouped hero and role claims.
- Define a session as consecutive matches whose gap from the preceding match's end is under 90 minutes.
- Mark role classification inferred unless a source provides it directly.
- Calculate KDA as `(kills + assists) / max(1, deaths)`.
- Treat correlation as descriptive, never causal.
- Leave lane, objectives, item timings, lead conversion, and timestamped death analysis unavailable when detailed match telemetry is absent.
- Base recommendations only on thresholds actually supported by the selected-period dataset.

