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

PROPERTY_TRANSFER_TAX_RATE = Decimal("0.20")

CITY_PROFILES = {
    "beijing": {
        "label": "Beijing 2025 contribution year, 2025-07 to 2026-06",
        "social_base_min": Decimal("7162"),
        "social_base_max": Decimal("35811"),
        "housing_fund_base_min": Decimal("2540"),
        "housing_fund_base_max": Decimal("35811"),
        "default_housing_fund_rate": Decimal("0.12"),
        "employee_social_rates": {
            "pension": Decimal("0.08"),
            "medical": Decimal("0.02"),
            "unemployment": Decimal("0.005"),
        },
        "employee_medical_fixed": Decimal("3"),
        "employer_social_rates": {
            "pension": Decimal("0.16"),
            "medical_maternity": Decimal("0.098"),
            "unemployment": Decimal("0.005"),
            "work_injury": Decimal("0.002"),
        },
    },
}


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


def parse_non_negative_decimal(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"invalid decimal value: {raw}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("values must be non-negative")
    return value


def parse_rate(raw: str) -> Decimal:
    value = parse_non_negative_decimal(raw)
    if value > 1:
        value = value / Decimal("100")
    if value > 1:
        raise argparse.ArgumentTypeError("rates must be a decimal fraction or percentage from 0 to 100")
    return value


def clamp(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return min(max(value, lower), upper)


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


def proportional_tax(taxable_income: Decimal, rate: Decimal) -> Decimal:
    if taxable_income <= 0:
        return Decimal("0.00")
    return money(taxable_income * rate)


def calculated_option_spread(args: argparse.Namespace) -> Decimal:
    option_fields = (args.option_shares, args.option_fmv, args.option_strike)
    if not any(value is not None for value in option_fields):
        return Decimal("0.00")
    if any(value is None for value in option_fields):
        raise SystemExit("--option-shares, --option-fmv, and --option-strike must be provided together.")
    per_share_spread = max(args.option_fmv - args.option_strike, Decimal("0"))
    return money(args.option_shares * per_share_spread)


def total_equity_incentive_income(args: argparse.Namespace) -> Decimal:
    return money(
        args.equity_incentive_income
        + args.rsu_vest_value
        + args.restricted_stock_value
        + args.stock_award_value
        + args.option_spread
        + calculated_option_spread(args)
    )


def monthly_components(base: Decimal, rates: dict[str, Decimal], fixed: dict[str, Decimal] | None = None) -> dict[str, Decimal]:
    components = {name: money(base * rate) for name, rate in rates.items()}
    if fixed:
        for name, amount in fixed.items():
            components[name] = money(components.get(name, Decimal("0.00")) + amount)
    components["total"] = money(sum(components.values(), Decimal("0.00")))
    return components


def build_contributions(args: argparse.Namespace) -> dict[str, Any]:
    profile = CITY_PROFILES.get(args.city) if args.city else None
    notes: list[str] = []

    employee_social_monthly = args.social_insurance_monthly
    employer_social_monthly = args.employer_social_insurance_monthly
    employee_housing_monthly = args.housing_fund_monthly
    employer_housing_monthly = args.employer_housing_fund_monthly

    employee_social_components = {"manual": employee_social_monthly} if employee_social_monthly is not None else {}
    employer_social_components = {"manual": employer_social_monthly} if employer_social_monthly is not None else {}

    social_base = args.social_insurance_base or args.monthly_base
    housing_base = args.housing_fund_base or args.monthly_base
    applied_social_base = social_base
    applied_housing_base = housing_base

    if profile:
        applied_social_base = clamp(social_base, profile["social_base_min"], profile["social_base_max"])
        applied_housing_base = clamp(housing_base, profile["housing_fund_base_min"], profile["housing_fund_base_max"])
        notes.append(f"Applied city profile: {profile['label']}.")

        if employee_social_monthly is None:
            employee_social_components = monthly_components(
                applied_social_base,
                profile["employee_social_rates"],
                {"medical_fixed": profile["employee_medical_fixed"]},
            )
            employee_social_monthly = employee_social_components["total"]

        if employer_social_monthly is None:
            employer_rates = dict(profile["employer_social_rates"])
            if args.work_injury_rate is not None:
                employer_rates["work_injury"] = args.work_injury_rate
            employer_social_components = monthly_components(applied_social_base, employer_rates)
            employer_social_monthly = employer_social_components["total"]

        housing_rate = args.housing_fund_rate or profile["default_housing_fund_rate"]
        employer_housing_rate = args.employer_housing_fund_rate or housing_rate
        if employee_housing_monthly is None:
            employee_housing_monthly = money(applied_housing_base * housing_rate)
        if employer_housing_monthly is None:
            employer_housing_monthly = money(applied_housing_base * employer_housing_rate)
    else:
        employee_social_monthly = employee_social_monthly or Decimal("0.00")
        employer_social_monthly = employer_social_monthly or Decimal("0.00")
        employee_housing_monthly = employee_housing_monthly or Decimal("0.00")
        employer_housing_monthly = employer_housing_monthly or Decimal("0.00")

    months = Decimal(args.months)
    return {
        "city": args.city,
        "social_insurance_base_input": money(social_base),
        "housing_fund_base_input": money(housing_base),
        "social_insurance_base_applied": money(applied_social_base),
        "housing_fund_base_applied": money(applied_housing_base),
        "employee_social_insurance_monthly": money(employee_social_monthly),
        "employee_social_insurance_annual": money(employee_social_monthly * months),
        "employee_social_insurance_monthly_components": employee_social_components,
        "employer_social_insurance_monthly": money(employer_social_monthly),
        "employer_social_insurance_annual": money(employer_social_monthly * months),
        "employer_social_insurance_monthly_components": employer_social_components,
        "employee_housing_fund_monthly": money(employee_housing_monthly),
        "employee_housing_fund_annual": money(employee_housing_monthly * months),
        "employer_housing_fund_monthly": money(employer_housing_monthly),
        "employer_housing_fund_annual": money(employer_housing_monthly * months),
        "employee_contributions_monthly": money(employee_social_monthly + employee_housing_monthly),
        "employee_contributions_annual": money((employee_social_monthly + employee_housing_monthly) * months),
        "employer_contributions_monthly": money(employer_social_monthly + employer_housing_monthly),
        "employer_contributions_annual": money((employer_social_monthly + employer_housing_monthly) * months),
        "notes": notes,
    }


def month_index(value: int, name: str, max_months: int) -> int:
    if value < 1 or value > max_months:
        raise SystemExit(f"{name} must be from 1 to {max_months}.")
    return value


def build_monthly_breakdown(
    *,
    args: argparse.Namespace,
    selected: dict[str, Any],
    annual_base: Decimal,
    annual_bonus: Decimal,
    signing_bonus: Decimal,
    equity_incentive_income: Decimal,
    stock_sale_gain: Decimal,
    contributions: dict[str, Any],
) -> list[dict[str, Any]]:
    bonus_month = month_index(args.annual_bonus_month, "--annual-bonus-month", args.months)
    signing_month = month_index(args.signing_bonus_month, "--signing-bonus-month", args.months)
    equity_month = month_index(args.equity_income_month, "--equity-income-month", args.months)
    stock_sale_month = month_index(args.stock_sale_month, "--stock-sale-month", args.months)

    monthly_base = money(annual_base / Decimal(args.months))
    employee_housing_fund_monthly = contributions["employee_housing_fund_monthly"]
    employee_social_insurance_monthly = contributions["employee_social_insurance_monthly"]
    special_deduction_monthly = args.special_additional_deductions_monthly
    standard_deduction_monthly = money(args.standard_deduction_annual / Decimal("12"))
    other_deductions_monthly = money(args.other_deductions_annual / Decimal("12"))

    cumulative_comprehensive_income = Decimal("0.00")
    cumulative_deductions = Decimal("0.00")
    previous_comprehensive_tax = Decimal("0.00")
    rows: list[dict[str, Any]] = []

    for month in range(1, args.months + 1):
        comprehensive_income_this_month = monthly_base
        if month == signing_month and not (
            selected["separate_bonus"] and args.signing_bonus_treatment == "one-time-bonus"
        ):
            comprehensive_income_this_month += signing_bonus
        if month == bonus_month and not selected["separate_bonus"]:
            comprehensive_income_this_month += annual_bonus
        if month == equity_month and not selected["separate_equity"]:
            comprehensive_income_this_month += equity_incentive_income

        monthly_deductions = (
            standard_deduction_monthly
            + employee_housing_fund_monthly
            + employee_social_insurance_monthly
            + special_deduction_monthly
            + other_deductions_monthly
        )
        cumulative_comprehensive_income += comprehensive_income_this_month
        cumulative_deductions += monthly_deductions
        cumulative_taxable = max(cumulative_comprehensive_income - cumulative_deductions, Decimal("0.00"))
        cumulative_comprehensive_tax = progressive_tax(cumulative_taxable)
        comprehensive_tax_this_month = money(cumulative_comprehensive_tax - previous_comprehensive_tax)
        previous_comprehensive_tax = cumulative_comprehensive_tax

        one_time_bonus_tax_this_month = Decimal("0.00")
        if selected["separate_bonus"] and month == bonus_month:
            one_time_bonus_tax_this_month += selected["one_time_bonus_iit"]

        equity_tax_this_month = Decimal("0.00")
        if selected["separate_equity"] and month == equity_month:
            equity_tax_this_month += selected["equity_incentive_iit"]

        stock_sale_tax_this_month = Decimal("0.00")
        stock_sale_cash_this_month = Decimal("0.00")
        if month == stock_sale_month:
            stock_sale_tax_this_month += selected["stock_sale_iit"]
            stock_sale_cash_this_month += stock_sale_gain

        total_iit_this_month = money(
            comprehensive_tax_this_month
            + one_time_bonus_tax_this_month
            + equity_tax_this_month
            + stock_sale_tax_this_month
        )
        cash_income_this_month = monthly_base + stock_sale_cash_this_month
        if month == signing_month:
            cash_income_this_month += signing_bonus
        if month == bonus_month:
            cash_income_this_month += annual_bonus

        rows.append(
            {
                "month": month,
                "cash_income": money(cash_income_this_month),
                "comprehensive_income": money(comprehensive_income_this_month),
                "employee_social_insurance": money(employee_social_insurance_monthly),
                "employee_housing_fund": money(employee_housing_fund_monthly),
                "monthly_deductions_for_comprehensive_iit": money(monthly_deductions),
                "cumulative_taxable_comprehensive_income": money(cumulative_taxable),
                "comprehensive_iit": money(comprehensive_tax_this_month),
                "one_time_bonus_iit": money(one_time_bonus_tax_this_month),
                "equity_incentive_iit": money(equity_tax_this_month),
                "stock_sale_iit": money(stock_sale_tax_this_month),
                "total_iit": total_iit_this_month,
                "take_home_cash": money(
                    cash_income_this_month
                    - employee_social_insurance_monthly
                    - employee_housing_fund_monthly
                    - total_iit_this_month
                ),
            }
        )

    return rows


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
    equity_incentive_income: Decimal,
    stock_sale_gain: Decimal,
    stock_sale_taxable: bool,
    employee_housing_fund: Decimal,
    employee_social_insurance: Decimal,
    employer_housing_fund: Decimal,
    standard_deduction_annual: Decimal,
    special_additional_deductions_annual: Decimal,
    other_deductions_annual: Decimal,
    separate_bonus: bool,
    separate_equity: bool,
) -> dict[str, Any]:
    gross_cash_income = annual_base + annual_bonus + signing_bonus + stock_sale_gain
    employment_income = annual_base + annual_bonus + signing_bonus + equity_incentive_income
    gross_income = employment_income + stock_sale_gain
    annual_employee_contributions = employee_housing_fund + employee_social_insurance
    signing_in_bonus_bucket = signing_bonus_treatment == "one-time-bonus"

    if separate_bonus:
        one_time_bonus_income = annual_bonus + (signing_bonus if signing_in_bonus_bucket else Decimal("0"))
        comprehensive_income = (
            annual_base
            + (Decimal("0") if signing_in_bonus_bucket else signing_bonus)
            + equity_incentive_income
        )
    else:
        one_time_bonus_income = Decimal("0")
        comprehensive_income = employment_income

    if separate_equity:
        equity_incentive_income_separate = equity_incentive_income
        comprehensive_income -= equity_incentive_income
    else:
        equity_incentive_income_separate = Decimal("0")

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
    equity_incentive_iit = progressive_tax(equity_incentive_income_separate)
    stock_sale_iit = proportional_tax(stock_sale_gain, PROPERTY_TRANSFER_TAX_RATE) if stock_sale_taxable else Decimal("0.00")
    total_iit = comprehensive_iit + one_time_bonus_iit + equity_incentive_iit + stock_sale_iit
    annual_take_home_cash = gross_cash_income - annual_employee_contributions - total_iit
    annual_after_tax_value_including_housing_fund = (
        annual_take_home_cash + employee_housing_fund + employer_housing_fund
    )
    annual_after_tax_value_including_housing_fund_and_equity = (
        annual_after_tax_value_including_housing_fund + equity_incentive_income
    )
    effective_iit_rate = Decimal("0.00")
    if gross_income > 0:
        effective_iit_rate = (total_iit / gross_income * Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "name": name,
        "separate_bonus": separate_bonus,
        "separate_equity": separate_equity,
        "stock_sale_taxable": stock_sale_taxable,
        "gross_income": money(gross_income),
        "gross_cash_income": money(gross_cash_income),
        "employment_income": money(employment_income),
        "equity_incentive_income": money(equity_incentive_income),
        "comprehensive_income": money(comprehensive_income),
        "total_comprehensive_deductions": money(total_comprehensive_deductions),
        "taxable_comprehensive_income": money(taxable_comprehensive_income),
        "comprehensive_iit": money(comprehensive_iit),
        "one_time_bonus_income": money(one_time_bonus_income),
        "one_time_bonus_iit": money(one_time_bonus_iit),
        "separate_equity_incentive_income": money(equity_incentive_income_separate),
        "equity_incentive_iit": money(equity_incentive_iit),
        "stock_sale_gain": money(stock_sale_gain),
        "stock_sale_iit": money(stock_sale_iit),
        "total_iit": money(total_iit),
        "annual_employee_contributions": money(annual_employee_contributions),
        "annual_take_home_cash": money(annual_take_home_cash),
        "annual_after_tax_value_including_housing_fund": money(annual_after_tax_value_including_housing_fund),
        "annual_after_tax_value_including_housing_fund_and_equity": money(
            annual_after_tax_value_including_housing_fund_and_equity
        ),
        "effective_iit_rate_percent": effective_iit_rate,
    }


def calculate(args: argparse.Namespace) -> dict[str, Any]:
    months = Decimal(args.months)
    annual_base = money(args.monthly_base * months)
    contributions = build_contributions(args)
    employee_housing_fund = contributions["employee_housing_fund_annual"]
    employee_social_insurance = contributions["employee_social_insurance_annual"]
    employer_housing_fund = contributions["employer_housing_fund_annual"]
    special_additional_deductions_annual = money(args.special_additional_deductions_monthly * months)
    annual_bonus = args.annual_bonus
    signing_bonus = args.signing_bonus
    equity_incentive_income = total_equity_incentive_income(args)
    stock_sale_gain = args.stock_sale_gain

    separate_bonus_allowed = args.tax_year <= 2027 or args.force_separate_bonus_after_2027
    separate_equity_allowed = args.tax_year <= 2027 or args.force_separate_equity_after_2027
    stock_sale_taxable = not args.domestic_listed_stock_sale_exempt
    notes: list[str] = []
    notes.extend(contributions["notes"])
    scenarios: list[dict[str, Any]] = []
    bonus_bucket_amount = annual_bonus + (
        signing_bonus if args.signing_bonus_treatment == "one-time-bonus" else Decimal("0")
    )

    if args.annual_bonus_treatment == "separate" and not separate_bonus_allowed:
        raise SystemExit(
            "Annual one-time bonus separate taxation is modeled through 2027-12-31. "
            "Pass --force-separate-bonus-after-2027 only after confirming the policy still applies."
        )
    if args.equity_treatment == "separate" and not separate_equity_allowed:
        raise SystemExit(
            "Equity incentive separate taxation is modeled through 2027-12-31. "
            "Pass --force-separate-equity-after-2027 only after confirming the policy still applies."
        )

    if args.annual_bonus_treatment == "comprehensive" or bonus_bucket_amount <= 0:
        bonus_modes = [False]
    elif args.annual_bonus_treatment == "separate":
        bonus_modes = [True]
    elif separate_bonus_allowed:
        bonus_modes = [False, True]
    else:
        bonus_modes = [False]
        notes.append("Separate annual one-time bonus taxation was not assumed after 2027.")

    if args.equity_treatment == "comprehensive" or equity_incentive_income <= 0:
        equity_modes = [False]
    elif args.equity_treatment == "separate":
        equity_modes = [True]
    elif separate_equity_allowed:
        equity_modes = [False, True]
    else:
        equity_modes = [False]
        notes.append("Separate equity incentive taxation was not assumed after 2027.")

    for separate_bonus in bonus_modes:
        for separate_equity in equity_modes:
            name_parts = []
            name_parts.append("separate_bonus" if separate_bonus else "comprehensive_bonus")
            name_parts.append("separate_equity" if separate_equity else "comprehensive_equity")
            scenario = build_scenario(
                name="+".join(name_parts),
                annual_base=annual_base,
                annual_bonus=annual_bonus,
                signing_bonus=signing_bonus,
                signing_bonus_treatment=args.signing_bonus_treatment,
                equity_incentive_income=equity_incentive_income,
                stock_sale_gain=stock_sale_gain,
                stock_sale_taxable=stock_sale_taxable,
                employee_housing_fund=employee_housing_fund,
                employee_social_insurance=employee_social_insurance,
                employer_housing_fund=employer_housing_fund,
                standard_deduction_annual=args.standard_deduction_annual,
                special_additional_deductions_annual=special_additional_deductions_annual,
                other_deductions_annual=args.other_deductions_annual,
                separate_bonus=separate_bonus,
                separate_equity=separate_equity,
            )
            scenarios.append(scenario)

    selected = min(scenarios, key=lambda scenario: scenario["total_iit"])

    if (
        args.signing_bonus_treatment == "one-time-bonus"
        and selected["one_time_bonus_income"] >= signing_bonus
        and signing_bonus > 0
    ):
        notes.append("Signing bonus was combined into the single annual one-time bonus bucket.")
    if selected["separate_equity"] and equity_incentive_income > 0:
        notes.append("Equity incentive income was taxed separately from comprehensive income.")
    if args.domestic_listed_stock_sale_exempt and stock_sale_gain > 0:
        notes.append("Stock sale gain was treated as exempt because --domestic-listed-stock-sale-exempt was provided.")

    monthly_breakdown = []
    if args.monthly_breakdown:
        monthly_breakdown = build_monthly_breakdown(
            args=args,
            selected=selected,
            annual_base=annual_base,
            annual_bonus=annual_bonus,
            signing_bonus=signing_bonus,
            equity_incentive_income=equity_incentive_income,
            stock_sale_gain=stock_sale_gain,
            contributions=contributions,
        )

    return {
        "inputs": {
            "tax_year": args.tax_year,
            "months": args.months,
            "monthly_base": args.monthly_base,
            "city": args.city,
            "housing_fund_monthly_employee_input": args.housing_fund_monthly,
            "social_insurance_monthly_employee_input": args.social_insurance_monthly,
            "employer_housing_fund_monthly_input": args.employer_housing_fund_monthly,
            "annual_bonus": annual_bonus,
            "signing_bonus": signing_bonus,
            "equity_incentive_income": equity_incentive_income,
            "stock_sale_gain": stock_sale_gain,
            "annual_bonus_treatment": args.annual_bonus_treatment,
            "signing_bonus_treatment": args.signing_bonus_treatment,
            "equity_treatment": args.equity_treatment,
            "stock_sale_taxable": stock_sale_taxable,
            "standard_deduction_annual": args.standard_deduction_annual,
            "special_additional_deductions_annual": special_additional_deductions_annual,
            "other_deductions_annual": args.other_deductions_annual,
        },
        "contributions": contributions,
        "selected": selected,
        "scenarios": scenarios,
        "monthly_breakdown": monthly_breakdown,
        "notes": notes,
    }


def print_text(result: dict[str, Any]) -> None:
    selected = result["selected"]
    contributions = result["contributions"]
    print(f"Selected scenario: {selected['name']}")
    print(f"Annual gross income: {format_rmb(selected['gross_income'])}")
    print(f"Annual gross cash income: {format_rmb(selected['gross_cash_income'])}")
    print(f"Equity incentive income: {format_rmb(selected['equity_incentive_income'])}")
    print(f"Taxable comprehensive income: {format_rmb(selected['taxable_comprehensive_income'])}")
    print(f"Comprehensive IIT: {format_rmb(selected['comprehensive_iit'])}")
    print(f"One-time bonus IIT: {format_rmb(selected['one_time_bonus_iit'])}")
    print(f"Equity incentive IIT: {format_rmb(selected['equity_incentive_iit'])}")
    print(f"Stock sale IIT: {format_rmb(selected['stock_sale_iit'])}")
    print(f"Total IIT: {format_rmb(selected['total_iit'])}")
    print(f"Employee social insurance: {format_rmb(contributions['employee_social_insurance_annual'])}")
    print(f"Employee housing fund: {format_rmb(contributions['employee_housing_fund_annual'])}")
    print(f"Employee contributions withheld: {format_rmb(selected['annual_employee_contributions'])}")
    print(f"Employer social insurance: {format_rmb(contributions['employer_social_insurance_annual'])}")
    print(f"Employer housing fund: {format_rmb(contributions['employer_housing_fund_annual'])}")
    print(f"Annual take-home cash: {format_rmb(selected['annual_take_home_cash'])}")
    print(
        "Annual after-tax value including housing fund: "
        f"{format_rmb(selected['annual_after_tax_value_including_housing_fund'])}"
    )
    print(
        "Annual after-tax value including housing fund and equity: "
        f"{format_rmb(selected['annual_after_tax_value_including_housing_fund_and_equity'])}"
    )
    print(f"Effective IIT rate on gross income: {selected['effective_iit_rate_percent']}%")

    if len(result["scenarios"]) > 1:
        print()
        print("Scenario comparison:")
        for scenario in result["scenarios"]:
            print(
                f"- {scenario['name']}: total IIT {format_rmb(scenario['total_iit'])}, "
                f"take-home cash {format_rmb(scenario['annual_take_home_cash'])}, "
                "after-tax value including equity "
                f"{format_rmb(scenario['annual_after_tax_value_including_housing_fund_and_equity'])}"
            )

    if result["monthly_breakdown"]:
        print()
        print("Monthly breakdown:")
        for row in result["monthly_breakdown"]:
            print(
                f"- Month {row['month']:02d}: tax {format_rmb(row['total_iit'])}, "
                f"social {format_rmb(row['employee_social_insurance'])}, "
                f"housing fund {format_rmb(row['employee_housing_fund'])}, "
                f"take-home cash {format_rmb(row['take_home_cash'])}"
            )

    if result["notes"]:
        print()
        print("Notes:")
        for note in result["notes"]:
            print(f"- {note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate mainland China resident annual/monthly after-tax compensation."
    )
    parser.add_argument("--monthly-base", type=parse_money, default=Decimal("0.00"), help="Monthly gross base salary in RMB.")
    parser.add_argument("--months", type=int, default=12, choices=range(1, 13), metavar="{1..12}")
    parser.add_argument("--city", choices=sorted(CITY_PROFILES), help="Apply a built-in local contribution profile.")
    parser.add_argument(
        "--social-insurance-base",
        type=parse_money,
        help="Monthly social-insurance contribution base before local min/max clamping; defaults to monthly base.",
    )
    parser.add_argument(
        "--housing-fund-base",
        type=parse_money,
        help="Monthly housing-fund contribution base before local min/max clamping; defaults to monthly base.",
    )
    parser.add_argument(
        "--housing-fund-rate",
        type=parse_rate,
        help="Employee housing fund contribution rate, e.g. 0.12 or 12.",
    )
    parser.add_argument(
        "--employer-housing-fund-rate",
        type=parse_rate,
        help="Employer housing fund contribution rate; defaults to employee housing fund rate.",
    )
    parser.add_argument(
        "--work-injury-rate",
        type=parse_rate,
        help="Employer work-injury insurance rate for city-profile social insurance.",
    )
    parser.add_argument(
        "--housing-fund-monthly",
        type=parse_money,
        help="Employee-side monthly housing provident fund contribution. Overrides city-profile calculation.",
    )
    parser.add_argument(
        "--social-insurance-monthly",
        type=parse_money,
        help="Employee-side monthly social insurance contribution. Overrides city-profile calculation.",
    )
    parser.add_argument(
        "--employer-social-insurance-monthly",
        type=parse_money,
        help="Employer-side monthly social insurance contribution. Overrides city-profile calculation.",
    )
    parser.add_argument(
        "--employer-housing-fund-monthly",
        type=parse_money,
        help="Employer-side monthly housing fund contribution. Overrides city-profile calculation.",
    )
    parser.add_argument("--annual-bonus", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--signing-bonus", type=parse_money, default=Decimal("0.00"))
    parser.add_argument(
        "--equity-incentive-income",
        type=parse_money,
        default=Decimal("0.00"),
        help="Direct taxable equity incentive income, such as option spread, RSU vest value, restricted stock, or share award.",
    )
    parser.add_argument("--rsu-vest-value", "--rsu-value", dest="rsu_vest_value", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--restricted-stock-value", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--stock-award-value", "--share-award-value", dest="stock_award_value", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--option-spread", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--option-shares", type=parse_non_negative_decimal)
    parser.add_argument("--option-fmv", "--option-fair-market-value", dest="option_fmv", type=parse_money)
    parser.add_argument("--option-strike", "--option-exercise-price", dest="option_strike", type=parse_money)
    parser.add_argument(
        "--stock-sale-gain",
        type=parse_money,
        default=Decimal("0.00"),
        help="Realized taxable stock or equity sale gain. Use --domestic-listed-stock-sale-exempt when the exemption applies.",
    )
    parser.add_argument("--domestic-listed-stock-sale-exempt", action="store_true")
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
    parser.add_argument(
        "--equity-treatment",
        "--equity-incentive-treatment",
        dest="equity_treatment",
        choices=("auto", "separate", "comprehensive"),
        default="auto",
        help="Use auto to compare separate equity incentive taxation with comprehensive income taxation when available.",
    )
    parser.add_argument("--tax-year", type=int, default=date.today().year)
    parser.add_argument("--standard-deduction-annual", type=parse_money, default=Decimal("60000.00"))
    parser.add_argument("--special-additional-deductions-monthly", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--other-deductions-annual", type=parse_money, default=Decimal("0.00"))
    parser.add_argument("--force-separate-bonus-after-2027", action="store_true")
    parser.add_argument("--force-separate-equity-after-2027", action="store_true")
    parser.add_argument("--monthly-breakdown", action="store_true", help="Emit month-by-month IIT and contribution amounts.")
    parser.add_argument("--annual-bonus-month", type=int, default=12)
    parser.add_argument("--signing-bonus-month", type=int, default=1)
    parser.add_argument("--equity-income-month", type=int, default=12)
    parser.add_argument("--stock-sale-month", type=int, default=12)
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
