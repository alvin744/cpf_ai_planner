def generate_advice(
    base_payout,
    spending_today,
    inflated_spending_at_payout_start,
    probability_shortfall,
    payout_start_age
):
    advice = []

    if probability_shortfall <= 0.10:
        advice.append(
            f"✅ Probability of shortfall at payout start age ({payout_start_age}): {probability_shortfall * 100:.1f}%"
        )
    elif probability_shortfall <= 0.30:
        advice.append(
            f"⚠ Probability of shortfall at payout start age ({payout_start_age}): {probability_shortfall * 100:.1f}%"
        )
    else:
        advice.append(
            f"🚨 Probability of shortfall at payout start age ({payout_start_age}): {probability_shortfall * 100:.1f}%"
        )

    if base_payout >= inflated_spending_at_payout_start:
        advice.append(
            f"✅ Base projection suggests your estimated CPF LIFE payout at {payout_start_age} can cover your inflation-adjusted spending at {payout_start_age}."
        )
    else:
        advice.append(
            f"⚠ Base projection suggests your estimated CPF LIFE payout at {payout_start_age} may not cover your inflation-adjusted spending at {payout_start_age}."
        )

    if probability_shortfall <= 0.10:
        advice.append(
            "Your CPF-only plan looks resilient even after accounting for inflation and uncertainty."
        )
    elif probability_shortfall <= 0.30:
        advice.append(
            "Your CPF-only plan looks reasonable, but inflation and uncertainty could still create some retirement risk."
        )
        advice.append(
            "💡 Consider moderate CPF-only adjustments such as working slightly longer, increasing contributions, or lowering retirement spending expectations."
        )
    else:
        advice.append(
            "Inflation-adjusted simulation shows a meaningful risk that your CPF LIFE payout may not keep up with your spending target."
        )
        advice.append(
            "💡 Consider stronger CPF-only actions such as delaying work cessation, increasing CPF contributions, or reducing expected retirement spending."
        )

    return advice