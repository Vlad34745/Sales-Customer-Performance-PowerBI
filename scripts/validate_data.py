"""Data-quality checks and reference metrics for the Power BI project.

The Power BI report is built on six CSV files in ``Data/``. This module checks
that the files are internally consistent (keys, formulas, date coverage) and
recomputes the headline metrics shown in the report, so that the numbers in the
documentation can be verified outside Power BI.

Run from the repository root:

    python -m scripts.validate_data
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"

TABLE_FILES = {
    "sales": "FactSales.csv",
    "targets": "FactTargets.csv",
    "customers": "DimCustomers.csv",
    "products": "DimProducts.csv",
    "stores": "DimStores.csv",
    "dates": "DimDate.csv",
}

PRIMARY_KEYS = {
    "sales": "SalesID",
    "customers": "CustomerID",
    "products": "ProductID",
    "stores": "StoreID",
    "dates": "Date",
}

# (fact column, dimension table, dimension column)
FOREIGN_KEYS = [
    ("CustomerID", "customers", "CustomerID"),
    ("ProductID", "products", "ProductID"),
    ("StoreID", "stores", "StoreID"),
    ("OrderDate", "dates", "Date"),
]

MONEY_TOLERANCE = 0.01  # amounts are rounded to cents


def load_tables(data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Read all CSV files into a dict of DataFrames."""
    return {name: pd.read_csv(Path(data_dir) / file) for name, file in TABLE_FILES.items()}


def check_primary_keys(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Return a list of problems with missing or duplicated primary keys."""
    problems = []
    for table, key in PRIMARY_KEYS.items():
        column = tables[table][key]
        if column.isna().any():
            problems.append(f"{table}.{key} contains empty values")
        if column.duplicated().any():
            problems.append(f"{table}.{key} contains duplicates")
    return problems


def check_foreign_keys(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Return problems where a fact row points to a missing dimension row."""
    problems = []
    sales = tables["sales"]
    for column, dim_table, dim_column in FOREIGN_KEYS:
        orphans = ~sales[column].isin(tables[dim_table][dim_column])
        if orphans.any():
            problems.append(f"{int(orphans.sum())} sales rows have no match in {dim_table}.{dim_column}")
    regions = set(tables["stores"]["Region"])
    if not set(tables["targets"]["Region"]).issubset(regions):
        problems.append("targets contain regions that do not exist in stores")
    return problems


def check_amount_formulas(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Check that sales, cost, profit and return amounts follow their formulas."""
    problems = []
    sales = tables["sales"].merge(tables["products"][["ProductID", "UnitCost"]], on="ProductID")

    expected_sales = sales["Quantity"] * sales["UnitPrice"] * (1 - sales["DiscountPct"])
    if ((expected_sales - sales["SalesAmount"]).abs() > MONEY_TOLERANCE).any():
        problems.append("SalesAmount differs from Quantity * UnitPrice * (1 - DiscountPct)")

    if ((sales["Quantity"] * sales["UnitCost"] - sales["CostAmount"]).abs() > MONEY_TOLERANCE).any():
        problems.append("CostAmount differs from Quantity * UnitCost")

    profit = sales["SalesAmount"] - sales["CostAmount"] - sales["ProfitAmount"]
    if (profit.abs() > MONEY_TOLERANCE).any():
        problems.append("ProfitAmount differs from SalesAmount - CostAmount")

    returned = sales["ReturnFlag"] == 1
    if (sales.loc[~returned, "ReturnAmount"] != 0).any():
        problems.append("ReturnAmount is not zero for orders that were not returned")
    if ((sales.loc[returned, "ReturnAmount"] - sales.loc[returned, "SalesAmount"]).abs() > MONEY_TOLERANCE).any():
        problems.append("ReturnAmount differs from SalesAmount for returned orders")
    return problems


def check_date_coverage(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Check that the calendar is continuous and covers all sales and targets."""
    problems = []
    dates = pd.to_datetime(tables["dates"]["Date"])
    expected = pd.date_range(dates.min(), dates.max(), freq="D")
    if len(expected) != len(dates):
        problems.append("DimDate has gaps")
    order_dates = pd.to_datetime(tables["sales"]["OrderDate"])
    if order_dates.min() < dates.min() or order_dates.max() > dates.max():
        problems.append("sales fall outside the DimDate range")
    months = set(tables["dates"]["YearMonth"])
    if not set(tables["targets"]["Month"]).issubset(months):
        problems.append("targets contain months missing from DimDate")
    return problems


def run_all_checks(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Run every integrity check and return all problems found."""
    return (
        check_primary_keys(tables)
        + check_foreign_keys(tables)
        + check_amount_formulas(tables)
        + check_date_coverage(tables)
    )


def _share_of_top(values: pd.Series, count: int) -> float:
    ordered = values.sort_values(ascending=False)
    return float(ordered.head(count).sum() / ordered.sum())


def reference_metrics(tables: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Recompute the headline report metrics (no slicers selected)."""
    sales = tables["sales"].copy()
    sales["Year"] = pd.to_datetime(sales["OrderDate"]).dt.year
    sales = sales.merge(tables["stores"][["StoreID", "StoreType"]], on="StoreID")

    total_sales = float(sales["SalesAmount"].sum())
    total_profit = float(sales["ProfitAmount"].sum())
    by_year = sales.groupby("Year")["SalesAmount"].sum()
    latest = by_year.index.max()

    by_product = sales.groupby("ProductID")["SalesAmount"].sum()
    by_customer = sales.groupby("CustomerID")["SalesAmount"].sum()
    top_customer_count = -(-len(by_customer) // 10)  # ceiling of 10%

    outlet = sales[sales["StoreType"] == "Outlet"]
    deep = sales[sales["DiscountPct"] >= 0.35]

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "profit_margin": total_profit / total_sales,
        "sales_yoy_latest_year": float(by_year[latest] / by_year[latest - 1] - 1),
        "net_sales": total_sales - float(sales["ReturnAmount"].sum()),
        "return_value_share": float(sales["ReturnAmount"].sum() / total_sales),
        "top_product_share": _share_of_top(by_product, 1),
        "top_10_percent_customer_share": _share_of_top(by_customer, top_customer_count),
        "store_count": float(tables["stores"]["StoreID"].nunique()),
        "outlet_margin": float(outlet["ProfitAmount"].sum() / outlet["SalesAmount"].sum()),
        "outlet_sales_share": float(outlet["SalesAmount"].sum() / total_sales),
        "outlet_profit_share": float(outlet["ProfitAmount"].sum() / total_profit),
        "deep_discount_orders": float(len(deep)),
        "deep_discount_profit": float(deep["ProfitAmount"].sum()),
    }


def main() -> int:
    tables = load_tables()
    problems = run_all_checks(tables)
    if problems:
        print("Data checks FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("All data checks passed.\n")
    for name, value in reference_metrics(tables).items():
        print(f"{name:32s} {value:,.4f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())  # pragma: no cover
