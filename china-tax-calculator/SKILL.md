---
name: china-tax-calculator
description: Calculate mainland China resident individual annual and monthly after-tax compensation from monthly base salary, city social-insurance and housing-fund policies, annual one-time bonus, signing bonus, stock option spread, RSU vesting, restricted stock, share awards, taxable stock-sale gains, special additional deductions, and cash or total-value assumptions. Use when Codex needs to estimate China mainland take-home pay, compare separate taxation versus comprehensive-income taxation, explain IIT and contribution assumptions, or produce a reusable compensation breakdown.
---

# China Tax Calculator

## Core Workflow

Use `scripts/china_tax_calculator.py` for deterministic calculations. Read `references/china-mainland-iit-rules.md` when the user asks for assumptions, policy details, or a manual explanation.

1. Confirm the taxpayer is a mainland China resident individual and the income is employment compensation.
2. Normalize all amounts to RMB before calculating.
3. Treat `monthly_base` as monthly gross salary and multiply by `months`, default `12`.
4. If the user provides `housing_fund_monthly` or `social_insurance_monthly`, treat those as employee-side monthly amounts and prefer them over city-profile calculations.
5. If the user provides `--city beijing`, calculate monthly social insurance and housing fund from the local profile, contribution bases, and rates, applying the profile's min/max bases.
6. Treat `annual_bonus` as a potential "全年一次性奖金". The script can compare separate taxation with comprehensive-income taxation when the policy applies.
7. Treat `signing_bonus` as comprehensive income by default. Only combine it with the one-time bonus bucket when the user explicitly says the employer treats it as annual one-time bonus compensation.
8. Treat stock options, RSUs, restricted stock, and share awards as equity incentive income. Use direct `--equity-incentive-income` or event-specific helpers such as `--option-shares`, `--option-fmv`, `--option-strike`, and `--rsu-vest-value`.
9. Treat realized stock-sale gains separately from equity vest/exercise income. Use `--stock-sale-gain`, and add `--domestic-listed-stock-sale-exempt` only when the listed-stock transfer exemption applies.
10. Return cash take-home, social-insurance and housing-fund contributions, after-tax value including housing fund, and after-tax value including housing fund plus unsold equity.

## Quick Start

```bash
python3 scripts/china_tax_calculator.py \
  --monthly-base 50000 \
  --city beijing \
  --housing-fund-rate 12 \
  --annual-bonus 100000 \
  --signing-bonus 50000 \
  --rsu-vest-value 200000 \
  --monthly-breakdown
```

Useful optional inputs:

- `--social-insurance-monthly`: employee-side pension, medical, unemployment, etc.
- `--city beijing`: calculate Beijing social insurance and housing fund from local base caps and contribution rates.
- `--social-insurance-base` / `--housing-fund-base`: override the base used before city min/max clamping.
- `--housing-fund-rate`: employee housing-fund rate, e.g. `0.12` or `12`.
- `--employer-housing-fund-rate`: employer housing-fund rate; defaults to employee rate.
- `--special-additional-deductions-monthly`: monthly专项附加扣除 total.
- `--other-deductions-annual`: annual legally deductible items.
- `--employer-housing-fund-monthly`: employer-side housing fund override for total-value reporting.
- `--annual-bonus-treatment auto|separate|comprehensive`: default `auto` chooses the lower modeled IIT.
- `--signing-bonus-treatment comprehensive|one-time-bonus`: default `comprehensive`.
- `--equity-treatment auto|separate|comprehensive`: default `auto` compares eligible equity incentive separate taxation with comprehensive income taxation.
- `--equity-incentive-income`: direct taxable equity incentive income total.
- `--rsu-vest-value`, `--restricted-stock-value`, `--stock-award-value`: event-specific equity incentive inputs.
- `--option-spread`: direct option taxable spread, or use `--option-shares`, `--option-fmv`, and `--option-strike`.
- `--stock-sale-gain`: realized stock/equity sale gain.
- `--domestic-listed-stock-sale-exempt`: mark stock-sale gain as exempt when the domestic listed-stock exemption applies.
- `--monthly-breakdown`: emit month-by-month IIT, social insurance, housing fund, and take-home cash.
- `--annual-bonus-month`, `--signing-bonus-month`, `--equity-income-month`, `--stock-sale-month`: place event taxes into the chosen month for monthly breakdowns.
- `--json`: emit machine-readable JSON.

## Output Interpretation

The script reports:

- `annual_take_home_cash`: gross cash minus employee-side housing fund, employee-side social insurance, and individual income tax.
- `annual_after_tax_value_including_housing_fund`: cash take-home plus employee-side housing fund balance and optional employer-side housing fund.
- `annual_after_tax_value_including_housing_fund_and_equity`: above plus equity incentive value, useful when RSUs/options are not immediately sold.
- `contributions`: employee and employer monthly/annual social insurance and housing fund, with city-applied bases when available.
- `total_iit`: total individual income tax across comprehensive income, annual one-time bonus, equity incentive income, and stock sale gains.
- scenario comparisons when `--annual-bonus-treatment auto` or `--equity-treatment auto` is used.
- `monthly_breakdown`: present only when `--monthly-breakdown` is provided.

## Boundaries

City contribution bases and rates change over time. Prefer user-provided monthly amounts for exact payroll reconciliation. Use city profiles for planning estimates, and cite the profile snapshot in any user-facing answer.

Do not present the result as tax, legal, or payroll advice. State that it is an estimate based on the modeled inputs and current referenced rules.

For tax years after 2027, do not assume the annual one-time bonus separate-tax policy still applies. The script defaults to comprehensive taxation unless the user explicitly confirms and passes `--force-separate-bonus-after-2027`.

For tax years after 2027, do not assume equity incentive separate taxation still applies. The script defaults to comprehensive taxation unless the user explicitly confirms and passes `--force-separate-equity-after-2027`.
