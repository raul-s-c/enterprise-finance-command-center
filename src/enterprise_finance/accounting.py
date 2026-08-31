from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd


ACCOUNT_META = {
    "1000_CASH": ("Balance Sheet", "Cash", "Asset"),
    "1100_AR": ("Balance Sheet", "Trade Receivables", "Asset"),
    "1150_IC_AR": ("Balance Sheet", "Intercompany Receivables", "Asset"),
    "1200_INVENTORY": ("Balance Sheet", "Inventory", "Asset"),
    "1500_PPE": ("Balance Sheet", "Property Plant & Equipment", "Asset"),
    "1510_CIP": ("Balance Sheet", "Construction in Progress", "Asset"),
    "1590_ACCUM_DEP": ("Balance Sheet", "Accumulated Depreciation", "Contra Asset"),
    "2100_AP": ("Balance Sheet", "Trade Payables", "Liability"),
    "2150_IC_AP": ("Balance Sheet", "Intercompany Payables", "Liability"),
    "2200_TAX_PAYABLE": ("Balance Sheet", "Tax Payable", "Liability"),
    "2500_DEBT": ("Balance Sheet", "Borrowings", "Liability"),
    "3000_SHARE_CAPITAL": ("Balance Sheet", "Share Capital", "Equity"),
    "3200_RETAINED_EARNINGS": ("Balance Sheet", "Retained Earnings", "Equity"),
    "4000_EXTERNAL_REVENUE": ("P&L", "External Revenue", "Revenue"),
    "4100_IC_REVENUE": ("P&L", "Intercompany Revenue", "Revenue"),
    "5000_EXTERNAL_COGS": ("P&L", "External Cost of Sales", "Expense"),
    "5050_SERVICE_DELIVERY": ("P&L", "Service Delivery Cost", "Expense"),
    "5200_FACTORY_COST": ("P&L", "Factory Manufacturing Cost", "Expense"),
    "5300_VARIABLE_SELLING": ("P&L", "Variable Selling & Logistics", "Expense"),
    "5400_FIXED_PRODUCTION": ("P&L", "Fixed Production Cost", "Expense"),
    "6000_OPEX": ("P&L", "Operating Expenses", "Expense"),
    "6100_DEPRECIATION": ("P&L", "Depreciation", "Expense"),
    "7000_INTEREST": ("P&L", "Net Interest", "Expense"),
    "7100_TAX": ("P&L", "Income Tax", "Expense"),
}

P_AND_L_ACCOUNTS = {a for a, meta in ACCOUNT_META.items() if meta[0] == "P&L"}


@dataclass(frozen=True)
class AccountingResult:
    journal: pd.DataFrame
    capex: pd.DataFrame
    intercompany: pd.DataFrame
    factory: pd.DataFrame


def chart_of_accounts() -> pd.DataFrame:
    return pd.DataFrame([
        {"account": account, "statement": meta[0], "line": meta[1], "account_type": meta[2]}
        for account, meta in ACCOUNT_META.items()
    ])


def _add(rows: list[dict], *, month: str, entity: str, division: str, journal_id: str, journal_type: str, account: str, debit: float = 0.0, credit: float = 0.0, counterparty: str = "EXTERNAL", description: str = "", cash_flow_category: str = "", product: str = "", customer: str = "") -> None:
    if abs(debit) < 0.005 and abs(credit) < 0.005:
        return
    rows.append({
        "month": month, "entity": entity, "division": division, "journal_id": journal_id,
        "journal_type": journal_type, "account": account, "debit": round(float(debit), 2),
        "credit": round(float(credit), 2), "counterparty": counterparty, "description": description,
        "cash_flow_category": cash_flow_category, "product": product, "customer": customer,
    })


