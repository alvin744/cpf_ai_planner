import streamlit as st
import pandas as pd
import numpy as np

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

st.set_page_config(
    page_title="CPF AI Retirement Planner",
    layout="centered",
    initial_sidebar_state="auto",
)

# -----------------------------------------------------
# Planning baselines
# -----------------------------------------------------

BASE_YEAR = 2026
BASE_FRS_2026 = 220_400.0
BASE_BRS_2026 = BASE_FRS_2026 / 2
BASE_ERS_2026 = BASE_FRS_2026 * 2

WIDGET_KEY_MAP = {
    "age": "age_input",
    "stop_work_age": "stop_work_age_input",
    "payout_age": "payout_age_input",
    "salary": "salary_input",
    "spending": "spending_input",
    "oa_start": "oa_start_input",
    "sa_start": "sa_start_input",
    "ma_start": "ma_start_input",
    "salary_growth": "salary_growth_input",
    "inflation": "inflation_input",
    "years_retirement": "years_retirement_input",
    "plan": "plan_input",
    "monthly_oa_housing": "monthly_oa_housing_input",
    "housing_end_age": "housing_end_age_input",
    "annual_oa_other": "annual_oa_other_input",
    "sa_cash_topup_per_year": "sa_cash_topup_per_year_input",
    "oa_to_sa_transfer_per_year": "oa_to_sa_transfer_per_year_input",
    "pledge_property_brs": "pledge_property_brs_input",
}

DEFAULT_INPUTS = {
    "age": 30,
    "stop_work_age": 65,
    "payout_age": 65,
    "salary": 5000.0,
    "spending": 3000.0,
    "oa_start": 80000.0,
    "sa_start": 30000.0,
    "ma_start": 10000.0,
    "salary_growth": 0.03,
    "inflation": 0.02,
    "years_retirement": 30,
    "plan": "Standard",
    "monthly_oa_housing": 0.0,
    "housing_end_age": 55,
    "annual_oa_other": 0.0,
    "sa_cash_topup_per_year": 0.0,
    "oa_to_sa_transfer_per_year": 0.0,
    "pledge_property_brs": False,
}

# -----------------------------------------------------
# Session state init
# -----------------------------------------------------

if "planner_inputs" not in st.session_state:
    st.session_state.planner_inputs = DEFAULT_INPUTS.copy()

if "planner_has_run" not in st.session_state:
    st.session_state.planner_has_run = True

for field, widget_key in WIDGET_KEY_MAP.items():
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state.planner_inputs[field]


# -----------------------------------------------------
# Core helpers
# -----------------------------------------------------

def estimate_cpf_life_payout(ra_balance: float, plan: str) -> float:
    if plan == "Standard":
        rate = 0.0079
    elif plan == "Basic":
        rate = 0.0069
    else:
        rate = 0.0063
    return ra_balance * rate


def get_cohort_retirement_sums(current_age: int, inflation_rate: float) -> dict:
    years_to_55 = max(55 - current_age, 0)
    cohort_year = BASE_YEAR + years_to_55

    frs = BASE_FRS_2026 * ((1 + inflation_rate) ** years_to_55)
    brs = BASE_BRS_2026 * ((1 + inflation_rate) ** years_to_55)
    ers = BASE_ERS_2026 * ((1 + inflation_rate) ** years_to_55)

    return {
        "cohort_year": cohort_year,
        "brs": brs,
        "frs": frs,
        "ers": ers,
    }


def get_allocation(age: int) -> dict:
    if age < 55:
        return {"oa": 0.23, "sa": 0.06, "ra": 0.0, "ma": 0.08}
    elif age < 60:
        return {"oa": 0.12, "sa": 0.0, "ra": 0.115, "ma": 0.105}
    elif age < 65:
        return {"oa": 0.035, "sa": 0.0, "ra": 0.11, "ma": 0.105}
    else:
        return {"oa": 0.01, "sa": 0.0, "ra": 0.05, "ma": 0.105}


def money(x: float) -> str:
    return f"${x:,.0f}"


