REFERENCE_BRS_2026 = 110_200.0
REFERENCE_FRS_2026 = 220_400.0
REFERENCE_ERS_2026 = 440_800.0


def get_plan_public_description(plan):
    if plan == "Standard":
        return "Steady monthly payouts for life."
    elif plan == "Basic":
        return "Lower starting payouts that may decline later."
    elif plan == "Escalating":
        return "Lower starting payouts that grow by 2% yearly."
    return ""


def get_deferral_multiplier(payout_start_age: int) -> float:
    years_deferred = max(int(payout_start_age) - 65, 0)
    return 1 + (0.05 * years_deferred)


def get_scaled_anchor_payouts(brs, frs, ers, payout_start_age):
    """
    Backward-compatible helper for older files that still import this function.
    Returns approximate monthly payout anchors for Standard plan.
    """
    deferral_multiplier = get_deferral_multiplier(payout_start_age)

    return {
        "brs": (brs * 0.078 / 12) * deferral_multiplier,
        "frs": (frs * 0.078 / 12) * deferral_multiplier,
        "ers": (ers * 0.078 / 12) * deferral_multiplier,
    }


def estimate_cpf_life_payout(ra_balance, plan, brs, frs, ers, payout_start_age):
    """
    Public-facing approximation:
    Monthly payout ~= RA balance * annual payout factor / 12,
    then adjusted by payout start age.
    """
    if ra_balance <= 0:
        return 0.0

    if plan == "Standard":
        annual_factor = 0.078
    elif plan == "Basic":
        annual_factor = 0.068
    elif plan == "Escalating":
        annual_factor = 0.062
    else:
        annual_factor = 0.078

    base_monthly = ra_balance * annual_factor / 12
    age_adjusted = base_monthly * get_deferral_multiplier(payout_start_age)
    return age_adjusted


def get_payout_over_retirement_years(starting_monthly_payout, years_in_retirement, plan="Standard"):
    payout_series = []

    for year in range(years_in_retirement + 1):
        if plan == "Standard":
            payout = starting_monthly_payout
        elif plan == "Escalating":
            payout = starting_monthly_payout * ((1.02) ** year)
        elif plan == "Basic":
            if year <= 25:
                payout = starting_monthly_payout
            else:
                decline_years = year - 25
                payout = starting_monthly_payout * ((0.985) ** decline_years)
        else:
            payout = starting_monthly_payout

        payout_series.append(payout)

    return payout_series