import streamlit as st
import pandas as pd
import numpy as np

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
    "annual_oa_other": "annual_oa_other_input",
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
    "annual_oa_other": 0.0,
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
# CPF LIFE payout estimate
# -----------------------------------------------------

def estimate_cpf_life_payout(ra_balance: float, plan: str) -> float:
    if plan == "Standard":
        rate = 0.0079
    elif plan == "Basic":
        rate = 0.0069
    else:
        rate = 0.0063
    return ra_balance * rate


# -----------------------------------------------------
# Cohort retirement sums
# -----------------------------------------------------

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


# -----------------------------------------------------
# Simplified contribution / allocation assumptions
# -----------------------------------------------------

def get_allocation(age: int) -> dict:
    if age < 55:
        return {"oa": 0.23, "sa": 0.06, "ra": 0.0, "ma": 0.08}
    elif age < 60:
        return {"oa": 0.12, "sa": 0.0, "ra": 0.115, "ma": 0.105}
    elif age < 65:
        return {"oa": 0.035, "sa": 0.0, "ra": 0.11, "ma": 0.105}
    else:
        return {"oa": 0.01, "sa": 0.0, "ra": 0.05, "ma": 0.105}


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
    annual_oa_other: float,
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

        annual_oa_deduction = (monthly_oa_housing * 12) + annual_oa_other
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


# -----------------------------------------------------
# Sidebar inputs
# -----------------------------------------------------

st.sidebar.header("Your Inputs")

st.sidebar.number_input(
    "Current Age",
    min_value=18,
    max_value=70,
    step=1,
    key="age_input",
)

st.sidebar.number_input(
    "Age You Stop Working",
    min_value=40,
    max_value=70,
    step=1,
    key="stop_work_age_input",
)

st.sidebar.number_input(
    "CPF LIFE Payout Start Age",
    min_value=65,
    max_value=70,
    step=1,
    key="payout_age_input",
)

st.sidebar.number_input(
    "Monthly Salary",
    min_value=0.0,
    max_value=50000.0,
    step=100.0,
    key="salary_input",
)

st.sidebar.number_input(
    "Expected Monthly Retirement Spending (today's dollars)",
    min_value=0.0,
    max_value=20000.0,
    step=100.0,
    key="spending_input",
)

st.sidebar.number_input(
    "Starting OA Balance",
    min_value=0.0,
    max_value=2000000.0,
    step=1000.0,
    key="oa_start_input",
)

st.sidebar.number_input(
    "Starting SA Balance",
    min_value=0.0,
    max_value=2000000.0,
    step=1000.0,
    key="sa_start_input",
)

st.sidebar.number_input(
    "Starting MA Balance",
    min_value=0.0,
    max_value=2000000.0,
    step=1000.0,
    key="ma_start_input",
)

st.sidebar.slider(
    "Annual Salary Growth",
    min_value=0.0,
    max_value=0.10,
    key="salary_growth_input",
)

st.sidebar.slider(
    "Annual Inflation Rate",
    min_value=0.0,
    max_value=0.10,
    key="inflation_input",
)

st.sidebar.slider(
    "Years in Retirement",
    min_value=10,
    max_value=40,
    key="years_retirement_input",
)

st.sidebar.selectbox(
    "CPF LIFE Plan",
    ["Standard", "Basic", "Escalating"],
    key="plan_input",
)

st.sidebar.markdown("### Optional OA Usage")

st.sidebar.number_input(
    "Monthly OA used for housing",
    min_value=0.0,
    max_value=5000.0,
    step=100.0,
    key="monthly_oa_housing_input",
)

st.sidebar.number_input(
    "Annual OA used for other purposes",
    min_value=0.0,
    max_value=20000.0,
    step=100.0,
    key="annual_oa_other_input",
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
annual_oa_other = float(inputs["annual_oa_other"])

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
    annual_oa_other=annual_oa_other,
    inflation_rate=inflation,
)

ra = base["ra"]
payout = estimate_cpf_life_payout(ra, plan)
inflated_spending = spending * ((1 + inflation) ** (payout_age - age))
gap = inflated_spending - payout
sums = base["sums"]