def scenario_result(
    age: int,
    stop_work_age: int,
    payout_age: int,
    salary: float,
    spending: float,
    oa_start: float,
    sa_start: float,
    ma_start: float,
    salary_growth: float,
    inflation: float,
    plan: str,
    monthly_oa_housing: float,
    housing_end_age: int,
    annual_oa_other: float,
    sa_cash_topup_per_year: float,
    oa_to_sa_transfer_per_year: float,
):
    result = simulate_plan(
        current_age=age,
        stop_work_age=stop_work_age,
        payout_age=payout_age,
        salary=salary,
        salary_growth=salary_growth,
        oa_start=oa_start,
        sa_start=sa_start,
        ma_start=ma_start,
        monthly_oa_housing=monthly_oa_housing,
        housing_end_age=housing_end_age,
        annual_oa_other=annual_oa_other,
        sa_cash_topup_per_year=sa_cash_topup_per_year,
        oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
        inflation_rate=inflation,
    )
    ra = result["ra"]
    payout = estimate_cpf_life_payout(ra, plan)
    future_spending = spending * ((1 + inflation) ** (payout_age - age))
    gap = future_spending - payout
    return {
        "ra": ra,
        "payout": payout,
        "future_spending": future_spending,
        "gap": gap,
    }


def generate_ai_explanation(context: dict, user_question: str = "") -> str:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed.")

    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in Streamlit secrets.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an educational CPF retirement planning assistant.

Use the data below to explain the user's retirement scenario in plain English.
Do not provide regulated financial advice.
Do not make guarantees.
Keep the response practical, concise, and easy to understand.

Include:
1. A short explanation of the current result
2. The main reason for the retirement gap
3. The top 3 actions to consider in this scenario
4. Any important trade-offs or cautions
5. A reminder that this is a simplified educational model

User question:
{user_question if user_question else "No specific question. Explain the scenario."}

Scenario context:
{context}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )
    return response.output_text


# -----------------------------------------------------
# Simulation
# -----------------------------------------------------

def simulate_plan(
    current_age: int,
    stop_work_age: int,
    payout_age: int,
    salary: float,
    salary_growth: float,
    oa_start: float,
    sa_start: float,
    ma_start: float,
    monthly_oa_housing: float,
    housing_end_age: int,
    annual_oa_other: float,
    sa_cash_topup_per_year: float,
    oa_to_sa_transfer_per_year: float,
    inflation_rate: float,
):
    sums = get_cohort_retirement_sums(current_age, inflation_rate)
    frs = sums["frs"]

    oa = float(oa_start)
    sa = float(sa_start)
    ma = float(ma_start)
    ra = 0.0

    history = []
    transferred_to_ra = False

    for age in range(current_age, payout_age):
        working = age < stop_work_age

        if age < 55 and sa_cash_topup_per_year > 0:
            sa += sa_cash_topup_per_year

        if age < 55 and oa_to_sa_transfer_per_year > 0:
            transfer = min(oa, oa_to_sa_transfer_per_year)
            oa -= transfer
            sa += transfer

        if working:
            annual_salary = salary * 12
            alloc = get_allocation(age)

            oa += annual_salary * alloc["oa"]
            sa += annual_salary * alloc["sa"]
            ma += annual_salary * alloc["ma"]

            if age >= 55:
                ra_contrib = annual_salary * alloc["ra"]
                room_in_ra = max(frs - ra, 0.0)
                ra_to_add = min(ra_contrib, room_in_ra)
                oa_redirect = ra_contrib - ra_to_add
                ra += ra_to_add
                oa += oa_redirect

        housing_deduction = monthly_oa_housing * 12 if age < housing_end_age else 0.0
        annual_oa_deduction = housing_deduction + annual_oa_other
        oa = max(0.0, oa - annual_oa_deduction)

        if (age + 1) == 55 and not transferred_to_ra:
            transfer_amount = min(oa + sa, frs)

            sa_transfer = min(sa, transfer_amount)
            sa -= sa_transfer
            transfer_amount -= sa_transfer

            oa_transfer = min(oa, transfer_amount)
            oa -= oa_transfer

            ra += sa_transfer + oa_transfer
            transferred_to_ra = True

        oa *= 1.025
        sa *= 1.04
        ma *= 1.04
        ra *= 1.04

        if working:
            salary *= (1 + salary_growth)

        history.append({
            "Age": age + 1,
            "OA": max(0.0, oa),
            "SA": max(0.0, sa),
            "MA": max(0.0, ma),
            "RA": max(0.0, ra),
            "Total": max(0.0, oa) + max(0.0, sa) + max(0.0, ma) + max(0.0, ra),
        })

    history_df = pd.DataFrame(history)
    if not history_df.empty:
        history_df["Age"] = history_df["Age"].astype(int)
        for col in ["OA", "SA", "MA", "RA", "Total"]:
            history_df[col] = pd.to_numeric(history_df[col], errors="coerce").fillna(0.0)
            history_df[col] = history_df[col].clip(lower=0).round(2)

    return {
        "oa": max(0.0, oa),
        "sa": max(0.0, sa),
        "ma": max(0.0, ma),
        "ra": max(0.0, ra),
        "history": history_df,
        "sums": sums,
    }


