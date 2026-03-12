# CPF AI Retirement Planner

A simplified CPF retirement projection and strategy simulator built with Streamlit.

This tool helps users estimate how their CPF balances may grow over time, compare projected CPF LIFE payouts against future spending needs, and understand the gap between benchmark retirement sums and personal retirement goals.

## What this app does

- Projects CPF balances across:
  - Ordinary Account (OA)
  - Special Account (SA)
  - MediSave Account (MA)
  - Retirement Account (RA)
- Estimates cohort-based:
  - Basic Retirement Sum (BRS)
  - Full Retirement Sum (FRS)
  - Enhanced Retirement Sum (ERS)
- Estimates CPF LIFE monthly payout under:
  - Standard
  - Basic
  - Escalating
- Compares projected payout against inflation-adjusted retirement spending
- Shows retirement target shortfall in RA terms
- Simulates early retirement scenarios
- Shows housing deduction impact in a simplified way
- Visualizes CPF growth and longevity risk

## Important disclaimer

This tool is for **educational planning support only**.

It is **not the official CPF estimator** and does **not** replace financial advice.  
Actual CPF balances, allocation rules, retirement sums, and CPF LIFE payouts depend on CPF Board policies and official calculations.

## Current model limitations

This app uses simplified assumptions for public planning use. For example:

- contribution allocation is simplified
- post-55 contribution handling is simplified
- CPF LIFE payout is estimated using a simplified payout factor
- housing and other OA usage are modeled in a simplified manner
- results should be treated as directional planning output, not exact CPF forecasts

## Tech stack

- Python
- Streamlit
- Pandas
- NumPy

## Project structure

Example structure:

```text
.
├── app.py
├── requirements.txt
├── README.md
└── ...
