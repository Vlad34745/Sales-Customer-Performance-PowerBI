# Data Dictionary

## FactSales

| Column | Description | Type |
|---|---|---|
| SalesID | Unique transaction identifier | Text |
| OrderDate | Transaction date | Date |
| CustomerID | Customer business key | Text |
| ProductID | Product business key | Text |
| StoreID | Store business key | Text |
| Channel | Sales channel | Text |
| PaymentMethod | Payment method | Text |
| Quantity | Units sold | Whole Number |
| UnitPrice | Transaction unit price | Decimal |
| DiscountPct | Discount applied | Decimal |
| SalesAmount | Gross transaction revenue after discount | Decimal |
| CostAmount | Transaction cost | Decimal |
| ProfitAmount | SalesAmount minus CostAmount | Decimal |
| ReturnFlag | Indicates whether transaction was returned | Whole Number |
| ReturnAmount | Returned sales amount | Decimal |

## DimCustomers

| Column | Description |
|---|---|
| CustomerID | Unique customer key |
| CustomerName | Customer name |
| Segment | Customer segment |
| Region | Customer region attribute |
| Country | Customer country |
| SignupDate | Customer signup date |

## DimProducts

| Column | Description |
|---|---|
| ProductID | Unique product key |
| ProductName | Product name |
| Category | Product category |
| Subcategory | Product subcategory |
| UnitCost | Standard product cost |
| ListPrice | Standard list price |
| ProductLaunchDate | Product launch date |

## DimStores

| Column | Description |
|---|---|
| StoreID | Unique store key |
| StoreName | Store name |
| Region | Store region |
| City | Store city |
| StoreType | Flagship / Standard / Outlet |

## DimDate

| Column | Description |
|---|---|
| Date | Calendar date |
| Year | Calendar year |
| Quarter | Quarter |
| MonthNumber | Month number |
| Month | Month name |
| YearMonth | Display field for monthly trends |
| Weekday | Day name |
| IsWeekend | Weekend flag |

## FactTargets

| Column | Description |
|---|---|
| Month | First day of the target month |
| Region | Target region |
| TargetSales | Monthly sales target |

## Important semantic note

`DimCustomers[Region]` and `DimStores[Region]` represent different concepts.

- Customer Region = customer attribute
- Store Region = store/business region

Keep the distinction clear in report labels when both concepts are discussed.