def scenario_summary(
    label: str,
    age: int,
    stop_work_age: int,
    payout_age: int,
    salary: float,
    spending: float,
    oa_start: float,
    sa_start: float,
    ma_start: float,
    salary_growth: float,
    inflation: float,
    plan: str,
    monthly_oa_housing: float,
    housing_end_age: int,
    annual_oa_other: float,
    sa_cash_topup_per_year: float,
    oa_to_sa_transfer_per_year: float,
):
    result = simulate_plan(
        current_age=age,
        stop_work_age=stop_work_age,
        payout_age=payout_age,
        salary=salary,
        salary_growth=salary_growth,
        oa_start=oa_start,
        sa_start=sa_start,
        ma_start=ma_start,
        monthly_oa_housing=monthly_oa_housing,
        housing_end_age=housing_end_age,
        annual_oa_other=annual_oa_other,
        sa_cash_topup_per_year=sa_cash_topup_per_year,
        oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
        inflation_rate=inflation,
    )
    ra = result["ra"]
    payout = estimate_cpf_life_payout(ra, plan)
    future_spending = spending * ((1 + inflation) ** (payout_age - age))
    gap = future_spending - payout

    return {
        "Scenario": label,
        "RA at payout": ra,
        "CPF LIFE payout": payout,
        "Inflated spending": future_spending,
        "Gap": gap,
    }


def build_recommendations(
    age: int,
    stop_work_age: int,
    payout_age: int,
    salary: float,
    spending: float,
    oa_start: float,
    sa_start: float,
    ma_start: float,
    salary_growth: float,
    inflation: float,
    plan: str,
    monthly_oa_housing: float,
    housing_end_age: int,
    annual_oa_other: float,
    sa_cash_topup_per_year: float,
    oa_to_sa_transfer_per_year: float,
    current_gap: float,
):
    recommendations = []

    current = scenario_result(
        age, stop_work_age, payout_age, salary, spending, oa_start, sa_start, ma_start,
        salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
        sa_cash_topup_per_year, oa_to_sa_transfer_per_year
    )

    reduce_spending = scenario_result(
        age, stop_work_age, payout_age, salary, spending * 0.8, oa_start, sa_start, ma_start,
        salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
        sa_cash_topup_per_year, oa_to_sa_transfer_per_year
    )
    recommendations.append({
        "Action": "Reduce retirement spending target by 20%",
        "Estimated gap improvement": current["gap"] - reduce_spending["gap"],
        "Why it helps": "Lower retirement spending directly narrows the monthly income gap.",
    })

    if payout_age < 70:
        delay_payout = scenario_result(
            age, stop_work_age, 70, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        )
        recommendations.append({
            "Action": "Delay CPF LIFE payout start to age 70",
            "Estimated gap improvement": current["gap"] - delay_payout["gap"],
            "Why it helps": "A later payout start can raise projected monthly CPF LIFE payouts in this model.",
        })

    if stop_work_age < 65:
        work_longer = scenario_result(
            age, 65, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        )
        recommendations.append({
            "Action": "Work until age 65",
            "Estimated gap improvement": current["gap"] - work_longer["gap"],
            "Why it helps": "More working years can increase CPF contributions and projected RA.",
        })

    if monthly_oa_housing > 0:
        cut_housing = scenario_result(
            age, stop_work_age, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, 0.0, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        )
        recommendations.append({
            "Action": "Reduce or stop OA used for housing",
            "Estimated gap improvement": current["gap"] - cut_housing["gap"],
            "Why it helps": "Less OA outflow leaves more balance available for retirement accumulation.",
        })

    if sa_cash_topup_per_year == 0:
        add_topup = scenario_result(
            age, stop_work_age, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            8000.0, oa_to_sa_transfer_per_year
        )
        recommendations.append({
            "Action": "Add SA cash top-up of $8,000 per year",
            "Estimated gap improvement": current["gap"] - add_topup["gap"],
            "Why it helps": "Pre-55 SA top-ups can improve long-term retirement accumulation in this simplified model.",
        })

    if oa_to_sa_transfer_per_year == 0 and oa_start > 0:
        add_transfer = scenario_result(
            age, stop_work_age, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, 3000.0
        )
        recommendations.append({
            "Action": "Add OA → SA transfer of $3,000 per year",
            "Estimated gap improvement": current["gap"] - add_transfer["gap"],
            "Why it helps": "Moving OA to SA may support stronger retirement balances before age 55.",
        })

    recommendations = [r for r in recommendations if r["Estimated gap improvement"] > 0]
    recommendations = sorted(recommendations, key=lambda x: x["Estimated gap improvement"], reverse=True)

    if current_gap > 0:
        recommendations.append({
            "Action": "Build non-CPF retirement savings",
            "Estimated gap improvement": 0.0,
            "Why it helps": "If CPF LIFE still does not fully cover spending, non-CPF savings can help cover the remaining gap.",
        })

    return recommendations


