from __future__ import annotations

from typing import Any


IMPACT_WEIGHT = {"high": 3, "medium": 2, "low": 1}
CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}


def _clamp(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 1)


def _priority(
    title: str,
    evidence: str,
    explanation: str,
    action: str,
    *,
    impact: str,
    confidence: str,
    actionability: str = "high",
) -> dict[str, str]:
    return {
        "title": title,
        "evidence": evidence,
        "explanation": explanation,
        "action": action,
        "impact": impact,
        "confidence": confidence,
        "actionability": actionability,
    }


def build_recommendations(analysis: dict[str, Any], language: str = "ru") -> dict[str, Any]:
    def tr(ru: str, en: str) -> str:
        return ru if language == "ru" else en

    overview = analysis["overview"]
    matches = int(overview.get("matches") or 0)
    winrate = overview.get("winrate")
    deaths = overview.get("deaths")
    candidates: list[dict[str, str]] = []
    strengths: list[str] = []
    breakdown: list[dict[str, Any]] = []

    form_score = _clamp(5 + ((winrate or 50) - 50) / 4) if winrate is not None else None
    if form_score is not None:
        breakdown.append(
            {
                "name": tr("Текущая форма", "Current form"),
                "score": form_score,
                "confidence": "high" if matches >= 50 else "medium" if matches >= 20 else "low",
                "explanation": tr(
                    f"{winrate}% WR на {matches} матчах выбранного периода.",
                    f"{winrate}% WR across {matches} matches in the selected period.",
                ),
            }
        )
        if matches >= 20 and winrate >= 52:
            strengths.append(tr(f"Положительная форма: {winrate}% WR на большой выборке из {matches} матчей.", f"Positive form: {winrate}% WR across a substantial sample of {matches} matches."))

    death_losses = analysis["deaths"].get("losses")
    death_wins = analysis["deaths"].get("wins")
    bucket_10 = next((row for row in analysis["deaths"]["buckets"] if row["name"] == "10+"), None)
    survival_score = _clamp(10 - max(0, (deaths or 4) - 4) * 0.85) if deaths is not None else None
    if survival_score is not None:
        breakdown.append(
            {
                "name": tr("Выживаемость и позиционирование", "Survivability and positioning"),
                "score": survival_score,
                "confidence": "high" if matches >= 20 else "low",
                "explanation": tr(
                    f"В среднем {deaths} смертей; {death_wins} в победах и {death_losses} в поражениях.",
                    f"{deaths} deaths on average; {death_wins} in wins and {death_losses} in losses.",
                ),
            }
        )
    if deaths is not None and deaths >= 8 and death_losses is not None:
        evidence = tr(
            f"В среднем {deaths} смертей; в победах {death_wins}, в поражениях {death_losses}.",
            f"{deaths} deaths on average; {death_wins} in wins and {death_losses} in losses.",
        )
        if bucket_10 and bucket_10["matches"] >= 5:
            evidence += tr(
                f" При 10+ смертях WR падает до {bucket_10['winrate']}% на {bucket_10['matches']} матчах.",
                f" At 10+ deaths, WR falls to {bucket_10['winrate']}% across {bucket_10['matches']} matches.",
            )
        candidates.append(
            _priority(
                tr("Слишком много смертей", "Too many deaths"),
                evidence,
                tr(
                    "Смерти не просто портят KDA: они отдают сопернику темп и выключают тебя из фарма, защиты и ключевых objectives.",
                    "Deaths do more than hurt KDA: they give away tempo and remove you from farming, defense, and key objectives.",
                ),
                tr(
                    "На следующие 30 игр держать цель ≤7 смертей. В каждом поражении с 10+ смертями разобрать момент за 20–30 секунд до трёх последних смертей.",
                    "For the next 30 games, target ≤7 deaths. In every loss with 10+ deaths, review the 20–30 seconds before the final three deaths.",
                ),
                impact="high",
                confidence="high" if matches >= 20 else "low",
            )
        )
    elif deaths is not None:
        strengths.append(tr(f"Контроль смертей: в среднем {deaths} за матч.", f"Death control: {deaths} per match on average."))

    heroes = analysis.get("heroes", [])
    reliable_heroes = [hero for hero in heroes if hero["matches"] >= 10]
    main_hero = heroes[0] if heroes else None
    hero_score = None
    if main_hero and main_hero.get("winrate") is not None:
        concentration = float(main_hero.get("pick_rate") or 0)
        hero_score = _clamp(5 + (main_hero["winrate"] - 50) / 6 + min(2, concentration / 25))
        breakdown.append(
            {
                "name": tr("Пул и мастерство героев", "Hero pool and mastery"),
                "score": hero_score,
                "confidence": main_hero["confidence"],
                "explanation": tr(
                    f"Главный герой {main_hero['name']}: {main_hero['matches']} матчей, {main_hero['winrate']}% WR, доля {main_hero['pick_rate']}%.",
                    f"Main hero {main_hero['name']}: {main_hero['matches']} matches, {main_hero['winrate']}% WR, {main_hero['pick_rate']}% share.",
                ),
            }
        )
        if main_hero["matches"] >= 10 and main_hero["winrate"] >= 54:
            strengths.append(
                tr(
                    f"Главный рабочий герой — {main_hero['name']}: {main_hero['matches']} матчей и {main_hero['winrate']}% WR.",
                    f"The main proven hero is {main_hero['name']}: {main_hero['matches']} matches and {main_hero['winrate']}% WR.",
                )
            )

    if main_hero and main_hero["matches"] >= 15 and matches > main_hero["matches"]:
        rest_matches = matches - main_hero["matches"]
        rest_wins = int(overview["wins"]) - int(main_hero["wins"])
        rest_wr = round(rest_wins / rest_matches * 100, 2) if rest_matches else None
        if rest_wr is not None and main_hero["winrate"] - rest_wr >= 5:
            candidates.append(
                _priority(
                    tr("Результат проседает вне основного героя", "Results drop outside the main hero"),
                    tr(
                        f"{main_hero['name']}: {main_hero['winrate']}% WR на {main_hero['matches']} матчах; остальные герои вместе: {rest_wr}% на {rest_matches} матчах.",
                        f"{main_hero['name']}: {main_hero['winrate']}% WR across {main_hero['matches']} matches; all other heroes combined: {rest_wr}% across {rest_matches} matches.",
                    ),
                    tr(
                        "Основной герой уже приносит результат, а расширение пула снижает средний итог. Это управляемый источник потери WR.",
                        "The main hero already produces results, while expanding the pool lowers the average outcome. This is a controllable source of lost WR.",
                    ),
                    tr(
                        f"Собрать ranked-пул из {main_hero['name']} и ещё 2–3 героев с лучшей свежей статистикой. Остальных проверять вне ranked или после отдельного replay-разбора.",
                        f"Build a ranked pool around {main_hero['name']} plus 2–3 heroes with the best recent evidence. Test the rest outside ranked or after dedicated replay review.",
                    ),
                    impact="high",
                    confidence="high" if rest_matches >= 30 else "medium",
                )
            )

    weak_hero = next(
        (
            hero
            for hero in heroes
            if hero["matches"] >= 5
            and hero.get("winrate") is not None
            and winrate is not None
            and hero["winrate"] <= winrate - 10
        ),
        None,
    )
    if weak_hero:
        candidates.append(
            _priority(
                tr("Проверить убыточного героя", "Review a losing hero"),
                tr(f"{weak_hero['name']}: {weak_hero['matches']} матчей, {weak_hero['winrate']}% WR, KDA {weak_hero['kda']}.", f"{weak_hero['name']}: {weak_hero['matches']} matches, {weak_hero['winrate']}% WR, {weak_hero['kda']} KDA."),
                tr("Выборка ещё не доказывает, что герой тебе не подходит, но уже достаточна для проверки решений и билда.", "The sample does not prove that the hero is unsuitable, but it is enough to review decisions and builds."),
                tr(f"Поставить {weak_hero['name']} на паузу в ranked на 20 игр и разобрать минимум 3 поражения перед возвратом.", f"Pause {weak_hero['name']} in ranked for 20 games and review at least three losses before returning."),
                impact="medium",
                confidence=weak_hero["confidence"],
            )
        )

    consistency = analysis["consistency"].get("score")
    if consistency is not None:
        breakdown.append(
            {
                "name": tr("Стабильность", "Consistency"),
                "score": consistency,
                "confidence": analysis["consistency"]["confidence"],
                "explanation": tr("Оценка разброса kills, deaths и KDA между матчами.", "Variation in kills, deaths, and KDA between matches."),
            }
        )
        if consistency < 5.5 and matches >= 20:
            candidates.append(
                _priority(
                    tr("Высокий разброс качества игр", "High game-to-game variance"),
                    tr(f"Consistency score: {consistency}/10 на {matches} матчах.", f"Consistency score: {consistency}/10 across {matches} matches."),
                    tr("Сильные матчи чередуются с тяжёлыми провалами. Для роста WR важнее поднять нижнюю границу игры, чем искать ещё более яркие победы.", "Strong matches alternate with heavy drop-offs. Raising the floor matters more for WR than producing even bigger wins."),
                    tr("На 30 игр выбрать один показатель контроля: смерти. Считать успешной игру, где цель по смертям выполнена, даже если матч проигран.", "For 30 games, track one control metric: deaths. Count a game as process-successful when the death target is met, even in a loss."),
                    impact="high",
                    confidence=analysis["consistency"]["confidence"],
                )
            )
        elif consistency >= 7:
            strengths.append(tr(f"Стабильность результатов: {consistency}/10.", f"Performance consistency: {consistency}/10."))

    time_rows = [row for row in analysis.get("time_of_day", []) if row["matches"] >= 10 and row.get("winrate") is not None]
    if time_rows and winrate is not None:
        best_time = max(time_rows, key=lambda row: row["winrate"])
        worst_time = min(time_rows, key=lambda row: row["winrate"])
        if best_time["winrate"] >= winrate + 5:
            strengths.append(
                tr(
                    f"Лучшее окно по текущей выборке — {best_time['name']}: {best_time['winrate']}% WR на {best_time['matches']} матчах.",
                    f"The best current time window is {best_time['name']}: {best_time['winrate']}% WR across {best_time['matches']} matches.",
                )
            )
        if worst_time["winrate"] <= winrate - 8:
            candidates.append(
                _priority(
                    tr("Неудачное время для ranked", "Poor ranked time window"),
                    tr(f"В интервале {worst_time['name']} WR {worst_time['winrate']}% на {worst_time['matches']} матчах против общего {winrate}%.", f"During {worst_time['name']}, WR is {worst_time['winrate']}% across {worst_time['matches']} matches versus {winrate}% overall."),
                    tr("Это корреляция, а не доказанная причина, но разница достаточно велика для безопасного практического теста.", "This is correlation, not proven causation, but the gap is large enough for a safe practical test."),
                    tr(f"На следующие 25 ranked-игр не начинать очередь в {worst_time['name']} по настроенной локальной зоне; затем сравнить WR заново.", f"For the next 25 ranked games, avoid queueing during {worst_time['name']} in the configured local timezone, then compare WR again."),
                    impact="medium",
                    confidence=worst_time["confidence"],
                )
            )

    duration_rows = [row for row in analysis.get("duration", []) if row["matches"] >= 10 and row.get("winrate") is not None]
    late = next((row for row in duration_rows if row["name"] == "55+"), None)
    late_score = None
    if late and winrate is not None:
        late_score = _clamp(5 + (late["winrate"] - winrate) / 5)
        breakdown.append(
            {
                "name": tr("Решения в поздней игре", "Late-game decisions"),
                "score": late_score,
                "confidence": late["confidence"],
                "explanation": tr(f"В матчах 55+ минут WR {late['winrate']}%, смерти {late['deaths']} на {late['matches']} играх.", f"In 55+ minute matches, WR is {late['winrate']}% with {late['deaths']} deaths across {late['matches']} games."),
            }
        )
        if late["winrate"] <= winrate - 8:
            candidates.append(
                _priority(
                    tr("Провал в очень длинных матчах", "Drop-off in very long matches"),
                    tr(f"Матчи 55+ минут: {late['winrate']}% WR и {late['deaths']} смертей в среднем на {late['matches']} играх.", f"55+ minute matches: {late['winrate']}% WR and {late['deaths']} average deaths across {late['matches']} games."),
                    tr("Чем дольше матч, тем дороже одна смерть и тем важнее buyback, позиция до драки и выбор objective.", "The longer the match, the more expensive each death becomes, and the more buyback, pre-fight positioning, and objective choice matter."),
                    tr("Разбирать все поражения 55+ минут: последнюю смерть, наличие buyback и решение команды за минуту до неё. После 40-й минуты не заходить в тёмную зону первым.", "Review every 55+ minute loss: the final death, buyback status, and the team's decision one minute before it. After minute 40, do not enter dark areas first."),
                    impact="high",
                    confidence=late["confidence"],
                )
            )

    fatigue = analysis["sessions"].get("fatigue_delta")
    after_two_losses = analysis["streaks"].get("after_2_loss", {})
    session_score = 6.0
    session_evidence = tr("Данных об играх 6+ в сессии недостаточно.", "There is not enough data for game 6+ sessions.")
    if fatigue is not None:
        session_score = _clamp(5 + fatigue / 5)
        session_evidence = tr(f"Разница WR игр 6+ к первым трём: {fatigue} п.п.", f"Game 6+ versus first-three WR delta: {fatigue} pp.")
    elif after_two_losses.get("matches", 0) >= 10 and winrate is not None:
        delta = float(after_two_losses["winrate"]) - float(winrate)
        session_score = _clamp(5 + delta / 5)
        session_evidence = tr(f"После двух поражений следующий WR {after_two_losses['winrate']}% на {after_two_losses['matches']} случаях.", f"After two losses, next-match WR is {after_two_losses['winrate']}% across {after_two_losses['matches']} cases.")
        if after_two_losses["winrate"] >= winrate:
            strengths.append(tr("По текущей выборке нет признака автоматического tilt-провала после двух поражений подряд.", "The current sample does not show an automatic tilt collapse after two consecutive losses."))
    breakdown.append({"name": tr("Дисциплина сессий", "Session discipline"), "score": session_score, "confidence": "medium" if matches >= 20 else "low", "explanation": session_evidence})

    if fatigue is not None and fatigue <= -8:
        candidates.append(
            _priority(
                tr("Усталость в длинных сессиях", "Fatigue in long sessions"),
                tr(f"WR первых трёх игр {analysis['sessions']['first_3_wr']}%, игр 6+ {analysis['sessions']['game_6_plus_wr']}%; разница {fatigue} п.п.", f"First-three WR is {analysis['sessions']['first_3_wr']}%, game 6+ WR is {analysis['sessions']['game_6_plus_wr']}%; a {fatigue} pp gap."),
                tr("Качество решений снижается по мере продолжения сессии.", "Decision quality declines as the session continues."),
                tr("Ограничить ranked-сессию пятью матчами и завершать её после двух поражений подряд.", "Limit ranked sessions to five matches and stop after two consecutive losses."),
                impact="high",
                confidence="medium",
            )
        )

    if analysis["trend"].get("direction") == "declining":
        candidates.append(
            _priority(
                tr("Форма снижается", "Declining form"),
                tr("Последний сегмент периода слабее первого по WR.", "The final period segment has a lower WR than the first."),
                tr("Это повод временно упростить пул и процесс принятия решений.", "This is a reason to temporarily simplify the pool and decision process."),
                tr("На 15 игр оставить только основной пул и одну измеримую цель, затем повторить срез.", "For 15 games, use only the main pool and one measurable goal, then rerun the analysis."),
                impact="medium",
                confidence="medium",
            )
        )

    # Keep every coaching report useful even when no negative threshold fires.
    # These are maintenance experiments tied to the observed baseline, not invented leaks.
    if len(candidates) < 3 and main_hero:
        candidates.append(
            _priority(
                tr("Закрепить доказанный пул", "Lock in the proven pool"),
                tr(f"Самый частый герой {main_hero['name']}: {main_hero['matches']} матчей, {main_hero['winrate']}% WR.", f"Most-played hero {main_hero['name']}: {main_hero['matches']} matches, {main_hero['winrate']}% WR."),
                tr("Даже без явного провала на других героях стабильный основной пул упрощает решения и делает следующий срез сравнимым.", "Even without a clear failure on other heroes, a stable core pool simplifies decisions and makes the next report comparable."),
                tr(f"На следующие 30 игр держать {main_hero['name']} и ещё 2–3 заранее выбранных героя минимум в 70% ranked-матчей.", f"For the next 30 games, use {main_hero['name']} plus 2–3 preselected heroes in at least 70% of ranked matches."),
                impact="medium",
                confidence=main_hero["confidence"],
            )
        )
    if len(candidates) < 3 and deaths is not None:
        maintenance_target = max(3, round(deaths))
        candidates.append(
            _priority(
                tr("Стабилизировать контроль смертей", "Stabilize death control"),
                tr(f"Текущий baseline — {deaths} смертей в среднем и медиана {overview.get('median_deaths')}.", f"The current baseline is {deaths} average deaths with a {overview.get('median_deaths')} median."),
                tr("Даже если смерти не достигли критического порога, стабильный лимит снижает разброс качества матчей.", "Even when deaths are below the critical threshold, a stable limit reduces game-to-game variance."),
                tr(f"На 30 игр удерживать большинство матчей на уровне ≤{maintenance_target} смертей и отдельно отмечать превышения.", f"For 30 games, keep most matches at ≤{maintenance_target} deaths and flag every overrun."),
                impact="medium",
                confidence="high" if matches >= 20 else "low",
            )
        )
    if len(candidates) < 3 and matches >= 20:
        candidates.append(
            _priority(
                tr("Зафиксировать измеримый baseline", "Lock in a measurable baseline"),
                tr(f"Текущий срез: {matches} матчей, {winrate}% WR, KDA {overview.get('kda')}, deaths {deaths}.", f"Current baseline: {matches} matches, {winrate}% WR, {overview.get('kda')} KDA, {deaths} deaths."),
                tr("Без фиксированной контрольной точки невозможно понять, помогли ли изменения, или результат изменился случайно.", "Without a fixed checkpoint, it is impossible to tell whether changes helped or the result moved randomly."),
                tr("Не менять правила плана 30 игр, затем сравнить WR, deaths, основной пул и consistency с этим baseline.", "Keep the plan unchanged for 30 games, then compare WR, deaths, main pool, and consistency with this baseline."),
                impact="low",
                confidence="high" if matches >= 50 else "medium",
            )
        )

    candidates.sort(
        key=lambda item: (
            IMPACT_WEIGHT[item["impact"]],
            CONFIDENCE_WEIGHT[item["confidence"]],
            IMPACT_WEIGHT.get(item["actionability"], 1),
        ),
        reverse=True,
    )
    if not candidates:
        candidates.append(
            _priority(
                tr("Нет подтверждённого крупного leak", "No confirmed major leak"),
                tr(f"Проанализировано {matches} матчей; сильный проблемный порог не сработал.", f"{matches} matches were analyzed; no strong problem threshold was triggered."),
                tr("Это не означает, что ошибок нет: публичная статистика не заменяет replay-анализ.", "This does not mean there are no mistakes: public statistics do not replace replay review."),
                tr("Собрать ещё 20–50 матчей с одной ролью и повторить анализ.", "Collect another 20–50 matches on one role and rerun the analysis."),
                impact="low",
                confidence="low",
            )
        )

    if not strengths:
        strengths.append(tr("Выборка пока не подтверждает отдельную сильную сторону с достаточной уверенностью.", "The sample does not yet confirm a distinct strength with enough confidence."))

    weights = {
        tr("Текущая форма", "Current form"): 0.25,
        tr("Выживаемость и позиционирование", "Survivability and positioning"): 0.20,
        tr("Пул и мастерство героев", "Hero pool and mastery"): 0.20,
        tr("Стабильность", "Consistency"): 0.15,
        tr("Дисциплина сессий", "Session discipline"): 0.10,
        tr("Решения в поздней игре", "Late-game decisions"): 0.10,
    }
    weighted = [(float(row["score"]), weights.get(row["name"], 0.1)) for row in breakdown if row.get("score") is not None]
    overall_score = round(sum(score * weight for score, weight in weighted) / sum(weight for _, weight in weighted), 1) if weighted else None
    if overall_score is None:
        label = tr("Недостаточно данных", "Not enough data")
    elif overall_score >= 8:
        label = tr("Очень сильная текущая форма", "Very strong current form")
    elif overall_score >= 6.5:
        label = tr("Сильная форма с точечными утечками", "Strong form with specific leaks")
    elif overall_score >= 5:
        label = tr("Средняя форма с понятным потенциалом роста", "Average form with clear growth potential")
    else:
        label = tr("Нестабильная форма — нужен упрощённый план", "Unstable form — simplify the plan")

    top = candidates[:5]
    strongest = strengths[0]
    biggest = top[0]
    coach_summary = tr(
        f"Текущий результат — {winrate}% WR. Главный плюс: {strongest} Главный резерв роста: {biggest['title'].lower()}. Для повышения WR не нужно менять всё сразу: первые 30 игр сфокусируйся на действии «{biggest['action']}».",
        f"The current result is {winrate}% WR. Main strength: {strongest} The largest growth lever is {biggest['title'].lower()}. Do not change everything at once: for the first 30 games, focus on “{biggest['action']}”.",
    )

    best_pool = [hero["name"] for hero in heroes if hero["matches"] >= 5 and hero.get("winrate") is not None and hero["winrate"] >= (winrate or 50)][:4]
    plan_30 = {
        "main_focus": biggest["title"],
        "death_target": 7 if deaths is not None and deaths >= 8 else round(deaths) if deaths is not None else None,
        "ranked_pool": best_pool or ([main_hero["name"]] if main_hero else []),
        "session_limit": 5,
        "stop_loss": 2,
        "avoid_time": next((row["name"] for row in time_rows if winrate is not None and row["winrate"] <= winrate - 8), None),
        "mandatory_review": tr("Все поражения с 10+ смертями и все поражения 55+ минут", "Every loss with 10+ deaths and every 55+ minute loss"),
        "checkpoint": tr("Повторный срез после 30 игр", "Rerun the report after 30 games"),
    }
    plan_100 = {
        "hero_pool": min(4, max(2, len(best_pool))) if heroes else None,
        "maximum_ranked_games_per_session": 5,
        "stop_loss": 2,
        "deaths_target": plan_30["death_target"],
        "replay_review": plan_30["mandatory_review"],
        "main_metric": biggest["title"],
        "secondary_metric": tr("WR на основном пуле", "WR on the main pool"),
        "baseline_matches": matches,
    }

    return {
        "overall_rating": {
            "score": overall_score,
            "label": label,
            "confidence": "high" if matches >= 50 else "medium" if matches >= 20 else "low",
            "explanation": tr("Это оценка текущей эффективности по доступной статистике, а не ранг и не оценка чистой механики.", "This is a current-efficiency rating from available statistics, not a rank or a pure mechanics score."),
        },
        "rating_breakdown": breakdown,
        "coach_summary": coach_summary,
        "strengths": strengths[:4],
        "weaknesses": [item["explanation"] for item in top[:4]],
        "top_leaks": top,
        "quick_actions": [item["action"] for item in top[:3]],
        "what_to_stop": [item["action"] for item in top[:3]],
        "what_to_start": [tr("Перед каждой сессией выбрать одну цель и записать результат после неё.", "Choose one goal before each session and record the result afterward."), tr("Разбирать решение до смерти, а не только сам момент смерти.", "Review the decision before each death, not only the death itself.")],
        "what_to_keep": strengths[:3],
        "next_30_games_plan": plan_30,
        "next_100_ranked_plan": plan_100,
    }
