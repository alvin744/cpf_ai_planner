import math

PLANNER_BASE_YEAR = 2026

KNOWN_RETIREMENT_SUMS = {
    2025: {"brs": 106_500.0, "frs": 213_000.0, "ers": 426_000.0},
    2026: {"brs": 110_200.0, "frs": 220_400.0, "ers": 440_800.0},
    2027: {"brs": 114_100.0, "frs": 228_200.0, "ers": 456_400.0},
}

KNOWN_BHS = {
    2026: 79_000.0,
}

CPF_OW_CEILING = 8_000.0


def round_total_cpf(amount):
    return math.floor(amount + 0.5)


def get_retirement_sum_year(age):
    years_to_55 = 55 - int(age)
    return PLANNER_BASE_YEAR + years_to_55


def get_bhs_fix_year(age):
    years_to_65 = 65 - int(age)
    return PLANNER_BASE_YEAR + years_to_65


def get_retirement_sums_for_year(turn55_year, inflation_assumption):
    if turn55_year in KNOWN_RETIREMENT_SUMS:
        return KNOWN_RETIREMENT_SUMS[turn55_year]

    if turn55_year < 2025:
        return KNOWN_RETIREMENT_SUMS[2025]

    years_after_2027 = turn55_year - 2027
    growth = max(float(inflation_assumption), 0.0)

    brs = KNOWN_RETIREMENT_SUMS[2027]["brs"] * ((1 + growth) ** years_after_2027)
    frs = brs * 2
    ers = brs * 4

    return {"brs": brs, "frs": frs, "ers": ers}


def get_bhs_for_year(target_year, inflation_assumption):
    if target_year in KNOWN_BHS:
        return KNOWN_BHS[target_year]

    if target_year < 2026:
        return KNOWN_BHS[2026]

    years_after_2026 = target_year - 2026
    growth = max(float(inflation_assumption), 0.0)
    return KNOWN_BHS[2026] * ((1 + growth) ** years_after_2026)


def get_allocation_rates(age):
    if age <= 35:
        return {"oa": 0.6217, "sa": 0.1621, "ma": 0.2162}
    elif age <= 45:
        return {"oa": 0.5677, "sa": 0.1891, "ma": 0.2432}
    elif age <= 50:
        return {"oa": 0.5136, "sa": 0.2162, "ma": 0.2702}
    elif age < 55:
        return {"oa": 0.4055, "sa": 0.3108, "ma": 0.2837}
    elif age <= 60:
        return {"oa": 0.3530, "ra": 0.3382, "ma": 0.3088}
    elif age <= 65:
        return {"oa": 0.14, "ra": 0.44, "ma": 0.42}
    elif age <= 70:
        return {"oa": 0.0607, "ra": 0.303, "ma": 0.6363}
    else:
        return {"oa": 0.08, "ra": 0.08, "ma": 0.84}


def get_monthly_total_cpf_contribution(age, monthly_wage):
    wage = float(monthly_wage)

    if wage <= 50:
        total = 0.0
    elif age <= 55:
        if wage <= 500:
            total = 0.17 * wage
        elif wage <= 750:
            total = 0.17 * wage + 0.60 * (wage - 500)
        else:
            total = 0.37 * min(wage, CPF_OW_CEILING)
    elif age <= 60:
        if wage <= 500:
            total = 0.16 * wage
        elif wage <= 750:
            total = 0.16 * wage + 0.54 * (wage - 500)
        else:
            total = 0.34 * min(wage, CPF_OW_CEILING)
    elif age <= 65:
        if wage <= 500:
            total = 0.125 * wage
        elif wage <= 750:
            total = 0.125 * wage + 0.375 * (wage - 500)
        else:
            total = 0.25 * min(wage, CPF_OW_CEILING)
    elif age <= 70:
        if wage <= 500:
            total = 0.09 * wage
        elif wage <= 750:
            total = 0.09 * wage + 0.225 * (wage - 500)
        else:
            total = 0.165 * min(wage, CPF_OW_CEILING)
    else:
        if wage <= 500:
            total = 0.075 * wage
        elif wage <= 750:
            total = 0.075 * wage + 0.15 * (wage - 500)
        else:
            total = 0.125 * min(wage, CPF_OW_CEILING)

    return float(round_total_cpf(total))


def create_ra(oa, sa, ra, frs):
    needed = max(frs - ra, 0.0)

    transfer_sa = min(sa, needed)
    sa -= transfer_sa
    ra += transfer_sa

    needed = max(frs - ra, 0.0)

    transfer_oa = min(oa, needed)
    oa -= transfer_oa
    ra += transfer_oa

    oa += sa
    sa = 0.0

    return oa, sa, ra


