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

## Cash Versus Retained Value

Use these two concepts distinctly:

```text
annual_take_home_cash =
  gross employment cash
  - employee housing fund
  - employee social insurance
  - IIT

annual_after_tax_value_including_housing_fund =
  annual_take_home_cash
  + employee housing fund
  + optional employer housing fund
```

The first figure answers liquid cash after payroll deductions. The second figure treats housing fund balances as retained employee value.

## Official Sources

- Individual Income Tax Law, State Taxation Administration Shanghai page: https://shanghai.chinatax.gov.cn/zcfw/zcfgk/grsds/201809/t441789.html
- Comprehensive income rate table PDF, State Taxation Administration policy database: https://fgk.chinatax.gov.cn/zcfgk/c100012/c5196787/5196787/files/%E4%B8%AA%E4%BA%BA%E6%89%80%E5%BE%97%E7%A8%8E%E7%A8%8E%E7%8E%87%E8%A1%A8%EF%BC%88%E7%BB%BC%E5%90%88%E6%89%80%E5%BE%97%E9%80%82%E7%94%A8%EF%BC%89.pdf
- 2025 comprehensive income annual settlement rules, State Taxation Administration: https://fgk.chinatax.gov.cn/zcfgk/c100011/c5238560/5238560/files/%E4%B8%AA%E4%BA%BA%E6%89%80%E5%BE%97%E7%A8%8E%E7%BB%BC%E5%90%88%E6%89%80%E5%BE%97%E6%B1%87%E7%AE%97%E6%B8%85%E7%BC%B4%E7%AE%A1%E7%90%86%E5%8A%9E%E6%B3%95.pdf
- Annual one-time bonus extension summary, State Taxation Administration: https://www.chinatax.gov.cn/chinatax/n810219/n810780/c5211283/content.html
- Annual one-time bonus Q&A, State Taxation Administration Shanghai page: https://shanghai.chinatax.gov.cn/zcfw/rdwd/202501/t474844.html
