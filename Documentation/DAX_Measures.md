# DAX Measures

This document records the main DAX measures used in the Power BI report.

> **Important:** The final PBIX remains the source of truth. If a measure in your saved PBIX has a slightly different implementation, keep the PBIX version and update this document to match it.

## 1. Core Sales Measures

```DAX
Total Sales =
SUM(FactSales[SalesAmount])
```

```DAX
Total Cost =
SUM(FactSales[CostAmount])
```

```DAX
Total Profit =
SUM(FactSales[ProfitAmount])
```

```DAX
Total Orders =
DISTINCTCOUNT(FactSales[SalesID])
```

```DAX
Total Quantity =
SUM(FactSales[Quantity])
```

## 2. Profitability

```DAX
Profit Margin % =
DIVIDE(
    [Total Profit],
    [Total Sales]
)
```

```DAX
Average Order Value =
DIVIDE(
    [Total Sales],
    [Total Orders]
)
```

```DAX
Average Discount % =
AVERAGE(FactSales[DiscountPct])
```

## 3. Returns

```DAX
Returned Orders =
CALCULATE(
    [Total Orders],
    FactSales[ReturnFlag] = 1
)
```

```DAX
Return Rate % =
DIVIDE(
    [Returned Orders],
    [Total Orders]
)
```

```DAX
Total Return Amount =
SUM(FactSales[ReturnAmount])
```

## 4. Time Intelligence

The Date table should be marked as a date table using `DimDate[Date]`.

> **Fix (important).** The original `Sales LY` used `SAMEPERIODLASTYEAR` directly. With no Year selected, it shifts the whole 2022–2025 range back one year, so the report compared the 4-year total ($324.6M) with a 3-year total ($228.1M) and showed a meaningless **+42.3%** YoY. The measures below return a blank when several years are in context for `Sales LY`, and `Sales YoY %` then compares the **latest selected year with the year before it** (2025 vs 2024 = **+11.4%**).

```DAX
Sales LY =
IF(
    HASONEVALUE(DimDate[Year]),
    CALCULATE(
        [Total Sales],
        SAMEPERIODLASTYEAR(DimDate[Date])
    )
)
```

```DAX
Sales YoY % =
VAR LatestYear =
    MAX(DimDate[Year])
VAR SalesLatest =
    CALCULATE([Total Sales], DimDate[Year] = LatestYear)
VAR SalesPrior =
    CALCULATE([Total Sales], DimDate[Year] = LatestYear - 1)
RETURN
    IF(
        HASONEVALUE(DimDate[Year]),
        DIVIDE([Total Sales] - [Sales LY], [Sales LY]),
        DIVIDE(SalesLatest - SalesPrior, SalesPrior)
    )
```

The same fix applies to profit. If your `Profit LY` / `Profit YoY %` are built the original way, replace them:

```DAX
Profit LY =
IF(
    HASONEVALUE(DimDate[Year]),
    CALCULATE(
        [Total Profit],
        SAMEPERIODLASTYEAR(DimDate[Date])
    )
)
```

```DAX
Profit YoY % =
VAR LatestYear =
    MAX(DimDate[Year])
VAR ProfitLatest =
    CALCULATE([Total Profit], DimDate[Year] = LatestYear)
VAR ProfitPrior =
    CALCULATE([Total Profit], DimDate[Year] = LatestYear - 1)
RETURN
    IF(
        HASONEVALUE(DimDate[Year]),
        DIVIDE([Total Profit] - [Profit LY], [Profit LY]),
        DIVIDE(ProfitLatest - ProfitPrior, ProfitPrior)
    )
```

Add a small note under the KPI card: *"With several years selected: latest selected year vs the year before."*

## 5. Active Customers

```DAX
Active Customers =
DISTINCTCOUNT(
    FactSales[CustomerID]
)
```

```DAX
Sales per Active Customer =
DIVIDE(
    [Total Sales],
    [Active Customers]
)
```

## 6. Target vs Actual

```DAX
Actual Sales =
[Total Sales]
```

```DAX
Target Sales =
SUM(FactTargets[TargetSales])
```

```DAX
Target Variance =
[Actual Sales] - [Target Sales]
```

```DAX
Target Achievement % =
DIVIDE(
    [Actual Sales],
    [Target Sales],
    0
)
```

## 7. Dynamic Insight: Sales

