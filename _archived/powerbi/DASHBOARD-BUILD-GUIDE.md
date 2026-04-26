# DataPulse Dashboard Build Guide -- Midnight Pharma

> Step-by-step instructions for building the complete 10-page DataPulse dashboard in Power BI Desktop.
> Follow each step sequentially. Every visual placement, measure binding, and formatting rule is specified.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Power BI Desktop** | Latest version (March 2026+) with Field Parameters support |
| **PostgreSQL connection** | `localhost:5432/datapulse`, schema `public_marts` |
| **Theme file** | `powerbi/midnight-pharma.json` (in this repository) |
| **Semantic model** | Existing PBIX with 99 DAX measures + 11-item calc group already loaded |
| **DAX additions** | 16 new measures from `powerbi/dashboard-dax-additions.md` already created |
| **Disconnected tables** | `Metric Selector`, `_ViewToggle`, `_KPIDisplayMode` already created |
| **Egypt TopoJSON** | Downloaded from Power BI community for Shape Map visual |

### Color Reference (keep open while building)

| Role | Hex | Where Used |
|------|-----|------------|
| Page background | `#0D1117` | Canvas wallpaper |
| Card surface | `#161B22` | All card/panel backgrounds |
| Elevated surface | `#21262D` | Hover states, nav bar, slicer panels |
| Border | `#30363D` | 1px card borders, separators |
| Text primary | `#E6EDF3` | Headings, KPI values |
| Text secondary | `#A8B3BD` | Subtitles, axis labels (WCAG 4.5:1) |
| Accent Teal | `#00BFA5` | Primary KPIs, active nav, default chart color |
| Accent Blue | `#2196F3` | Secondary chart series |
| Accent Amber | `#FFB300` | Warnings, discount highlights |
| Positive | `#2E7D32` | Growth up |
| Positive light | `#81C784` | Slight positive |
| Warning | `#F57C00` | Slight negative |
| Negative | `#C62828` | Strong negative |
| Neutral | `#9E9E9E` | No data / blank |

---

## Step 1: Apply Theme

1. Open the existing DataPulse PBIX file.
2. Go to **View** tab > **Themes** > **Browse for themes**.
3. Navigate to `powerbi/midnight-pharma.json` and select it.
4. Click **Apply**.
5. **Verify:** The canvas background should turn `#0D1117` (near-black). All existing visuals should pick up the new colors.

If the background does not change automatically:
- Go to **Format** pane > **Page background** > Color: `#0D1117`, Transparency: 0%.
- Go to **Format** pane > **Wallpaper** > Color: `#0D1117`, Transparency: 0%.

Repeat the wallpaper/background check on every page you create.

---

## Step 2: Create All 13 Pages

### 2.1 Create Pages

Right-click the page tab at the bottom and select **New page** until you have 13 pages total. Rename each page exactly as shown:

| # | Page Name | Size | Visible | Tooltip Page |
|---|-----------|------|---------|-------------|
| 1 | **Overview** | 1280 x 720 | Yes | No |
| 2 | **Revenue** | 1280 x 720 | Yes | No |
| 3 | **Products** | 1280 x 720 | Yes | No |
| 4 | **Customers** | 1280 x 720 | Yes | No |
| 5 | **Staff** | 1280 x 720 | Yes | No |
| 6 | **Returns** | 1280 x 720 | Yes | No |
| 7 | **Discounts** | 1280 x 720 | Yes | No |
| 8 | **Trends** | 1280 x 720 | Yes | No |
| 9 | **Data Quality** | 1280 x 720 | Yes | No |
| 10 | **Validation** | 1280 x 720 | Yes | No |
| 11 | **Tooltip Product** | 320 x 240 | **Hidden** | **Yes** |
| 12 | **Tooltip Customer** | 280 x 200 | **Hidden** | **Yes** |
| 13 | **Tooltip Month** | 260 x 180 | **Hidden** | **Yes** |

### 2.2 Configure Page Settings

For **each main page (1-10)**:
1. Select the page tab.
2. Open **Format** pane > **Page information** > **Page type**: Default.
3. **Canvas settings** > Type: Custom > Width: 1280, Height: 720.
4. **Page background**: Color `#0D1117`, Transparency 0%.
5. **Wallpaper**: Color `#0D1117`, Transparency 0%.

For **each tooltip page (11-13)**:
1. Select the page tab.
2. **Page information** > **Page type**: Tooltip.
3. **Canvas settings** > Type: Custom.
   - Tooltip Product: Width 320, Height 240.
   - Tooltip Customer: Width 280, Height 200.
   - Tooltip Month: Width 260, Height 180.
4. **Allow use as tooltip**: ON.
5. **Page background**: Color `#161B22`, Transparency 0%.
6. Right-click the page tab > **Hide page**.

---

## Step 3: Build Navigation Sidebar

The sidebar is a group of shapes and buttons placed on the left edge of every main page.

### 3.1 Build Sidebar on Page 1 (Overview)

#### Background rectangle

1. Insert > Shapes > **Rectangle**.
2. Position: X=0, Y=0, Width=60, Height=720.
3. Format:
   - Fill: `#161B22`, Transparency 0%.
   - Border: ON, Color `#30363D`, Width 1px (right side only -- if Power BI does not support per-side borders, apply 1px all around).
   - Border radius: 0.
   - Shadow: OFF.

#### DataPulse brand mark (top)

1. Insert > **Image** or **Text box**.
2. Position: X=5, Y=8, Width=50, Height=40.
3. If using text: Type "DP", Segoe UI Semibold 16pt, Color `#00BFA5`, center-aligned.
4. No action (non-clickable).

#### Navigation buttons (10 total)

Create each button using Insert > **Buttons** > **Blank** (or **Navigator** if available). Position them vertically below the brand mark.

| Button | Y Position | Icon Text | Page Navigation Target | Alt-text |
|--------|-----------|-----------|----------------------|----------|
| Overview | 60 | Home icon | Page 1: Overview | Navigate to Overview |
| Revenue | 110 | $ icon | Page 2: Revenue | Navigate to Revenue |
| Products | 160 | Pill icon | Page 3: Products | Navigate to Products |
| Customers | 210 | People icon | Page 4: Customers | Navigate to Customers |
| Staff | 260 | Badge icon | Page 5: Staff | Navigate to Staff |
| Returns | 310 | Arrow icon | Page 6: Returns | Navigate to Returns |
| Discounts | 360 | Tag icon | Page 7: Discounts | Navigate to Discounts |
| Trends | 410 | Chart icon | Page 8: Trends | Navigate to Trends |
| Data Quality | 480 | Shield icon | Page 9: Data Quality | Navigate to Data Quality |
| Validation | 530 | Check icon | Page 10: Validation | Navigate to Validation |

**For each button:**

1. Position: X=0, Width=60, Height=40.
2. **Style** > Default state:
   - Fill: `#161B22`, Transparency 0%.
   - Text: Icon character (or use image), Color `#A8B3BD`, 14pt, center-aligned.
   - Border: OFF.
3. **Style** > Hover state:
   - Fill: `#21262D`.
   - Text color: `#E6EDF3`.
4. **Action** > Type: **Page navigation** > Destination: (select the target page).

#### Active state indicator

For the **current page's button** (on Page 1, the Overview button):

1. Insert > Shapes > **Rectangle**.
2. Position: X=0, Y=60 (same Y as the active button), Width=3, Height=40.
3. Fill: `#00BFA5`.
4. Border: OFF.
5. Change the active button's default fill to `#21262D`.

#### Group the sidebar

1. Select all sidebar elements (background rectangle + brand mark + 10 buttons + active accent).
2. Right-click > **Group** > Name the group "Sidebar".

### 3.2 Copy Sidebar to All Pages

1. Select the "Sidebar" group on Page 1.
2. Ctrl+C.
3. Navigate to Page 2, Ctrl+V. Adjust the active accent bar:
   - Move the 3px teal accent to Y=110 (Revenue button position).
   - Change Revenue button default fill to `#21262D`, reset Overview button fill to `#161B22`.
4. Repeat for Pages 3-10, moving the accent bar to the corresponding button position each time.

| Page | Active Button | Accent Y Position |
|------|--------------|-------------------|
| 1 Overview | Overview | 60 |
| 2 Revenue | Revenue | 110 |
| 3 Products | Products | 160 |
| 4 Customers | Customers | 210 |
| 5 Staff | Staff | 260 |
| 6 Returns | Returns | 310 |
| 7 Discounts | Discounts | 360 |
| 8 Trends | Trends | 410 |
| 9 Data Quality | Data Quality | 480 |
| 10 Validation | Validation | 530 |

---

## Step 4: Build Global Filter Panel

### 4.1 Create the Filter Panel Overlay (on Page 1)

1. Insert > Shapes > **Rectangle**.
2. Position: X=1000, Y=0, Width=280, Height=720.
3. Fill: `#161B22`, Transparency 0%.
4. Border: Left side `#30363D` 1px (or all sides 1px).
5. Shadow: ON, `#000000` 70% transparency, BottomRight preset.

#### Panel title

1. Insert > **Text box** at X=1010, Y=10, Width=260, Height=30.
2. Text: "Filters", Segoe UI Semibold 14pt, Color `#E6EDF3`.

#### Add 5 slicers inside the panel

| # | Slicer Field | Type | Position (X, Y, W, H) | Default |
|---|-------------|------|----------------------|---------|
| 1 | `dim_date[year]` | Dropdown | 1010, 50, 260, 60 | Latest year |
| 2 | `dim_date[quarter_label]` | Buttons (horizontal) | 1010, 120, 260, 50 | All |
| 3 | `dim_date[month_name]` | Dropdown (multi-select) | 1010, 180, 260, 60 | All |
| 4 | `dim_billing[billing_group]` | Buttons (horizontal) | 1010, 250, 260, 50 | All |
| 5 | `dim_site[site_name]` | Dropdown (search enabled) | 1010, 310, 260, 60 | All |

