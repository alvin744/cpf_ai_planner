import random
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from core.models import MemberProfile
from core.projection import project_cpf
from core.payout import estimate_cpf_life_payout
from simulation.monte_carlo import run_retirement_simulation


MODEL_DIR = Path("artifacts")
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "risk_model_v6.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "risk_model_v6_metadata.joblib"

FEATURE_COLS = [
    "age",
    "retirement_age",
    "payout_start_age",
    "monthly_salary",
    "monthly_spending",
    "starting_oa",
    "starting_sa",
    "starting_ma",
    "annual_salary_growth",
    "annual_inflation_rate",
    "years_to_payout_start",
    "plan_code",
    "projected_total_balance",
    "projected_ra_at_payout_start",
    "projected_cpf_life_payout",
    "inflated_spending_at_payout_start",
    "payout_spending_ratio",
]


def plan_to_code(plan):
    if plan == "Basic":
        return 0
    elif plan == "Standard":
        return 1
    elif plan == "Escalating":
        return 2
    return 1


def make_random_member():
    age = random.randint(25, 55)
    retirement_age = random.randint(max(age + 2, 55), 70)
    payout_start_age = random.randint(65, 70)

    monthly_salary = random.randint(2500, 12000)
    monthly_spending = random.randint(1800, 7000)

    starting_oa = random.randint(0, 250000)
    starting_sa = random.randint(0, 180000)
    starting_ma = random.randint(0, 150000)

    annual_salary_growth = random.uniform(0.01, 0.06)
    annual_inflation_rate = random.uniform(0.01, 0.04)
    years_in_retirement = random.randint(20, 30)
    cpf_life_plan = random.choice(["Standard", "Basic", "Escalating"])

    return MemberProfile(
        age=age,
        retirement_age=retirement_age,
        payout_start_age=payout_start_age,
        monthly_salary=monthly_salary,
        monthly_spending=monthly_spending,
        starting_oa=starting_oa,
        starting_sa=starting_sa,
        starting_ma=starting_ma,
        annual_salary_growth=annual_salary_growth,
        annual_inflation_rate=annual_inflation_rate,
        years_in_retirement=years_in_retirement,
        property_pledge=False,
        cpf_life_plan=cpf_life_plan
    )


def label_from_shortfall(shortfall_probability):
    if shortfall_probability < 0.10:
        return "low"
    elif shortfall_probability < 0.30:
        return "medium"
    return "high"


def build_feature_row(member):
    projection = project_cpf(member)
    payout = estimate_cpf_life_payout(
        projection["ra_at_payout_start"],
        member.cpf_life_plan,
        projection["brs"],
        projection["frs"],
        projection["ers"],
        member.payout_start_age
    )

    years_to_payout_start = max(member.payout_start_age - member.age, 0)
    inflated_spending_at_payout_start = member.monthly_spending * (
        (1 + member.annual_inflation_rate) ** years_to_payout_start
    )

    payout_spending_ratio = payout / max(inflated_spending_at_payout_start, 1)

    return {
        "age": member.age,
        "retirement_age": member.retirement_age,
        "payout_start_age": member.payout_start_age,
        "monthly_salary": member.monthly_salary,
        "monthly_spending": member.monthly_spending,
        "starting_oa": member.starting_oa,
        "starting_sa": member.starting_sa,
        "starting_ma": member.starting_ma,
        "annual_salary_growth": member.annual_salary_growth,
        "annual_inflation_rate": member.annual_inflation_rate,
        "years_to_payout_start": years_to_payout_start,
        "plan_code": plan_to_code(member.cpf_life_plan),
        "projected_total_balance": projection["total_balance"],
        "projected_ra_at_payout_start": projection["ra_at_payout_start"],
        "projected_cpf_life_payout": payout,
        "inflated_spending_at_payout_start": inflated_spending_at_payout_start,
        "payout_spending_ratio": payout_spending_ratio
    }


def generate_training_data(n=600):
    rows = []

    for i in range(n):
        member = make_random_member()

        shortfall_probability, _ = run_retirement_simulation(
            member,
            simulations=200,
            seed=1000 + i
        )

        row = build_feature_row(member)
        row["risk_label"] = label_from_shortfall(shortfall_probability)
        rows.append(row)

    return pd.DataFrame(rows)


def train_risk_model():
    df = generate_training_data()
    X = df[FEATURE_COLS]
    y = df["risk_label"]

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42
    )
    model.fit(X, y)
    return model


def save_model_and_metadata(model):
    joblib.dump(model, MODEL_PATH)
    joblib.dump({"feature_cols": FEATURE_COLS}, MODEL_METADATA_PATH)


@lru_cache(maxsize=1)
def load_or_train_model():
    if MODEL_PATH.exists() and MODEL_METADATA_PATH.exists():
        metadata = joblib.load(MODEL_METADATA_PATH)
        if metadata.get("feature_cols", []) == FEATURE_COLS:
            return joblib.load(MODEL_PATH)

    model = train_risk_model()
    save_model_and_metadata(model)
    return model


def predict_risk(member):
    model = load_or_train_model()

    row = build_feature_row(member)
    data = pd.DataFrame([row])[FEATURE_COLS]

    prediction = model.predict(data)[0]
    probabilities = model.predict_proba(data)[0]
    class_names = model.classes_

    prob_map = {
        class_names[i]: float(probabilities[i])
        for i in range(len(class_names))
    }

    return prediction, prob_map