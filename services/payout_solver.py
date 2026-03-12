from core.payout import get_scaled_anchor_payouts, get_deferral_multiplier


def estimate_required_ra(target_monthly_payout, brs, frs, ers, payout_start_age):
    payouts = get_scaled_anchor_payouts(brs, frs, ers, payout_start_age)

    anchors = [
        (0.0, 0.0),
        (brs, payouts["brs"]),
        (frs, payouts["frs"]),
        (ers, payouts["ers"]),
    ]

    for i in range(len(anchors) - 1):
        ra1, payout1 = anchors[i]
        ra2, payout2 = anchors[i + 1]

        if payout1 <= target_monthly_payout <= payout2:
            slope = (ra2 - ra1) / (payout2 - payout1)
            return ra1 + (target_monthly_payout - payout1) * slope

    ra1, payout1 = anchors[-2]
    ra2, payout2 = anchors[-1]
    slope = (ra2 - ra1) / (payout2 - payout1)
    return ra2 + (target_monthly_payout - payout2) * slope


def analyze_payout_gap(projected_ra_at_payout_start, required_payout, brs, frs, ers, payout_start_age):
    required_ra = estimate_required_ra(
        required_payout,
        brs,
        frs,
        ers,
        payout_start_age
    )
    shortfall_ra = required_ra - projected_ra_at_payout_start

    if required_ra <= brs:
        required_level = "Below BRS"
    elif required_ra <= frs:
        required_level = "BRS/FRS range"
    elif required_ra <= ers:
        required_level = "FRS/ERS range"
    else:
        required_level = "Above ERS"

    return {
        "required_monthly_payout": required_payout,
        "required_ra": required_ra,
        "projected_ra": projected_ra_at_payout_start,
        "ra_shortfall": shortfall_ra,
        "required_retirement_sum_level": required_level,
        "brs": brs,
        "frs": frs,
        "ers": ers,
    }