# -----------------------------------------------------
# Sidebar inputs
# -----------------------------------------------------

st.sidebar.header("Your Inputs")

st.sidebar.number_input("Current Age", min_value=18, max_value=70, step=1, key="age_input")
st.sidebar.number_input("Age You Stop Working", min_value=40, max_value=70, step=1, key="stop_work_age_input")
st.sidebar.number_input("CPF LIFE Payout Start Age", min_value=65, max_value=70, step=1, key="payout_age_input")
st.sidebar.number_input("Monthly Salary", min_value=0.0, max_value=50000.0, step=100.0, key="salary_input")
st.sidebar.number_input(
    "Expected Monthly Retirement Spending (today's dollars)",
    min_value=0.0,
    max_value=50000.0,
    step=100.0,
    key="spending_input",
)
st.sidebar.number_input("Starting OA Balance", min_value=0.0, max_value=2000000.0, step=1000.0, key="oa_start_input")
st.sidebar.number_input("Starting SA Balance", min_value=0.0, max_value=2000000.0, step=1000.0, key="sa_start_input")
st.sidebar.number_input("Starting MA Balance", min_value=0.0, max_value=2000000.0, step=1000.0, key="ma_start_input")
st.sidebar.slider("Annual Salary Growth", min_value=0.0, max_value=0.10, key="salary_growth_input")
st.sidebar.slider("Annual Inflation Rate", min_value=0.0, max_value=0.10, key="inflation_input")
st.sidebar.slider("Years in Retirement", min_value=10, max_value=40, key="years_retirement_input")
st.sidebar.selectbox("CPF LIFE Plan", ["Standard", "Basic", "Escalating"], key="plan_input")

st.sidebar.markdown("### Optional OA Usage")
st.sidebar.number_input(
    "Monthly OA used for housing",
    min_value=0.0,
    max_value=5000.0,
    step=100.0,
    key="monthly_oa_housing_input",
)
st.sidebar.number_input(
    "Housing usage ends at age",
    min_value=18,
    max_value=100,
    step=1,
    key="housing_end_age_input",
)
st.sidebar.number_input(
    "Annual OA used for other purposes",
    min_value=0.0,
    max_value=20000.0,
    step=100.0,
    key="annual_oa_other_input",
)

st.sidebar.markdown("### Retirement Strategy Options")
st.sidebar.number_input(
    "SA Cash Top-Up (per year)",
    min_value=0.0,
    max_value=200000.0,
    step=1000.0,
    key="sa_cash_topup_per_year_input",
)
st.sidebar.caption("In this simplified version, SA cash top-up is applied only before age 55.")

st.sidebar.number_input(
    "OA → SA Transfer (per year)",
    min_value=0.0,
    max_value=200000.0,
    step=1000.0,
    key="oa_to_sa_transfer_per_year_input",
)
st.sidebar.caption("In this simplified version, OA → SA transfer is applied only before age 55 and is capped by available OA balance.")

st.sidebar.checkbox(
    "Pledge existing property (use BRS at withdrawal)",
    key="pledge_property_brs_input",
)
st.sidebar.caption(
    "In this simplified version, property pledge changes the benchmark interpretation from FRS to BRS only. "
    "It does not directly change the CPF LIFE payout formula."
)

run_clicked = st.sidebar.button("Run Planner", type="primary")

if run_clicked:
    st.session_state.planner_inputs = {
        field: st.session_state[widget_key]
        for field, widget_key in WIDGET_KEY_MAP.items()
    }
    st.session_state.planner_has_run = True
    st.rerun()


# -----------------------------------------------------
# Main page
# -----------------------------------------------------

st.title("CPF AI Retirement Planner")
st.caption("A simplified CPF projection and strategy simulator for educational planning.")
st.info("On smaller screens, open inputs from the top-left arrow, adjust them, then tap Run Planner.")

if not st.session_state.planner_has_run:
    st.info("Fill in the inputs and click Run Planner.")
    st.stop()

inputs = st.session_state.planner_inputs