def _opening_balances(config: dict, first_month: str, rows: list[dict]) -> dict[str, float]:
    debt_balance: dict[str, float] = {}
    factory_entities = set(config["factories"])
    for entity_cfg in config["entities"]:
        entity = entity_cfg["code"]
        is_factory = entity in factory_entities
        cash = 15_000_000.0 if entity == "DE01" else (9_000_000.0 if is_factory else 7_000_000.0)
        ppe = 34_000_000.0 if is_factory else 9_000_000.0
        accum_dep = ppe * 0.22
        debt = 14_000_000.0 if is_factory else (8_000_000.0 if entity == "DE01" else 2_000_000.0)
        debt_balance[entity] = debt
        share_capital = cash + ppe - accum_dep - debt
        jid = f"OPEN-{entity}"
        _add(rows, month=first_month, entity=entity, division="Corporate", journal_id=jid, journal_type="opening", account="1000_CASH", debit=cash, description="Opening cash", cash_flow_category="opening")
        _add(rows, month=first_month, entity=entity, division="Corporate", journal_id=jid, journal_type="opening", account="1500_PPE", debit=ppe, description="Opening PPE")
        _add(rows, month=first_month, entity=entity, division="Corporate", journal_id=jid, journal_type="opening", account="1590_ACCUM_DEP", credit=accum_dep, description="Opening accumulated depreciation")
        _add(rows, month=first_month, entity=entity, division="Corporate", journal_id=jid, journal_type="opening", account="2500_DEBT", credit=debt, description="Opening borrowings")
        _add(rows, month=first_month, entity=entity, division="Corporate", journal_id=jid, journal_type="opening", account="3000_SHARE_CAPITAL", credit=share_capital, description="Opening equity")
    return debt_balance


def _capex_schedule(config: dict, months: pd.PeriodIndex) -> tuple[pd.DataFrame, dict[tuple[str, str], float]]:
    rows: list[dict] = []
    capacity: dict[tuple[str, str], float] = {}
    month_set = set(months)
    for project in config["capex_projects"]:
        start = pd.Period(project["start"], freq="M")
        build_months = int(project["build_months"])
        spend_months = pd.period_range(start=start, periods=build_months, freq="M")
        x = np.linspace(0.25, np.pi - 0.25, build_months)
        weights = np.sin(x)
        weights = weights / weights.sum()
        go_live = start + build_months - 1
        for idx, period in enumerate(spend_months):
            if period in month_set:
                rows.append({
                    "month": str(period), "project": project["id"], "project_name": project["name"],
                    "entity": project["entity"], "division": project["division"], "event": "SPEND",
                    "amount": round(float(project["budget"]) * float(weights[idx]), 2), "go_live": str(go_live),
                    "useful_life_months": int(project["useful_life_months"]), "capacity_increase_pct": float(project["capacity_increase_pct"]),
                })
        if go_live in month_set:
            rows.append({
                "month": str(go_live), "project": project["id"], "project_name": project["name"],
                "entity": project["entity"], "division": project["division"], "event": "GO_LIVE",
                "amount": float(project["budget"]), "go_live": str(go_live),
                "useful_life_months": int(project["useful_life_months"]), "capacity_increase_pct": float(project["capacity_increase_pct"]),
            })
        if project["entity"] in config["factories"]:
            for period in months:
                if period >= go_live:
                    capacity[(str(period), project["entity"])] = capacity.get((str(period), project["entity"]), 0.0) + float(project["capacity_increase_pct"])
    return pd.DataFrame(rows), capacity