**For each slicer:**
- Format > Background: `#161B22`.
- Header: `#E6EDF3` 11pt Segoe UI Semibold.
- Items: `#A8B3BD` 10pt.
- Selection: `#00BFA5` highlight.

#### Clear All button

1. Insert > **Button** > Blank at X=1010, Y=650, Width=260, Height=40.
2. Text: "Clear All Filters", `#A8B3BD` 10pt, centered.
3. Fill: `#21262D`.
4. Hover fill: `#00BFA5`, Hover text: `#0D1117`.
5. Action: Type = **Bookmark** > (will be assigned in Step 18).

### 4.2 Configure Sync Slicers

1. View > **Sync slicers** pane.
2. For each of the 5 slicers, check **Sync** and **Visible** for ALL 10 main pages.
3. Uncheck Visible for tooltip pages (11-13).

### 4.3 Create Filter Toggle Button

On every main page, add a funnel icon button in the top-right corner:

1. Insert > **Button** > Blank.
2. Position: X=1230, Y=10, Width=40, Height=40.
3. Text: Funnel icon (Unicode `U+25BC` or use an image).
4. Fill: `#21262D`, Border: `#30363D` 1px, Radius 4.
5. Hover fill: `#00BFA5`.
6. Action: Type = **Bookmark** (assigned in Step 18).
7. Alt-text: "Toggle filter panel".

### 4.4 Group the Filter Panel

1. Select all filter panel elements (rectangle + title + 5 slicers + clear button).
2. Group > Name "FilterPanel".
3. Copy this group to all 10 main pages.

---

## Step 5: Create Field Parameter

### 5.1 Create via UI

1. Go to **Modeling** tab > **New Parameter** > **Fields**.
2. In the dialog:
   - Name: `Metric Selector`
   - Add these fields in order:
     1. `_Measures[Net Revenue]`
     2. `_Measures[Gross Revenue]`
     3. `_Measures[Total Quantity]`
     4. `_Measures[Discount Rate %]`
   - Check "Add slicer to this page": YES.
3. Click **Create**.

### 5.2 Configure the Slicer

1. Power BI will add a slicer visual automatically. Move it to:
   - Page 2 (Revenue): X=70, Y=55, Width=400, Height=35.
2. Format the slicer as **horizontal buttons**.
3. Style:
   - Items font: `#A8B3BD` 10pt.
   - Selected item: Fill `#00BFA5`, Text `#0D1117`.
   - Unselected: Fill `#21262D`, Text `#A8B3BD`.
4. Copy this slicer to Pages 3 (Products) and 5 (Staff) at the same position.

### 5.3 Hide the Table

1. In the Fields pane, right-click the `Metric Selector` table.
2. Select **Hide in Report View**.

---

## Step 6: Build Tooltip Pages

### 6.1 Tooltip Product (Page 11)

Canvas: 320 x 240, Background `#161B22`, Border `#30363D` 1px, Radius 4.

| Visual | Type | Position (X, Y, W, H) | Field/Measure | Format |
|--------|------|----------------------|---------------|--------|
| Drug Name | Card | 10, 10, 300, 30 | `dim_product[drug_name]` | Bold 14pt `#E6EDF3` |
| Brand | Card | 10, 40, 300, 20 | `dim_product[brand]` | Italic 10pt `#A8B3BD` |
| Category Breadcrumb | Card | 10, 60, 300, 20 | `dim_product[category]` + ` > ` + `dim_product[drug_division]` (use a text measure or multi-row card) | 10pt `#A8B3BD` |
| Net Revenue | Card | 10, 90, 140, 50 | `[Net Revenue]` | 20pt `#00BFA5`, label "Revenue" 9pt `#A8B3BD` |
| Return Rate | Card | 160, 90, 140, 50 | `[Return Rate %]` | 16pt, conditional bg via `[Return Rate Color]` |
| Discount Rate | Card | 10, 150, 140, 50 | `[Discount Rate %]` | 16pt, conditional bg via `[Discount Rate Color]` |
| Quantity | Card | 160, 150, 140, 50 | `[Total Quantity]` | 16pt `#E6EDF3` |

**Assign to visuals:** On any page containing a visual with `dim_product[drug_name]`:
1. Select the visual > Format > **Tooltip** > Type: **Report page** > Page: **Tooltip Product**.

### 6.2 Tooltip Customer (Page 12)

Canvas: 280 x 200, Background `#161B22`.

| Visual | Type | Position (X, Y, W, H) | Field/Measure | Format |
|--------|------|----------------------|---------------|--------|
| Customer Name | Card | 10, 10, 260, 30 | `dim_customer[customer_name]` | Bold 14pt `#E6EDF3` |
| Net Revenue | Card | 10, 50, 125, 50 | `[Net Revenue]` | 18pt `#00BFA5`, label 9pt |
| Invoices | Card | 145, 50, 125, 50 | `[Unique Invoices]` | 18pt `#E6EDF3`, label 9pt |
| Insurance | Card | 10, 110, 125, 40 | `[Insurance Customer %]` | 14pt, icon: shield if >0 |
| Walk-in | Card | 145, 110, 125, 40 | `[Walk-in %]` | 14pt `#A8B3BD` |
| Summary | Multi-row card | 10, 155, 260, 40 | `[Tooltip Customer Summary]` | 9pt `#A8B3BD` |

**Assign to visuals** with `dim_customer[customer_name]`.

### 6.3 Tooltip Month (Page 13)

Canvas: 260 x 180, Background `#161B22`.

| Visual | Type | Position (X, Y, W, H) | Field/Measure | Format |
|--------|------|----------------------|---------------|--------|
| Period | Card | 10, 10, 240, 25 | `dim_date[year_month]` | Bold 12pt `#E6EDF3` |
| Revenue MTD | Card | 10, 40, 240, 40 | `[Revenue MTD]` | 18pt `#00BFA5`, label "MTD Revenue" 9pt |
| MoM Arrow | Card | 10, 85, 115, 40 | `[Revenue MoM Arrow]` | 14pt, conditional color via `[Revenue MoM Color]` |
| YoY Arrow | Card | 135, 85, 115, 40 | `[Revenue YoY Arrow]` | 14pt, conditional color via `[Revenue YoY Color]` |
| Summary | Multi-row card | 10, 130, 240, 45 | `[Tooltip Month Summary]` | 9pt `#A8B3BD` |

**Assign to visuals** with `dim_date[year_month]` on time-axis charts.

---

## Step 7: Build Page 1 -- Overview (Executive Dashboard)

**Usable area:** X=60 to X=1280, Y=0 to Y=720 (sidebar occupies 0-60).

### 7.1 Common Page Header

These elements appear on every main page. Build them once here, then copy to all pages.

#### Dynamic title bar

1. Insert > **Card** visual.
2. Position: X=70, Y=8, Width=700, Height=40.
3. Field: `[Title - Overview]` (from Report Helpers folder).
4. Format:
   - Background: transparent (Transparency 100%).
   - Callout value: 16pt Segoe UI Semibold `#E6EDF3`.
   - Category label: OFF.
   - Border: OFF, Shadow: OFF.
5. Alt-text: "Page title showing current page name and active filters".

#### Filter state subtitle

1. Insert > **Card** visual.
2. Position: X=70, Y=42, Width=700, Height=22.
3. Field: `[Filter State Text]` (from Report Helpers folder).
4. Format:
   - Background: transparent.
   - Callout value: 10pt Segoe UI `#A8B3BD`.
   - Category label: OFF.
   - Border: OFF, Shadow: OFF.

#### Last refresh timestamp

1. Insert > **Card** visual.
2. Position: X=1100, Y=695, Width=170, Height=20.
3. Field: `[Selected Period Label]` or a text measure showing last refresh date.
4. Format: 9pt `#A8B3BD`, transparent background, right-aligned.

#### Filter toggle button

Already placed in Step 4.3 at X=1230, Y=10.

### 7.2 Row 1 -- KPI Cards (4 cards)

Each card: Width=280, Height=110. Spacing between cards: 15px.

| Card | Position (X, Y) | Primary Measure | Sub-Measure | Accent Color |
|------|-----------------|----------------|-------------|-------------|
| A | 70, 70 | `[Net Revenue]` | `[Revenue MoM Arrow]` | `#00BFA5` (left bar) |
| B | 365, 70 | `[Unique Invoices]` | `[Invoices MoM Arrow]` | `#2196F3` |
| C | 660, 70 | `[Unique Customers]` | `[Customers MoM Arrow]` | `#FFB300` |
| D | 955, 70 | `[Avg Invoice Value]` | `[Revenue YoY Arrow]` | `#E91E63` |

**Build each KPI card as follows:**

1. Insert > Shapes > **Rectangle** (the card container).
   - Size: 280 x 110.
   - Fill: `#161B22`, Border: `#30363D` 1px, Radius 8.
   - Shadow: ON, `#000000` 70% transparency, 4px offset.

2. Insert > Shapes > **Rectangle** (left accent bar).
   - Position: left edge of the card, Width=4, Height=110.
   - Fill: accent color (see table above).
   - Border: OFF.

3. Insert > **Card** visual (primary value).
   - Position: 40px from card left, 15px from top. Width=200, Height=50.
   - Field: Primary measure (e.g., `[Net Revenue]`).
   - Callout value: 28pt Segoe UI Semibold `#E6EDF3`.
   - Category label: Show, 9pt `#A8B3BD`.
   - Background: transparent, Border: OFF.

