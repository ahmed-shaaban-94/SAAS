# Dashboard DAX Additions

> New measures and objects for the enhanced DataPulse dashboard.
> These are **additions** to the existing 99 measures in the `_Measures` table.
>
> Existing model: 8 tables, 6 relationships, 99 measures, 11-item calc group.

---

## Table of Contents

1. [Field Parameter -- Metric Selector](#1-field-parameter--metric-selector)
2. [Tooltip Support Measures](#2-tooltip-support-measures)
3. [Accessibility Enhancement Measures (Badge Updates)](#3-accessibility-enhancement-measures-badge-updates)
4. [Shape Map Measure](#4-shape-map-measure)
5. [Bookmark Toggle Helper Measures](#5-bookmark-toggle-helper-measures)
6. [Additional KPI Cards](#6-additional-kpi-cards)
7. [Summary of Changes](#7-summary-of-changes)

---

## 1. Field Parameter -- Metric Selector

> **How to create:** Power BI Desktop > Modeling > New Parameter > Fields.
> This creates a disconnected table + slicer that lets users switch the displayed metric dynamically.

### Table: `Metric Selector`

Power BI will auto-generate the table and a `Metric Selector` measure. The definition below is the equivalent DAX.

```dax
Metric Selector = {
    ("Net Revenue",    NAMEOF('_Measures'[Net Revenue]),    0),
    ("Gross Revenue",  NAMEOF('_Measures'[Gross Revenue]),  1),
    ("Quantity",       NAMEOF('_Measures'[Total Quantity]),  2),
    ("Discount Rate %", NAMEOF('_Measures'[Discount Rate %]), 3)
}
```

| Property | Value |
|----------|-------|
| **Type** | Field Parameter (disconnected table) |
| **Created via** | Modeling > New Parameter > Fields |
| **Slicer visual** | Dropdown or button slicer on every page |
| **Usage** | Place `Metric Selector Fields` on the Y-axis of charts instead of a hardcoded measure |

### Auto-generated measure

```dax
Metric Selector Fields =
    SELECTEDMEASURE()
```

> **Note:** After creation, rename the auto-generated column to `Metric Selector Fields`
> if Power BI uses a different default name. Ensure the `Metric Selector` table
> is hidden from the field list (right-click > Hide in Report View) and only the
> slicer visual exposes it.

---

## 2. Tooltip Support Measures

These measures produce concatenated text strings for use in **tooltip pages** (Report Page Tooltips). None of these exist in the current 99 measures.

### 2.1 Tooltip Product Summary

| Property | Value |
|----------|-------|
| **Name** | `Tooltip Product Summary` |
| **Table** | `_Measures` |
| **Display Folder** | `Tooltips` |
| **Format String** | *(none -- text)* |
| **Description** | Concatenated product summary for tooltip page |

```dax
Tooltip Product Summary =
VAR _name   = SELECTEDVALUE(dim_product[drug_name], "Multiple Products")
VAR _brand  = SELECTEDVALUE(dim_product[brand], "")
VAR _cat    = SELECTEDVALUE(dim_product[category], "")
VAR _status = SELECTEDVALUE(dim_product[drug_status], "")
VAR _rev    = FORMAT([Net Revenue], "#,##0")
VAR _qty    = FORMAT([Total Quantity], "#,##0")
VAR _rank   = FORMAT([Product Revenue Rank], "#,##0")
RETURN
    _name
    & IF(_brand <> "", UNICHAR(10) & "Brand: " & _brand, "")
    & IF(_cat <> "",   UNICHAR(10) & "Category: " & _cat, "")
    & IF(_status <> "", UNICHAR(10) & "Status: " & _status, "")
    & UNICHAR(10) & "Revenue: " & _rev
    & UNICHAR(10) & "Quantity: " & _qty
    & IF(NOT ISBLANK([Product Revenue Rank]),
          UNICHAR(10) & "Rank: #" & _rank, "")
```

### 2.2 Tooltip Customer Summary

| Property | Value |
|----------|-------|
| **Name** | `Tooltip Customer Summary` |
| **Table** | `_Measures` |
| **Display Folder** | `Tooltips` |
| **Format String** | *(none -- text)* |
| **Description** | Concatenated customer summary for tooltip page |

```dax
Tooltip Customer Summary =
VAR _name    = SELECTEDVALUE(dim_customer[customer_name], "Multiple Customers")
VAR _rev     = FORMAT([Net Revenue], "#,##0")
VAR _invCnt  = FORMAT([Unique Invoices], "#,##0")
VAR _avgInv  = FORMAT([Avg Invoice Value], "#,##0.00")
VAR _lastTx  = FORMAT([Last Transaction Date], "DD-MMM-YYYY")
RETURN
    _name
    & UNICHAR(10) & "Revenue: " & _rev
    & UNICHAR(10) & "Invoices: " & _invCnt
    & UNICHAR(10) & "Avg Invoice: " & _avgInv
    & IF(NOT ISBLANK([Last Transaction Date]),
          UNICHAR(10) & "Last Txn: " & _lastTx, "")
```

### 2.3 Tooltip Month Summary

| Property | Value |
|----------|-------|
| **Name** | `Tooltip Month Summary` |
| **Table** | `_Measures` |
| **Display Folder** | `Tooltips` |
| **Format String** | *(none -- text)* |
| **Description** | Concatenated month summary for tooltip page |

```dax
Tooltip Month Summary =
VAR _period  = SELECTEDVALUE(dim_date[year_month], "Multiple Periods")
VAR _rev     = FORMAT([Net Revenue], "#,##0")
VAR _qty     = FORMAT([Total Quantity], "#,##0")
VAR _inv     = FORMAT([Unique Invoices], "#,##0")
VAR _cust    = FORMAT([Unique Customers], "#,##0")
VAR _mom     = [Revenue MoM Badge]
RETURN
    _period
    & UNICHAR(10) & "Revenue: " & _rev
    & UNICHAR(10) & "Quantity: " & _qty
    & UNICHAR(10) & "Invoices: " & _inv
    & UNICHAR(10) & "Customers: " & _cust
    & IF(_mom <> "--", UNICHAR(10) & "MoM: " & _mom, "")
```

### 2.4 Last Transaction Date

| Property | Value |
|----------|-------|
| **Name** | `Last Transaction Date` |
| **Table** | `_Measures` |
| **Display Folder** | `Tooltips` |
| **Format String** | `DD-MMM-YYYY` |
| **Description** | Most recent transaction date in current filter context |

```dax
Last Transaction Date =
MAX(fct_sales[date_key])
```

> **Note:** `date_key` is an integer surrogate key (YYYYMMDD). If you need a proper date,
> use `MAXX(fct_sales, RELATED(dim_date[full_date]))` instead. Adjust based on your
> model's date column in `fct_sales`.

---

## 3. Accessibility Enhancement Measures (Badge Updates)

The existing Direction measures return numeric values (1/0/-1) and are hidden.
The existing Badge measures use `^` and `v` characters. The updates below create
**new Unicode arrow badge measures** that are more accessible and visually clear.

> **Strategy:** Create new measures rather than modifying the existing ones, so that
> conditional formatting rules referencing the numeric Direction measures continue to work.

### 3.1 Revenue MoM Arrow

| Property | Value |
|----------|-------|
| **Name** | `Revenue MoM Arrow` |
| **Table** | `_Measures` |
| **Display Folder** | `Conditional Formatting` |
| **Format String** | *(none -- text)* |
| **Description** | Unicode arrow badge for MoM revenue change |

```dax
Revenue MoM Arrow =
VAR _dir = [Revenue MoM Direction]
VAR _pct = [Revenue MoM %]
RETURN
    IF(
        ISBLANK(_pct), "--",
        SWITCH(
            _dir,
            1,  UNICHAR(9650) & " " & FORMAT(_pct, "0.0%"),
            -1, UNICHAR(9660) & " " & FORMAT(_pct, "0.0%"),
            UNICHAR(9654) & " " & FORMAT(_pct, "0.0%")
        )
    )
```

> `UNICHAR(9650)` = &#9650; (black up-pointing triangle),
> `UNICHAR(9660)` = &#9660; (black down-pointing triangle),
> `UNICHAR(9654)` = &#9654; (black right-pointing triangle).

### 3.2 Revenue YoY Arrow

| Property | Value |
|----------|-------|
| **Name** | `Revenue YoY Arrow` |
| **Table** | `_Measures` |
| **Display Folder** | `Conditional Formatting` |
| **Format String** | *(none -- text)* |
| **Description** | Unicode arrow badge for YoY revenue change |

```dax
Revenue YoY Arrow =
VAR _dir = [Revenue YoY Direction]
VAR _pct = [Revenue YoY %]
RETURN
    IF(
        ISBLANK(_pct), "--",
        SWITCH(
            _dir,
            1,  UNICHAR(9650) & " " & FORMAT(_pct, "0.0%"),
            -1, UNICHAR(9660) & " " & FORMAT(_pct, "0.0%"),
            UNICHAR(9654) & " " & FORMAT(_pct, "0.0%")
        )
    )
```

### 3.3 Invoices MoM Arrow

| Property | Value |
|----------|-------|
| **Name** | `Invoices MoM Arrow` |
| **Table** | `_Measures` |
| **Display Folder** | `Conditional Formatting` |
| **Format String** | *(none -- text)* |
| **Description** | Unicode arrow badge for MoM invoice count change |

```dax
Invoices MoM Arrow =
VAR _dir = [Invoices MoM Direction]
VAR _pct = [Invoices MoM %]
RETURN
    IF(
        ISBLANK(_pct), "--",
        SWITCH(
            _dir,
            1,  UNICHAR(9650) & " " & FORMAT(_pct, "0.0%"),
            -1, UNICHAR(9660) & " " & FORMAT(_pct, "0.0%"),
            UNICHAR(9654) & " " & FORMAT(_pct, "0.0%")
        )
    )
```

### 3.4 Customers MoM Arrow

| Property | Value |
|----------|-------|
| **Name** | `Customers MoM Arrow` |
| **Table** | `_Measures` |
| **Display Folder** | `Conditional Formatting` |
| **Format String** | *(none -- text)* |
| **Description** | Unicode arrow badge for MoM customer count change |

```dax
Customers MoM Arrow =
VAR _dir = [Customers MoM Direction]
VAR _pct = [Customers MoM %]
RETURN
    IF(
        ISBLANK(_pct), "--",
        SWITCH(
            _dir,
            1,  UNICHAR(9650) & " " & FORMAT(_pct, "0.0%"),
            -1, UNICHAR(9660) & " " & FORMAT(_pct, "0.0%"),
            UNICHAR(9654) & " " & FORMAT(_pct, "0.0%")
        )
    )
```

### 3.5 Quantity MoM Arrow

| Property | Value |
|----------|-------|
| **Name** | `Quantity MoM Arrow` |
| **Table** | `_Measures` |
| **Display Folder** | `Conditional Formatting` |
| **Format String** | *(none -- text)* |
| **Description** | Unicode arrow badge for MoM quantity change |

```dax
Quantity MoM Arrow =
VAR _dir = [Quantity MoM Direction]
VAR _pct = [Quantity MoM %]
RETURN
    IF(
        ISBLANK(_pct), "--",
        SWITCH(
            _dir,
            1,  UNICHAR(9650) & " " & FORMAT(_pct, "0.0%"),
            -1, UNICHAR(9660) & " " & FORMAT(_pct, "0.0%"),
            UNICHAR(9654) & " " & FORMAT(_pct, "0.0%")
        )
    )
```

---

## 4. Shape Map Measure

For a **Shape Map** visual (e.g., Saudi Arabia governorates), the existing `[Net Revenue]` measure
can be placed directly on the "Color saturation" well, with the governorate column on "Location".

However, if you need a dedicated measure that resolves the geographic granularity:

### 4.1 Revenue by Governorate

| Property | Value |
|----------|-------|
| **Name** | `Revenue by Governorate` |
| **Table** | `_Measures` |
| **Display Folder** | `Report Helpers` |
| **Format String** | `#,##0` |
| **Description** | Net Revenue resolved at governorate level for shape map |

```dax
Revenue by Governorate =
IF(
    HASONEVALUE(dim_site[area_manager]),
    [Net Revenue],
    BLANK()
)
```

> **Note:** This measure returns BLANK when multiple governorates are in context,
> preventing misleading totals on the shape map. Replace `dim_site[area_manager]`
> with the actual governorate column name if different (e.g., `dim_site[governorate]`).

---

## 5. Bookmark Toggle Helper Measures

These measures support **bookmark-driven** view switching (Detail vs. Summary) and
KPI display mode toggling. They require **disconnected tables** created in the model.

### 5.1 Disconnected Table: `_ViewToggle`

Create manually via **Enter Data** or **New Table**:

```dax
_ViewToggle = DATATABLE(
    "View", STRING,
    {
        {"Summary"},
        {"Detail"}
    }
)
```

### 5.2 Is Detail View

| Property | Value |
|----------|-------|
| **Name** | `Is Detail View` |
| **Table** | `_Measures` |
| **Display Folder** | `Report Helpers` |
| **Format String** | `0` |
| **Description** | Returns 1 when Detail view is selected, 0 for Summary |
| **IsHidden** | `true` |

```dax
Is Detail View =
IF(
    SELECTEDVALUE('_ViewToggle'[View], "Summary") = "Detail",
    1,
    0
)
```

> **Usage:** Bind to the "Visible" property of visuals via conditional formatting,
> or use with bookmarks where DAX-driven visibility is needed.

### 5.3 Disconnected Table: `_KPIDisplayMode`

```dax
_KPIDisplayMode = DATATABLE(
    "Display Mode", STRING,
    {
        {"Absolute"},
        {"Percentage"}
    }
)
```

### 5.4 KPI Display Mode

| Property | Value |
|----------|-------|
| **Name** | `KPI Display Mode` |
| **Table** | `_Measures` |
| **Display Folder** | `Report Helpers` |
| **Format String** | *(none -- text)* |
| **Description** | Returns the selected display mode for KPI cards (Absolute or Percentage) |
| **IsHidden** | `true` |

```dax
KPI Display Mode =
SELECTEDVALUE('_KPIDisplayMode'[Display Mode], "Absolute")
```

### 5.5 KPI Dynamic Value

| Property | Value |
|----------|-------|
| **Name** | `KPI Dynamic Value` |
| **Table** | `_Measures` |
| **Display Folder** | `Report Helpers` |
| **Format String** | *(dynamic -- see FormatStringExpression)* |
| **Description** | Switches between absolute Net Revenue and MoM % based on toggle |

```dax
KPI Dynamic Value =
IF(
    [KPI Display Mode] = "Percentage",
    [Revenue MoM %],
    [Net Revenue]
)
```

**Format String Expression** (dynamic formatting):

```dax
KPI Dynamic Value FormatString =
IF(
    [KPI Display Mode] = "Percentage",
    "0.0%",
    "#,##0"
)
```

> **Note:** Apply the format string expression via Measure Tools > Dynamic Format String.

---

## 6. Additional KPI Cards

Cross-referencing the requested measures against the existing 99:

| Requested Measure | Already Exists? | Action |
|-------------------|----------------|--------|
| Revenue per Product | YES -- `Product Analytics` folder | No action needed |
| Revenue per Customer | YES -- `Customer Analytics` folder | No action needed |
| Revenue per Staff | YES -- `Staff Performance` folder | No action needed |
| Invoices per Staff | YES -- `Staff Performance` folder | No action needed |
| Avg Items per Customer | YES -- `Customer Analytics` folder | No action needed |
| Insurance Customers | YES -- `Customer Analytics` folder | No action needed |
| Walk-in Revenue | YES -- `Customer Analytics` folder | No action needed |
| Account Revenue | YES -- `Customer Analytics` folder | No action needed |
| Walk-in % | YES -- `Customer Analytics` folder | No action needed |
| Active Product % | YES -- `Product Analytics` folder (revenue-based) | No action needed |
| Top 20% Product Revenue % | YES -- `Product Analytics` folder | No action needed |
| Staff Contribution % | YES -- `Staff Performance` folder | No action needed |
| Product Revenue Rank | YES -- `Conditional Formatting` folder | No action needed |
| Staff Revenue Rank | YES -- `Conditional Formatting` folder | No action needed |
| Insurance % | YES -- `Revenue Mix` folder (revenue-based) | See note below |

> **Note on Insurance %:** The existing `Insurance %` is in `Revenue Mix` and calculates
> insurance revenue as a share of total revenue. The requested version
> `DIVIDE([Insurance Customers], [Unique Customers])` is a **customer count ratio**,
> which is a different metric. This new measure is added below.

### New measures (not in existing 99):

### 6.1 Insurance Customer %

| Property | Value |
|----------|-------|
| **Name** | `Insurance Customer %` |
| **Table** | `_Measures` |
| **Display Folder** | `Customer Analytics` |
| **Format String** | `0.00%` |
| **Description** | Percentage of customers with insurance transactions |

```dax
Insurance Customer % =
DIVIDE(
    [Insurance Customers],
    [Unique Customers],
    0
)
```

### 6.2 Active Product Count %

| Property | Value |
|----------|-------|
| **Name** | `Active Product Count %` |
| **Table** | `_Measures` |
| **Display Folder** | `Product Analytics` |
| **Format String** | `0.00%` |
| **Description** | Percentage of distinct products sold that have Active status (count-based, not revenue-based) |

```dax
Active Product Count % =
VAR _activeCount =
    CALCULATE(
        DISTINCTCOUNT(fct_sales[product_key]),
        dim_product[drug_status] = "Active"
    )
VAR _totalCount = [Unique Products Sold]
RETURN
    DIVIDE(_activeCount, _totalCount, 0)
```

> **Note:** The existing `Active Product %` is revenue-weighted. This measure is
> count-weighted (what fraction of distinct products are Active).

---

## 7. Summary of Changes

### New Measures (16 total)

| # | Measure Name | Folder | Type |
|---|-------------|--------|------|
| 1 | `Tooltip Product Summary` | Tooltips | Text |
| 2 | `Tooltip Customer Summary` | Tooltips | Text |
| 3 | `Tooltip Month Summary` | Tooltips | Text |
| 4 | `Last Transaction Date` | Tooltips | Date |
| 5 | `Revenue MoM Arrow` | Conditional Formatting | Text |
| 6 | `Revenue YoY Arrow` | Conditional Formatting | Text |
| 7 | `Invoices MoM Arrow` | Conditional Formatting | Text |
| 8 | `Customers MoM Arrow` | Conditional Formatting | Text |
| 9 | `Quantity MoM Arrow` | Conditional Formatting | Text |
| 10 | `Revenue by Governorate` | Report Helpers | Currency |
| 11 | `Is Detail View` | Report Helpers | Integer |
| 12 | `KPI Display Mode` | Report Helpers | Text |
| 13 | `KPI Dynamic Value` | Report Helpers | Numeric |
| 14 | `Insurance Customer %` | Customer Analytics | Percentage |
| 15 | `Active Product Count %` | Product Analytics | Percentage |
| 16 | `KPI Dynamic Value FormatString` | Report Helpers | Text (format expr) |

### New Disconnected Tables (3 total)

| Table | Purpose |
|-------|---------|
| `Metric Selector` | Field parameter for metric switching |
| `_ViewToggle` | Summary/Detail bookmark toggle |
| `_KPIDisplayMode` | Absolute/Percentage KPI display |

### Existing Measures Confirmed (14 of 16 requested KPIs already exist)

All of the following are already in the model and require **no changes**:

- `Revenue per Product` (Product Analytics)
- `Revenue per Customer` (Customer Analytics)
- `Revenue per Staff` (Staff Performance)
- `Invoices per Staff` (Staff Performance)
- `Avg Items per Customer` (Customer Analytics)
- `Insurance Customers` (Customer Analytics)
- `Insurance %` (Revenue Mix -- revenue-based)
- `Walk-in Revenue` (Customer Analytics)
- `Account Revenue` (Customer Analytics)
- `Walk-in %` (Customer Analytics)
- `Active Product %` (Product Analytics -- revenue-based)
- `Top 20% Product Revenue %` (Product Analytics)
- `Staff Contribution %` (Staff Performance)
- `Product Revenue Rank` (Conditional Formatting)
- `Staff Revenue Rank` (Conditional Formatting)

### Post-Creation Checklist

- [ ] Create `Metric Selector` field parameter via Modeling > New Parameter > Fields
- [ ] Create `_ViewToggle` and `_KPIDisplayMode` tables via Enter Data
- [ ] Hide all three disconnected tables from Report View
- [ ] Add all 16 new measures to `_Measures` table
- [ ] Set `Is Detail View` and `KPI Display Mode` as hidden
- [ ] Apply dynamic format string to `KPI Dynamic Value`
- [ ] Create tooltip pages (Product, Customer, Month) and bind summary measures
- [ ] Test arrow measures render correctly in KPI card subtitles
- [ ] Verify `Revenue by Governorate` returns BLANK for multi-region contexts
