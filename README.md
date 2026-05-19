# China Tax Calculator Skill

这是一个 Codex skill，用于估算中国大陆居民个人的年度和月度税后收入。它按月 base、城市社保/公积金规则、年终奖、签字费、option、RSU、限制性股票、股权奖励、股票卖出收益、专项附加扣除等输入，输出现金税后、包含公积金后的税后总价值、社保/公积金缴纳额和可选月度明细。

## 安装到 Codex

如果已经 clone 了这个仓库，可以直接把 skill 目录链接到 Codex skill 目录：

```bash
ln -s "$(pwd)/china-tax-calculator" "${CODEX_HOME:-$HOME/.codex}/skills/china-tax-calculator"
```

安装后重启 Codex，让新 skill 被自动发现。

## 使用 Codex Skill

重启 Codex 后，可以这样问：

```text
使用 $china-tax-calculator，帮我算：
北京，月 base 50000，公积金 12%，年终奖 100000，签字费 50000，RSU vest 200000，每年税后多少？顺便给我每月税额和社保公积金。
```

也可以补充更多输入：

```text
使用 $china-tax-calculator，月 base 80000，北京社保公积金，公积金比例 12%，专项附加扣除 2000/月，年终 300000，签字费 100000，option spread 500000，帮我比较年终奖和股权激励单独计税/并入综合所得。
```

## 直接运行计算脚本

```bash
cd china-tax-calculator
python3 scripts/china_tax_calculator.py \
  --monthly-base 50000 \
  --city beijing \
  --housing-fund-rate 12 \
  --annual-bonus 100000 \
  --signing-bonus 50000 \
  --rsu-vest-value 200000 \
  --monthly-breakdown
```

常用参数：

```bash
--social-insurance-monthly 3000
--city beijing
--social-insurance-base 50000
--housing-fund-base 50000
--housing-fund-rate 12
--special-additional-deductions-monthly 2000
--employer-housing-fund-monthly 6000
--annual-bonus-treatment auto
--signing-bonus-treatment comprehensive
--equity-treatment auto
--option-shares 10000 --option-fmv 50 --option-strike 10
--rsu-vest-value 200000
--stock-sale-gain 50000
--domestic-listed-stock-sale-exempt
--monthly-breakdown
--json
```

字段含义：

- `--monthly-base`：月度税前 base。
- `--city beijing`：按北京 2025 缴费年度 profile 计算社保和公积金基数上下限。
- `--housing-fund-monthly`：个人每月实际缴纳的公积金金额；如果提供，会覆盖城市 profile 计算。
- `--social-insurance-monthly`：个人每月社保扣款；如果提供，会覆盖城市 profile 计算。
- `--social-insurance-base` / `--housing-fund-base`：社保/公积金缴费基数，城市 profile 会套上下限。
- `--housing-fund-rate`：公积金个人缴纳比例，`12` 和 `0.12` 都可以。
- `--annual-bonus`：年终奖，默认可参与“全年一次性奖金”单独计税比较。
- `--signing-bonus`：签字费，默认按综合所得处理。
- `--annual-bonus-treatment auto`：自动选择年终奖单独计税或并入综合所得中税额更低的方案。
- `--signing-bonus-treatment one-time-bonus`：只有在雇主明确把签字费按全年一次性奖金处理时才使用。
- `--equity-incentive-income`：直接输入股权激励应税收入总额。
- `--rsu-vest-value`：RSU vest 当年应税价值。
- `--restricted-stock-value`：限制性股票当年应税价值。
- `--stock-award-value`：股权奖励当年应税价值。
- `--option-spread`：直接输入期权行权价差；也可以用 `--option-shares`、`--option-fmv`、`--option-strike` 自动算。
- `--equity-treatment auto`：自动比较股权激励单独计税和并入综合所得。
- `--stock-sale-gain`：股票/股权卖出已实现收益；默认按财产转让所得 20% 估算。
- `--domestic-listed-stock-sale-exempt`：确认适用个人转让上市公司股票暂免时使用。
- `--monthly-breakdown`：返回每月个税、社保、公积金和现金到手。
- `--annual-bonus-month` / `--signing-bonus-month` / `--equity-income-month` / `--stock-sale-month`：控制月度明细里事件发生月份。

输出里：

- `annual_take_home_cash` 是年度现金税后收入。
- `annual_after_tax_value_including_housing_fund` 是现金税后加个人公积金余额和可选公司公积金后的总价值。
- `annual_after_tax_value_including_housing_fund_and_equity` 是再加上 RSU/option/股权激励价值后的总税后价值。
- `contributions` 会拆出个人/公司每月和每年的社保、公积金缴纳额。
- `monthly_breakdown` 在传入 `--monthly-breakdown` 时返回每月税额、社保、公积金、到手现金。
- `total_iit` 是估算个人所得税总额。

## 使用 npx add 安装

这个仓库包含一个 npm CLI 入口，命令名是 `add`。当前可以直接从 GitHub 运行：

```bash
npx --yes --package github:haoyang9804/tax_calculator_skill_for_Chinese_Mainlander add
```

如果需要走 SSH：

```bash
npx --yes --package git+ssh://git@github.com/haoyang9804/tax_calculator_skill_for_Chinese_Mainlander.git add
```

它会把 `china-tax-calculator` 安装到：

```text
${CODEX_HOME:-$HOME/.codex}/skills/china-tax-calculator
```

如果目标目录已经存在，命令会跳过覆盖。需要强制覆盖时：

```bash
npx --yes --package github:haoyang9804/tax_calculator_skill_for_Chinese_Mainlander add --force
```

如果之后发布到 npm，可以使用：

```bash
npm publish
npx --yes --package tax-calculator-skill-for-chinese-mainlander add
```

注意：字面量 `npx add` 只有在 npm 上存在名为 `add` 的包并且这个包暴露 `add` 命令时才成立。这个仓库已经把二进制命令命名为 `add`，因此推荐的形式是 `npx --package <这个包或 GitHub 仓库> add`。这也是不抢占通用包名的更稳妥做法。

## 税制边界

该 skill 只做估算，不构成税务、法律或薪酬建议。城市社保和公积金政策变化很快；北京 profile 是按参考文档中的政策快照建模，精确 payroll reconciliation 仍应优先使用个人实际月缴金额。全年一次性奖金和上市公司股权激励单独计税政策按参考文档建模，2027 年之后默认不再假设相关政策继续有效。
