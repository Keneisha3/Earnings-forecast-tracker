"""The standardized line items, and the XBRL tags companies use for each.

Companies tag the same number differently (revenue alone has at least five common tags, and
most companies switched tags when ASC 606 arrived in 2018). Each item lists its tags in order
of preference; for any one period the first tag that has a value wins, and the tag used is kept
so every number can be traced back to the filing.

kind "flow": a value over a period (income statement, cash flow). Quarterly values are read
directly from three-month periods or derived from year-to-date ones (cash flow statements and
the fourth quarter are usually only reported year to date).
kind "instant": a value on a date (balance sheet).
"""

FLOW, INSTANT = "flow", "instant"

ITEMS = {
    # income statement
    "revenue": ("income", FLOW, "USD", [
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
        "SalesRevenueGoodsNet", "RevenuesNetOfInterestExpense"]),
    "cost_of_revenue": ("income", FLOW, "USD", [
        "CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"]),
    "gross_profit": ("income", FLOW, "USD", ["GrossProfit"]),
    "operating_income": ("income", FLOW, "USD", ["OperatingIncomeLoss"]),
    "net_income": ("income", FLOW, "USD", ["NetIncomeLoss", "ProfitLoss"]),
    "eps_diluted": ("income", FLOW, "USD/shares", ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"]),
    "shares_diluted": ("income", FLOW, "shares", ["WeightedAverageNumberOfDilutedSharesOutstanding"]),
    # balance sheet
    "cash": ("balance", INSTANT, "USD", [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]),
    "total_assets": ("balance", INSTANT, "USD", ["Assets"]),
    "total_liabilities": ("balance", INSTANT, "USD", ["Liabilities"]),
    "equity": ("balance", INSTANT, "USD", [
        "StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
    "long_term_debt": ("balance", INSTANT, "USD", ["LongTermDebtNoncurrent", "LongTermDebt"]),
    # cash flow
    "operating_cash_flow": ("cash_flow", FLOW, "USD", ["NetCashProvidedByUsedInOperatingActivities"]),
    "capex": ("cash_flow", FLOW, "USD", ["PaymentsToAcquirePropertyPlantAndEquipment"]),
}

# Items that are not additive across quarters: a quarter derived from year-to-date totals is an
# approximation (share counts change within a year), and is marked "approx".
NOT_ADDITIVE = {"eps_diluted", "shares_diluted"}

FORMS = ("10-Q", "10-K", "10-Q/A", "10-K/A")