> **Decimal point in text insights.** Text built with `FORMAT` follows the model locale, so it showed `$324,6M` next to `$324.6M` on the cards, even after the default format locale was set to English (United States). Passing `"en-US"` as the third argument of `FORMAT` did not change the text in this model. Wrapping each decimal `FORMAT` in `SUBSTITUTE(..., ",", ".")` forces a decimal point whatever the locale is.


Updated to use the fixed `Sales YoY %` and to say which year the growth refers to when several years are selected.

```DAX
Insight Sales =
VAR SalesValue =
    [Total Sales]
VAR SelectedYear =
    SELECTEDVALUE(DimDate[Year])
VAR LatestYear =
    MAX(DimDate[Year])
VAR YoYGrowth =
    [Sales YoY %]
VAR SalesText =
    "$" & SUBSTITUTE(FORMAT(SalesValue / 1000000, "0.0"), ",", ".") & "M"
RETURN
    IF(
        ISBLANK(SalesValue),
        "No sales in the current filter context.",
        "Sales " &
        IF(
            NOT ISBLANK(SelectedYear),
            "in " & FORMAT(SelectedYear, "0"),
            "in the selected period"
        ) &
        " reached " &
        SalesText &
        IF(
            NOT ISBLANK(YoYGrowth),
            " (" & SUBSTITUTE(FORMAT(YoYGrowth, "+0.0%;-0.0%"), ",", ".") & " YoY" &
                IF(ISBLANK(SelectedYear), " in " & FORMAT(LatestYear, "0"), "") &
            ").",
            "."
        )
    )
```

## 8. Dynamic Insight: Online Mix

```DAX
Insight Online Mix =
VAR TotalSalesAllChannels =
    CALCULATE(
        [Total Sales],
        REMOVEFILTERS(FactSales[Channel])
    )

VAR OnlineSales =
    CALCULATE(
        [Total Sales],
        REMOVEFILTERS(FactSales[Channel]),
        FactSales[Channel] = "Online"
    )

VAR OnlineShare =
    DIVIDE(
        OnlineSales,
        TotalSalesAllChannels
    )

RETURN
    IF(
        ISBLANK(OnlineShare),
        "No online sales in the current filter context.",
        "Online accounts for " &
        SUBSTITUTE(FORMAT(OnlineShare, "0.0%"), ",", ".") &
        " of total sales."
    )
```

## 9. Dynamic Insight: Top Category

> Retired: kept in the model but no longer shown on any page (replaced by `Insight Top Product`). It ignores Category slicers by design.

```DAX
Insight Top Category =
VAR CategoryTable =
    ADDCOLUMNS(
        ALL(DimProducts[Category]),
        "@Sales",
            CALCULATE([Total Sales])
    )

VAR TopCategoryRow =
    TOPN(
        1,
        CategoryTable,
        [@Sales],
        DESC,
        DimProducts[Category],
        ASC
    )

VAR TopCategoryName =
    MAXX(
        TopCategoryRow,
        DimProducts[Category]
    )

VAR TopCategorySales =
    MAXX(
        TopCategoryRow,
        [@Sales]
    )

VAR TotalCategorySales =
    CALCULATE(
        [Total Sales],
        REMOVEFILTERS(DimProducts[Category])
    )

VAR TopCategoryShare =
    DIVIDE(
        TopCategorySales,
        TotalCategorySales
    )

RETURN
    IF(
        ISBLANK(TopCategoryName),
        "No category data in the current filter context.",
        "Top category is " &
        TopCategoryName &
        ", contributing " &
        SUBSTITUTE(FORMAT(TopCategoryShare, "0.0%"), ",", ".") &
        " of sales."
    )
```

## 10. Dynamic Insight: Top Region

> Retired: kept in the model but no longer shown on any page (replaced by `Insight Deep Discounts`). It ignores Region slicers by design.

```DAX
Insight Top Region =
VAR RegionTable =
    ADDCOLUMNS(
        ALL(DimRegion[Region]),
        "@Sales",
            CALCULATE([Total Sales])
    )

VAR TopRegionRow =
    TOPN(
        1,
        RegionTable,
        [@Sales],
        DESC,
        DimRegion[Region],
        ASC
    )

VAR TopRegionName =
    MAXX(
        TopRegionRow,
        DimRegion[Region]
    )

VAR TopRegionSales =
    MAXX(
        TopRegionRow,
        [@Sales]
    )

RETURN
    IF(
        ISBLANK(TopRegionName),
        "No regional data in the current filter context.",
        "Top store region is " &
        TopRegionName &
        ", generating $" &
        SUBSTITUTE(FORMAT(TopRegionSales / 1000000, "0.0"), ",", ".") &
        "M in sales."
    )
```