age = int(inputs["age"])
stop_work_age = int(inputs["stop_work_age"])
payout_age = int(inputs["payout_age"])
salary = float(inputs["salary"])
spending = float(inputs["spending"])
oa_start = float(inputs["oa_start"])
sa_start = float(inputs["sa_start"])
ma_start = float(inputs["ma_start"])
salary_growth = float(inputs["salary_growth"])
inflation = float(inputs["inflation"])
years_retirement = int(inputs["years_retirement"])
plan = inputs["plan"]
monthly_oa_housing = float(inputs["monthly_oa_housing"])
housing_end_age = int(inputs["housing_end_age"])
annual_oa_other = float(inputs["annual_oa_other"])
sa_cash_topup_per_year = float(inputs["sa_cash_topup_per_year"])
oa_to_sa_transfer_per_year = float(inputs["oa_to_sa_transfer_per_year"])
pledge_property_brs = bool(inputs["pledge_property_brs"])

base = simulate_plan(
    current_age=age,
    stop_work_age=stop_work_age,
    payout_age=payout_age,
    salary=salary,
    salary_growth=salary_growth,
    oa_start=oa_start,
    sa_start=sa_start,
    ma_start=ma_start,
    monthly_oa_housing=monthly_oa_housing,
    housing_end_age=housing_end_age,
    annual_oa_other=annual_oa_other,
    sa_cash_topup_per_year=sa_cash_topup_per_year,
    oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
    inflation_rate=inflation,
)

ra = base["ra"]
payout = estimate_cpf_life_payout(ra, plan)
inflated_spending = spending * ((1 + inflation) ** (payout_age - age))
gap = inflated_spending - payout
sums = base["sums"]
coverage_ratio = payout / inflated_spending if inflated_spending > 0 else 1.0
withdrawal_benchmark = sums["brs"] if pledge_property_brs else sums["frs"]
withdrawal_benchmark_name = "BRS" if pledge_property_brs else "FRS"

recommendations = build_recommendations(
    age=age,
    stop_work_age=stop_work_age,
    payout_age=payout_age,
    salary=salary,
    spending=spending,
    oa_start=oa_start,
    sa_start=sa_start,
    ma_start=ma_start,
    salary_growth=salary_growth,
    inflation=inflation,
    plan=plan,
    monthly_oa_housing=monthly_oa_housing,
    housing_end_age=housing_end_age,
    annual_oa_other=annual_oa_other,
    sa_cash_topup_per_year=sa_cash_topup_per_year,
    oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
    current_gap=gap,
)

with st.expander("Input Summary Used", expanded=False):
    st.write(f"Current age: {age}")
    st.write(f"Stop work age: {stop_work_age}")
    st.write(f"CPF LIFE payout start age: {payout_age}")
    st.write(f"Monthly salary: {money(salary)}")
    st.write(f"Expected monthly retirement spending today: {money(spending)}")
    st.write(f"Starting OA / SA / MA: {money(oa_start)} / {money(sa_start)} / {money(ma_start)}")
    st.write(f"Annual salary growth: {salary_growth:.1%}")
    st.write(f"Annual inflation rate: {inflation:.1%}")
    st.write(f"Years in retirement: {years_retirement}")
    st.write(f"CPF LIFE plan: {plan}")
    st.write(f"Monthly OA used for housing: {money(monthly_oa_housing)}")
    st.write(f"Housing usage ends at age: {housing_end_age}")
    st.write(f"Annual OA used for other purposes: {money(annual_oa_other)}")
    st.write(f"SA cash top-up per year: {money(sa_cash_topup_per_year)}")
    st.write(f"OA → SA transfer per year: {money(oa_to_sa_transfer_per_year)}")
    st.write(f"Use BRS benchmark via property pledge: {'Yes' if pledge_property_brs else 'No'}")

st.header("Key Metrics")
st.metric("Projected RA", money(ra))
st.metric("CPF LIFE", f"{money(payout)}/month")
st.metric("Future spending", f"{money(inflated_spending)}/month")
st.metric("Gap", money(gap))

st.header("Retirement Risk")
if coverage_ratio >= 1.0:
    st.success(
        "🟢 Low retirement risk: your projected CPF LIFE payout is close to or above your spending target at payout age."
    )
elif coverage_ratio >= 0.8:
    st.warning(
        "🟡 Moderate retirement risk: your projected CPF LIFE payout may cover much of your spending target, but a gap remains."
    )
else:
    st.error(
        "🔴 High retirement risk: your projected CPF LIFE payout is significantly below your spending target, so additional planning may be needed."
    )