4. Insert > **Card** visual (delta badge).
   - Position: 40px from card left, 70px from top. Width=200, Height=35.
   - Field: Sub-measure (e.g., `[Revenue MoM Arrow]`).
   - Callout value: 12pt `#E6EDF3`.
   - Category label: OFF.
   - Background: transparent, Border: OFF.
   - **Conditional formatting** on font color: Format > Callout value > fx > Based on field value > `[Revenue MoM Color]`.

5. Group the 4 elements for each card. Name groups: "KPI_Revenue", "KPI_Invoices", "KPI_Customers", "KPI_AvgBasket".

**Interaction setting:** Select each KPI card group > Format > Edit interactions > set all other visuals to **No interaction**.

### 7.3 Row 2 Left -- Area Chart (Net Revenue Trend)

1. Insert > **Area chart**.
2. Position: X=70, Y=195, Width=710, Height=230.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Y-axis**: `[Net Revenue]`
   - **Secondary Y-axis**: (none -- add `[Revenue PY]` as a line via the "Line y-axis" well if using combo chart; otherwise overlay with a Line chart)
4. Format:
   - Title: "Revenue Trend", 12pt `#E6EDF3`.
   - Area fill: `#00BFA5` 40% transparency.
   - Line: `#00BFA5` 3px solid.
   - If adding PY comparison line: `#A8B3BD` 2px dashed.
   - X-axis labels: `#A8B3BD` 9pt, rotate 45 degrees if needed.
   - Y-axis labels: `#A8B3BD` 9pt.
   - Gridlines: `#21262D`.
   - Legend: Bottom-center, `#A8B3BD` 9pt.
5. **Tooltip**: Type=Report page, Page=Tooltip Month.
6. Alt-text: "Area chart showing net revenue over time by month with previous year comparison".

### 7.4 Row 2 Right -- Donut Chart (Revenue by Billing Group)

1. Insert > **Donut chart**.
2. Position: X=795, Y=195, Width=465, Height=230.
3. Fields:
   - **Legend**: `dim_billing[billing_group]`
   - **Values**: `[Net Revenue]`
4. Format:
   - Title: "Revenue by Billing Group", 12pt `#E6EDF3`.
   - Inner radius: 60%.
   - Slice colors (set individually):
     - Cash: `#00BFA5`
     - Credit: `#2196F3`
     - Delivery: `#FFB300`
     - Delivery Credit: `#FF5722`
     - Pick-Up: `#9E9E9E`
   - Slice border: `#0D1117` 1px.
   - Detail labels: `#E6EDF3` 10pt, show category + percentage.
   - Legend: Bottom-center, `#A8B3BD` 9pt.
5. Alt-text: "Donut chart showing revenue distribution by billing group".

### 7.5 Row 3 Left -- Top 10 Products Bar Chart

1. Insert > **Clustered bar chart** (horizontal bars).
2. Position: X=70, Y=440, Width=400, Height=260.
3. Fields:
   - **Y-axis**: `dim_product[drug_name]`
   - **X-axis**: `[Net Revenue]`
4. Format:
   - Title: "Top 10 Products", 12pt `#E6EDF3`.
   - Data color: `#00BFA5`.
   - **Top N filter**: Visual-level filter > `dim_product[drug_name]` > Top N > 10 > By value: `[Net Revenue]`.
   - Sort: `[Net Revenue]` descending.
   - Data labels: ON, `#E6EDF3` 10pt.
   - Y-axis labels: `#A8B3BD` 9pt.
   - Gridlines: `#21262D`.
5. **Tooltip**: Type=Report page, Page=Tooltip Product.
6. Alt-text: "Horizontal bar chart showing top 10 products by net revenue".

### 7.6 Row 3 Center -- 2x2 Mini Card Cluster

Insert 4 **Card** visuals in a 2x2 grid:

| Card | Position (X, Y, W, H) | Measure | Format |
|------|----------------------|---------|--------|
| Gross Revenue | 485, 440, 180, 120 | `[Gross Revenue]` | 20pt `#E6EDF3`, label `#A8B3BD` 9pt |
| Total Discount | 680, 440, 180, 120 | `[Total Discount]` | 20pt `#FFB300`, label `#A8B3BD` 9pt |
| Return Rate % | 485, 575, 180, 120 | `[Return Rate %]` | 20pt, conditional color via `[Return Rate Color]` |
| Discount Rate % | 680, 575, 180, 120 | `[Discount Rate %]` | 20pt, conditional color via `[Discount Rate Color]` |

Each card:
- Background: `#161B22`, Border: `#30363D` 1px, Radius 8.
- Shadow: ON.
- Interaction: No interaction.

### 7.7 Row 3 Right -- Top 5 Sites Matrix

1. Insert > **Matrix** visual.
2. Position: X=875, Y=440, Width=385, Height=260.
3. Fields:
   - **Rows**: `dim_site[site_name]`
   - **Values**: `[Net Revenue]`, `[Revenue MoM %]`
4. Format:
   - Title: "Top Sites", 12pt `#E6EDF3`.
   - Visual-level filter: Top N > 5 on `dim_site[site_name]` by `[Net Revenue]`.
   - Column headers: `#E6EDF3` 11pt, background `#21262D`.
   - Row values: `#A8B3BD` 10pt, background `#161B22`.
   - Grid: `#30363D`.
   - **Conditional formatting** on `[Revenue MoM %]`: Background color > Based on field value > `[Revenue MoM Color]`.
   - Row padding: 4.
5. Interaction: Cross-highlight (default).
6. Alt-text: "Matrix showing top 5 sites by revenue with month-over-month change".

### 7.8 Detail View Toggle (Bookmark-driven)

This is a "Show Detail" button that swaps Row 3 for a full-width detail table. Build it now; bookmark assignment happens in Step 18.

1. Insert > **Button** > Blank.
2. Position: X=70, Y=425, Width=100, Height=25.
3. Text: "Show Detail", 10pt `#00BFA5`.
4. Fill: transparent, Border: `#00BFA5` 1px, Radius 4.
5. Hover: Fill `#00BFA5`, Text `#0D1117`.
6. Action: Type=Bookmark (assigned later).

**Detail table** (hidden by default, revealed by bookmark):

1. Insert > **Table** visual.
2. Position: X=70, Y=440, Width=1190, Height=260.
3. Fields: `dim_date[year_month]`, `dim_product[drug_name]`, `dim_customer[customer_name]`, `dim_site[site_name]`, `[Net Revenue]`, `[Total Quantity]`, `[Unique Invoices]`.
4. Format per theme (column headers `#21262D`, values `#A8B3BD`).
5. **Initially hidden** -- set the table's visibility to OFF (or rely on bookmark to toggle).

---

## Step 8: Build Page 2 -- Revenue Analysis

### 8.1 Page Header

Copy the header group from Page 1. Change the title card field to `[Title - Revenue]`.

### 8.2 Row 1 -- 6 Mini-KPI Cards

Each card: Width=185, Height=80. Starting X=70, Y=70, spacing=10px.

| # | X | Measure | Label |
|---|---|---------|-------|
| 1 | 70 | `[Net Revenue]` | Net Revenue |
| 2 | 265 | `[Gross Revenue]` | Gross Revenue |
| 3 | 460 | `[Total Discount]` | Total Discount |
| 4 | 655 | `[Discount Rate %]` | Discount Rate |
| 5 | 850 | `[Net to Gross Ratio]` | Net:Gross Ratio |
| 6 | 1045 | `[Revenue YTD]` | Revenue YTD |

Format: Same card style as Overview KPI cards but smaller. Callout 20pt, label 9pt.

### 8.3 Metric Selector Slicer

Place the `Metric Selector` slicer (from Step 5) at X=70, Y=55, Width=400, Height=35.

### 8.4 Row 2 -- Combo Chart (Revenue + MoM%)

1. Insert > **Line and clustered column chart**.
2. Position: X=70, Y=160, Width=1190, Height=220.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Column y-axis**: `Metric Selector Fields` (from field parameter)
   - **Line y-axis**: `[Revenue MoM %]`
4. Format:
   - Title: "Revenue Trend with MoM Growth", 12pt.
   - Column color: `#00BFA5`.
   - Line color: `#FFB300`, 3px, markers ON.
   - Dual y-axis: Left = revenue (formatted `#,##0`), Right = percentage (formatted `0.0%`).
   - Gridlines: `#21262D`.
5. Tooltip: Tooltip Month page.
6. Alt-text: "Combo chart showing selected metric by month as columns and month-over-month percentage as line".

### 8.5 Row 3 Left -- Stacked Bar (Revenue by Billing x Quarter)

1. Insert > **Stacked bar chart**.
2. Position: X=70, Y=395, Width=380, Height=300.
3. Fields:
   - **Y-axis**: `dim_date[quarter_label]`
   - **X-axis**: `[Net Revenue]`
   - **Legend**: `dim_billing[billing_group]`
4. Format:
   - Title: "Revenue by Billing Group & Quarter".
   - Legend colors: Same as donut in Overview.
   - Data labels: OFF (too crowded).
5. Alt-text: "Stacked bar chart showing revenue breakdown by billing group across quarters".

### 8.6 Row 3 Center -- Egypt Shape Map

> **Prerequisite:** The `governorate` column must exist in `dim_site`. If not yet available, substitute with a basic **Clustered bar chart** of `dim_site[area_manager]` by `[Net Revenue]` as a placeholder.

1. Insert > **Shape Map** visual (may need to enable in Options > Preview features).
2. Position: X=465, Y=395, Width=340, Height=300.
3. Fields:
   - **Location**: `dim_site[governorate]` (or `dim_site[area_manager]` if using placeholder)
   - **Color saturation**: `[Revenue by Governorate]`
