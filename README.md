# CPF AI Retirement Planner

A public-facing educational retirement planning web app built with Streamlit.

This tool helps users explore CPF retirement scenarios, estimate CPF LIFE payouts, compare strategies, and understand possible ways to improve retirement adequacy using a simplified planning model.

## Features

- CPF LIFE payout projection
- Retirement gap analysis
- Benchmark comparison against estimated BRS / FRS / ERS
- Early retirement scenario comparison
- Housing impact simulation
- SA cash top-up simulation
- OA to SA transfer simulation
- Property pledge benchmark interpretation
- Recommendation engine for possible improvement actions
- AI Retirement Coach using OpenAI for plain-English explanations

## How it works

The app uses a rule-based CPF simulation engine to project retirement outcomes based on user inputs such as:

- current age
- stop work age
- payout start age
- salary
- retirement spending target
- OA / SA / MA balances
- housing usage
- SA cash top-ups
- OA to SA transfers

The AI layer does not perform the core retirement calculations.  
Instead, it uses OpenAI to explain the results in plain English, answer user questions, and highlight possible next steps.

## Important note

This planner is for **educational planning support only**.

It does **not** replace:
- the official CPF estimator
- professional financial advice
- actual CPF Board calculations and policies

Some features use simplified assumptions, including:
- SA cash top-up applied only before age 55
- OA to SA transfer applied only before age 55
- property pledge affects benchmark interpretation only in this version
- impact estimates are directional and may not add up exactly

## Tech stack

- Python
- Streamlit
- Pandas
- NumPy
- OpenAI API

## Run locally

Install dependencies:

```bash
pip install -r requirements.txt