# Mainland China Resident IIT Rules

Policy snapshot: checked on 2026-05-19. Re-check official sources before changing embedded thresholds or using this skill for later tax years.

## Resident Comprehensive Income

For resident individuals, comprehensive income includes wages and salaries, labor service remuneration, author's remuneration, and royalties. Employment compensation such as monthly base salary and ordinary signing bonus should normally be modeled as wages and salaries within annual comprehensive income.

Annual taxable comprehensive income:

```text
comprehensive income
- 60000 standard deduction
- employee-side social insurance and housing provident fund special deductions
- special additional deductions
- other legally determined deductions
```

Annual comprehensive income tax rates:

| Annual taxable income | Rate | Quick deduction |
| --- | ---: | ---: |
| <= 36,000 | 3% | 0 |
| > 36,000 and <= 144,000 | 10% | 2,520 |
| > 144,000 and <= 300,000 | 20% | 16,920 |
| > 300,000 and <= 420,000 | 25% | 31,920 |
| > 420,000 and <= 660,000 | 30% | 52,920 |
| > 660,000 and <= 960,000 | 35% | 85,920 |
| > 960,000 | 45% | 181,920 |

Tax formula:

```text
tax = annual taxable income * rate - quick deduction
```

## Annual One-Time Bonus

Through 2027-12-31, qualifying annual one-time bonus can either:

1. be taxed separately, or
2. be included in annual comprehensive income.

For separate taxation:

```text
monthly-equivalent = annual one-time bonus / 12
bonus tax = annual one-time bonus * applicable monthly rate - monthly quick deduction
```

Monthly converted comprehensive rate table:

| Monthly equivalent | Rate | Quick deduction |
| --- | ---: | ---: |
| <= 3,000 | 3% | 0 |
| > 3,000 and <= 12,000 | 10% | 210 |
| > 12,000 and <= 25,000 | 20% | 1,410 |
| > 25,000 and <= 35,000 | 25% | 2,660 |
| > 35,000 and <= 55,000 | 30% | 4,410 |
| > 55,000 and <= 80,000 | 35% | 7,160 |
| > 80,000 | 45% | 15,160 |

The separate annual bonus method can be used only once per taxpayer per tax year. Do not split multiple bonuses into multiple separate-tax buckets.

## Equity Incentives: Options, RSUs, Restricted Stock, Share Awards

For resident individuals, qualifying listed-company equity incentives can be taxed separately through 2027-12-31. Covered instruments include stock options, stock appreciation rights, restricted stock, and equity awards. The policy text uses "股权激励"; this skill maps common user wording as follows:

| User wording | Model as |
| --- | --- |
| option / 股票期权 | taxable option spread, usually fair market value minus strike price times exercised shares |
| RSU | RSU vest value |
| restricted stock / 限制性股票 | restricted stock taxable value |
| stock award / 股权奖励 | share award taxable value |

When separate equity-incentive taxation applies:

```text
equity incentive tax = equity incentive taxable income * annual comprehensive rate - annual quick deduction
```

Use the annual comprehensive income rate table above, not the annual one-time bonus monthly-equivalent table. If a resident individual obtains equity incentives more than once in the same tax year, combine them for this calculation.

If the separate policy does not apply, or if the user requests comprehensive treatment, include the equity incentive income in annual comprehensive income.

## Stock or Equity Sale Gains

Do not mix equity vest/exercise income with later stock sale gains.

For taxable stock or equity sale gains:

```text
taxable gain = transfer income - original value - reasonable expenses
tax = taxable gain * 20%
```

Personal transfers of listed-company shares have a continuing exemption in some cases. Use `--domestic-listed-stock-sale-exempt` only when the user confirms the listed-stock transfer exemption applies. For overseas stock sale gains, restricted shares, private equity, or other taxable property-transfer cases, use `--stock-sale-gain` without the exemption flag unless the user provides a contrary basis.

## Local Contributions: Beijing Profile

City contribution rules are local and time sensitive. The script currently includes `--city beijing` as a built-in planning profile for the 2025 contribution year.

Beijing 2025 profile:

| Item | Monthly base min | Monthly base max |
| --- | ---: | ---: |
| Social insurance | 7,162 | 35,811 |
| Housing fund | 2,540 | 35,811 |

Default Beijing employee social insurance rates in the script:

| Item | Employee rate |
| --- | ---: |
| Pension | 8% |
| Medical | 2% + RMB 3/month |
| Unemployment | 0.5% |

Default Beijing employer social insurance rates in the script:

| Item | Employer rate |
| --- | ---: |
| Pension | 16% |
| Medical including maternity | 9.8% |
| Unemployment | 0.5% |
| Work injury | 0.2%, override with `--work-injury-rate` |

Beijing housing fund rates are selected by the employer within the allowed range. The script defaults to 12% for planning and allows override with `--housing-fund-rate` and `--employer-housing-fund-rate`.

Manual monthly contribution inputs override city-profile calculations:

```text
--social-insurance-monthly
--housing-fund-monthly
--employer-social-insurance-monthly
--employer-housing-fund-monthly
```

## Monthly Breakdown

With `--monthly-breakdown`, the script estimates monthly withholding using cumulative comprehensive-income withholding:

```text
cumulative taxable comprehensive income
= cumulative comprehensive income
- cumulative standard deduction
- cumulative employee social insurance
- cumulative employee housing fund
- cumulative special additional deductions
- cumulative other deductions
```

Monthly comprehensive IIT equals cumulative comprehensive IIT minus prior-month cumulative comprehensive IIT.

Separate annual bonus tax, separate equity incentive tax, and stock-sale tax are assigned to the event month:

```text
--annual-bonus-month
--signing-bonus-month
--equity-income-month
--stock-sale-month
```

This is an estimate for planning. Actual employer withholding can differ based on payroll timing, filings, and local handling.

## Cash Versus Retained Value

Use these two concepts distinctly:

```text
annual_take_home_cash =
  gross cash income
  - employee housing fund
  - employee social insurance
  - IIT

annual_after_tax_value_including_housing_fund =
  annual_take_home_cash
  + employee housing fund
  + optional employer housing fund

annual_after_tax_value_including_housing_fund_and_equity =
  annual_after_tax_value_including_housing_fund
  + equity incentive value
```

The first figure answers liquid cash after payroll deductions and tax. The second figure treats housing fund balances as retained employee value. The third figure also includes unsold equity incentive value such as RSU vest value or option spread.

## Official Sources

- Individual Income Tax Law, State Taxation Administration Shanghai page: https://shanghai.chinatax.gov.cn/zcfw/zcfgk/grsds/201809/t441789.html
- Comprehensive income rate table PDF, State Taxation Administration policy database: https://fgk.chinatax.gov.cn/zcfgk/c100012/c5196787/5196787/files/%E4%B8%AA%E4%BA%BA%E6%89%80%E5%BE%97%E7%A8%8E%E7%A8%8E%E7%8E%87%E8%A1%A8%EF%BC%88%E7%BB%BC%E5%90%88%E6%89%80%E5%BE%97%E9%80%82%E7%94%A8%EF%BC%89.pdf
- 2025 comprehensive income annual settlement rules, State Taxation Administration: https://fgk.chinatax.gov.cn/zcfgk/c100011/c5238560/5238560/files/%E4%B8%AA%E4%BA%BA%E6%89%80%E5%BE%97%E7%A8%8E%E7%BB%BC%E5%90%88%E6%89%80%E5%BE%97%E6%B1%87%E7%AE%97%E6%B8%85%E7%BC%B4%E7%AE%A1%E7%90%86%E5%8A%9E%E6%B3%95.pdf
- Annual one-time bonus extension summary, State Taxation Administration: https://www.chinatax.gov.cn/chinatax/n810219/n810780/c5211283/content.html
- Annual one-time bonus Q&A, State Taxation Administration Shanghai page: https://shanghai.chinatax.gov.cn/zcfw/rdwd/202501/t474844.html
- Listed-company equity incentive IIT extension, Ministry of Finance: https://szs.mof.gov.cn/zhengcefabu/202308/t20230822_3903474.htm
- Listed-company equity incentive IIT summary, State Taxation Administration Fujian page: https://fujian.chinatax.gov.cn/bsfw/sfyhzc/grsds/202310/t20231019_532150.html
- 2025 Beijing housing fund contribution base limits, Beijing public service page: https://banshi.beijing.gov.cn/zcjd/202509/t20250925_428450.html
- 2025 Beijing social-insurance contribution base limits, Beijing municipal portal: https://www.beijing.gov.cn/fuwu/bmfw/sy/jrts/tzxx/202509/t20250919_4205649.html
- Individual stock transfer exemption, State Taxation Administration Liaoning page: https://liaoning.chinatax.gov.cn/art/2020/9/14/art_1991_49409.html
- Taxable restricted-share transfer formula, State Taxation Administration Shanghai page: https://shanghai.chinatax.gov.cn/zcfw/rdwd/201205/t398804.html
