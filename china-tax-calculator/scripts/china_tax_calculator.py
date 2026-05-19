#!/usr/bin/env python3
"""Estimate annual after-tax employment compensation for mainland China residents."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


CENT = Decimal("0.01")

ANNUAL_COMPREHENSIVE_BRACKETS = (
    (Decimal("36000"), Decimal("0.03"), Decimal("0")),
    (Decimal("144000"), Decimal("0.10"), Decimal("2520")),
    (Decimal("300000"), Decimal("0.20"), Decimal("16920")),
    (Decimal("420000"), Decimal("0.25"), Decimal("31920")),
    (Decimal("660000"), Decimal("0.30"), Decimal("52920")),
    (Decimal("960000"), Decimal("0.35"), Decimal("85920")),
    (None, Decimal("0.45"), Decimal("181920")),
)

MONTHLY_BONUS_BRACKETS = (
    (Decimal("3000"), Decimal("0.03"), Decimal("0")),
    (Decimal("12000"), Decimal("0.10"), Decimal("210")),
    (Decimal("25000"), Decimal("0.20"), Decimal("1410")),
    (Decimal("35000"), Decimal("0.25"), Decimal("2660")),
    (Decimal("55000"), Decimal("0.30"), Decimal("4410")),
    (Decimal("80000"), Decimal("0.35"), Decimal("7160")),
    (None, Decimal("0.45"), Decimal("15160")),
)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def parse_money(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"invalid decimal amount: {raw}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("amounts must be non-negative")
    return money(value)


def rate_for(taxable_income: Decimal, brackets: tuple[tuple[Decimal | None, Decimal, Decimal], ...]) -> tuple[Decimal, Decimal]:
    for ceiling, rate, quick_deduction in brackets:
        if ceiling is None or taxable_income <= ceiling:
            return rate, quick_deduction
    raise RuntimeError("unreachable tax bracket")


def progressive_tax(taxable_income: Decimal) -> Decimal:
    if taxable_income <= 0:
        return Decimal("0.00")
    rate, quick_deduction = rate_for(taxable_income, ANNUAL_COMPREHENSIVE_BRACKETS)
    return money(max(taxable_income * rate - quick_deduction, Decimal("0")))


def one_time_bonus_tax(bonus: Decimal) -> Decimal:
    if bonus <= 0:
        return Decimal("0.00")
    monthly_equivalent = bonus / Decimal("12")
    rate, quick_deduction = rate_for(monthly_equivalent, MONTHLY_BONUS_BRACKETS)
    return money(max(bonus * rate - quick_deduction, Decimal("0")))


def decimal_to_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, list):
        return [decimal_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: decimal_to_json(item) for key, item in value.items()}
    return value


def format_rmb(value: Decimal) -> str:
    return f"RMB {value:,.2f}"


def build_scenario(
    *,
    name: str,
    annual_base: Decimal,
    annual_bonus: Decimal,
    signing_bonus: Decimal,
    signing_bonus_treatment: str,
    employee_housing_fund: Decimal,
    employee_social_insurance: Decimal,
    employer_housing_fund: Decimal,
    standard_deduction_annual: Decimal,
    special_additional_deductions_annual: Decimal,
    other_deductions_annual: Decimal,
    separate_bonus: bool,
) -> dict[str, Any]:
    gross_income = annual_base + annual_bonus + signing_bonus
    annual_employee_contributions = employee_housing_fund + employee_social_insurance
    signing_in_bonus_bucket = signing_bonus_treatment == "one-time-bonus"

    if separate_bonus:
        one_time_bonus_income = annual_bonus + (signing_bonus if signing_in_bonus_bucket else Decimal("0"))
        comprehensive_income = annual_base + (Decimal("0") if signing_in_bonus_bucket else signing_bonus)
    else:
        one_time_bonus_income = Decimal("0")
        comprehensive_income = gross_income

    total_comprehensive_deductions = (
        standard_deduction_annual
        + employee_housing_fund
        + employee_social_insurance
        + special_additional_deductions_annual
        + other_deductions_annual
    )
    taxable_comprehensive_income = max(comprehensive_income - total_comprehensive_deductions, Decimal("0"))
    comprehensive_iit = progressive_tax(taxable_comprehensive_income)
    one_time_bonus_iit = one_time_bonus_tax(one_time_bonus_income)
    total_iit = comprehensive_iit + one_time_bonus_iit
    annual_take_home_cash = gross_income - annual_employee_contributions - total_iit
    annual_after_tax_value_including_housing_fund = (
        annual_take_home_cash + employee_housing_fund + employer_housing_fund
    )
    effective_iit_rate = Decimal("0.00")
    if gross_income > 0:
        effective_iit_rate = (total_iit / gross_income * Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "name": name,
        "gross_income": money(gross_income),
        "comprehensive_income": money(comprehensive_income),
        "total_comprehensive_deductions": money(total_comprehensive_deductions),
        "taxable_comprehensive_income": money(taxable_comprehensive_income),
        "comprehensive_iit": money(comprehensive_iit),
        "one_time_bonus_income": money(one_time_bonus_income),
        "one_time_bonus_iit": money(one_time_bonus_iit),
        "total_iit": money(total_iit),
        "annual_employee_contributions": money(annual_employee_contributions),
        "annual_take_home_cash": money(annual_take_home_cash),
        "annual_after_tax_value_including_housing_fund": money(annual_after_tax_value_including_housing_fund),
        "effective_iit_rate_percent": effective_iit_rate,
    }


def calculate(args: argparse.Namespace) -> dict[str, Any]:
    months = Decimal(args.months)
    annual_base = money(args.monthly_base * months)
    employee_housing_fund = money(args.housing_fund_monthly * months)
    employee_social_insurance = money(args.social_insurance_monthly * months)
    employer_housing_fund = money(args.employer_housing_fund_monthly * months)
    special_additional_deductions_annual = money(args.special_additional_deductions_monthly * months)
    annual_bonus = args.annual_bonus
    signing_bonus = args.signing_bonus

    separate_bonus_allowed = args.tax_year <= 2027 or args.force_separate_bonus_after_2027
    notes: list[str] = []
    scenarios: list[dict[str, Any]] = []

    comprehensive = build_scenario(
        name="comprehensive",
        annual_base=annual_base,
        annual_bonus=annual_bonus,
        signing_bonus=signing_bonus,
        signing_bonus_treatment=args.signing_bonus_treatment,
        employee_housing_fund=employee_housing_fund,
        employee_social_insurance=employee_social_insurance,
        employer_housing_fund=employer_housing_fund,
        standard_deduction_annual=args.standard_deduction_annual,
        special_additional_deductions_annual=special_additional_deductions_annual,
        other_deductions_annual=args.other_deductions_annual,
        separate_bonus=False,
    )
    scenarios.append(comprehensive)

    separate = None
    bonus_bucket_amount = annual_bonus + (
        signing_bonus if args.signing_bonus_treatment == "one-time-bonus" else Decimal("0")
    )
    if bonus_bucket_amount > 0 and separate_bonus_allowed:
        separate = build_scenario(
            name="separate_one_time_bonus",
            annual_base=annual_base,
            annual_bonus=annual_bonus,
            signing_bonus=signing_bonus,
            signing_bonus_treatment=args.signing_bonus_treatment,
            employee_housing_fund=employee_housing_fund,
            employee_social_insurance=employee_social_insurance,
            employer_housing_fund=employer_housing_fund,
            standard_deduction_annual=args.standard_deduction_annual,
            special_additional_deductions_annual=special_additional_deductions_annual,
            other_deductions_annual=args.other_deductions_annual,
            separate_bonus=True,
        )
        scenarios.append(separate)

    if args.annual_bonus_treatment == "separate" and not separate_bonus_allowed:
        raise SystemExit(
            "Annual one-time bonus separate taxation is modeled through 2027-12-31. "
            "Pass --force-separate-bonus-after-2027 only after confirming the policy still applies."
        )

    if args.annual_bonus_treatment == "comprehensive" or separate is None:
        selected = comprehensive
        if args.annual_bonus_treatment == "auto" and bonus_bucket_amount > 0 and not separate_bonus_allowed:
            notes.append("Separate annual one-time bonus taxation was not assumed after 2027.")
    elif args.annual_bonus_treatment == "separate":
        selected = separate
    else:
        selected = min(scenarios, key=lambda scenario: scenario["total_iit"])

    if (
        args.signing_bonus_treatment == "one-time-bonus"
        and selected["one_time_bonus_income"] >= signing_bonus
        and signing_bonus > 0
    ):
        notes.append("Signing bonus was combined into the single annual one-time bonus bucket.")

    return {
        "inputs": {
            "tax_year": args.tax_year,
            "months": args.months,
            "monthly_base": args.monthly_base,
            "housing_fund_monthly_employee": args.housing_fund_monthly,
            "social_insurance_monthly_employee": args.social_insurance_monthly,
            "employer_housing_fund_monthly": args.employer_housing_fund_monthly,
            "annual_bonus": annual_bonus,
            "signing_bonus": signing_bonus,
            "annual_bonus_treatment": args.annual_bonus_treatment,
            "signing_bonus_treatment": args.signing_bonus_treatment,
            "standard_deduction_annual": args.standard_deduction_annual,
            "special_additional_deductions_annual": special_additional_deductions_annual,
            "other_deductions_annual": args.other_deductions_annual,
        },
        "selected": selected,
        "scenarios": scenarios,
        "notes": notes,
    }


def print_text(result: dict[str, Any]) -> None:
    selected = result["selected"]
    print(f"Selected scenario: {selected['name']}")
    print(f"Annual gross income: {format_rmb(selected['gross_income'])}")
    print(f"Taxable comprehensive income: {format_rmb(selected['taxable_comprehensive_income'])}")
    print(f"Comprehensive IIT: {format_rmb(selected['comprehensive_iit'])}")
    print(f"One-time bonus IIT: {format_rmb(selected['one_time_bonus_iit'])}")
    print(f"Total IIT: {format_rmb(selected['total_iit'])}")
    print(f"Employee contributions withheld: {format_rmb(selected['annual_employee_contributions'])}")
    print(f"Annual take-home cash: {format_rmb(selected['annual_take_home_cash'])}")
    print(
        "Annual after-tax value including housing fund: "
        f"{format_rmb(selected['annual_after_tax_value_including_housing_fund'])}"
    )
    print(f"Effective IIT rate on gross income: {selected['effective_iit_rate_percent']}%")

    if len(result["scenarios"]) > 1:
        print()
        print("Scenario comparison:")
        for scenario in result["scenarios"]:
            print(
                f"- {scenario['name']}: total IIT {format_rmb(scenario['total_iit'])}, "
                f"take-home cash {format_rmb(scenario['annual_take_home_cash'])}"
            )

    if result["notes"]:
        print()
        print("Notes:")
        for note in result["notes"]:
            print(f"- {note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate mainland China resident annual after-tax employment compensation."
    )
    parser.add_argument("--monthly-base", type=parse_money, required=True, help="Monthly gross base salary in RMB.")
    parser.add_argument("--months", type=int, default=12, choices=range(1, 13), metavar="{1..12}")
    parser.add_argument(
        "--housing-fund-monthly",
        type=parse_money,
        default=Decimal("0.00"),
        help="Employee-side monthly housing provident fund contribution.",
    )
    parser.add_argument(
        "--social-insurance-monthly",
        type=parse_money,
        default=Decimal("0.00"),
        help="Employee-side monthly social insurance contribution.",
    )
    parser.add_argument(
        "--employer-housing-fund-monthly",
        type=parse_money,
        default=Decimal("0.00"),
        help="Employer-side monthly housing fund contribution, used only in total-value reporting.",
    )
    parser.add_argument("--annual-bonus", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--signing-bonus", type=parse_money, default=Decimal("0.00"))
    parser.add_argument(
        "--annual-bonus-treatment",
        choices=("auto", "separate", "comprehensive"),
        default="auto",
        help="Use auto to choose the lower modeled IIT when separate bonus taxation is available.",
    )
    parser.add_argument(
        "--signing-bonus-treatment",
        choices=("comprehensive", "one-time-bonus"),
        default="comprehensive",
        help="Use one-time-bonus only when the employer treats signing bonus as part of the annual one-time bonus.",
    )
    parser.add_argument("--tax-year", type=int, default=date.today().year)
    parser.add_argument("--standard-deduction-annual", type=parse_money, default=Decimal("60000.00"))
    parser.add_argument("--special-additional-deductions-monthly", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--other-deductions-annual", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--force-separate-bonus-after-2027", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = calculate(args)
    if args.json:
        print(json.dumps(decimal_to_json(result), ensure_ascii=False, indent=2))
    else:
        print_text(result)


if __name__ == "__main__":
    main()
