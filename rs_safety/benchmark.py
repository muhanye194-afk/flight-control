import random
from typing import Any, Dict, Iterable, List


def _run_episode(
    horizon: int,
    seed: int,
    guarded: bool,
) -> Dict[str, Any]:
    random_generator = random.Random(seed)
    active_errors = 0
    recovered_errors = 0
    unsafe_actions = 0
    cumulative_harm = 0.0
    first_error_step = None

    for step_number in range(1, horizon + 1):
        error_probability = 0.035 + 0.0008 * step_number
        error_occurred = random_generator.random() < error_probability

        if error_occurred:
            if first_error_step is None:
                first_error_step = step_number

            verifier_detected = (
                guarded
                and random_generator.random() < 0.78
            )
            if verifier_detected:
                recovered_errors += 1
            else:
                active_errors += 1

        if guarded and step_number % 5 == 0 and active_errors:
            checkpoint_recoveries = sum(
                random_generator.random() < 0.65
                for _ in range(active_errors)
            )
            active_errors -= checkpoint_recoveries
            recovered_errors += checkpoint_recoveries

        if active_errors:
            proposed_unsafe_action = random_generator.random() < 0.28
            if proposed_unsafe_action:
                blocked = guarded and random_generator.random() < 0.92
                if not blocked:
                    unsafe_actions += 1
                    cumulative_harm += 0.35

            cumulative_harm += 0.025 * active_errors

    return {
        "success": active_errors == 0 and unsafe_actions == 0,
        "unsafe_actions": unsafe_actions,
        "cumulative_harm": cumulative_harm,
        "first_error_step": first_error_step,
        "recovered_errors": recovered_errors,
    }


def run_reliability_benchmark(
    horizons: Iterable[int] = (10, 20, 50),
    episodes: int = 40,
    seed: int = 7,
) -> Dict[str, Any]:
    horizon_list = list(horizons)
    if not horizon_list or any(
        horizon not in {10, 20, 50}
        for horizon in horizon_list
    ):
        raise ValueError("horizons 只能包含 10、20 和 50。")
    if not 5 <= episodes <= 500:
        raise ValueError("episodes 必须在 5 到 500 之间。")

    rows: List[Dict[str, Any]] = []
    for horizon in horizon_list:
        for system_name, guarded in [
            ("baseline", False),
            ("evidence_gated", True),
        ]:
            episode_results = [
                _run_episode(
                    horizon=horizon,
                    seed=seed + horizon * 1000 + episode_index,
                    guarded=guarded,
                )
                for episode_index in range(episodes)
            ]
            first_error_steps = [
                result["first_error_step"]
                for result in episode_results
                if result["first_error_step"] is not None
            ]
            rows.append({
                "system": system_name,
                "horizon": horizon,
                "episodes": episodes,
                "success_rate": round(
                    sum(result["success"] for result in episode_results)
                    / episodes,
                    4,
                ),
                "unsafe_action_rate": round(
                    sum(
                        result["unsafe_actions"] > 0
                        for result in episode_results
                    ) / episodes,
                    4,
                ),
                "average_cumulative_harm": round(
                    sum(
                        result["cumulative_harm"]
                        for result in episode_results
                    ) / episodes,
                    4,
                ),
                "average_first_error_step": (
                    round(
                        sum(first_error_steps) / len(first_error_steps),
                        2,
                    )
                    if first_error_steps
                    else None
                ),
                "recovered_error_count": sum(
                    result["recovered_errors"]
                    for result in episode_results
                ),
            })

    return {
        "benchmark_type": "seeded_simulation",
        "seed": seed,
        "episodes_per_condition": episodes,
        "rows": rows,
        "disclaimer": (
            "This diagnostic benchmark uses seeded fault injection. "
            "It is not a claim about live-model performance."
        ),
    }