with st.expander("Input Summary Used", expanded=False):
    st.write(f"Current age: {age}")
    st.write(f"Stop work age: {stop_work_age}")
    st.write(f"CPF LIFE payout start age: {payout_age}")
    st.write(f"Monthly salary: ${salary:,.0f}")
    st.write(f"Expected monthly retirement spending today: ${spending:,.0f}")
    st.write(f"Starting OA / SA / MA: ${oa_start:,.0f} / ${sa_start:,.0f} / ${ma_start:,.0f}")
    st.write(f"Annual salary growth: {salary_growth:.1%}")
    st.write(f"Annual inflation rate: {inflation:.1%}")
    st.write(f"Years in retirement: {years_retirement}")
    st.write(f"CPF LIFE plan: {plan}")

st.header("Key Metrics")
st.metric("Projected RA", f"${ra:,.0f}")
st.metric("CPF LIFE", f"${payout:,.0f}/month")
st.metric("Future spending", f"${inflated_spending:,.0f}/month")
st.metric("Gap", f"${gap:,.0f}")

with st.expander(f"Estimated Retirement Sums for Your Cohort (Turning 55 in {sums['cohort_year']})", expanded=True):
    st.metric("Estimated BRS", f"${sums['brs']:,.0f}")
    st.metric("Estimated FRS", f"${sums['frs']:,.0f}")
    st.metric("Estimated ERS", f"${sums['ers']:,.0f}")

with st.expander("Benchmark vs Personal Target", expanded=True):
    if ra >= sums["frs"]:
        st.info(
            "Your projected RA meets the model's estimated FRS benchmark for your cohort. "
            "This benchmark is different from your personal spending target."
        )
    else:
        st.warning(
            "Your projected RA is below the model's estimated FRS benchmark for your cohort."
        )

    if gap > 0:
        st.warning(
            "Even if the simplified benchmark is met, your projected CPF LIFE payout may still fall short of your personal spending target."
        )
    else:
        st.success(
            "Your projected CPF LIFE payout may cover your current personal spending target in this model."
        )

st.header("Retirement Target Solver")
required_ra = inflated_spending / 0.0079
shortfall_ra = required_ra - ra

st.write(f"Required RA to support spending: ${required_ra:,.0f}")
st.write(f"Your projected RA: ${ra:,.0f}")

if shortfall_ra > 0:
    st.warning(f"Additional RA needed: ${shortfall_ra:,.0f}")
else:
    st.success("Your CPF may cover your target retirement spending.")

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
            annual_oa_other=annual_oa_other,
            inflation_rate=inflation,
        )
        payout_test = estimate_cpf_life_payout(scenario["ra"], plan)
        early_results.append((test_age, payout_test))
        st.metric(f"Stop Work {test_age}", f"${payout_test:,.0f}/month")

    unique_payouts = {round(p, 2) for _, p in early_results}
    if len(unique_payouts) == 1:
        st.info(
            "In this scenario, you are projected to meet the model's simplified retirement-sum threshold by age 55. "
            "Because post-55 RA contributions are capped in this simplified version, stopping work at 55, 60, or 65 "
            "produces the same projected CPF LIFE payout. This does not mean the payout is enough to meet your personal spending target."
        )

with st.expander("Housing vs Retirement Impact", expanded=True):
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
            annual_oa_other=annual_oa_other,
            inflation_rate=inflation,
        )

        payout_no_housing = estimate_cpf_life_payout(no_housing["ra"], plan)
        impact = payout_no_housing - payout

        st.write(
            f"Using ${monthly_oa_housing:,.0f}/month of OA for housing may reduce CPF LIFE payout by about ${impact:,.0f}/month."
        )

        if impact == 0:
            st.info(
                "In this scenario, the current housing deduction does not change projected CPF LIFE payout in this simplified model. "
                "That does not necessarily mean housing has no real-world impact; it means the current deduction still leaves you above the model's simplified threshold."
            )

    if monthly_oa_housing == 0 and annual_oa_other > 0 and base["ra"] >= sums["frs"]:
        st.caption(
            "Small OA deductions may not materially change CPF LIFE payout when retirement sums are already met in this simplified model."
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