## 11. Net Sales and Return Value

`Total Sales` includes orders that were later returned. Net Sales removes the refunded value. It is defined here simply as SalesAmount less ReturnAmount; the dataset is synthetic and has simplified return and cost accounting, so this is not an accounting net-revenue figure.

```DAX
Net Sales =
[Total Sales] - [Total Return Amount]
```

```DAX
Return Value % =
DIVIDE(
    [Total Return Amount],
    [Total Sales]
)
```

## 12. Discount Bands (calculated columns on FactSales)

Used for the *Profit Margin % by Discount Band* chart. Create both columns in **FactSales** (Table tools → New column), then select `Discount Band` and use **Column tools → Sort by column → Discount Band Order**.

```DAX
Discount Band =
SWITCH(
    TRUE(),
    FactSales[DiscountPct] = 0,    "0%",
    FactSales[DiscountPct] <= 0.05, "5%",
    FactSales[DiscountPct] <= 0.10, "10%",
    FactSales[DiscountPct] <= 0.15, "15%",
    FactSales[DiscountPct] <= 0.20, "20%",
    FactSales[DiscountPct] <= 0.30, "30%",
    "40-50%"
)
```

```DAX
Discount Band Order =
SWITCH(
    TRUE(),
    FactSales[DiscountPct] = 0,    1,
    FactSales[DiscountPct] <= 0.05, 2,
    FactSales[DiscountPct] <= 0.10, 3,
    FactSales[DiscountPct] <= 0.15, 4,
    FactSales[DiscountPct] <= 0.20, 5,
    FactSales[DiscountPct] <= 0.30, 6,
    7
)
```

## 13. Store Type Shares

Used for the *Share of Sales vs Share of Profit by Store Type* chart.

```DAX
Store Type Sales Share % =
DIVIDE(
    [Total Sales],
    CALCULATE([Total Sales], REMOVEFILTERS(DimStores[StoreType]))
)
```

```DAX
Store Type Profit Share % =
DIVIDE(
    [Total Profit],
    CALCULATE([Total Profit], REMOVEFILTERS(DimStores[StoreType]))
)
```

## 14. Per-Store Measures (Target vs Actual page)

Show that regional target gaps are explained by store count. Add all three to the region table next to `Target Achievement %`.

```DAX
Store Count =
DISTINCTCOUNT(DimStores[StoreID])
```

```DAX
Sales per Store =
DIVIDE([Total Sales], [Store Count])
```

```DAX
Target per Store =
DIVIDE([Target Sales], [Store Count])
```

## 15. Concentration Measures

```DAX
Top Product Share % =
VAR ProductSales =
    ADDCOLUMNS(
        VALUES(DimProducts[ProductName]),
        "@Sales", [Total Sales]
    )
RETURN
    DIVIDE(
        MAXX(ProductSales, [@Sales]),
        [Total Sales]
    )
```

```DAX
Top 10% Customers Share % =
VAR CustomerSales =
    ADDCOLUMNS(
        VALUES(FactSales[CustomerID]),
        "@Sales", [Total Sales]
    )
VAR TopCustomerCount =
    ROUNDUP(COUNTROWS(CustomerSales) * 0.1, 0)
VAR TopSales =
    SUMX(
        TOPN(TopCustomerCount, CustomerSales, [@Sales], DESC),
        [@Sales]
    )
RETURN
    DIVIDE(TopSales, [Total Sales])
```

## 16. New Dynamic Insights

These replace `Insight Top Category` and `Insight Top Region`, which only repeated what the charts beside them already showed.

```DAX
Insight Top Product =
VAR ProductSales =
    ADDCOLUMNS(
        VALUES(DimProducts[ProductName]),
        "@Sales", [Total Sales]
    )
VAR TopRow =
    TOPN(1, ProductSales, [@Sales], DESC)
VAR TopName =
    MAXX(TopRow, DimProducts[ProductName])
VAR TopSales =
    MAXX(TopRow, [@Sales])
RETURN
    IF(
        ISBLANK(TopName),
        "No product data in the current filter context.",
        TopName & " alone generates " &
        SUBSTITUTE(FORMAT(DIVIDE(TopSales, [Total Sales]), "0.0%"), ",", ".") &
        " of sales."
    )
```