with st.expander("Today vs Payout-Age Dollars", expanded=True):
    st.metric("Today's spending target", f"{money(spending)}/month")
    st.metric(f"Equivalent spending at age {payout_age}", f"{money(inflated_spending)}/month")
    st.metric(f"Projected CPF LIFE at age {payout_age}", f"{money(payout)}/month")
    st.metric(f"Gap at age {payout_age}", f"{money(gap)}/month")

with st.expander(f"Estimated Retirement Sums for Your Cohort (Turning 55 in {sums['cohort_year']})", expanded=True):
    st.metric("Estimated BRS", money(sums["brs"]))
    st.metric("Estimated FRS", money(sums["frs"]))
    st.metric("Estimated ERS", money(sums["ers"]))

with st.expander("Withdrawal Benchmark Assumption", expanded=True):
    st.write(
        f"This run uses **{withdrawal_benchmark_name}** as the simplified withdrawal benchmark for benchmark interpretation."
    )
    if pledge_property_brs:
        st.info(
            "Property pledge is switched on, so benchmark interpretation uses BRS instead of FRS. "
            "This affects the benchmark view only and does not directly change the CPF LIFE payout formula in this simplified model."
        )
    else:
        st.info(
            "Property pledge is switched off, so benchmark interpretation uses FRS in this simplified model."
        )

with st.expander("Benchmark vs Personal Target", expanded=True):
    if ra >= withdrawal_benchmark:
        st.info(
            f"Your projected RA meets the model's estimated {withdrawal_benchmark_name} benchmark for your cohort. "
            "This benchmark is different from your personal spending target."
        )
    else:
        st.warning(
            f"Your projected RA is below the model's estimated {withdrawal_benchmark_name} benchmark for your cohort."
        )

    if gap > 0:
        st.warning(
            "Even if the simplified benchmark is met, your projected CPF LIFE payout may still fall short of your personal spending target."
        )
    else:
        st.success("Your projected CPF LIFE payout may cover your current personal spending target in this model.")

st.header("Retirement Target Solver")
required_ra = inflated_spending / 0.0079
shortfall_ra = required_ra - ra

st.write(f"Required RA to support spending: {money(required_ra)}")
st.write(f"Your projected RA: {money(ra)}")

if shortfall_ra > 0:
    st.warning(f"Additional RA needed: {money(shortfall_ra)}")
else:
    st.success("Your CPF may cover your target retirement spending.")

with st.expander("Recommended Actions", expanded=True):
    if not recommendations:
        st.success("No clear improvement actions stood out in this simplified model.")
    else:
        for i, rec in enumerate(recommendations[:5], start=1):
            st.markdown(f"**{i}. {rec['Action']}**")
            if rec["Estimated gap improvement"] > 0:
                st.write(f"Estimated gap improvement: {money(rec['Estimated gap improvement'])}/month")
            st.caption(rec["Why it helps"])

    st.caption(
        "These suggestions are scenario-based ideas generated from this simplified model. "
        "They are educational prompts, not personalized financial advice."
    )

st.header("AI Retirement Coach")
ai_question = st.text_input(
    "Ask about this result",
    placeholder="Why is my gap so high?"
)

if st.button("Explain My Plan with AI"):
    try:
        ai_context = {
            "inputs": {
                "age": age,
                "stop_work_age": stop_work_age,
                "payout_age": payout_age,
                "salary": salary,
                "spending_today": spending,
                "oa_start": oa_start,
                "sa_start": sa_start,
                "ma_start": ma_start,
                "monthly_oa_housing": monthly_oa_housing,
                "housing_end_age": housing_end_age,
                "annual_oa_other": annual_oa_other,
                "sa_cash_topup_per_year": sa_cash_topup_per_year,
                "oa_to_sa_transfer_per_year": oa_to_sa_transfer_per_year,
                "property_pledge_brs": pledge_property_brs,
            },
            "outputs": {
                "projected_ra": ra,
                "cpf_life_payout": payout,
                "future_spending": inflated_spending,
                "gap": gap,
                "benchmark_used": withdrawal_benchmark_name,
                "retirement_risk_ratio": coverage_ratio,
            },
            "recommendations": recommendations[:5],
            "model_notes": [
                "This is a simplified educational model.",
                "SA cash top-up is applied only before age 55.",
                "OA to SA transfer is applied only before age 55.",
                "Property pledge changes benchmark interpretation only, not payout formula.",
                "Impact estimates are directional and may not add up exactly.",
            ],
        }

        ai_text = generate_ai_explanation(ai_context, ai_question)
        st.write(ai_text)

    except Exception as e:
        st.error(f"Unable to generate AI explanation: {e}")