4. Format:
   - Map: Load Egypt TopoJSON.
   - Color: Diverging gradient -- Min `#B2DFDB`, Max `#00BFA5`.
   - Title: "Revenue by Region".
   - Background: `#161B22`.
5. Tooltip: Tooltip Month page.
6. Alt-text: "Shape map of Egypt showing revenue intensity by governorate, darker teal indicates higher revenue".

### 8.7 Row 3 Right -- Site Performance Matrix

1. Insert > **Matrix**.
2. Position: X=820, Y=395, Width=440, Height=300.
3. Fields:
   - **Rows**: `dim_site[site_name]`
   - **Columns**: `dim_date[year]`
   - **Values**: `[Net Revenue]`
4. Format:
   - Title: "Site Revenue by Year".
   - Subtotals: ON, by `dim_site[area_manager]` if hierarchy exists.
   - **Conditional formatting**: Background color on `[Net Revenue]` cells > Rules > diverging green-red.
   - Column headers: `#21262D`, Row headers: `#161B22`.
5. Alt-text: "Matrix showing site-level revenue by year with conditional background colors".

---

## Step 9: Build Page 3 -- Product Performance

### 9.1 Page Header + Metric Selector

Copy header, change title to `[Title - Products]`. Add Metric Selector slicer at X=70, Y=55.

### 9.2 Row 1 -- 4 KPI Cards

Same style as Overview. Width=280, Height=90. Y=70.

| # | X | Primary | Sub-Measure |
|---|---|---------|-------------|
| 1 | 70 | `[Unique Products Sold]` | (none) |
| 2 | 365 | `[Revenue per Product]` | (none) |
| 3 | 660 | `[Active Product Count %]` | (none) |
| 4 | 955 | `[Top 20% Product Revenue %]` | (none) |

### 9.3 Row 2 Left -- Treemap

1. Insert > **Treemap**.
2. Position: X=70, Y=175, Width=650, Height=240.
3. Fields:
   - **Category**: `dim_product[category]`
   - **Details** (drill-down): `dim_product[drug_division]`, then `dim_product[drug_name]`
   - **Values**: `Metric Selector Fields`
4. Format:
   - Title: "Product Revenue by Category".
   - Data labels: `#E6EDF3` 10pt, show category + value.
   - **Conditional formatting** on color: Based on `[Revenue MoM %]` > Diverging: `#C62828` (negative) to `#2E7D32` (positive), center `#9E9E9E`.
   - Drill-down: Enable drill icon in visual header.
5. **Interaction**: Set to **No interaction** (prevents cascade queries).
6. Tooltip: Tooltip Product page.
7. Alt-text: "Treemap showing product categories sized by selected metric and colored by month-over-month growth".

### 9.4 Row 2 Right -- Top 15 Products Bar

1. Insert > **Clustered bar chart**.
2. Position: X=735, Y=175, Width=525, Height=240.
3. Fields:
   - **Y-axis**: `dim_product[drug_name]`
   - **X-axis**: `Metric Selector Fields`
4. Filter: Top N = 15 by `[Net Revenue]`.
5. Sort: Descending by value.
6. Data color: `#00BFA5`. Data labels ON.
7. Title: "Top 15 Products".
8. Tooltip: Tooltip Product page.
9. Alt-text: "Horizontal bar chart of top 15 products by selected metric".

### 9.5 Row 3 Left -- Stacked Column (Revenue by Drug Status)

1. Insert > **Stacked column chart**.
2. Position: X=70, Y=430, Width=590, Height=270.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Y-axis**: `[Net Revenue]`
   - **Legend**: `dim_product[drug_status]`
4. Title: "Revenue by Product Status Over Time".
5. Alt-text: "Stacked column chart showing revenue trends split by product status".

### 9.6 Row 3 Right -- Product Detail Table

1. Insert > **Table**.
2. Position: X=675, Y=430, Width=585, Height=270.
3. Fields: `dim_product[drug_name]`, `dim_product[brand]`, `[Net Revenue]`, `[Return Rate %]`, `[Product Revenue Rank]`, `[Total Quantity]`.
4. Format:
   - Top N filter: 50.
   - **Conditional formatting** on `[Net Revenue]`: Data bars, `#00BFA5`.
   - **Conditional formatting** on `[Return Rate %]`: Background color via `[Return Rate Color]`.
   - Scrollable: vertical scrollbar enabled.
5. Title: "Product Detail".
6. Alt-text: "Scrollable table of top 50 products with revenue, return rate, rank, and quantity".

### 9.7 Page-Specific Slicers

Add inline slicers below the title bar:

| Slicer | Field | Position (X, Y, W, H) | Type |
|--------|-------|----------------------|------|
| Category | `dim_product[category]` | 550, 55, 200, 35 | Dropdown |
| Division | `dim_product[drug_division]` | 760, 55, 200, 35 | Dropdown |
| Status | `dim_product[drug_status]` | 970, 55, 150, 35 | Buttons |

Do NOT sync these across pages (page-specific only).

---

## Step 10: Build Page 4 -- Customer Insights

### 10.1 Page Header

Copy header, change title to `[Title - Customers]`.

### 10.2 Row 1 -- 4 KPI Cards (Y=70)

| # | X | Measure | Accent |
|---|---|---------|--------|
| 1 | 70 | `[Unique Customers]` | `#00BFA5` |
| 2 | 365 | `[Revenue per Customer]` | `#2196F3` |
| 3 | 660 | `[Avg Items per Customer]` | `#FFB300` |
| 4 | 955 | `[Insurance Customers]` | `#E91E63` |

### 10.3 Row 2 Left -- Walk-in vs Account Donut

1. Insert > **Donut chart**.
2. Position: X=70, Y=195, Width=580, Height=230.
3. Fields:
   - **Legend**: Create a calculated column or use `dim_customer[is_walk_in]` (True/False).
   - **Values**: `[Net Revenue]`
4. Center label: `[Walk-in %]` (add as a Card overlaid on the donut center).
5. Colors: Walk-in = `#00BFA5`, Account = `#2196F3`.
6. Title: "Walk-in vs Account Revenue".
7. Alt-text: "Donut chart comparing revenue from walk-in customers versus account customers".

### 10.4 Row 2 Right -- Customer Value Scatter

1. Insert > **Scatter chart**.
2. Position: X=665, Y=195, Width=595, Height=230.
3. Fields:
   - **X-axis**: `[Unique Invoices]` (per customer -- may need `CALCULATE([Unique Invoices])`)
   - **Y-axis**: `[Revenue per Customer]`
   - **Size**: `[Total Quantity]`
   - **Details**: `dim_customer[customer_name]`
4. Format:
   - Title: "Customer Value Map".
   - Bubble color: `#00BFA5`.
   - Bubble outline: `#0D1117`.
   - Reference lines: Add median lines for X and Y (Format > Analytics > Median line).
     - Line color: `#30363D`, dashed.
5. Tooltip: Tooltip Customer page.
6. Alt-text: "Scatter plot mapping customers by invoice count and revenue, bubble size shows quantity".

### 10.5 Row 3 -- Customer Matrix (Full Width)

1. Insert > **Matrix**.
2. Position: X=70, Y=440, Width=1190, Height=260.
3. Fields:
   - **Rows**: `dim_customer[customer_name]`
   - **Values**: `[Net Revenue]`, `[Unique Invoices]`, `[Revenue per Customer]`, `[Return Rate %]`
4. Filter: Top N = 50 by `[Net Revenue]`.
5. Conditional formatting:
   - `[Net Revenue]`: Data bars `#00BFA5`.
   - `[Return Rate %]`: Background via `[Return Rate Color]`.
6. Title: "Top 50 Customers".
7. Alt-text: "Matrix of top 50 customers by revenue with data bars and conditional return rate colors".

### 10.6 Page-Specific Slicers

| Slicer | Field | Position | Type |
|--------|-------|----------|------|
| Customer | `dim_customer[customer_name]` | 550, 55, 300, 35 | Dropdown (search enabled) |
| Walk-in | `dim_customer[is_walk_in]` | 870, 55, 100, 35 | Toggle (ON/OFF) |

---

## Step 11: Build Page 5 -- Staff Performance

### 11.1 Page Header + Metric Selector

Copy header, title `[Title - Staff]`. Add Metric Selector slicer at X=70, Y=55.

### 11.2 Row 1 -- 4 KPI Cards (Y=70)

| # | X | Measure |
|---|---|---------|
| 1 | 70 | `[Active Staff Count]` |
| 2 | 365 | `[Revenue per Staff]` |
| 3 | 660 | `[Invoices per Staff]` |
| 4 | 955 | `[Avg Qty per Staff]` |

### 11.3 Row 2 Left -- Top 20 Staff Bar

1. Insert > **Clustered bar chart**.
2. Position: X=70, Y=175, Width=590, Height=240.
3. Fields:
   - **Y-axis**: `dim_staff[staff_name]`
   - **X-axis**: `Metric Selector Fields`
4. Filter: Top N = 20 by `[Net Revenue]`.
5. Data color: `#00BFA5`. Data labels ON (show rank via label content).
6. Title: "Top 20 Staff by Selected Metric".
7. Alt-text: "Horizontal bar chart of top 20 staff members by selected metric".

### 11.4 Row 2 Right -- Staff Scatter

1. Insert > **Scatter chart**.
2. Position: X=675, Y=175, Width=585, Height=240.
3. Fields:
   - **X-axis**: `[Invoices per Staff]`
   - **Y-axis**: `[Revenue per Staff]`
   - **Size**: `[Unique Customers]`
   - **Details**: `dim_staff[staff_name]`
4. Title: "Staff Productivity Map".
5. Bubble color: `#00BFA5`, outline `#0D1117`.
6. Alt-text: "Scatter plot of staff showing invoices vs revenue per person, bubble size is customer count".

