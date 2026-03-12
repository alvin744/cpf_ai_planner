from core.projection import project_cpf
from core.payout import estimate_cpf_life_payout, get_payout_over_retirement_years
from simulation.monte_carlo import run_retirement_simulation
from ai.advisor import generate_advice
from ai.nudging import generate_nudges
from ai.optimizer import optimize_strategy
from ai.ml_model import predict_risk
from services.payout_solver import analyze_payout_gap


def run_retirement_analysis(member):
    projection = project_cpf(member)

    brs = projection["brs"]
    frs = projection["frs"]
    ers = projection["ers"]

    payout = estimate_cpf_life_payout(
        projection["ra_at_payout_start"],
        member.cpf_life_plan,
        brs,
        frs,
        ers,
        member.payout_start_age
    )

    payout_series = get_payout_over_retirement_years(
        payout,
        member.years_in_retirement,
        member.cpf_life_plan
    )

    years_to_payout_start = max(member.payout_start_age - member.age, 0)
    inflated_spending_at_payout_start = member.monthly_spending * (
        (1 + member.annual_inflation_rate) ** years_to_payout_start
    )

    probability_shortfall, avg_payout = run_retirement_simulation(
        member,
        seed=42
    )

    optimization_result = optimize_strategy(
        member,
        probability_shortfall
    )

    advice = generate_advice(
        payout,
        member.monthly_spending,
        inflated_spending_at_payout_start,
        probability_shortfall,
        member.payout_start_age
    )

    nudges = generate_nudges(
        member,
        probability_shortfall,
        optimization_result=optimization_result
    )

    ml_risk_label, ml_risk_probs = predict_risk(member)

    gap_analysis = analyze_payout_gap(
        projection["ra_at_payout_start"],
        inflated_spending_at_payout_start,
        brs,
        frs,
        ers,
        member.payout_start_age
    )

    return {
        "projection": projection,
        "payout": payout,
        "payout_series": payout_series,
        "inflated_spending_at_payout_start": inflated_spending_at_payout_start,
        "shortfall": probability_shortfall,
        "avg_payout": avg_payout,
        "advice": advice,
        "nudges": nudges,
        "optimization_result": optimization_result,
        "ml_risk_label": ml_risk_label,
        "ml_risk_probs": ml_risk_probs,
        "gap_analysis": gap_analysis,
    }