def route_ma_overflow(age, overflow, oa, sa, ra, frs):
    if overflow <= 0:
        return oa, sa, ra

    if age < 55:
        if sa < frs:
            sa_room = frs - sa
            to_sa = min(overflow, sa_room)
            sa += to_sa
            overflow -= to_sa
        oa += overflow
    else:
        if ra < frs:
            ra_room = frs - ra
            to_ra = min(overflow, ra_room)
            ra += to_ra
            overflow -= to_ra
        oa += overflow

    return oa, sa, ra


def project_cpf(member):
    age = int(member.age)
    end_age = max(int(member.retirement_age), int(member.payout_start_age))

    retirement_sum_year = get_retirement_sum_year(member.age)
    sums = get_retirement_sums_for_year(retirement_sum_year, member.annual_inflation_rate)
    brs = sums["brs"]
    frs = sums["frs"]
    ers = sums["ers"]

    bhs_fix_year = get_bhs_fix_year(member.age)
    bhs_at_65 = get_bhs_for_year(bhs_fix_year, member.annual_inflation_rate)

    oa = float(member.starting_oa)
    sa = float(member.starting_sa)
    ma = float(member.starting_ma)
    ra = 0.0

    salary = float(member.monthly_salary)

    ra_created = False
    ra_at_55 = 0.0
    ra_at_payout = 0.0

    history = []

    while age < end_age:
        current_year = PLANNER_BASE_YEAR + (age - int(member.age))
        applicable_bhs = get_bhs_for_year(current_year, member.annual_inflation_rate) if age < 65 else bhs_at_65

        if age == 55 and not ra_created:
            oa, sa, ra = create_ra(oa, sa, ra, frs)
            ra_created = True
            ra_at_55 = ra

        working = age < member.retirement_age

        if working:
            annual_cpf = get_monthly_total_cpf_contribution(age, min(salary, CPF_OW_CEILING)) * 12
            allocation = get_allocation_rates(age)

            ma_contribution = annual_cpf * allocation["ma"]
            ma += ma_contribution

            if ma > applicable_bhs:
                overflow = ma - applicable_bhs
                ma = applicable_bhs
                oa, sa, ra = route_ma_overflow(age, overflow, oa, sa, ra, frs)

            if age < 55:
                sa_contribution = annual_cpf * allocation["sa"]
                sa += sa_contribution

                oa_contribution = annual_cpf - ma_contribution - sa_contribution
                oa += oa_contribution
            else:
                retirement_contribution = annual_cpf * allocation["ra"]

                if ra < frs:
                    needed = frs - ra
                    ra_add = min(retirement_contribution, needed)
                    oa_extra = retirement_contribution - ra_add
                else:
                    ra_add = 0.0
                    oa_extra = retirement_contribution

                ra += ra_add

                oa_contribution = annual_cpf - ma_contribution - retirement_contribution
                oa += oa_contribution + oa_extra

            # Optional realism: OA used for housing / insurance
            oa -= float(member.monthly_oa_housing) * 12
            oa -= float(member.annual_oa_insurance)
            oa = max(oa, 0.0)

        oa *= 1.025

        if age < 55:
            sa *= 1.04
        else:
            ra *= 1.04

        ma *= 1.04
        if ma > applicable_bhs:
            overflow = ma - applicable_bhs
            ma = applicable_bhs
            oa, sa, ra = route_ma_overflow(age, overflow, oa, sa, ra, frs)

        if working:
            salary *= (1 + member.annual_salary_growth)

        age += 1

        if age == member.payout_start_age:
            ra_at_payout = ra

        history.append({
            "age": age,
            "oa_balance": oa,
            "sa_balance": sa,
            "ra_balance": ra,
            "ma_balance": ma,
            "applicable_bhs": applicable_bhs,
            "total_balance": oa + sa + ra + ma
        })

    if ra_at_payout == 0 and member.payout_start_age >= 55:
        ra_at_payout = ra

    if ra_at_payout >= ers:
        level = "ERS"
    elif ra_at_payout >= frs:
        level = "FRS"
    elif ra_at_payout >= brs:
        level = "BRS"
    else:
        level = "Below BRS"

    return {
        "oa_balance": oa,
        "sa_balance": sa,
        "ra_balance": ra,
        "ra_at_55": ra_at_55,
        "ra_at_payout_start": ra_at_payout,
        "ma_balance": ma,
        "bhs_at_65": bhs_at_65,
        "current_bhs_2026": KNOWN_BHS[2026],
        "total_balance": oa + sa + ra + ma,
        "brs": brs,
        "frs": frs,
        "ers": ers,
        "retirement_sum_year": retirement_sum_year,
        "bhs_fix_year": bhs_fix_year,
        "retirement_sum_level": level,
        "yearly_records": history
    }