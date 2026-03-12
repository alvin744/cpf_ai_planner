from core.models import MemberProfile
from services.retirement_service import run_retirement_analysis


def main():
    print("=== CPF AI Retirement Planner ===\n")

    member = MemberProfile(
        age=30,
        retirement_age=65,
        monthly_salary=5000,
        monthly_spending=3000,
        starting_oa=80000,
        starting_sa=30000,
        starting_ma=10000,
        annual_salary_growth=0.03,
        annual_inflation_rate=0.02,
        years_in_retirement=25
    )

    (
        projection,
        payout,
        shortfall,
        avg_payout,
        advice,
        nudges,
        optimization_result,
        ml_risk_label,
        ml_risk_probs
    ) = run_retirement_analysis(member)

    print("--- CPF Projection (Deterministic) ---")
    print(f"OA Balance: {projection['oa_balance']:,.2f}")
    print(f"SA Balance: {projection['sa_balance']:,.2f}")
    print(f"MA Balance: {projection['ma_balance']:,.2f}")
    print(f"Total Balance: {projection['total_balance']:,.2f}")
    print(f"Estimated Monthly Payout: {payout:,.2f}")
    print(f"Expected Monthly Spending: {member.monthly_spending}")

    if payout >= member.monthly_spending:
        print("Status: Sufficient")
    else:
        print("Status: Potential shortfall")

    print()
    print("--- Retirement Simulation (Monte Carlo) ---")
    print(f"Probability of shortfall: {shortfall * 100:.1f}%")
    print(f"Average monthly payout: {avg_payout:,.2f}")

    print()
    print("--- AI Advice ---")
    for item in advice:
        print("-", item)

    print()
    print("--- AI Nudges ---")
    for item in nudges:
        print("-", item)

    print()
    print("--- Strategy Optimizer ---")
    best = optimization_result["best_strategy"]
    base_shortfall = optimization_result["base_shortfall"]

    print("Best strategy found:")

    if best["extra_savings"] > 0:
        print(f"- Increase savings by ${best['extra_savings']}/month")
    if best["delay_years"] > 0:
        print(f"- Delay retirement by {best['delay_years']} years")
    if best["spending_cut_pct"] > 0:
        print(f"- Reduce retirement spending by {best['spending_cut_pct']:.0f}%")

    if (
        best["extra_savings"] == 0
        and best["delay_years"] == 0
        and best["spending_cut_pct"] == 0
    ):
        print("- No change needed")

    print(f"\nShortfall probability improves from {base_shortfall * 100:.1f}% to {best['new_shortfall'] * 100:.1f}%")
    print(f"Average monthly payout under best strategy: {best['new_avg_payout']:,.2f}")

    print()
    print("--- ML Risk Assessment ---")

    # Determine highest probability class
    top_class = max(ml_risk_probs, key=ml_risk_probs.get)
    top_prob = ml_risk_probs[top_class]

    # Confidence threshold
    CONFIDENCE_THRESHOLD = 0.70

    if top_prob >= CONFIDENCE_THRESHOLD:
        print(f"ML pattern assessment: {top_class.upper()}")
    else:
        print("ML pattern assessment: MIXED")
        print("Model confidence is mixed. Simulation remains the primary risk estimate.")

    print(
        "Risk probabilities:",
        ", ".join(
            [f"{k}={v * 100:.1f}%" for k, v in sorted(ml_risk_probs.items())]
        )
    )


if __name__ == "__main__":
    main()