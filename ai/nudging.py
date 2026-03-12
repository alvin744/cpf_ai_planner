import copy
from simulation.monte_carlo import run_retirement_simulation


def generate_nudges(member, base_shortfall, optimization_result=None):
    nudges = []

    if optimization_result is not None:
        best = optimization_result["best_strategy"]
        meaningful_improvement = optimization_result["meaningful_improvement"]

        if meaningful_improvement:
            strategy_parts = []

            if best["extra_savings"] > 0:
                strategy_parts.append(f"increasing savings by ${best['extra_savings']}/month")
            if best["delay_years"] > 0:
                strategy_parts.append(f"delaying work stop age by {best['delay_years']} years")
            if best["spending_cut_pct"] > 0:
                strategy_parts.append(f"reducing spending by {best['spending_cut_pct']:.0f}%")

            if strategy_parts:
                joined = ", ".join(strategy_parts)
                nudges.append(
                    f"💡 Strongest tested CPF-only lever: {joined} could reduce shortfall risk by {best['improvement_pct']:.1f}%."
                )

    if base_shortfall <= 0.01:
        if not nudges:
            nudges.append("✅ Your current CPF-only plan already appears strong. No major nudges are needed.")
        return nudges

    strategies = []

    s1 = copy.deepcopy(member)
    s1.monthly_salary += 500
    strategies.append(("Increase savings by $500/month", s1))

    s2 = copy.deepcopy(member)
    s2.retirement_age += 3
    strategies.append(("Delay age you stop working by 3 years", s2))

    s3 = copy.deepcopy(member)
    s3.monthly_spending *= 0.8
    strategies.append(("Reduce retirement spending by 20%", s3))

    for name, scenario_member in strategies:
        new_shortfall, _ = run_retirement_simulation(scenario_member, seed=42)
        improvement = (base_shortfall - new_shortfall) * 100

        if improvement >= 5:
            nudges.append(
                f"💡 Tested nudge: {name} could reduce shortfall risk by {improvement:.1f}%."
            )

    if not nudges:
        nudges.append(
            "ℹ️ No tested CPF-only nudge materially improved the outcome. Your target may be beyond what the currently tested CPF-only changes can support."
        )

    # Deduplicate while preserving order
    unique = []
    seen = set()
    for n in nudges:
        if n not in seen:
            unique.append(n)
            seen.add(n)

    return unique