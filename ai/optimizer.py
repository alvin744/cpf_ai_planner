import copy
from simulation.monte_carlo import run_retirement_simulation


def optimize_strategy(member, base_shortfall):
    scenarios = []

    savings_options = [0, 300, 500, 800]
    retirement_delay_options = [0, 2, 3, 5]
    spending_reduction_options = [0.0, 0.10, 0.20, 0.25]

    for extra_savings in savings_options:
        for delay_years in retirement_delay_options:
            for spending_cut in spending_reduction_options:
                scenario_member = copy.deepcopy(member)

                scenario_member.monthly_salary += extra_savings
                scenario_member.retirement_age += delay_years
                scenario_member.monthly_spending *= (1 - spending_cut)

                new_shortfall, new_avg_payout = run_retirement_simulation(
                    scenario_member,
                    seed=42
                )

                improvement = (base_shortfall - new_shortfall) * 100

                scenarios.append({
                    "extra_savings": extra_savings,
                    "delay_years": delay_years,
                    "spending_cut_pct": spending_cut * 100,
                    "new_shortfall": new_shortfall,
                    "new_avg_payout": new_avg_payout,
                    "improvement_pct": improvement
                })

    best = sorted(
        scenarios,
        key=lambda x: (x["new_shortfall"], -x["new_avg_payout"])
    )[0]

    meaningful_improvement = best["improvement_pct"] >= 5.0

    return {
        "base_shortfall": base_shortfall,
        "best_strategy": best,
        "meaningful_improvement": meaningful_improvement
    }