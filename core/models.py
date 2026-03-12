from dataclasses import dataclass


@dataclass
class MemberProfile:
    age: int
    retirement_age: int
    payout_start_age: int
    monthly_salary: float
    monthly_spending: float
    starting_oa: float
    starting_sa: float
    starting_ma: float
    annual_salary_growth: float
    annual_inflation_rate: float
    years_in_retirement: int
    property_pledge: bool
    cpf_life_plan: str

    # New optional realism inputs
    monthly_oa_housing: float = 0.0
    annual_oa_insurance: float = 0.0