with st.expander("Early Retirement Simulator", expanded=True):
    early_results = []
    for test_age in [55, 60, 65]:
        scenario = simulate_plan(
            current_age=age,
            stop_work_age=test_age,
            payout_age=payout_age,
            salary=salary,
            salary_growth=salary_growth,
            oa_start=oa_start,
            sa_start=sa_start,
            ma_start=ma_start,
            monthly_oa_housing=monthly_oa_housing,
            housing_end_age=housing_end_age,
            annual_oa_other=annual_oa_other,
            sa_cash_topup_per_year=sa_cash_topup_per_year,
            oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
            inflation_rate=inflation,
        )
        payout_test = estimate_cpf_life_payout(scenario["ra"], plan)
        early_results.append((test_age, payout_test))
        st.metric(f"Stop Work {test_age}", f"{money(payout_test)}/month")

    unique_payouts = {round(p, 2) for _, p in early_results}
    if len(unique_payouts) == 1:
        st.info(
            "In this scenario, you are projected to meet the model's simplified retirement-sum threshold by age 55. "
            "Because post-55 RA contributions are capped in this simplified version, stopping work at 55, 60, or 65 "
            "produces the same projected CPF LIFE payout. This does not mean the payout is enough to meet your personal spending target."
        )

with st.expander("Scenario Comparison Engine", expanded=True):
    scenarios = [
        scenario_summary(
            "Current plan",
            age, stop_work_age, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        ),
        scenario_summary(
            "Stop work at 60",
            age, 60, payout_age, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        ),
        scenario_summary(
            "Start payout at 70",
            age, stop_work_age, 70, salary, spending, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        ),
        scenario_summary(
            "Reduce spending by 20%",
            age, stop_work_age, payout_age, salary, spending * 0.8, oa_start, sa_start, ma_start,
            salary_growth, inflation, plan, monthly_oa_housing, housing_end_age, annual_oa_other,
            sa_cash_topup_per_year, oa_to_sa_transfer_per_year
        ),
    ]

    scenario_df = pd.DataFrame(scenarios)
    display_df = scenario_df.copy()
    display_df["RA at payout"] = display_df["RA at payout"].map(money)
    display_df["CPF LIFE payout"] = display_df["CPF LIFE payout"].map(lambda x: f"{money(x)}/month")
    display_df["Inflated spending"] = display_df["Inflated spending"].map(lambda x: f"{money(x)}/month")
    display_df["Gap"] = display_df["Gap"].map(money)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    improvements = []
    current_gap_value = scenarios[0]["Gap"]
    for row in scenarios[1:]:
        gap_reduction = current_gap_value - row["Gap"]
        improvements.append({
            "Scenario": row["Scenario"],
            "Gap reduction": gap_reduction,
        })

    best = max(improvements, key=lambda x: x["Gap reduction"])
    if best["Gap reduction"] > 0:
        st.success(
            f"Best tested improvement: **{best['Scenario']}**. "
            f"It improves the monthly gap by about **{money(best['Gap reduction'])}** in this simplified model."
        )
    else:
        st.info("None of the preset scenarios materially improved the current gap in this simplified model.")

with st.expander("Housing Impact in Current Scenario", expanded=True):
    if monthly_oa_housing == 0:
        st.write("No OA housing deduction is currently applied in this scenario.")
    else:
        no_housing = simulate_plan(
            current_age=age,
            stop_work_age=stop_work_age,
            payout_age=payout_age,
            salary=salary,
            salary_growth=salary_growth,
            oa_start=oa_start,
            sa_start=sa_start,
            ma_start=ma_start,
            monthly_oa_housing=0.0,
            housing_end_age=housing_end_age,
            annual_oa_other=annual_oa_other,
            sa_cash_topup_per_year=sa_cash_topup_per_year,
            oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
            inflation_rate=inflation,
        )
        payout_no_housing = estimate_cpf_life_payout(no_housing["ra"], plan)
        impact = payout_no_housing - payout

        st.write(
            f"Using {money(monthly_oa_housing)}/month of OA for housing until age {housing_end_age} may reduce CPF LIFE payout by about {money(impact)}/month in this simplified model."
        )

    st.caption(
        "In this simplified model, different OA and SA paths can still converge to a similar projected RA once the retirement-account cap region is reached. "
        "So individual impact estimates are directional and may not add up exactly."
    )

    if monthly_oa_housing == 0 and annual_oa_other > 0 and base["ra"] >= withdrawal_benchmark:
        st.caption(
            "Small OA deductions may not materially change CPF LIFE payout when retirement-sum benchmarks are already met in this simplified model."
        )