### 11.5 Row 3 -- Staff Matrix (Full Width)

1. Insert > **Matrix**.
2. Position: X=70, Y=430, Width=1190, Height=270.
3. Fields:
   - **Rows**: `dim_staff[staff_position]` (expandable to `dim_staff[staff_name]`)
   - **Values**: `[Net Revenue]`, `[Unique Invoices]`, `[Revenue per Staff]`, `[Staff Contribution %]`
4. Conditional formatting:
   - `[Net Revenue]`: Data bars `#00BFA5`.
   - `[Staff Contribution %]`: Background color gradient (low=`#161B22`, high=`#00BFA5` 40% transparency).
5. Row expansion: Enable +/- expand icons on `staff_position`.
6. Title: "Staff Performance by Position".
7. Alt-text: "Expandable matrix showing staff grouped by position with revenue, invoices, and contribution metrics".

### 11.6 Page-Specific Slicers

| Slicer | Field | Position | Type |
|--------|-------|----------|------|
| Position | `dim_staff[staff_position]` | 550, 55, 200, 35 | Dropdown |
| Name | `dim_staff[staff_name]` | 760, 55, 300, 35 | Dropdown (search) |

---

## Step 12: Build Page 6 -- Returns Analysis

### 12.1 Page Header

Title: `[Title - Returns]`.

### 12.2 Row 1 -- 4 KPI Cards (Y=70)

| # | X | Measure | Accent |
|---|---|---------|--------|
| 1 | 70 | `[Return Value]` | `#C62828` |
| 2 | 365 | `[Return Rate %]` | `#F57C00` |
| 3 | 660 | `[Return Invoices]` | `#FFB300` |
| 4 | 955 | `[Return Quantity]` | `#9E9E9E` |

### 12.3 Row 2 Left -- Return Rate Trend Line

1. Insert > **Line chart**.
2. Position: X=70, Y=195, Width=590, Height=230.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Y-axis**: `[Return Rate %]`
4. Format:
   - Line color: `#C62828`, 3px, markers ON.
   - **Reference line** (Analytics pane): Constant line at company average Return Rate %. Color `#A8B3BD`, dashed.
   - Title: "Return Rate Trend".
5. Conditional formatting on data point color: via `[Return Rate Color]`.
6. Tooltip: Tooltip Month page.
7. Alt-text: "Line chart showing return rate percentage trend by month with company average reference line".

### 12.4 Row 2 Right -- Return Value by Billing Group

1. Insert > **Clustered bar chart**.
2. Position: X=675, Y=195, Width=585, Height=230.
3. Fields:
   - **Y-axis**: `dim_billing[billing_group]`
   - **X-axis**: `[Return Value]`
4. Data color: `#C62828`. Sort descending.
5. Title: "Returns by Billing Group".
6. Alt-text: "Horizontal bar chart of return value split by billing group".

### 12.5 Row 3 Left -- Top 20 Return Products Table

1. Insert > **Table**.
2. Position: X=70, Y=440, Width=590, Height=260.
3. Fields: `dim_product[drug_name]`, `[Return Value]`, `[Return Quantity]`, `[Return Rate %]`.
4. Filter: Top N = 20 by `[Return Value]`.
5. Conditional formatting: `[Return Rate %]` background via `[Return Rate Color]`.
6. Title: "Top Return Products".
7. Tooltip: Tooltip Product page.
8. Alt-text: "Table of top 20 products by return value showing return quantity and rate".

### 12.6 Row 3 Right -- Top 20 Return Customers Table

1. Insert > **Table**.
2. Position: X=675, Y=440, Width=585, Height=260.
3. Fields: `dim_customer[customer_name]`, `[Return Value]`, `[Return Invoices]`, `[Return Rate %]`.
4. Filter: Top N = 20 by `[Return Value]`.
5. Conditional formatting: `[Return Rate %]` background via `[Return Rate Color]`.
6. Title: "Top Return Customers".
7. Tooltip: Tooltip Customer page.
8. Alt-text: "Table of top 20 customers by return value showing invoice count and return rate".

### 12.7 Page-Specific Filter

Apply a **page-level filter**: `fct_sales[is_return]` = TRUE. This ensures the entire page shows only return transactions.

---

## Step 13: Build Page 7 -- Discount Analysis

### 13.1 Page Header

Title: `[Title - Discounts]`.

### 13.2 Row 1 -- 4 KPI Cards (Y=70)

| # | X | Measure |
|---|---|---------|
| 1 | 70 | `[Total Discount]` |
| 2 | 365 | `[Discount Rate %]` |
| 3 | 660 | `[Avg Discount per Invoice]` |
| 4 | 955 | `[Net to Gross Ratio]` |

### 13.3 Row 2 Left -- Gross Revenue + Discount Rate Combo

1. Insert > **Line and clustered column chart**.
2. Position: X=70, Y=195, Width=720, Height=230.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Column y-axis**: `[Gross Revenue]`
   - **Line y-axis**: `[Discount Rate %]`
4. Format:
   - Column color: `#2196F3`.
   - Line color: `#FFB300`, 3px, markers ON.
   - Dual y-axis labels.
   - Title: "Gross Revenue vs Discount Rate".
5. Alt-text: "Combo chart showing gross revenue as columns and discount rate as a line over time".

### 13.4 Row 2 Right -- Discount by Billing Group Bar

1. Insert > **Clustered bar chart**.
2. Position: X=805, Y=195, Width=455, Height=230.
3. Fields:
   - **Y-axis**: `dim_billing[billing_group]`
   - **X-axis**: `[Total Discount]`
4. Data color: `#FFB300`. Sort descending.
5. Title: "Discount by Billing Group".
6. Alt-text: "Horizontal bar chart of total discount split by billing group".

### 13.5 Row 3 Left -- Discount Heatmap Matrix

1. Insert > **Matrix**.
2. Position: X=70, Y=440, Width=590, Height=260.
3. Fields:
   - **Rows**: `dim_product[category]`
   - **Columns**: `dim_date[quarter_label]`
   - **Values**: `[Discount Rate %]`
4. **Conditional formatting**: Background color on values > Based on field value > `[Discount Rate Color]`.
5. Title: "Discount Rate by Category & Quarter".
6. Alt-text: "Heatmap matrix showing discount rate by product category and quarter with color intensity".

### 13.6 Row 3 Right -- Top 20 Discount Products Table

1. Insert > **Table**.
2. Position: X=675, Y=440, Width=585, Height=260.
3. Fields: `dim_product[drug_name]`, `[Total Discount]`, `[Discount Rate %]`, `[Net to Gross Ratio]`.
4. Filter: Top N = 20 by `[Discount Rate %]`.
5. Conditional formatting: `[Discount Rate %]` background via `[Discount Rate Color]`.
6. Title: "Highest Discount Products".
7. Alt-text: "Table of top 20 products by discount rate showing total discount and net-to-gross ratio".

---

## Step 14: Build Page 8 -- Trends & Time Intelligence

This is the **primary consumer** of the 11-item calculation group.

### 14.1 Page Header

Title: `[Title - Trends]`.

### 14.2 Row 1 -- Calculation Group Slicer

1. The Time Intelligence calc group creates a `Time Calculation[Name]` column (or similar).
2. Insert > **Slicer**.
3. Position: X=70, Y=70, Width=1190, Height=45.
4. Field: `Time Calculation[Name]` (the calc group item names).
5. Format as **horizontal buttons**:
   - Items: Current | MTD | QTD | YTD | PM | PQ | PY | MoM% | QoQ% | YoY% | Rolling 3M
   - Selected fill: `#00BFA5`, text `#0D1117`.
   - Unselected fill: `#21262D`, text `#A8B3BD`.
   - Font: 10pt.
6. Single select: ON.
7. Default: "Current".
8. Alt-text: "Button slicer to select time intelligence calculation: Current, MTD, QTD, YTD, and comparisons".

### 14.3 Row 2 -- 4 Dynamic KPI Cards (Y=125)

These cards respond to the calc group selection.

| # | X | Measure |
|---|---|---------|
| 1 | 70 | `[Net Revenue]` |
| 2 | 365 | `[Unique Invoices]` |
| 3 | 660 | `[Unique Customers]` |
| 4 | 955 | `[Total Quantity]` |

> **Key behavior:** When the user selects "YTD" in the calc group slicer, all 4 cards automatically show YTD values because the calc group modifies the SELECTEDMEASURE() context.

Card format: Same as Overview KPI cards (280x90).

### 14.4 Row 3 -- Current vs PY Line Chart (Full Width)

1. Insert > **Line chart**.
2. Position: X=70, Y=225, Width=1190, Height=200.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Y-axis**: `[Net Revenue]` (current period -- affected by calc group)
   - **Secondary line** (add to Y-axis): `[Revenue PY]`
4. Format:
   - Current line: `#00BFA5` 3px solid, markers ON.
   - PY line: `#A8B3BD` 2px dashed, markers OFF.
   - Title: "Revenue: Current Period vs Previous Year".
   - Legend: Bottom-center, labels "Current" and "Previous Year".
5. Tooltip: Tooltip Month page.
6. Alt-text: "Dual line chart comparing current period revenue with previous year, showing seasonality".

### 14.5 Row 4 Left -- Waterfall (MoM Variance)

1. Insert > **Waterfall chart**.
2. Position: X=70, Y=440, Width=590, Height=260.
3. Fields:
   - **Category**: `dim_date[month_name]` (or `dim_date[year_month]`)
   - **Y-axis**: `[Revenue MoM Variance]` (if available; otherwise use `[Net Revenue]` and let waterfall calculate sequential differences)