def build_accounting(config: dict, months: pd.PeriodIndex, macro: pd.DataFrame, operations: pd.DataFrame) -> AccountingResult:
    rows: list[dict] = []
    first_month = str(months[0])
    debt_balance = _opening_balances(config, first_month, rows)
    capex, capacity_increase = _capex_schedule(config, months)
    markup = float(config["transfer_pricing"]["manufacturing_cost_plus"])
    settlement_ratio = float(config["transfer_pricing"]["settlement_ratio"])

    ar_balance: dict[tuple[str, str], float] = defaultdict(float)
    ap_balance: dict[tuple[str, str], float] = defaultdict(float)
    inventory_balance: dict[tuple[str, str], float] = defaultdict(float)
    ic_balance: dict[tuple[str, str], float] = defaultdict(float)
    tax_balance: dict[str, float] = defaultdict(float)
    cip_balance: dict[str, float] = defaultdict(float)
    intercompany_rows: list[dict] = []
    factory_rows: list[dict] = []
    capex_by_month = capex.groupby("month") if not capex.empty else None

    for month_index, period in enumerate(months):
        month = str(period)
        m = macro.iloc[month_index]
        month_ops = operations[operations["month"] == month].copy()
        sales_agg = month_ops.groupby(["entity", "division"], as_index=False).revenue.sum()
        external_accruals: dict[tuple[str, str], float] = defaultdict(float)
        factory_external_cost: dict[str, float] = defaultdict(float)
        factory_units: dict[str, float] = defaultdict(float)

        for idx, r in month_ops.reset_index(drop=True).iterrows():
            entity, division = str(r.entity), str(r.division)
            rev = float(r.revenue)
            product, customer = str(r.product), str(r.customer)
            jid = f"SALE-{month}-{idx:05d}-{entity}"
            _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="sale", account="1100_AR", debit=rev, description="External customer invoice", product=product, customer=customer)
            _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="sale", account="4000_EXTERNAL_REVENUE", credit=rev, description="External customer invoice", product=product, customer=customer)

            variable_selling = float(r.variable_selling_cost)
            opex = float(r.opex)
            fixed_prod = float(r.fixed_production_cost)
            direct = float(r.variable_production_cost)

            if division in {"Hardware", "Spare Parts"}:
                transfer_cogs = (direct + fixed_prod) * (1.0 + markup)
                cjid = f"COGS-{month}-{idx:05d}-{entity}"
                _add(rows, month=month, entity=entity, division=division, journal_id=cjid, journal_type="cogs", account="5000_EXTERNAL_COGS", debit=transfer_cogs, description="External cost of sales at transfer price", product=product, customer=customer)
                _add(rows, month=month, entity=entity, division=division, journal_id=cjid, journal_type="cogs", account="1200_INVENTORY", credit=transfer_cogs, description="Inventory consumption", product=product, customer=customer)
            else:
                sjid = f"SERV-{month}-{idx:05d}-{entity}"
                _add(rows, month=month, entity=entity, division=division, journal_id=sjid, journal_type="service_cost", account="5050_SERVICE_DELIVERY", debit=direct, description="Direct service delivery", product=product, customer=customer)
                _add(rows, month=month, entity=entity, division=division, journal_id=sjid, journal_type="service_cost", account="2100_AP", credit=direct, description="Direct service delivery accrual", product=product, customer=customer)
                external_accruals[(entity, division)] += direct
                fjid = f"FIX-{month}-{idx:05d}-{entity}"
                _add(rows, month=month, entity=entity, division=division, journal_id=fjid, journal_type="fixed_production", account="5400_FIXED_PRODUCTION", debit=fixed_prod, description="Fixed delivery capacity cost", product=product, customer=customer)
                _add(rows, month=month, entity=entity, division=division, journal_id=fjid, journal_type="fixed_production", account="2100_AP", credit=fixed_prod, description="Fixed delivery capacity accrual", product=product, customer=customer)
                external_accruals[(entity, division)] += fixed_prod

            if variable_selling:
                vjid = f"VARSELL-{month}-{idx:05d}-{entity}"
                _add(rows, month=month, entity=entity, division=division, journal_id=vjid, journal_type="variable_selling", account="5300_VARIABLE_SELLING", debit=variable_selling, description="Variable selling and logistics", product=product, customer=customer)
                _add(rows, month=month, entity=entity, division=division, journal_id=vjid, journal_type="variable_selling", account="2100_AP", credit=variable_selling, description="Variable selling accrual", product=product, customer=customer)
                external_accruals[(entity, division)] += variable_selling
            if opex:
                ojid = f"OPEX-{month}-{idx:05d}-{entity}"
                _add(rows, month=month, entity=entity, division=division, journal_id=ojid, journal_type="opex", account="6000_OPEX", debit=opex, description="Operating expenses", product=product, customer=customer)
                _add(rows, month=month, entity=entity, division=division, journal_id=ojid, journal_type="opex", account="2100_AP", credit=opex, description="Operating expense accrual", product=product, customer=customer)
                external_accruals[(entity, division)] += opex

        for _, sale in sales_agg.iterrows():
            entity, division = str(sale.entity), str(sale.division)
            revenue = float(sale.revenue)
            dso = float(config["divisions"][division]["dso"])
            key = (entity, division)
            target_end = revenue * dso / 30.0
            available = ar_balance[key] + revenue
            collection = min(max(available - target_end, 0.0), available)
            if collection:
                jid = f"COLL-{month}-{entity}-{division.replace(' ', '')}"
                _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="collection", account="1000_CASH", debit=collection, description="Customer collections", cash_flow_category="customer_collections")
                _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="collection", account="1100_AR", credit=collection, description="Customer collections")
            ar_balance[key] = available - collection

        physical = month_ops[month_ops["division"].isin(["Hardware", "Spare Parts"])].copy()
        if not physical.empty:
            physical["group_cost"] = physical["variable_production_cost"] + physical["fixed_production_cost"]
            physical["transfer_cogs"] = physical["group_cost"] * (1.0 + markup)
            for (buyer, division), grp in physical.groupby(["entity", "division"]):
                sold_tp = float(grp["transfer_cogs"].sum())
                dio = float(config["divisions"][division]["dio"])
                inv_key = (str(buyer), str(division))
                opening_inv = inventory_balance[inv_key]
                target_end = sold_tp * dio / 30.0
                purchase_tp = max(sold_tp + target_end - opening_inv, 0.0)
                by_factory = grp.groupby("source_factory", as_index=False).group_cost.sum()
                total_group_cost = float(by_factory.group_cost.sum())
                for _, frow in by_factory.iterrows():
                    seller = str(frow.source_factory)
                    share = float(frow.group_cost) / total_group_cost if total_group_cost else 0.0
                    invoice = purchase_tp * share
                    if invoice <= 0:
                        continue
                    manufacturing_cost = invoice / (1.0 + markup)
                    btype = division.replace(" ", "")
                    jid_b = f"ICBUY-{month}-{buyer}-{seller}-{btype}"
                    _add(rows, month=month, entity=str(buyer), division=str(division), journal_id=jid_b, journal_type="intercompany_purchase", account="1200_INVENTORY", debit=invoice, counterparty=seller, description="Intercompany inventory receipt")
                    _add(rows, month=month, entity=str(buyer), division=str(division), journal_id=jid_b, journal_type="intercompany_purchase", account="2150_IC_AP", credit=invoice, counterparty=seller, description="Intercompany payable")
                    jid_s = f"ICSALE-{month}-{seller}-{buyer}-{btype}"
                    _add(rows, month=month, entity=seller, division=str(division), journal_id=jid_s, journal_type="intercompany_sale", account="1150_IC_AR", debit=invoice, counterparty=str(buyer), description="Intercompany receivable")
                    _add(rows, month=month, entity=seller, division=str(division), journal_id=jid_s, journal_type="intercompany_sale", account="4100_IC_REVENUE", credit=invoice, counterparty=str(buyer), description="Cost-plus manufacturing transfer")
                    jid_c = f"MFG-{month}-{seller}-{buyer}-{btype}"
                    _add(rows, month=month, entity=seller, division=str(division), journal_id=jid_c, journal_type="factory_cost", account="5200_FACTORY_COST", debit=manufacturing_cost, counterparty=str(buyer), description="Manufacturing cost of transferred goods")
                    _add(rows, month=month, entity=seller, division=str(division), journal_id=jid_c, journal_type="factory_cost", account="2100_AP", credit=manufacturing_cost, counterparty="EXTERNAL", description="Factory supplier and labor accrual")
                    factory_external_cost[seller] += manufacturing_cost
                    source = grp.loc[grp.source_factory.eq(seller)]
                    avg_unit_group_cost = float(source["group_cost"].sum()) / max(float(source["quantity"].sum()), 1.0)
                    factory_units[seller] += manufacturing_cost / max(avg_unit_group_cost, 1.0)
                    pair = (str(buyer), seller)
                    ic_balance[pair] += invoice
                    intercompany_rows.append({"month": month, "seller": seller, "buyer": str(buyer), "division": str(division), "invoice": round(invoice, 2), "manufacturing_cost": round(manufacturing_cost, 2), "markup": round(invoice - manufacturing_cost, 2)})
                inventory_balance[inv_key] = opening_inv + purchase_tp - sold_tp

        for factory, cost in factory_external_cost.items():
            external_accruals[(factory, "Hardware")] += cost
        for (entity, division), accrual in list(external_accruals.items()):
            dpo = float(config["divisions"].get(division, config["divisions"]["Hardware"])["dpo"])
            key = (entity, division)
            target_end = accrual * dpo / 30.0
            available = ap_balance[key] + accrual
            payment = min(max(available - target_end, 0.0), available)
            if payment:
                jid = f"PAY-{month}-{entity}-{division.replace(' ', '')}"
                _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="supplier_payment", account="2100_AP", debit=payment, description="Supplier payments")
                _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="supplier_payment", account="1000_CASH", credit=payment, description="Supplier payments", cash_flow_category="supplier_payments")
            ap_balance[key] = available - payment

        for (buyer, seller), outstanding in list(ic_balance.items()):
            settlement = outstanding * settlement_ratio
            if settlement <= 0.005:
                continue
            jid_b = f"ICSET-B-{month}-{buyer}-{seller}"
            _add(rows, month=month, entity=buyer, division="Corporate", journal_id=jid_b, journal_type="intercompany_settlement", account="2150_IC_AP", debit=settlement, counterparty=seller, description="Intercompany settlement")
            _add(rows, month=month, entity=buyer, division="Corporate", journal_id=jid_b, journal_type="intercompany_settlement", account="1000_CASH", credit=settlement, counterparty=seller, description="Intercompany settlement", cash_flow_category="intercompany_settlement")
            jid_s = f"ICSET-S-{month}-{seller}-{buyer}"
            _add(rows, month=month, entity=seller, division="Corporate", journal_id=jid_s, journal_type="intercompany_settlement", account="1000_CASH", debit=settlement, counterparty=buyer, description="Intercompany settlement", cash_flow_category="intercompany_settlement")
            _add(rows, month=month, entity=seller, division="Corporate", journal_id=jid_s, journal_type="intercompany_settlement", account="1150_IC_AR", credit=settlement, counterparty=buyer, description="Intercompany settlement")
            ic_balance[(buyer, seller)] = outstanding - settlement

        if capex_by_month is not None and month in capex_by_month.groups:
            for _, event in capex_by_month.get_group(month).iterrows():
                entity, division, project = str(event.entity), str(event.division), str(event.project)
                if event["event"] == "SPEND":
                    amount = float(event.amount)
                    jid = f"CAPEX-{month}-{project}"
                    _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="capex", account="1510_CIP", debit=amount, description=str(event.project_name))
                    _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="capex", account="1000_CASH", credit=amount, description=str(event.project_name), cash_flow_category="capex")
                    cip_balance[project] += amount
                elif event["event"] == "GO_LIVE":
                    amount = cip_balance.get(project, float(event.amount))
                    jid = f"GOLIVE-{month}-{project}"
                    _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="capex_transfer", account="1500_PPE", debit=amount, description=f"Go-live: {event.project_name}")
                    _add(rows, month=month, entity=entity, division=division, journal_id=jid, journal_type="capex_transfer", account="1510_CIP", credit=amount, description=f"Go-live: {event.project_name}")
                    cip_balance[project] = 0.0

        for entity_cfg in config["entities"]:
            entity = entity_cfg["code"]
            opening_ppe = 34_000_000.0 if entity in config["factories"] else 9_000_000.0
            depreciation = opening_ppe / 144.0
            for project in config["capex_projects"]:
                if project["entity"] != entity:
                    continue
                go_live = pd.Period(project["start"], freq="M") + int(project["build_months"]) - 1
                if period > go_live:
                    depreciation += float(project["budget"]) / float(project["useful_life_months"])
            jid = f"DEP-{month}-{entity}"
            _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="depreciation", account="6100_DEPRECIATION", debit=depreciation, description="Monthly depreciation")
            _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="depreciation", account="1590_ACCUM_DEP", credit=depreciation, description="Monthly depreciation")

        for entity, debt in list(debt_balance.items()):
            interest = debt * float(m["policy_rate"]) / 12.0
            if interest:
                jid = f"INT-{month}-{entity}"
                _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="interest", account="7000_INTEREST", debit=interest, description="Interest expense")
                _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="interest", account="1000_CASH", credit=interest, description="Interest paid", cash_flow_category="interest")
            if period.month in {3, 6, 9, 12} and debt > 0:
                principal = min(debt * 0.0125, debt)
                jid = f"DEBT-{month}-{entity}"
                _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="debt_repayment", account="2500_DEBT", debit=principal, description="Scheduled debt amortization")
                _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="debt_repayment", account="1000_CASH", credit=principal, description="Scheduled debt amortization", cash_flow_category="debt_repayment")
                debt_balance[entity] -= principal

        op_month = pd.DataFrame(rows)
        op_month = op_month[(op_month.month == month) & op_month.account.isin(P_AND_L_ACCOUNTS) & ~op_month.journal_type.eq("closing")].copy()
        if not op_month.empty:
            op_month["signed"] = op_month.debit - op_month.credit
            for entity, grp in op_month.groupby("entity"):
                pretax = -float(grp["signed"].sum())
                tax = max(pretax, 0.0) * float(config["group"]["corporate_tax_rate"])
                if tax:
                    jid = f"TAXACC-{month}-{entity}"
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="tax", account="7100_TAX", debit=tax, description="Income tax accrual")
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="tax", account="2200_TAX_PAYABLE", credit=tax, description="Income tax payable")
                    tax_balance[entity] += tax
                if period.month in {3, 6, 9, 12} and tax_balance[entity] > 0:
                    pay = tax_balance[entity] * 0.78
                    jid = f"TAXPAY-{month}-{entity}"
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="tax_payment", account="2200_TAX_PAYABLE", debit=pay, description="Quarterly tax payment")
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=jid, journal_type="tax_payment", account="1000_CASH", credit=pay, description="Quarterly tax payment", cash_flow_category="tax")
                    tax_balance[entity] -= pay

        current = pd.DataFrame(rows)
        current = current[(current.month == month) & current.account.isin(P_AND_L_ACCOUNTS) & ~current.journal_type.eq("closing")].copy()
        if not current.empty:
            current["signed"] = current.debit - current.credit
            for entity, entity_grp in current.groupby("entity"):
                closing_signed_sum = 0.0
                close_id = f"CLOSE-{month}-{entity}"
                for account, amount in entity_grp.groupby("account").signed.sum().items():
                    amount = float(amount)
                    if abs(amount) < 0.005:
                        continue
                    if amount > 0:
                        _add(rows, month=month, entity=entity, division="Corporate", journal_id=close_id, journal_type="closing", account=account, credit=amount, description="Month-end P&L close")
                        closing_signed_sum -= amount
                    else:
                        _add(rows, month=month, entity=entity, division="Corporate", journal_id=close_id, journal_type="closing", account=account, debit=-amount, description="Month-end P&L close")
                        closing_signed_sum += -amount
                if closing_signed_sum > 0:
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=close_id, journal_type="closing", account="3200_RETAINED_EARNINGS", credit=closing_signed_sum, description="Profit transferred to retained earnings")
                elif closing_signed_sum < 0:
                    _add(rows, month=month, entity=entity, division="Corporate", journal_id=close_id, journal_type="closing", account="3200_RETAINED_EARNINGS", debit=-closing_signed_sum, description="Loss transferred to retained earnings")

        for factory, fcfg in config["factories"].items():
            base_capacity = float(fcfg["base_monthly_capacity_units"])
            capacity = base_capacity * (1.0 + capacity_increase.get((month, factory), 0.0))
            units = factory_units.get(factory, 0.0)
            factory_rows.append({"month": month, "factory": factory, "factory_name": fcfg["name"], "produced_units": round(units, 2), "capacity_units": round(capacity, 2), "utilization": round(units / capacity if capacity else 0.0, 4), "capacity_increase_pct": round(capacity / base_capacity - 1.0, 4)})

    journal = pd.DataFrame(rows)
    if intercompany_rows:
        intercompany = pd.DataFrame(intercompany_rows)
        balances = [{"buyer": buyer, "seller": seller, "ending_ic_balance": round(outstanding, 2)} for (buyer, seller), outstanding in ic_balance.items()]
        intercompany = intercompany.merge(pd.DataFrame(balances), on=["buyer", "seller"], how="left")
    else:
        intercompany = pd.DataFrame(columns=["month", "seller", "buyer", "division", "invoice", "manufacturing_cost", "markup", "ending_ic_balance"])
    return AccountingResult(journal=journal, capex=capex, intercompany=intercompany, factory=pd.DataFrame(factory_rows))