with st.expander("SA Top-Up Impact in Current Scenario", expanded=True):
    if sa_cash_topup_per_year == 0:
        st.write("No annual SA cash top-up is currently applied.")
    else:
        strategy_off = simulate_plan(
            current_age=age,
            stop_work_age=stop_work_age,
            payout_age=payout_age,
            salary=salary,
            salary_growth=salary_growth,
            oa_start=oa_start,
            sa_start=sa_start,
            ma_start=ma_start,
            monthly_oa_housing=monthly_oa_housing,
            housing_end_age=housing_end_age,
            annual_oa_other=annual_oa_other,
            sa_cash_topup_per_year=0.0,
            oa_to_sa_transfer_per_year=oa_to_sa_transfer_per_year,
            inflation_rate=inflation,
        )
        payout_without_strategy = estimate_cpf_life_payout(strategy_off["ra"], plan)
        strategy_gain = payout - payout_without_strategy

        st.write(f"SA cash top-up per year: {money(sa_cash_topup_per_year)}")
        st.write(f"Estimated CPF LIFE uplift from this annual action: {money(strategy_gain)}/month")
        st.caption("This uplift is estimated using the simplified assumption that SA cash top-ups are applied only before age 55.")

    st.caption(
        "In this simplified model, different OA and SA paths can still converge to a similar projected RA once the retirement-account cap region is reached. "
        "So individual impact estimates are directional and may not add up exactly."
    )

with st.expander("OA → SA Transfer Impact in Current Scenario", expanded=True):
    if oa_to_sa_transfer_per_year == 0:
        st.write("No annual OA → SA transfer is currently applied.")
    else:
        transfer_off = simulate_plan(
            current_age=age,
            stop_work_age=stop_work_age,
            payout_age=payout_age,
            salary=salary,
            salary_growth=salary_growth,
            oa_start=oa_start,
            sa_start=sa_start,
            ma_start=ma_start,
            monthly_oa_housing=monthly_oa_housing,
            housing_end_age=housing_end_age,
            annual_oa_other=annual_oa_other,
            sa_cash_topup_per_year=sa_cash_topup_per_year,
            oa_to_sa_transfer_per_year=0.0,
            inflation_rate=inflation,
        )
        payout_without_transfer = estimate_cpf_life_payout(transfer_off["ra"], plan)
        transfer_gain = payout - payout_without_transfer

        st.write(f"OA → SA transfer per year: {money(oa_to_sa_transfer_per_year)}")
        st.write(f"Estimated CPF LIFE uplift from this annual action: {money(transfer_gain)}/month")
        st.caption("This uplift is estimated using the simplified assumption that OA → SA transfers are applied only before age 55 and are capped by available OA balance.")

    st.caption(
        "In this simplified model, different OA and SA paths can still converge to a similar projected RA once the retirement-account cap region is reached. "
        "So individual impact estimates are directional and may not add up exactly."
    )

st.header("Retirement Gap Over Time")
retirement_ages = np.arange(payout_age, payout_age + years_retirement, dtype=int)
monthly_income = np.repeat(float(payout), len(retirement_ages))
monthly_spending = inflated_spending * (1.02 ** (retirement_ages - payout_age))

gap_df = pd.DataFrame({
    "Age": retirement_ages,
    "Income": monthly_income,
    "Spending": monthly_spending,
}).set_index("Age")

st.line_chart(gap_df)
st.caption(
    "CPF LIFE is designed for lifelong monthly payouts. This chart shows projected income versus projected spending over time, not CPF LIFE depletion."
)

st.header("CPF Growth Projection")
history = base["history"]
if not history.empty:
    growth_df = history[["Age", "OA", "SA", "MA", "RA"]].copy()
    for col in ["OA", "SA", "MA", "RA"]:
        growth_df[col] = growth_df[col].clip(lower=0).round(2)
    growth_df["Age"] = growth_df["Age"].astype(int)
    growth_df = growth_df.set_index("Age")
    st.line_chart(growth_df)

st.header("Longevity Risk")
longevity_ages = np.arange(payout_age, payout_age + years_retirement, dtype=int)
income = np.repeat(float(payout), len(longevity_ages))
spending_curve = inflated_spending * (1.02 ** (longevity_ages - payout_age))

longevity_df = pd.DataFrame({
    "Age": longevity_ages,
    "Income": income,
    "Spending": spending_curve,
}).set_index("Age")

st.line_chart(longevity_df)

st.divider()
st.caption("""
This planner is for educational planning support only.
It does not replace the official CPF estimator or financial advice.
Actual CPF LIFE payouts depend on CPF Board calculations and policies.
""")