4. Format:
   - Increase: `#2E7D32`.
   - Decrease: `#C62828`.
   - Total: `#00BFA5`.
   - Title: "Revenue Month-over-Month Variance".
5. **Interaction**: Set to **No interaction** (informational only).
6. Alt-text: "Waterfall chart showing month-over-month revenue changes, green for increases and red for decreases".

### 14.6 Row 4 Right -- Time Intelligence Matrix

1. Insert > **Matrix**.
2. Position: X=675, Y=440, Width=585, Height=260.
3. Fields:
   - **Rows**: `dim_date[year_month]`
   - **Values**: `[Revenue MTD]`, `[Revenue YTD]`, `[Revenue MoM %]`, `[Revenue YoY %]`
4. Conditional formatting:
   - `[Revenue MoM %]`: Font color via `[Revenue MoM Color]`.
   - `[Revenue YoY %]`: Font color via `[Revenue YoY Color]`.
5. Title: "Time Intelligence Summary".
6. Alt-text: "Matrix of months showing MTD revenue, YTD revenue, and MoM/YoY growth rates with color coding".

---

## Step 15: Build Page 9 -- Data Quality

### 15.1 Page Header

Title: `[Title - Data Quality]`.

### 15.2 Row 1 -- 5 Severity KPI Cards (Y=70)

Each card: Width=220, Height=100.

| # | X | Measure | Icon Logic |
|---|---|---------|-----------|
| 1 | 70 | `[Unknown Customer Rows]` | Green if 0, Amber if <1%, Red if >1% |
| 2 | 300 | `[Unknown Staff Rows]` | Same traffic-light |
| 3 | 530 | `[Unknown Product Rows]` | Same |
| 4 | 760 | `[Negative Qty Non-Return]` | Green=0, Red>0 |
| 5 | 990 | `[Orphan Row Count]` | Green=0, Red>0 |

**Conditional formatting:** Apply background color using rules:
- Value = 0: Background `#2E7D32` (green).
- Value > 0 and < 1% of total rows: Background `#F57C00` (amber).
- Value >= 1% of total rows: Background `#C62828` (red).

### 15.3 Row 2 Left -- Unknown Rows Trend

1. Insert > **Stacked column chart**.
2. Position: X=70, Y=185, Width=590, Height=230.
3. Fields:
   - **X-axis**: `dim_date[year_month]`
   - **Y-axis**: `[Unknown Customer Rows]`, `[Unknown Staff Rows]`, `[Unknown Product Rows]`
   - **Legend**: (auto from multiple measures)
4. Title: "Unknown Dimension Rows Over Time".
5. Alt-text: "Stacked column chart showing count of unknown rows by dimension type over time".

### 15.4 Row 2 Right -- Gauge Visuals (Unknown %)

Create 3 **Gauge** visuals side by side:

| Gauge | Position (X, Y, W, H) | Value Measure | Target |
|-------|----------------------|---------------|--------|
| Customer | 675, 185, 195, 230 | `[Unknown Customer %]` | 0% |
| Staff | 880, 185, 195, 230 | `[Unknown Staff %]` | 0% |
| Product | 1065, 185, 195, 230 | `[Unknown Product %]` | 0% |

Format each:
- Callout: 20pt `#E6EDF3`.
- Gauge fill: `#00BFA5`.
- Target: `#A8B3BD`.
- Axis: Min=0, Max= (auto or set to 5%).
- Title: dimension name.

> **Note:** If `Unknown Customer %`, `Unknown Staff %`, `Unknown Product %` measures do not exist, create them as `DIVIDE([Unknown Customer Rows], COUNTROWS(fct_sales), 0)`.

### 15.5 Row 3 -- Summary Matrix (Full Width)

1. Insert > **Matrix**.
2. Position: X=70, Y=430, Width=1190, Height=270.
3. Fields:
   - **Rows**: `dim_date[year_month]`
   - **Values**: `[Unknown Customer Rows]`, `[Unknown Staff Rows]`, `[Unknown Product Rows]`, `[Negative Qty Non-Return]`, `[Orphan Row Count]`
4. Conditional formatting: Background on all value columns with traffic-light rules (0=green, >0=amber/red).
5. Title: "Data Quality Summary by Month".
6. Alt-text: "Matrix showing data quality anomaly counts by month and type with traffic-light formatting".

---

## Step 16: Build Page 10 -- Validation

### 16.1 Page Header

Title: `[Title - Validation]`.

### 16.2 Row 1 -- 3 Reconciliation Cards (Y=70)

Width=380, Height=100 each.

| # | X | Measure | Label |
|---|---|---------|-------|
| 1 | 70 | Total row count (use `COUNTROWS(fct_sales)`) | Total Fact Rows |
| 2 | 465 | `[Gross Revenue]` | Total Gross Revenue |
| 3 | 860 | `[Net Revenue]` | Total Net Revenue |

Format: Large 28pt callout, `#00BFA5` accent.

### 16.3 Row 2 -- Reconciliation Matrix (Full Width)

1. Insert > **Matrix**.
2. Position: X=70, Y=185, Width=1190, Height=250.
3. Fields:
   - **Rows**: `dim_date[year]`
   - **Values**: `[Gross Revenue]`, `[Total Discount]`, `[Net Revenue]`
4. Grand totals: ON (both row and column).
5. Title: "Revenue Reconciliation by Year".
6. Alt-text: "Matrix showing gross revenue, discount, and net revenue by year for reconciliation".

### 16.4 Row 3 -- Orphan Detail Table

1. Insert > **Table**.
2. Position: X=70, Y=450, Width=1190, Height=250.
3. Fields: Show rows from `fct_sales` where dimension keys = -1 (Unknown).
   - Apply visual-level filter: `fct_sales[customer_key]` = -1 OR `fct_sales[product_key]` = -1 OR `fct_sales[staff_key]` = -1 OR `fct_sales[site_key]` = -1.
   - Columns: `fct_sales[reference_no]`, `fct_sales[date_key]`, `fct_sales[customer_key]`, `fct_sales[product_key]`, `fct_sales[staff_key]`, `fct_sales[site_key]`, `[Net Revenue]`.
4. Title: "Orphan Records (Unmatched Dimension Keys)".
5. Alt-text: "Detail table showing fact rows with unmatched dimension keys pointing to the Unknown member".

---

## Step 17: Configure Drill-Through

### 17.1 Add Drill-Through Filters

Navigate to each target page and add the drill-through field:

| Target Page | Drill-Through Field | How to Add |
|-------------|--------------------|----|
| **Products** (Page 3) | `dim_product[drug_name]` | Drag to "Add drill-through fields here" well on Page 3 |
| **Products** (Page 3) | `dim_product[category]` | Drag to drill-through well |
| **Customers** (Page 4) | `dim_customer[customer_name]` | Drag to drill-through well |
| **Staff** (Page 5) | `dim_staff[staff_name]` | Drag to drill-through well |
| **Returns** (Page 6) | `dim_product[drug_name]` | Drag to drill-through well |

### 17.2 Add Back Button

On each drill-through target page:

1. Insert > **Buttons** > **Back** (Power BI auto-creates this when drill-through is configured).
2. If not auto-created: Insert > Button > Blank.
   - Position: X=70, Y=695, Width=80, Height=25.
   - Text: "< Back", 10pt `#00BFA5`.
   - Fill: transparent.
   - Action: Type = **Back**.
3. Alt-text: "Back button to return from drill-through".

### 17.3 Test Drill-Through

1. Go to Page 1 (Overview).
2. Right-click any product name in the Top 10 bar chart.
3. Select **Drill through** > **Products**.
4. Verify Page 3 loads filtered to that product.
5. Click the Back button. Verify return to Page 1.

Repeat testing for Customer, Staff, and Returns drill-through paths.

---

## Step 18: Create Bookmarks

### 18.1 Open the Bookmarks Pane

View > **Bookmarks pane**.

### 18.2 Create All 8 Bookmark Pairs

For each pair, configure which visuals/elements are visible in each state.

#### Pair 1: FilterPanel_Show / FilterPanel_Hide (All Pages)