```DAX
Insight Deep Discounts =
VAR DeepOrders =
    CALCULATE([Total Orders], FactSales[DiscountPct] >= 0.35)
VAR DeepProfit =
    CALCULATE([Total Profit], FactSales[DiscountPct] >= 0.35)
RETURN
    IF(
        DeepOrders = 0,
        "No orders with a 35%+ discount in the current filter context.",
        "Orders with a 35%+ discount " &
        IF(DeepProfit < 0, "lost $", "earned $") &
        SUBSTITUTE(FORMAT(ABS(DeepProfit) / 1000000, "0.0"), ",", ".") & "M."
    )
```

Suggested layout for the four insight cards on Executive Overview: `Insight Sales`, `Insight Online Mix`, `Insight Top Product`, `Insight Deep Discounts`.

## 17. Customer Measures and Customer Label

> **Why `Customer Label` exists.** `DimCustomers[CustomerName]` is **not unique**: 20,000 customers share only 320 names (about 63 customers per name). A chart that groups by name silently adds up dozens of different people: "Katrin Novak" showed $3.40M, but that was 66 customers with the same name, and the largest single customer is $2.42M. Customer charts must therefore be grouped by `Customer Label`, which includes the unique `CustomerID`.

Calculated column in **DimCustomers** (Table tools → New column):

```DAX
Customer Label =
DimCustomers[CustomerName] & " (" & DimCustomers[CustomerID] & ")"
```

```DAX
Total Customers =
DISTINCTCOUNT(DimCustomers[CustomerID])
```

```DAX
Sales per Customer =
DIVIDE(
    [Total Sales],
    [Total Customers],
    0
)
```

```DAX
Customer Rank =
IF(
    HASONEVALUE(DimCustomers[CustomerID]),
    RANKX(
        ALL(DimCustomers[CustomerID]),
        [Total Sales],
        ,
        DESC
    )
)
```

Cumulative share for the Top 20 chart. It works per `Customer Label` (unique customers). The denominator removes only the filter on the label, which also removes the chart's own Top N filter, so the share is measured against all sales in the current slicer selection (Year, Region, Segment, Country, Channel).

```DAX
Cumulative Sales % =
VAR CurrentCustomerSales =
    [Total Sales]
VAR TotalSalesAll =
    CALCULATE(
        [Total Sales],
        REMOVEFILTERS(DimCustomers[Customer Label])
    )
VAR CumulativeSales =
    SUMX(
        FILTER(
            ALLSELECTED(DimCustomers[Customer Label]),
            [Total Sales] >= CurrentCustomerSales
        ),
        [Total Sales]
    )
RETURN
    IF(
        NOT ISBLANK(CurrentCustomerSales),
        DIVIDE(CumulativeSales, TotalSalesAll, 0)
    )
```

Expected result with no slicers: the largest customer is **Tomasz Melnyk (CUST-17520), $2.42M**, and the 20th customer's cumulative share is **6.7%**.

## Measure Validation Checklist

Check each measure against the report:

- Total Sales responds to Year and Region filters.
- Sales LY is blank when several years are selected, and changes correctly when a single year is selected.
- Sales YoY % is blank for 2022 (no prior year) and shows the latest selected year vs the year before it when several years are selected.
- Target Sales changes with the Year filter.
- Target Achievement % equals Actual Sales / Target Sales.
- Active Customers reflects customers with transactions in the current filter context.
- Dynamic insights respond to slicers.

### Reference values (no slicers selected)

Use these to confirm the new measures return the expected values:

| Measure | Expected value |
|---|---:|
| Total Sales | $324,567,163 |
| Total Profit | $78,524,299 |
| Profit Margin % | 24.2% |
| Sales YoY % | +11.4% (2025 vs 2024) |
| Net Sales | $302.9M |
| Return Value % | 6.7% |
| Top Product Share % | 31.1% |
| Top 10% Customers Share % | 48.5% |
| Store Count | 200 |
| Largest single customer (by CustomerID) | $2.42M (CUST-17520) |
| Cumulative share of the top 20 customers | 6.7% |
| Profit Margin % at 40-50% discount band | −23.4% |
| Profit Margin % for Outlet stores | 9.2% |
| Sales Share % / Profit Share % for Outlet | 20.2% / 7.7% |
