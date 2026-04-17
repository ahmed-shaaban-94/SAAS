# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: marketing.spec.ts >> Marketing Landing Page — Pharma-First >> navbar has See Demo secondary CTA
- Location: e2e\marketing.spec.ts:52:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('header').getByRole('link', { name: /See Demo/i })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('header').getByRole('link', { name: /See Demo/i })

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - link "Skip to main content" [ref=e2] [cursor=pointer]:
    - /url: "#main-content"
  - generic [ref=e3]:
    - link "Skip to content" [ref=e4] [cursor=pointer]:
      - /url: "#main-content"
    - banner [ref=e5]:
      - navigation "Main navigation" [ref=e6]:
        - link "Data Pulse" [ref=e7] [cursor=pointer]:
          - /url: /
          - generic [ref=e8]:
            - img [ref=e9]
            - generic [ref=e11]: Data Pulse
          - img [ref=e13]
        - button "Open menu" [ref=e15]:
          - img [ref=e16]
    - main [ref=e17]:
      - generic [ref=e19]:
        - generic [ref=e20]:
          - generic [ref=e21]: Built for pharma sales and operations teams
          - heading "Turn pharma sales and operations data into daily decisions" [level=1] [ref=e23]
          - paragraph [ref=e24]: Upload spreadsheets or connect your data sources, clean them automatically, monitor revenue, branch performance, inventory health, and expiry risk, and give your team one dashboard they can act on every day.
          - generic [ref=e25]:
            - generic [ref=e26]:
              - paragraph [ref=e27]: Faster weekly reporting
              - paragraph [ref=e28]: Automated
            - generic [ref=e29]:
              - paragraph [ref=e30]: Earlier stock & expiry visibility
              - paragraph [ref=e31]: 30+ days
            - generic [ref=e32]:
              - paragraph [ref=e33]: View across sales & operations
              - paragraph [ref=e34]: One system
          - generic [ref=e35]:
            - link "Request Pilot Access" [ref=e36] [cursor=pointer]:
              - /url: "#pilot-access"
            - link "See Product Demo" [ref=e37] [cursor=pointer]:
              - /url: /demo
          - paragraph [ref=e38]: Best for commercial leaders, operations teams, and pharmacy groups that need clearer decisions without rebuilding their data stack from scratch.
        - generic [ref=e40]:
          - generic [ref=e46]: Data Pulse Dashboard
          - generic [ref=e47]:
            - generic [ref=e48]:
              - paragraph [ref=e49]: Total Revenue
              - paragraph [ref=e50]: EGP 4.2M
              - paragraph [ref=e51]: +12.5%
            - generic [ref=e52]:
              - paragraph [ref=e53]: Orders
              - paragraph [ref=e54]: 23,847
              - paragraph [ref=e55]: +8.3%
            - generic [ref=e56]:
              - paragraph [ref=e57]: Customers
              - paragraph [ref=e58]: 1,245
              - paragraph [ref=e59]: +15.2%
            - generic [ref=e60]:
              - paragraph [ref=e61]: Avg. Order
              - paragraph [ref=e62]: EGP 176
              - paragraph [ref=e63]: +4.1%
          - generic [ref=e64]:
            - paragraph [ref=e66]: Revenue Trend
            - generic [ref=e108]:
              - paragraph [ref=e110]: Channel Split
              - generic [ref=e112]:
                - paragraph [ref=e113]: Momentum
                - generic [ref=e114]:
                  - generic [ref=e115]: +23%
                  - generic [ref=e116]: Healthy
      - generic [ref=e119]:
        - paragraph [ref=e120]: "Built for teams that manage:"
        - generic [ref=e121]:
          - generic [ref=e122]: Branch performance
          - generic [ref=e123]: Product movement
          - generic [ref=e124]: Stock visibility
          - generic [ref=e125]: Expiry exposure
          - generic [ref=e126]: Supplier workflows
          - generic [ref=e127]: Purchasing operations
      - generic [ref=e130]:
        - generic [ref=e131]:
          - paragraph [ref=e132]: Core capabilities
          - heading "Everything you need to master your data" [level=2] [ref=e133]
          - paragraph [ref=e134]: From raw Excel files to AI-powered insights, Data Pulse handles every step of your sales analytics pipeline.
        - generic [ref=e135]:
          - generic [ref=e137]:
            - img [ref=e139]
            - heading "Data Intake That Works With Real Spreadsheets" [level=3] [ref=e143]
            - paragraph [ref=e144]: Import Excel and CSV files or connect managed sources without forcing your team to clean everything manually first.
          - generic [ref=e146]:
            - img [ref=e148]
            - heading "Automated Cleaning And Validation" [level=3] [ref=e151]
            - paragraph [ref=e152]: Catch duplicates, schema issues, and broken inputs before they distort your dashboards.
          - generic [ref=e154]:
            - img [ref=e156]
            - heading "Executive Revenue Visibility" [level=3] [ref=e158]
            - paragraph [ref=e159]: Track revenue, trend shifts, branch performance, and product movement from one executive overview.
          - generic [ref=e161]:
            - heading "Inventory And Expiry Awareness" [level=3] [ref=e163]
            - paragraph [ref=e164]: Surface stock and expiry risks early so teams can respond before margin and service levels are affected.
          - generic [ref=e166]:
            - img [ref=e168]
            - heading "Alerts And Explainable Insights" [level=3] [ref=e170]
            - paragraph [ref=e171]: Highlight what changed, where to look next, and which problems need action now.
          - generic [ref=e173]:
            - heading "Operational Reporting That Travels" [level=3] [ref=e175]
            - paragraph [ref=e176]: Turn dashboards into reports, briefings, and shared outputs for leaders, branches, and partner teams.
      - generic [ref=e179]:
        - generic [ref=e180]:
          - paragraph [ref=e181]: Pipeline flow
          - heading "How Data Pulse works" [level=2] [ref=e182]
          - paragraph [ref=e183]: Your data flows through four stages, each adding more value. From raw import to intelligent dashboards.
        - generic [ref=e184]:
          - generic [ref=e185]:
            - generic [ref=e186]:
              - img [ref=e188]
              - generic [ref=e192]: "1"
            - heading "Import your data" [level=3] [ref=e193]
            - paragraph [ref=e195]: Bring in spreadsheets or connected sources from sales and operations workflows.
          - generic [ref=e196]:
            - generic [ref=e199]: "2"
            - heading "Clean and validate automatically" [level=3] [ref=e200]
            - paragraph [ref=e202]: Standardize the data, catch quality issues, and make the numbers safer to trust.
          - generic [ref=e203]:
            - generic [ref=e204]:
              - img [ref=e206]
              - generic [ref=e208]: "3"
            - heading "See the business clearly" [level=3] [ref=e209]
            - paragraph [ref=e211]: Track executive KPIs, branch trends, inventory signals, and operational risks from one system.
          - generic [ref=e212]:
            - generic [ref=e215]: "4"
            - heading "Act faster" [level=3] [ref=e216]
            - paragraph [ref=e218]: Use alerts, reports, and drill-downs to move from explanation to action.
      - generic [ref=e223]:
        - generic [ref=e224]:
          - img [ref=e225]
          - paragraph [ref=e228]: Reporting cycles cut from days to hours
          - paragraph [ref=e229]: Weekly sales reporting that used to take days runs automatically.
        - generic [ref=e230]:
          - img [ref=e231]
          - paragraph [ref=e234]: One trusted view across commercial and operations data
          - paragraph [ref=e235]: Revenue, inventory, expiry, and branch performance in a single system.
        - generic [ref=e236]:
          - img [ref=e237]
          - paragraph [ref=e239]: Early visibility into stock and expiry risk
          - paragraph [ref=e240]: Catch problems before they become margin or service-level failures.
        - generic [ref=e241]:
          - img [ref=e242]
          - paragraph [ref=e244]: Faster investigation from alert to action
          - paragraph [ref=e245]: From anomaly detection to fix path — without manual data digging.
      - generic [ref=e248]:
        - generic [ref=e249]:
          - paragraph [ref=e250]: Pilot access
          - heading "Start with a focused rollout, not a bloated implementation" [level=2] [ref=e251]
          - paragraph [ref=e252]: DataPulse is best introduced through a focused pilot that proves value quickly for one team, one workflow, or one operating region.
        - generic [ref=e253]:
          - generic [ref=e254]:
            - heading "Explorer Pilot" [level=3] [ref=e255]
            - paragraph [ref=e256]: Best for teams validating fit with a sample workflow and a limited set of branches or data sources.
            - generic [ref=e257]: Pilot
            - list [ref=e258]:
              - listitem [ref=e259]:
                - img [ref=e260]
                - generic [ref=e262]: Up to 3 data sources
              - listitem [ref=e263]:
                - img [ref=e264]
                - generic [ref=e266]: Revenue and branch dashboards
              - listitem [ref=e267]:
                - img [ref=e268]
                - generic [ref=e270]: Automated cleaning and validation
              - listitem [ref=e271]:
                - img [ref=e272]
                - generic [ref=e274]: Pipeline health monitoring
              - listitem [ref=e275]:
                - img [ref=e276]
                - generic [ref=e278]: Onboarding support
            - link "Apply for Pilot" [ref=e279] [cursor=pointer]:
              - /url: /login
          - generic [ref=e281]:
            - generic [ref=e282]: Popular
            - heading "Operations Pilot" [level=3] [ref=e283]
            - paragraph [ref=e284]: Best for teams that need revenue visibility plus inventory, expiry, and operational monitoring in one environment.
            - generic [ref=e285]: Pilot
            - generic [ref=e286]:
              - generic [ref=e287]: 🎉
              - text: Most requested
            - list [ref=e288]:
              - listitem [ref=e289]:
                - img [ref=e290]
                - generic [ref=e292]: Unlimited data sources
              - listitem [ref=e293]:
                - img [ref=e294]
                - generic [ref=e296]: Full analytics and operations suite
              - listitem [ref=e297]:
                - img [ref=e298]
                - generic [ref=e300]: Inventory, expiry, and PO tracking
              - listitem [ref=e301]:
                - img [ref=e302]
                - generic [ref=e304]: Alerts and explainable insights
              - listitem [ref=e305]:
                - img [ref=e306]
                - generic [ref=e308]: Reports and briefings
              - listitem [ref=e309]:
                - img [ref=e310]
                - generic [ref=e312]: Dedicated pilot support
            - link "Apply for Pilot" [ref=e313] [cursor=pointer]:
              - /url: /login
          - generic [ref=e314]:
            - heading "Enterprise Rollout" [level=3] [ref=e315]
            - paragraph [ref=e316]: Best for organizations preparing for broader access, permissions, integrations, and formal onboarding.
            - generic [ref=e317]: Custom
            - list [ref=e318]:
              - listitem [ref=e319]:
                - img [ref=e320]
                - generic [ref=e322]: Everything in Operations Pilot
              - listitem [ref=e323]:
                - img [ref=e324]
                - generic [ref=e326]: SSO and role-based access
              - listitem [ref=e327]:
                - img [ref=e328]
                - generic [ref=e330]: Custom data connectors
              - listitem [ref=e331]:
                - img [ref=e332]
                - generic [ref=e334]: Reseller and white-label options
              - listitem [ref=e335]:
                - img [ref=e336]
                - generic [ref=e338]: SLA and dedicated support
              - listitem [ref=e339]:
                - img [ref=e340]
                - generic [ref=e342]: Formal onboarding program
            - link "Plan Rollout" [ref=e343] [cursor=pointer]:
              - /url: /login
      - generic [ref=e346]:
        - generic [ref=e347]:
          - heading "Frequently asked questions" [level=2] [ref=e348]
          - paragraph [ref=e349]: Everything you need to know about Data Pulse.
        - generic [ref=e350]:
          - generic [ref=e351]:
            - button "Who is DataPulse for?" [ref=e352]:
              - generic [ref=e353]: Who is DataPulse for?
              - img [ref=e354]
            - paragraph [ref=e356]: DataPulse is built for commercial, analytics, and operations teams that need one trusted view across sales, branch performance, inventory signals, and operational reporting. It is particularly well suited to pharma and retail operations groups.
          - generic [ref=e357]:
            - button "Do we need clean data before using it?" [ref=e358]:
              - generic [ref=e359]: Do we need clean data before using it?
              - img [ref=e360]
            - paragraph [ref=e362]: No. DataPulse is designed to help teams start with real-world spreadsheets and operational inputs, then clean and validate them in a structured flow. You do not need to prepare your data in advance.
          - generic [ref=e363]:
            - button "Is this only for dashboards?" [ref=e364]:
              - generic [ref=e365]: Is this only for dashboards?
              - img [ref=e366]
            - paragraph [ref=e368]: No. The product supports daily decisions through dashboards, alerts, reporting, and operational visibility. It is meant to be an active tool for teams making commercial and operational decisions.
          - generic [ref=e369]:
            - button "Can it support branch and product-level monitoring?" [ref=e370]:
              - generic [ref=e371]: Can it support branch and product-level monitoring?
              - img [ref=e372]
            - paragraph [ref=e374]: Yes. Branch performance, product movement, and exception visibility are core to the product. You can drill from an executive summary down to branch and product detail.
          - generic [ref=e375]:
            - button "What happens during a pilot?" [ref=e376]:
              - generic [ref=e377]: What happens during a pilot?
              - img [ref=e378]
            - paragraph [ref=e380]: A pilot focuses on a defined use case, a manageable data scope, and clear success criteria so your team can measure value quickly. We work with you to define what a successful pilot looks like before starting.
          - generic [ref=e381]:
            - button "Is the platform secure?" [ref=e382]:
              - generic [ref=e383]: Is the platform secure?
              - img [ref=e384]
            - paragraph [ref=e386]: DataPulse is built with role-aware access, row-level data isolation, auditability, and enterprise-minded controls so teams can trust how commercial and operational data is handled.
          - generic [ref=e387]:
            - button "How long does it take to see value?" [ref=e388]:
              - generic [ref=e389]: How long does it take to see value?
              - img [ref=e390]
            - paragraph [ref=e392]: Most teams see their first useful dashboard within hours of importing their first data file. A full pilot covering revenue visibility, inventory monitoring, and reporting typically shows value within one to two weeks.
          - generic [ref=e393]:
            - button "Can we connect live data sources?" [ref=e394]:
              - generic [ref=e395]: Can we connect live data sources?
              - img [ref=e396]
            - paragraph [ref=e398]: Yes. The Control Center supports managed source connections alongside manual file imports. Connected sources sync automatically on a schedule you control.
      - generic [ref=e403]:
        - paragraph [ref=e404]: Start with clarity
        - heading "See what your team should act on every day." [level=2] [ref=e405]
        - paragraph [ref=e406]: If your sales and operations data lives across spreadsheets, manual reports, and disconnected workflows, DataPulse can help you turn it into one clearer operating view.
        - generic [ref=e407]:
          - link "Request Pilot Access" [ref=e408] [cursor=pointer]:
            - /url: "#pilot-access"
          - link "See Product Demo" [ref=e409] [cursor=pointer]:
            - /url: /demo
        - paragraph [ref=e410]: Best for teams that want to prove value in a focused rollout before expanding company-wide.
    - contentinfo [ref=e411]:
      - generic [ref=e412]:
        - generic [ref=e413]:
          - generic [ref=e414]:
            - heading "Product" [level=3] [ref=e415]
            - list [ref=e416]:
              - listitem [ref=e417]:
                - link "How It Works" [ref=e418] [cursor=pointer]:
                  - /url: "#how-it-works"
              - listitem [ref=e419]:
                - link "Use Cases" [ref=e420] [cursor=pointer]:
                  - /url: "#use-cases"
              - listitem [ref=e421]:
                - link "Pilot Access" [ref=e422] [cursor=pointer]:
                  - /url: "#pilot-access"
          - generic [ref=e423]:
            - heading "Company" [level=3] [ref=e424]
            - list [ref=e425]:
              - listitem [ref=e426]:
                - link "About" [ref=e427] [cursor=pointer]:
                  - /url: /#how-it-works
              - listitem [ref=e428]:
                - link "Contact" [ref=e429] [cursor=pointer]:
                  - /url: mailto:info@smartdatapulse.tech
          - generic [ref=e430]:
            - heading "Legal" [level=3] [ref=e431]
            - list [ref=e432]:
              - listitem [ref=e433]:
                - link "Privacy Policy" [ref=e434] [cursor=pointer]:
                  - /url: /privacy
              - listitem [ref=e435]:
                - link "Terms of Service" [ref=e436] [cursor=pointer]:
                  - /url: /terms
        - generic [ref=e437]:
          - generic [ref=e438]:
            - img [ref=e439]
            - generic [ref=e441]: DataPulse
          - paragraph [ref=e442]: © 2026 DataPulse. All rights reserved.
  - button "Open Next.js Dev Tools" [ref=e448] [cursor=pointer]:
    - img [ref=e449]
  - alert [ref=e452]
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | 
  3   | test.describe("Marketing Landing Page — Pharma-First", () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto("/");
  6   |   });
  7   | 
  8   |   // ── Hero ──────────────────────────────────────────────────────────────────
  9   | 
  10  |   test("hero headline is pharma-first", async ({ page }) => {
  11  |     await expect(page.locator("h1")).toContainText(
  12  |       "Turn pharma sales and operations data into daily decisions",
  13  |       { timeout: 15000 }
  14  |     );
  15  |   });
  16  | 
  17  |   test("primary CTA reads Request Pilot Access", async ({ page }) => {
  18  |     const ctas = page.getByRole("link", { name: /Request Pilot Access/i });
  19  |     await expect(ctas.first()).toBeVisible();
  20  |   });
  21  | 
  22  |   test("no generic Get Started or Join Beta CTAs exist", async ({ page }) => {
  23  |     await expect(page.getByText(/Get Started Free/i)).toHaveCount(0);
  24  |     await expect(page.getByText(/Join Beta/i)).toHaveCount(0);
  25  |     await expect(page.getByText(/Start Free Trial/i)).toHaveCount(0);
  26  |   });
  27  | 
  28  |   // ── Trust bar ─────────────────────────────────────────────────────────────
  29  | 
  30  |   test("no placeholder trust claims", async ({ page }) => {
  31  |     // Old: "Trusted by 500+ data teams worldwide"
  32  |     await expect(page.getByText(/Trusted by/i)).toHaveCount(0);
  33  |     // Old placeholder company names
  34  |     await expect(page.getByText("Pharma Corp")).toHaveCount(0);
  35  |     await expect(page.getByText("RetailMax")).toHaveCount(0);
  36  |   });
  37  | 
  38  |   test("trust bar shows pharma use-case list", async ({ page }) => {
  39  |     await expect(
  40  |       page.getByText(/branch performance/i).first()
  41  |     ).toBeVisible();
  42  |   });
  43  | 
  44  |   // ── Navigation ────────────────────────────────────────────────────────────
  45  | 
  46  |   test("navbar has Pilot Access link", async ({ page }) => {
  47  |     await expect(
  48  |       page.locator("nav").getByRole("link", { name: /Pilot Access/i }).first()
  49  |     ).toBeVisible();
  50  |   });
  51  | 
  52  |   test("navbar has See Demo secondary CTA", async ({ page }) => {
  53  |     await expect(
  54  |       page.locator("header").getByRole("link", { name: /See Demo/i })
> 55  |     ).toBeVisible();
      |       ^ Error: expect(locator).toBeVisible() failed
  56  |   });
  57  | 
  58  |   test("no Features nav link (renamed to Product or Use Cases)", async ({ page }) => {
  59  |     // Old nav had "Features" as a link — new nav has "Product" and "Use Cases"
  60  |     const featureNavLink = page.locator('nav a[href="#features"]');
  61  |     await expect(featureNavLink).toHaveCount(0);
  62  |   });
  63  | 
  64  |   // ── How It Works ──────────────────────────────────────────────────────────
  65  | 
  66  |   test("how it works shows pharma operational steps", async ({ page }) => {
  67  |     const section = page.locator("#how-it-works");
  68  |     await expect(section).toBeVisible();
  69  |     await expect(section.getByText(/Import your data/i).first()).toBeVisible();
  70  |     await expect(section.getByText(/Clean and validate/i).first()).toBeVisible();
  71  |     await expect(section.getByText(/See the business clearly/i).first()).toBeVisible();
  72  |     await expect(section.getByText(/Act faster/i).first()).toBeVisible();
  73  |   });
  74  | 
  75  |   // ── Features ──────────────────────────────────────────────────────────────
  76  | 
  77  |   test("features section shows pharma-specific capabilities", async ({ page }) => {
  78  |     const section = page.locator("#product");
  79  |     await expect(section).toBeVisible();
  80  |     await expect(section.getByText(/Inventory And Expiry/i).first()).toBeVisible();
  81  |   });
  82  | 
  83  |   // ── Stats ─────────────────────────────────────────────────────────────────
  84  | 
  85  |   test("no numeric vanity stats", async ({ page }) => {
  86  |     // Old: "2.2M+ Rows Processed", "10x Faster than Pandas", "25+ API Endpoints"
  87  |     await expect(page.getByText(/10x/i)).toHaveCount(0);
  88  |     await expect(page.getByText(/Faster than Pandas/i)).toHaveCount(0);
  89  |     await expect(page.getByText(/API Endpoints/i)).toHaveCount(0);
  90  |   });
  91  | 
  92  |   test("qualitative claims section is visible", async ({ page }) => {
  93  |     await expect(
  94  |       page.getByText(/Reporting cycles/i).first()
  95  |     ).toBeVisible();
  96  |   });
  97  | 
  98  |   // ── Pilot Access (formerly Pricing) ───────────────────────────────────────
  99  | 
  100 |   test("section is Pilot Access not Pricing", async ({ page }) => {
  101 |     await expect(page.locator("#pilot-access")).toBeVisible();
  102 |     await expect(page.locator("#pricing")).toHaveCount(0);
  103 |   });
  104 | 
  105 |   test("pilot tiers use correct names", async ({ page }) => {
  106 |     const section = page.locator("#pilot-access");
  107 |     await expect(section.getByText("Explorer Pilot")).toBeVisible();
  108 |     await expect(section.getByText("Operations Pilot").first()).toBeVisible();
  109 |     await expect(section.getByText("Enterprise Rollout")).toBeVisible();
  110 |   });
  111 | 
  112 |   test("no old pricing tier names", async ({ page }) => {
  113 |     await expect(page.getByText(/^Starter$/)).toHaveCount(0);
  114 |     await expect(page.getByText(/^Pro$/)).toHaveCount(0);
  115 |   });
  116 | 
  117 |   // ── FAQ ───────────────────────────────────────────────────────────────────
  118 | 
  119 |   test("FAQ has pharma-specific questions", async ({ page }) => {
  120 |     const faqSection = page.locator("#faq");
  121 |     await expect(faqSection).toBeVisible();
  122 |     await expect(
  123 |       faqSection.getByText(/Who is DataPulse for/i)
  124 |     ).toBeVisible();
  125 |   });
  126 | 
  127 |   test("no technical FAQ questions", async ({ page }) => {
  128 |     await expect(
  129 |       page.getByText(/What data formats does Data Pulse support/i)
  130 |     ).toHaveCount(0);
  131 |     await expect(
  132 |       page.getByText(/How does the medallion architecture work/i)
  133 |     ).toHaveCount(0);
  134 |   });
  135 | 
  136 |   // ── CTA Section ───────────────────────────────────────────────────────────
  137 | 
  138 |   test("bottom CTA section uses pharma-first copy", async ({ page }) => {
  139 |     await expect(
  140 |       page.getByText(/See what your team should act on every day/i)
  141 |     ).toBeVisible();
  142 |   });
  143 | 
  144 |   test("no waitlist or launch language in CTA", async ({ page }) => {
  145 |     await expect(page.getByText(/Join the waitlist/i)).toHaveCount(0);
  146 |     await expect(page.getByText(/Launch with clarity/i)).toHaveCount(0);
  147 |   });
  148 | 
  149 |   // ── Static pages ─────────────────────────────────────────────────────────
  150 | 
  151 |   test("privacy page loads", async ({ page }) => {
  152 |     await page.goto("/privacy");
  153 |     await expect(page.locator("h1")).toContainText(/Privacy Policy/i);
  154 |   });
  155 | 
```