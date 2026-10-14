"""Tests for the dataset checks and for the reference values quoted in the docs."""

import pandas as pd
import pytest

from scripts import validate_data as vd


@pytest.fixture(scope="module")
def tables():
    return vd.load_tables()


def small_tables():
    """A tiny, valid dataset used to test that the checks catch broken data."""
    return {
        "sales": pd.DataFrame(
            {
                "SalesID": [1, 2],
                "OrderDate": ["2022-01-01", "2022-01-02"],
                "CustomerID": ["C1", "C1"],
                "ProductID": ["P1", "P1"],
                "StoreID": ["S1", "S1"],
                "Quantity": [2, 1],
                "UnitPrice": [100.0, 100.0],
                "DiscountPct": [0.1, 0.0],
                "SalesAmount": [180.0, 100.0],
                "CostAmount": [120.0, 60.0],
                "ProfitAmount": [60.0, 40.0],
                "ReturnFlag": [0, 1],
                "ReturnAmount": [0.0, 100.0],
            }
        ),
        "customers": pd.DataFrame({"CustomerID": ["C1"]}),
        "products": pd.DataFrame({"ProductID": ["P1"], "UnitCost": [60.0]}),
        "stores": pd.DataFrame({"StoreID": ["S1"], "Region": ["North"], "StoreType": ["Standard"]}),
        "dates": pd.DataFrame(
            {"Date": ["2022-01-01", "2022-01-02"], "YearMonth": ["2022-01", "2022-01"]}
        ),
        "targets": pd.DataFrame({"Month": ["2022-01"], "Region": ["North"], "TargetSales": [1.0]}),
    }


# --- checks on the real dataset ------------------------------------------------


def test_real_dataset_passes_all_checks(tables):
    assert vd.run_all_checks(tables) == []


def test_table_sizes_match_readme(tables):
    assert len(tables["sales"]) == 300_000
    assert len(tables["customers"]) == 20_000
    assert len(tables["products"]) == 2_000
    assert len(tables["stores"]) == 200
    assert len(tables["dates"]) == 1_461
    assert len(tables["targets"]) == 240


# --- reference values quoted in README / DAX_Measures.md -----------------------


def test_reference_metrics_match_documentation(tables):
    m = vd.reference_metrics(tables)
    assert m["total_sales"] == pytest.approx(324_567_163, abs=1)
    assert m["total_profit"] == pytest.approx(78_524_299, abs=1)
    assert m["profit_margin"] == pytest.approx(0.242, abs=0.0005)
    assert m["sales_yoy_latest_year"] == pytest.approx(0.114, abs=0.0005)
    assert m["net_sales"] == pytest.approx(302.9e6, rel=0.001)
    assert m["return_value_share"] == pytest.approx(0.067, abs=0.0005)
    assert m["top_product_share"] == pytest.approx(0.311, abs=0.0005)
    assert m["top_10_percent_customer_share"] == pytest.approx(0.485, abs=0.0005)
    assert m["store_count"] == 200
    assert m["outlet_margin"] == pytest.approx(0.092, abs=0.0005)
    assert m["outlet_sales_share"] == pytest.approx(0.202, abs=0.0005)
    assert m["outlet_profit_share"] == pytest.approx(0.077, abs=0.0005)
    assert m["deep_discount_orders"] == 14_647
    assert m["deep_discount_profit"] == pytest.approx(-2.23e6, rel=0.01)


def test_customer_names_are_not_unique(tables):
    """320 names are shared by 20,000 customers, so charts must group by ID, not by name."""
    customers = tables["customers"]
    assert customers["CustomerID"].is_unique
    assert customers["CustomerName"].nunique() == 320


def test_top_customer_and_concentration_by_id(tables):
    by_customer = tables["sales"].groupby("CustomerID")["SalesAmount"].sum().sort_values(ascending=False)
    assert by_customer.index[0] == "CUST-17520"
    assert by_customer.iloc[0] == pytest.approx(2.42e6, rel=0.005)
    assert by_customer.head(20).sum() / by_customer.sum() == pytest.approx(0.0666, abs=0.0005)


def test_all_deep_discounts_are_in_outlets(tables):
    sales = tables["sales"].merge(tables["stores"][["StoreID", "StoreType"]], on="StoreID")
    deep = sales[sales["DiscountPct"] >= 0.35]
    assert set(deep["StoreType"]) == {"Outlet"}


# --- the checks must detect broken data ----------------------------------------


def test_small_dataset_is_valid():
    assert vd.run_all_checks(small_tables()) == []


def test_detects_duplicate_and_empty_keys():
    t = small_tables()
    t["sales"].loc[1, "SalesID"] = 1
    t["customers"].loc[0, "CustomerID"] = None
    problems = vd.check_primary_keys(t)
    assert "sales.SalesID contains duplicates" in problems
    assert "customers.CustomerID contains empty values" in problems


def test_detects_orphan_foreign_keys_and_regions():
    t = small_tables()
    t["sales"].loc[0, "CustomerID"] = "UNKNOWN"
    t["targets"].loc[0, "Region"] = "Mars"
    problems = vd.check_foreign_keys(t)
    assert any("customers.CustomerID" in p for p in problems)
    assert "targets contain regions that do not exist in stores" in problems


def test_detects_broken_formulas():
    t = small_tables()
    t["sales"].loc[0, "SalesAmount"] = 999.0
    t["sales"].loc[0, "CostAmount"] = 1.0
    t["sales"].loc[1, "ReturnAmount"] = 5.0
    t["sales"].loc[0, "ReturnAmount"] = 7.0
    problems = vd.check_amount_formulas(t)
    assert len(problems) == 5


def test_detects_date_problems():
    t = small_tables()
    t["dates"] = pd.DataFrame({"Date": ["2022-01-01", "2022-01-05"], "YearMonth": ["2022-01", "2022-01"]})
    t["sales"].loc[1, "OrderDate"] = "2023-01-01"
    t["targets"].loc[0, "Month"] = "2030-01"
    problems = vd.check_date_coverage(t)
    assert "DimDate has gaps" in problems
    assert "sales fall outside the DimDate range" in problems
    assert "targets contain months missing from DimDate" in problems


def test_main_reports_success(capsys):
    assert vd.main() == 0
    assert "All data checks passed." in capsys.readouterr().out


def test_main_reports_failure(monkeypatch, capsys):
    broken = small_tables()
    broken["sales"].loc[0, "SalesAmount"] = 999.0
    monkeypatch.setattr(vd, "load_tables", lambda: broken)
    assert vd.main() == 1
    assert "Data checks FAILED" in capsys.readouterr().out