def validate_journal(journal: pd.DataFrame) -> dict:
    by_journal = journal.groupby("journal_id", as_index=False).agg(debit=("debit", "sum"), credit=("credit", "sum"))
    max_gap = float((by_journal.debit - by_journal.credit).abs().max()) if len(by_journal) else 0.0
    trial_gap = float(journal.debit.sum() - journal.credit.sum())
    return {"journal_balance_max_gap": round(max_gap, 2), "trial_balance_gap": round(trial_gap, 2)}


def legal_pnl(journal: pd.DataFrame) -> pd.DataFrame:
    frame = journal[journal.account.isin(P_AND_L_ACCOUNTS) & ~journal.journal_type.eq("closing")].copy()
    frame["amount"] = frame.debit - frame.credit
    pivot = frame.pivot_table(index=["month", "entity", "division"], columns="account", values="amount", aggfunc="sum", fill_value=0).reset_index()
    for account in P_AND_L_ACCOUNTS:
        if account not in pivot.columns:
            pivot[account] = 0.0
    pivot["external_revenue"] = -pivot["4000_EXTERNAL_REVENUE"]
    pivot["intercompany_revenue"] = -pivot["4100_IC_REVENUE"]
    pivot["revenue"] = pivot.external_revenue + pivot.intercompany_revenue
    pivot["cogs"] = pivot["5000_EXTERNAL_COGS"] + pivot["5050_SERVICE_DELIVERY"] + pivot["5200_FACTORY_COST"] + pivot["5400_FIXED_PRODUCTION"]
    pivot["gross_profit"] = pivot.revenue - pivot.cogs
    pivot["ebit"] = pivot.gross_profit - pivot["5300_VARIABLE_SELLING"] - pivot["6000_OPEX"] - pivot["6100_DEPRECIATION"]
    pivot["ebt"] = pivot.ebit - pivot["7000_INTEREST"]
    pivot["net_income"] = pivot.ebt - pivot["7100_TAX"]
    return pivot