**FilterPanel_Show:**
1. Make the FilterPanel group visible on the current page.
2. Add bookmark: Name = `FilterPanel_Show`.
3. Properties: Data = OFF (don't capture filter state), Display = ON, Current Page = ON.

**FilterPanel_Hide:**
1. Hide the FilterPanel group.
2. Add bookmark: Name = `FilterPanel_Hide`.
3. Same properties.

**Assign to funnel button:** Select the funnel toggle button > Action > Bookmark = `FilterPanel_Show` (first click shows). Create a second button overlaid that triggers `FilterPanel_Hide`.

> **Tip:** Use a single button with **Selection pane** toggling approach -- the button action alternates between the two bookmarks via the bookmark navigator or by layering two buttons.

#### Pair 2: Overview_Summary / Overview_Detail (Page 1)

**Overview_Summary:**
- Row 3 visuals (bar, mini-cards, matrix): Visible.
- Detail table: Hidden.
- "Show Detail" button text visible.

**Overview_Detail:**
- Row 3 visuals: Hidden.
- Detail table: Visible.
- Button text changes to "Show Summary".

Assign to the "Show Detail" button on Page 1.

#### Pair 3: Trends_Absolute / Trends_Growth (Page 8)

**Trends_Absolute:**
- Line chart (Row 3) shows absolute revenue values.
- KPI cards show absolute values.

**Trends_Growth:**
- Switch the calc group slicer to "MoM%" (if using data bookmark) or toggle visible chart set.

#### Pair 4: Trends_Combined / Trends_YoYSplit (Page 8)

**Trends_Combined:**
- Row 3 shows single combined Current vs PY line chart.

**Trends_YoYSplit:**
- Row 3 shows two separate line charts (current year left, PY right) for year-over-year comparison.

#### Pair 5: KPI_Absolute / KPI_Percentage (Pages 2 and 3)

**KPI_Absolute:**
- KPI cards show absolute values (Net Revenue, etc.).

**KPI_Percentage:**
- KPI cards show `[KPI Dynamic Value]` with format switching to percentage.

Assign to a small toggle button near the KPI row.

#### Pair 6: Sidebar_Expanded / Sidebar_Collapsed (All Pages)

**Sidebar_Expanded:**
- Sidebar width = 200px (if building expanded version with labels).
- All nav buttons show icon + text label.

**Sidebar_Collapsed:**
- Sidebar width = 60px (icon only, default state).

Assign to a hamburger icon button at the top of the sidebar.

### 18.3 Bookmark Properties Checklist

For every bookmark:
- **Data**: OFF (unless the bookmark should capture slicer state).
- **Display**: ON (captures visibility of visuals).
- **Current Page**: ON (only affects the current page, not all pages).
- **All Visuals**: Uncheck, then select only the specific visuals affected by the toggle.

---

## Step 19: Accessibility

### 19.1 Alt-Text Templates

Apply alt-text to **every visual** on every page using the Accessibility pane (Format > General > Alt text).

| Visual Type | Alt-Text Template |
|-------------|------------------|
| Card (KPI) | "[Measure name] showing [value description] for the selected period" |
| Bar chart | "Bar chart showing [dimension] ranked by [measure], top [N] shown" |
| Line chart | "Line chart showing [measure] trend over [time field]" |
| Donut chart | "Donut chart showing [measure] distribution by [dimension]" |
| Matrix | "Matrix showing [row field] by [column/value fields] with conditional formatting" |
| Scatter | "Scatter plot of [x-measure] vs [y-measure] with [size-measure] as bubble size" |
| Treemap | "Treemap showing [dimension hierarchy] sized by [measure]" |
| Table | "Data table listing [entity] with columns for [field list]" |
| Slicer | "Filter for [field name]" |
| Button | "Button to [action description]" |
| Shape Map | "Map showing [measure] by [geography], darker colors indicate higher values" |
| Waterfall | "Waterfall showing [measure] sequential changes by [dimension]" |

### 19.2 Tab Order

For each page, set the tab order in the **Selection pane** (View > Selection pane):

1. Page title card.
2. Filter state subtitle.
3. KPI cards (left to right).
4. Primary chart (Row 2 left).
5. Secondary chart (Row 2 right).
6. Row 3 visuals (left to right).
7. Slicers.
8. Navigation sidebar buttons (top to bottom).
9. Filter panel elements.

To reorder: Drag items in the Selection pane to match this sequence. Items at the **bottom** of the list get focus **first**.

### 19.3 Focus Ring Color

Power BI uses the system default focus ring. On the dark background, verify the focus ring is visible:
- If using custom theme, the focus ring should be teal (`#00BFA5`). The theme file already sets `tableAccent: "#00BFA5"` which influences focus indicators.
- Test by pressing Tab in reading view and verifying you can see which element has focus.

### 19.4 High Contrast Mode

Test the report in Power BI's built-in high contrast mode:
1. View > **High contrast colors** > select a theme.
2. Verify all text is readable and visuals are distinguishable.

---

## Step 20: Mobile Layout

### 20.1 Create Phone Layouts

For each of the 10 main pages:

1. View > **Mobile layout**.
2. Drag visuals from the desktop layout onto the phone canvas in this priority order:

| Priority | Visual | Width | Notes |
|----------|--------|-------|-------|
| 1 | Dynamic title | Full width | Top of page |
| 2 | KPI cards | 2-column grid | Stack 4 cards in 2x2 |
| 3 | Primary chart | Full width | Increase height to ~300px |
| 4 | Secondary chart | Full width | Below primary |
| 5 | Table/Matrix | Full width | Scrollable |
| 6 | Slicers | Collapsed | Use filter panel only |

### 20.2 Navigation for Mobile

Mobile does not support the left sidebar. Instead:

1. Rely on Power BI's built-in page navigation (swipe or page selector).
2. Optionally add a bottom tab bar with 5 buttons:
   - **Overview**, **Revenue**, **Products**, **Customers**, **Trends**.
   - Plus a "More" button that navigates to a menu page.

### 20.3 Test Mobile Layout

1. Publish the report to Power BI Service.
2. Open in the Power BI Mobile app.
3. Verify: All KPIs readable, charts interactive, slicers accessible.

---

## Step 21: Performance Optimization

### 21.1 Run Performance Analyzer

1. View > **Performance analyzer** > **Start recording**.
2. Navigate to **Page 8 (Trends)** -- heaviest page due to calc group.
3. Click **Refresh visuals**.
4. Review results: Every visual should render in **under 3 seconds**.
5. Repeat for **Page 3 (Products)** -- treemap with drill-down hierarchy.

If any visual exceeds 3 seconds:
- Check if it queries `fct_sales` directly when an `agg_*` table could be used.
- Reduce the Top N filter count.
- Remove unnecessary columns from the visual.

### 21.2 Aggregation Table Routing

Verify these visuals use aggregation tables (not fct_sales) for better performance:

| Visual | Should Use |
|--------|-----------|
| Overview area chart (Revenue Trend) | `agg_sales_monthly` |
| Staff bar chart (Top 20) | `agg_sales_by_staff` |
| Product treemap | `agg_sales_by_product` |
| Customer matrix | `agg_sales_by_customer` |
| Site matrix | `agg_sales_by_site` |
| Returns tables | `agg_returns` |

> **Note:** In Import mode, Power BI's VertiPaq engine may handle this efficiently regardless. However, if you switch to DirectQuery in the future, aggregation routing becomes critical.

### 21.3 Configure Incremental Refresh

Since `fct_sales` has 1M+ rows:

1. Go to **Power Query Editor** (Transform data).
2. On the `fct_sales` query, create two parameters:
   - `RangeStart` (DateTime) = start of refresh window.
   - `RangeEnd` (DateTime) = end of refresh window.
3. Filter `fct_sales` where `date_key >= RangeStart` and `date_key < RangeEnd`.
4. Close Power Query.
5. Right-click `fct_sales` in Fields > **Incremental refresh**.
6. Configure:
   - Store rows in the last: **3 Years**.
   - Refresh rows in the last: **1 Month**.
   - Detect data changes: OFF (or ON if you have a last-modified column).
7. Click Apply.

### 21.4 Visual Count Verification

Check each page stays within the 12-visual maximum (including slicers, cards, shapes):

| Page | Expected Visual Count |
|------|----------------------|
| Overview | 12 (4 KPI + area + donut + bar + 4 mini-cards + matrix + toggle button) |
| Revenue | 11 (6 KPI + combo + bar + map + matrix + slicer) |
| Products | 11 (4 KPI + treemap + bar + stacked col + table + 3 slicers) |
| Customers | 9 (4 KPI + donut + scatter + matrix + 2 slicers) |
| Staff | 10 (4 KPI + bar + scatter + matrix + 2 slicers + metric slicer) |
| Returns | 9 (4 KPI + line + bar + 2 tables) |
| Discounts | 9 (4 KPI + combo + bar + matrix + table) |
| Trends | 10 (calc slicer + 4 KPI + line + waterfall + matrix + 2 buttons) |
| Data Quality | 10 (5 KPI + stacked col + 3 gauges + matrix) |
| Validation | 6 (3 KPI + matrix + table) |

> All pages are at or below the 12-visual limit.

---

## Step 22: Final QA Checklist

Run through every item. Mark each as PASS or FAIL.

### Theme & Appearance

- [ ] 1. Theme applied -- canvas background is `#0D1117` on all 13 pages
- [ ] 2. Card backgrounds are `#161B22` with `#30363D` borders
- [ ] 3. Secondary text color is `#A8B3BD` (not `#8B949E`) on all axis labels and subtitles
- [ ] 4. Chart gridlines are `#21262D` (subtle, not distracting)

### Navigation

- [ ] 5. Click each of 10 sidebar buttons -- correct page loads
- [ ] 6. Active state indicator (teal accent bar) appears on correct button for each page
- [ ] 7. Sidebar appears consistently on all 10 main pages

### Slicers & Filters

- [ ] 8. Select Year 2025 + Quarter Q1 -- all 10 pages filter correctly (sync slicers working)
- [ ] 9. Filter panel toggle button shows/hides the right-side panel
- [ ] 10. Page-specific slicers (Products, Customers, Staff) filter only their page

### Dynamic Content

- [ ] 11. Each page title updates dynamically when filters are applied
- [ ] 12. Filter State Text subtitle reflects current slicer selections
- [ ] 13. Field Parameter: Switch metric on Page 2 to "Gross Revenue" -- combo chart Y-axis updates

### Tooltips

- [ ] 14. Hover over product name in any bar chart -- Product Tooltip page appears with drug_name, revenue, return rate
- [ ] 15. Hover over customer name -- Customer Tooltip page appears with customer details
- [ ] 16. Hover over time-axis point -- Month Tooltip page appears with MTD, MoM%, YoY%

### KPI Cards

- [ ] 17. All arrow badges show Unicode triangles (not just ^/v characters)
- [ ] 18. Arrow colors match direction: green for positive, red for negative, grey for neutral
- [ ] 19. MoM/YoY badges display both arrow AND percentage value

### Drill-Through

- [ ] 20. Right-click product on Overview > Drill through > Products -- filter passes correctly
- [ ] 21. Right-click customer on any page > Drill through > Customers -- works
- [ ] 22. Back button returns to source page after drill-through

### Calculation Group

- [ ] 23. Page 8: Select "YTD" in calc group slicer -- all 4 KPI cards show YTD values
- [ ] 24. Select "MoM%" -- values switch to percentage format
- [ ] 25. Select "PY" -- values show previous year figures

### Conditional Formatting

- [ ] 26. Revenue MoM % columns show green/red backgrounds based on direction
- [ ] 27. Return Rate % cells use traffic-light coloring
- [ ] 28. Discount Rate % heatmap shows color intensity by magnitude
- [ ] 29. Data quality cards show green (0) / amber / red backgrounds

### Bookmarks

- [ ] 30. FilterPanel Show/Hide -- panel slides in and out
- [ ] 31. Overview Summary/Detail -- Row 3 swaps between charts and detail table
- [ ] 32. All 8 bookmark pairs toggle correctly without affecting slicer state (Data = OFF verified)

### Accessibility

- [ ] 33. Tab through Page 1 with keyboard -- logical focus order (title > KPIs > charts > tables)
- [ ] 34. All visuals have descriptive alt-text (check via Accessibility pane)
- [ ] 35. Text secondary `#A8B3BD` is readable on `#0D1117` (WCAG 4.5:1 contrast ratio)

### Performance

- [ ] 36. Performance Analyzer: Page 8 (Trends) -- all visuals render under 3 seconds
- [ ] 37. Performance Analyzer: Page 3 (Products) -- all visuals render under 3 seconds
- [ ] 38. Total visual count per page does not exceed 12

### Mobile

- [ ] 39. Phone layout defined for all 10 main pages
- [ ] 40. KPI cards visible and readable on phone layout
- [ ] 41. Charts interactive on Power BI Mobile app

### Data Integrity

- [ ] 42. Overview Net Revenue KPI matches Revenue page total (cross-page consistency)
- [ ] 43. Validation page: Gross Revenue - Total Discount = Net Revenue (reconciliation check)
- [ ] 44. Data Quality page: All severity cards show expected counts (compare with SQL queries)
- [ ] 45. Shape map renders Egypt governorates (or placeholder bar chart if governorate column not available)

---

## Appendix A: Complete Measure Reference by Page

This table maps every measure used on each page for quick lookup.

### Page 1 -- Overview

| Measure | Folder | Visual |
|---------|--------|--------|
| `Net Revenue` | Core KPIs | KPI Card A, Area chart, Bar chart |
| `Revenue MoM Arrow` | Cond. Formatting | KPI Card A subtitle |
| `Revenue MoM Color` | Cond. Formatting | KPI Card A font color |
| `Unique Invoices` | Core KPIs | KPI Card B |
| `Invoices MoM Arrow` | Cond. Formatting | KPI Card B subtitle |
| `Unique Customers` | Core KPIs | KPI Card C |
| `Customers MoM Arrow` | Cond. Formatting | KPI Card C subtitle |
| `Avg Invoice Value` | Core KPIs | KPI Card D |
| `Revenue YoY Arrow` | Cond. Formatting | KPI Card D subtitle |
| `Revenue PY` | Time Intelligence | Area chart comparison line |
| `Gross Revenue` | Core KPIs | Mini card |
| `Total Discount` | Discount Analysis | Mini card |
| `Return Rate %` | Returns | Mini card |
| `Return Rate Color` | Cond. Formatting | Mini card background |
| `Discount Rate %` | Discount Analysis | Mini card |
| `Discount Rate Color` | Cond. Formatting | Mini card background |
| `Revenue MoM %` | Time Intelligence | Matrix conditional formatting |
| `Revenue MoM Color` | Cond. Formatting | Matrix background |
| `Title - Overview` | Page Titles | Dynamic title |
| `Filter State Text` | Report Helpers | Subtitle |
| `Selected Period Label` | Report Helpers | Last refresh |

### Page 2 -- Revenue

`Net Revenue`, `Gross Revenue`, `Total Discount`, `Discount Rate %`, `Net to Gross Ratio`, `Revenue YTD`, `Revenue MoM %`, `Metric Selector Fields`, `Revenue by Governorate`, `Revenue MoM Color`, `Title - Revenue`, `Filter State Text`

### Page 3 -- Products

`Unique Products Sold`, `Revenue per Product`, `Active Product Count %`, `Top 20% Product Revenue %`, `Net Revenue`, `Revenue MoM %`, `Return Rate %`, `Return Rate Color`, `Product Revenue Rank`, `Total Quantity`, `Metric Selector Fields`, `Discount Rate Color`, `Title - Products`, `Filter State Text`

### Page 4 -- Customers

`Unique Customers`, `Revenue per Customer`, `Avg Items per Customer`, `Insurance Customers`, `Insurance Customer %`, `Net Revenue`, `Walk-in %`, `Walk-in Revenue`, `Account Revenue`, `Unique Invoices`, `Return Rate %`, `Return Rate Color`, `Title - Customers`, `Filter State Text`

### Page 5 -- Staff

`Active Staff Count`, `Revenue per Staff`, `Invoices per Staff`, `Avg Qty per Staff`, `Net Revenue`, `Unique Invoices`, `Unique Customers`, `Staff Contribution %`, `Staff Revenue Rank`, `Metric Selector Fields`, `Title - Staff`, `Filter State Text`

### Page 6 -- Returns

`Return Value`, `Return Rate %`, `Return Rate Color`, `Return Invoices`, `Return Quantity`, `Net Revenue`, `Title - Returns`, `Filter State Text`

### Page 7 -- Discounts

`Total Discount`, `Discount Rate %`, `Discount Rate Color`, `Avg Discount per Invoice`, `Net to Gross Ratio`, `Gross Revenue`, `Title - Discounts`, `Filter State Text`

### Page 8 -- Trends

`Net Revenue`, `Revenue PY`, `Unique Invoices`, `Unique Customers`, `Total Quantity`, `Revenue MTD`, `Revenue YTD`, `Revenue MoM %`, `Revenue MoM Color`, `Revenue YoY %`, `Revenue YoY Color`, `Title - Trends`, `Filter State Text`

### Page 9 -- Data Quality

`Unknown Customer Rows`, `Unknown Staff Rows`, `Unknown Product Rows`, `Negative Qty Non-Return`, `Orphan Row Count`, `Title - Data Quality`, `Filter State Text`

### Page 10 -- Validation

`Gross Revenue`, `Total Discount`, `Net Revenue`, `Title - Validation`, `Filter State Text`

---

## Appendix B: DAX Expressions for New Measures

All 16 new DAX measures are documented in full in `powerbi/dashboard-dax-additions.md`. Key expressions referenced in this guide:

### Field Parameter

```dax
Metric Selector = {
    ("Net Revenue",    NAMEOF('_Measures'[Net Revenue]),    0),
    ("Gross Revenue",  NAMEOF('_Measures'[Gross Revenue]),  1),
    ("Quantity",       NAMEOF('_Measures'[Total Quantity]),  2),
    ("Discount Rate %", NAMEOF('_Measures'[Discount Rate %]), 3)
}
```

### Arrow Badge Pattern (applies to all 5 Arrow measures)

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

### Tooltip Summary Pattern

```dax
Tooltip Product Summary =
VAR _name   = SELECTEDVALUE(dim_product[drug_name], "Multiple Products")
VAR _brand  = SELECTEDVALUE(dim_product[brand], "")
VAR _cat    = SELECTEDVALUE(dim_product[category], "")
VAR _rev    = FORMAT([Net Revenue], "#,##0")
VAR _qty    = FORMAT([Total Quantity], "#,##0")
VAR _rank   = FORMAT([Product Revenue Rank], "#,##0")
RETURN
    _name
    & IF(_brand <> "", UNICHAR(10) & "Brand: " & _brand, "")
    & IF(_cat <> "",   UNICHAR(10) & "Category: " & _cat, "")
    & UNICHAR(10) & "Revenue: " & _rev
    & UNICHAR(10) & "Quantity: " & _qty
    & IF(NOT ISBLANK([Product Revenue Rank]),
          UNICHAR(10) & "Rank: #" & _rank, "")
```

### View Toggle Tables

```dax
_ViewToggle = DATATABLE("View", STRING, {{"Summary"}, {"Detail"}})

_KPIDisplayMode = DATATABLE("Display Mode", STRING, {{"Absolute"}, {"Percentage"}})
```

---

## Appendix C: Cross-Filter Interaction Settings

After building all pages, configure cross-filter behavior:

### Default: Cross-filter ON

Most chart-to-chart interactions should cross-filter. This is the Power BI default.

### Exceptions: Set to "No Interaction"

Select the **source visual**, then for each **target visual**, right-click > Edit interactions > choose the icon:

| Source Visual | Target(s) Set to No Interaction | Page |
|--------------|-------------------------------|------|
| All KPI cards | All other visuals | All pages |
| Products treemap | All other visuals | Products |
| Trends waterfall | All other visuals | Trends |

### Exceptions: Set to "Cross-highlight"

| Source Visual | Target(s) Set to Cross-highlight | Page |
|--------------|-------------------------------|------|
| All bar/column charts | All table/matrix visuals | All pages |

---

## Appendix D: Drill-Down Hierarchies

Configure these hierarchies in the Fields pane before assigning to visuals:

| Hierarchy Name | Levels | Used On |
|---------------|--------|---------|
| Product Hierarchy | `dim_product[category]` > `dim_product[drug_division]` > `dim_product[drug_name]` | Products treemap |
| Staff Hierarchy | `dim_staff[staff_position]` > `dim_staff[staff_name]` | Staff matrix |
| Time Hierarchy | `dim_date[year]` > `dim_date[quarter_label]` > `dim_date[year_month]` | Trends line chart |

To create: In the Fields pane, right-click `dim_product[category]` > **Create hierarchy**. Drag sub-levels into the hierarchy.

---

*End of Dashboard Build Guide.*
*Last updated: 2026-03-27.*
