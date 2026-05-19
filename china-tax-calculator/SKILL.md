---
name: china-tax-calculator
description: Calculate mainland China resident individual annual after-tax compensation from monthly base salary, employee housing provident fund, annual one-time bonus, signing bonus, social insurance, special additional deductions, and related cash or total-value assumptions. Use when Codex needs to estimate China mainland take-home pay, compare annual bonus separate taxation versus comprehensive-income taxation, explain IIT assumptions, or produce a reusable after-tax compensation breakdown.
---

# China Tax Calculator

## Core Workflow

Use `scripts/china_tax_calculator.py` for deterministic calculations. Read `references/china-mainland-iit-rules.md` when the user asks for assumptions, policy details, or a manual explanation.

1. Confirm the taxpayer is a mainland China resident individual and the income is employment compensation.
2. Normalize all amounts to RMB before calculating.
3. Treat `monthly_base` as monthly gross salary and multiply by `months`, default `12`.
4. Treat `housing_fund_monthly` as the employee-side monthly housing provident fund contribution. This is deducted from cash take-home and from taxable comprehensive income.
5. Treat `annual_bonus` as a potential "全年一次性奖金". The script can compare separate taxation with comprehensive-income taxation when the policy applies.
6. Treat `signing_bonus` as comprehensive income by default. Only combine it with the one-time bonus bucket when the user explicitly says the employer treats it as annual one-time bonus compensation.
7. Return both cash take-home and after-tax value including housing fund, because users may care about liquid income or total retained value.

## Quick Start

```bash
python3 scripts/china_tax_calculator.py \
  --monthly-base 50000 \
  --housing-fund-monthly 6000 \
  --annual-bonus 100000 \
  --signing-bonus 50000
```

Useful optional inputs:

- `--social-insurance-monthly`: employee-side pension, medical, unemployment, etc.
- `--special-additional-deductions-monthly`: monthly专项附加扣除 total.
- `--other-deductions-annual`: annual legally deductible items.
- `--employer-housing-fund-monthly`: employer-side housing fund for total-value reporting only.
- `--annual-bonus-treatment auto|separate|comprehensive`: default `auto` chooses the lower modeled IIT.
- `--signing-bonus-treatment comprehensive|one-time-bonus`: default `comprehensive`.
- `--json`: emit machine-readable JSON.

## Output Interpretation

The script reports:

- `annual_take_home_cash`: gross cash minus employee-side housing fund, employee-side social insurance, and individual income tax.
- `annual_after_tax_value_including_housing_fund`: cash take-home plus employee-side housing fund balance and optional employer-side housing fund.
- `total_iit`: total individual income tax across comprehensive income and any separate one-time bonus bucket.
- scenario comparisons when `--annual-bonus-treatment auto` is used.

## Boundaries

Do not model local social-insurance or housing-fund caps unless the user provides the exact monthly amounts. City contribution bases and rates vary, so this skill intentionally accepts already-computed monthly employee contributions.

Do not present the result as tax, legal, or payroll advice. State that it is an estimate based on the modeled inputs and current referenced rules.

For tax years after 2027, do not assume the annual one-time bonus separate-tax policy still applies. The script defaults to comprehensive taxation unless the user explicitly confirms and passes `--force-separate-bonus-after-2027`.