def balance_sheet(journal: pd.DataFrame) -> pd.DataFrame:
    bs_accounts = [a for a, meta in ACCOUNT_META.items() if meta[0] == "Balance Sheet"]
    frame = journal[journal.account.isin(bs_accounts)].copy()
    frame["signed"] = frame.debit - frame.credit
    monthly = frame.groupby(["month", "entity", "account"], as_index=False).signed.sum()
    months = sorted(monthly.month.unique())
    entities = sorted(monthly.entity.unique())
    rows: list[dict] = []
    cumulative: dict[tuple[str, str], float] = defaultdict(float)
    for month in months:
        scope = monthly[monthly.month.eq(month)]
        for _, r in scope.iterrows():
            cumulative[(str(r.entity), str(r.account))] += float(r.signed)
        for entity in entities:
            values = {a: cumulative[(entity, a)] for a in bs_accounts}
            assets = values["1000_CASH"] + values["1100_AR"] + values["1150_IC_AR"] + values["1200_INVENTORY"] + values["1500_PPE"] + values["1510_CIP"] + values["1590_ACCUM_DEP"]
            liabilities = -(values["2100_AP"] + values["2150_IC_AP"] + values["2200_TAX_PAYABLE"] + values["2500_DEBT"])
            equity = -(values["3000_SHARE_CAPITAL"] + values["3200_RETAINED_EARNINGS"])
            rows.append({
                "month": month, "entity": entity, "cash": values["1000_CASH"], "trade_receivables": values["1100_AR"],
                "ic_receivables": values["1150_IC_AR"], "inventory": values["1200_INVENTORY"], "ppe_gross": values["1500_PPE"],
                "cip": values["1510_CIP"], "accumulated_depreciation": values["1590_ACCUM_DEP"], "trade_payables": -values["2100_AP"],
                "ic_payables": -values["2150_IC_AP"], "tax_payable": -values["2200_TAX_PAYABLE"], "debt": -values["2500_DEBT"],
                "share_capital": -values["3000_SHARE_CAPITAL"], "retained_earnings": -values["3200_RETAINED_EARNINGS"],
                "assets": assets, "liabilities": liabilities, "equity": equity, "balance_check": assets - liabilities - equity,
            })
    return pd.DataFrame(rows)


def cash_flow(journal: pd.DataFrame) -> pd.DataFrame:
    cash = journal[journal.account.eq("1000_CASH")].copy()
    cash["cash_movement"] = cash.debit - cash.credit
    out = cash.pivot_table(index=["month", "entity"], columns="cash_flow_category", values="cash_movement", aggfunc="sum", fill_value=0).reset_index()
    for col in ["customer_collections", "supplier_payments", "capex", "interest", "tax", "debt_repayment", "intercompany_settlement", "opening"]:
        if col not in out:
            out[col] = 0.0
    out["operating_cash_flow"] = out.customer_collections + out.supplier_payments + out.interest + out.tax
    out["investing_cash_flow"] = out.capex
    out["financing_cash_flow"] = out.debt_repayment
    out["net_cash_movement"] = out[["customer_collections", "supplier_payments", "capex", "interest", "tax", "debt_repayment", "intercompany_settlement", "opening"]].sum(axis=1)
    out["free_cash_flow"] = out.operating_cash_flow + out.investing_cash_flow
    return out
