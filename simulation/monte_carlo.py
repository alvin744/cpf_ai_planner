import copy
import random

from core.projection import project_cpf
from core.payout import estimate_cpf_life_payout


def run_retirement_simulation(member, simulations=1000, seed=None):
    if seed is not None:
        random.seed(seed)

    shortfall_count = 0
    payouts = []

    for _ in range(simulations):
        simulated_member = copy.deepcopy(member)

        simulated_member.annual_salary_growth = max(
            0.0,
            member.annual_salary_growth + random.uniform(-0.02, 0.02)
        )

        simulated_inflation = max(
            0.0,
            member.annual_inflation_rate + random.uniform(-0.01, 0.015)
        )
        simulated_member.annual_inflation_rate = simulated_inflation

        projection = project_cpf(simulated_member)

        payout = estimate_cpf_life_payout(
            projection["ra_at_payout_start"],
            simulated_member.cpf_life_plan,
            projection["brs"],
            projection["frs"],
            projection["ers"],
            simulated_member.payout_start_age
        )
        payouts.append(payout)

        years_to_payout_start = max(simulated_member.payout_start_age - simulated_member.age, 0)
        inflated_spending = simulated_member.monthly_spending * (
            (1 + simulated_inflation) ** years_to_payout_start
        )

        if payout < inflated_spending:
            shortfall_count += 1

    probability_shortfall = shortfall_count / simulations
    avg_payout = sum(payouts) / len(payouts)

    return probability_shortfall, avg_payout