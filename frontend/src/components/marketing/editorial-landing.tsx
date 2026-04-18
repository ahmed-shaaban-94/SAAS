"use client";

/**
 * Editorial Landing (v2) — the pharma-first marketing page.
 *
 * Port of the hand-crafted HTML design. All custom styling lives in
 * `editorial-landing.css`, scoped under `.editorial-landing`.
 *
 * Sections:
 *   1. Sticky pulse bar (animated ECG heartbeat)
 *   2. Nav
 *   3. Hero (editorial headline + stats strip)
 *   4. Medallion pipeline (bronze → silver → gold)
 *   5. Live tenant wall (marquee)
 *   6. Feature grid (6 signature capabilities)
 *   7. Editorial pricing (Sahl / Nabḍ / Kubrā)
 *   8. Footer CTA + footer
 */

import { useEffect, useRef } from "react";
import Link from "next/link";
import "./editorial-landing.css";

// ─── Static data ────────────────────────────────────────────────

const TENANT_EVENTS = [
  { n: "Nile RX · Alexandria", v: "just reconciled 2,341 transactions", t: "2s AGO", c: "#1dd48b" },
  { n: "Horizon Pharmacy · Cairo", v: "flagged a stockout on Glucophage", t: "6s AGO", c: "#ffab3d" },
  { n: "Al-Shifa Group · Maadi", v: "approved an AI-drafted PO for EGP 214K", t: "12s AGO", c: "#00c7f2" },
  { n: "Medica Chain · Giza", v: "ran a 90-day forecast for Q3", t: "18s AGO", c: "#7467f8" },
  { n: "Saydalia · Nasr City", v: "closed the month at EGP 1.2M, +14% YoY", t: "24s AGO", c: "#1dd48b" },
  { n: "Green Pharmacy · Mansoura", v: "prevented EGP 38K in expiry losses", t: "31s AGO", c: "#ffab3d" },
  { n: "Al-Tawheed · Tanta", v: "transferred 400 units between branches", t: "40s AGO", c: "#00c7f2" },
  { n: "Cairo Care · Heliopolis", v: "caught a 22% anomaly in night shift AOV", t: "52s AGO", c: "#ff7b7b" },
  { n: "RxNow · Aswan", v: "onboarded 12K SKUs in 48 hours", t: "61s AGO", c: "#7467f8" },
  { n: "Alfa Pharma · Port Said", v: "ran an inter-branch transfer saving EGP 18K", t: "72s AGO", c: "#1dd48b" },
];

const BRONZE_SAMPLE = [
  "order_id  | date       | sku_id | qty | price",
  "──────────────────────────────────────────────",
  "887213    | 2026-04-18 | AMOX5  |   2 |  42.00",
  "887214    | 2026-04-18 | PAN-EX |   1 |  28.50",
  "887215    | 2026-04-18 | INS-LG |   1 | 240.00",
  "887216    | 2026-04-18 | GLU-M  |   3 |  65.75",
  "887217    | 2026-04-18 | VNT-IN |   1 | 118.00",
  "887218    | 2026-04-18 | CLX-2  |   4 |  19.25",
  "887219    | 2026-04-18 | AMOX5  |   1 |  42.00",
  "887220    | 2026-04-18 | PAN-EX |   2 |  28.50",
  "887221    | 2026-04-18 | MGS-50 |   1 |  88.00",
  "887222    | 2026-04-18 | INS-LG |   1 | 240.00",
  "887223    | 2026-04-18 | AMOX5  |   3 |  42.00",
];

// ─── Components ─────────────────────────────────────────────────

function PulseBar() {
  const pathRef = useRef<SVGPathElement>(null);
  const headRef = useRef<SVGCircleElement>(null);

  useEffect(() => {
    if (!pathRef.current || !headRef.current) return;
    const W = 1200;
    const H = 32;
    const mid = H / 2;
    const N = 220;
    const pts: Array<[number, number]> = [];
    for (let i = 0; i < N; i++) {
      const t = i / N;
      let y = mid;
      y -= Math.sin(t * Math.PI) * 5;
      y += (Math.random() - 0.5) * 2.5;
      if (Math.random() < 0.08) y -= 5 + Math.random() * 5;
      if (i === 48 || i === 120 || i === 178) y -= 11;
      pts.push([t * W, y]);
    }
    let d = "";
    pts.forEach((p, i) => {
      d += (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1);
    });
    pathRef.current.setAttribute("d", d);
    const last = pts[pts.length - 1];
    headRef.current.setAttribute("cx", String(last[0]));
    headRef.current.setAttribute("cy", String(last[1]));
  }, []);

  return (
    <div className="pulse-bar">
      <div className="pulse-row">
        <div className="pulse-label">
          <span className="pulse-dot" /> Platform pulse
        </div>
        <div className="pulse-wrap">
          <svg className="pulse-svg" viewBox="0 0 1200 32" preserveAspectRatio="none">
            <defs>
              <linearGradient id="el-pulse-line" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="#00c7f2" stopOpacity="0" />
                <stop offset="0.3" stopColor="#00c7f2" stopOpacity="0.9" />
                <stop offset="1" stopColor="#5cdfff" />
              </linearGradient>
            </defs>
            <path ref={pathRef} stroke="url(#el-pulse-line)" strokeWidth="1.6" fill="none" strokeLinecap="round" />
            <circle ref={headRef} r="3" fill="#5cdfff" filter="drop-shadow(0 0 3px #5cdfff)" />
          </svg>
        </div>
        <div className="pulse-stat">
          <span><b>12,847</b> tx/min</span><span>·</span>
          <span><b>214</b> tenants</span><span>·</span>
          <span className="g">99.94% uptime</span>
        </div>
      </div>
    </div>
  );
}

function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <span className="brand-mark" style={{ width: size, height: size }}>
      <svg width={size * 0.44} height={size * 0.44} viewBox="0 0 24 24" fill="none">
        <path d="M3 13h3l2-6 4 12 3-8 2 4h4" stroke="#f7fbff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function Nav() {
  return (
    <nav className="el-nav">
      <div className="nav-row">
        <Link href="/" className="brand">
          <LogoMark />
          DataPulse
        </Link>
        <div className="nav-links">
          <a href="#pipeline">Platform</a>
          <a href="#features">Product</a>
          <a href="#pricing">Pricing</a>
          <Link href="/docs">Docs</Link>
          <Link href="/customers">Customers</Link>
        </div>
        <div className="nav-spacer" />
        <Link href="/api/auth/signin" className="btn btn-ghost">Sign in</Link>
        <Link href="/dashboard" className="btn btn-primary">
          Open dashboard
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
            <path d="M5 12h14M13 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="hero-inner">
        <span className="eyebrow"><span className="ldot" /> v4.0 · the operations pilot is live</span>
        <h1 className="hero-h">
          Not another dashboard. <br />
          The <em>heartbeat</em> of your business, <br />
          turned into a <span className="it">decision.</span>
        </h1>
        <p className="hero-lede">
          DataPulse reads 1.1M transactions across your branches every day and wakes you up each
          morning with a single paragraph of what matters. <b>Every number is explainable.</b>{" "}
          Every trend has a cause. Every cause has a plan.
        </p>
        <div className="hero-cta">
          <Link href="/dashboard" className="btn btn-primary">
            See a live dashboard
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <path d="M5 12h14M13 5l7 7-7 7" />
            </svg>
          </Link>
          <a href="#pipeline" className="btn btn-outline">How the pipeline works</a>
          <span className="hero-meta"><b>14-day pilot</b> · no credit card · Egypt-hosted</span>
        </div>

        <div className="hero-stats">
          <div className="hs"><div className="v tabular">1.1M+</div><div className="k">transactions indexed</div></div>
          <div className="hs"><div className="v tabular">214</div><div className="k">pharmacies · MENA</div></div>
          <div className="hs"><div className="v tabular">8m 42s</div><div className="k">Bronze → Gold</div></div>
          <div className="hs"><div className="v tabular">99.94%</div><div className="k">30-day uptime</div></div>
        </div>
      </div>
    </section>
  );
}

function Medallion() {
  const silverBars = [
    { v: 42, h: 35 },
    { v: 67, h: 55 },
    { v: 89, h: 72 },
    { v: 54, h: 45 },
    { v: 78, h: 62 },
    { v: 91, h: 78 },
    { v: 63, h: 52 },
    { v: 82, h: 68 },
  ];
  const bronzeStreamed = [...BRONZE_SAMPLE, ...BRONZE_SAMPLE].join("\n");

  return (
    <section className="medallion" id="pipeline">
      <div className="med-inner">
        <div className="med-head">
          <span className="eyebrow"><span className="ldot" /> the medallion pipeline</span>
          <h2>Raw Excel walks in one end. <br /><em>Decisions</em> walk out the other.</h2>
          <p>
            Most platforms hide how your data becomes a metric. We show you every step —
            Bronze, Silver, Gold — because when the number surprises you, you need to know{" "}
            <em>why.</em>
          </p>
        </div>

        <div className="med-tracks">
          <div className="mtrack b">
            <div className="step-num"><span className="circle">1</span> BRONZE · RAW INGEST</div>
            <h3>Every row, as-is.</h3>
            <p>We ingest Excel, CSV, Sheets, MySQL, Shopify — the messy, human-typed reality. Nothing is thrown away. Every cell keeps its lineage.</p>
            <div className="mviz b">
              <div className="col">{bronzeStreamed}</div>
            </div>
            <div className="mstats">
              <div className="box"><div className="k">Rows/sec</div><div className="v tabular">28K</div></div>
              <div className="box"><div className="k">Parquet</div><div className="v tabular">57MB</div></div>
            </div>
          </div>

          <div className="mtrack s">
            <div className="step-num"><span className="circle">2</span> SILVER · CLEANED</div>
            <h3>Every row, trusted.</h3>
            <p>dbt staging deduplicates, type-casts, normalizes. Seven tests gate every column. Bad data never reaches an executive dashboard.</p>
            <div className="mviz s">
              {silverBars.map((b, i) => (
                <div key={i} className="bar" data-v={b.v} style={{ ["--h" as string]: `${b.h}%`, height: `${b.h}%` }} />
              ))}
            </div>
            <div className="mstats">
              <div className="box"><div className="k">dbt tests</div><div className="v tabular" style={{ color: "var(--green)" }}>7/7 ✓</div></div>
              <div className="box"><div className="k">Dedup rate</div><div className="v tabular">99.7%</div></div>
            </div>
          </div>

          <div className="mtrack g">
            <div className="step-num"><span className="circle">3</span> GOLD · DECISION READY</div>
            <h3>Every row, a story.</h3>
            <p>Star schema: 6 dimensions, 1 fact, 8 aggregations. 154 dbt tests. 99 DAX measures. The exact shape your executives already think in.</p>
            <div className="mviz g">
              <div className="tbl"><div className="tn">dim_date</div>date_key<br /><span className="c">year, month, q</span></div>
              <div className="tbl"><div className="tn">dim_product</div>product_key<br /><span className="c">name, category</span></div>
              <div className="tbl fact">
                <div className="tn" style={{ color: "var(--gold)" }}>fct_sales · 1.13M</div>
                <span className="k">revenue</span> · <span className="k">cost</span> · <span className="k">profit</span> · <span className="k">qty</span>
              </div>
            </div>
            <div className="mstats">
              <div className="box"><div className="k">Gold tests</div><div className="v tabular" style={{ color: "var(--green)" }}>154/154 ✓</div></div>
              <div className="box"><div className="k">DAX measures</div><div className="v tabular">99</div></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function TenantWall() {
  // Duplicate for seamless loop
  const row = [...TENANT_EVENTS, ...TENANT_EVENTS];
  return (
    <section className="tenant-wall">
      <div className="wall-label">
        <span className="dot" /> Live from the DataPulse network · updating every few seconds
      </div>
      <div className="marquee">
        {row.map((e, i) => (
          <div key={i} className="tcard">
            <div
              className="ava"
              style={{ background: `linear-gradient(135deg, ${e.c}, ${e.c}66)`, color: "#051520" }}
            >
              {e.n.charAt(0)}
            </div>
            <div className="txt">
              <b>{e.n}</b> {e.v}
              <div className="meta">{e.t}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Features() {
  return (
    <section className="feat" id="features">
      <div className="feat-head">
        <span className="eyebrow"><span className="ldot" /> six decisions, every morning</span>
        <h2>The six things DataPulse does that a dashboard can&apos;t.</h2>
        <p>We didn&apos;t build another chart factory. We built the answers your CEO would otherwise ask your analyst at 11pm.</p>
      </div>

      <div className="feat-grid">
        <div className="fcard wide">
          <div className="ftag"><span className="dot" /> FEATURE 01 · THE MORNING BRIEFING</div>
          <h3>A paragraph. Not a grid of 12 KPIs.</h3>
          <p>Every morning at 8am, an AI-generated narrative summarizes your business in one paragraph. Each highlighted word expands into a chart.</p>
          <div className="f-brief">
            Revenue is on pace to close the month at <span className="up">EGP 4.72M, +5% above plan</span>.
            Maadi is down <span className="dn">−18% from stockouts</span>. You have{" "}
            <span className="dn">EGP 142K of expiry exposure</span> that deserves a decision this morning.
          </div>
        </div>

        <div className="fcard">
          <div className="ftag"><span className="dot" /> 02 · PULSE LINE</div>
          <h3>The literal heartbeat.</h3>
          <p>One line runs across every page. Flatlines mean a branch is offline. Spikes mean a bulk order.</p>
          <div className="f-pulse">
            <svg viewBox="0 0 300 54" preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
              <path
                d="M0 30 L20 28 L30 30 L40 18 L45 40 L55 30 L80 28 L90 30 L100 14 L105 44 L120 28 L150 30 L160 20 L170 30 L200 28 L210 30 L220 8 L225 46 L240 28 L290 26"
                stroke="#5cdfff" strokeWidth="1.6" fill="none" strokeLinecap="round"
              />
              <circle cx="290" cy="26" r="3.5" fill="#5cdfff" filter="drop-shadow(0 0 4px #5cdfff)" />
            </svg>
          </div>
        </div>

        <div className="fcard">
          <div className="ftag"><span className="dot" /> 03 · COMMAND BAR</div>
          <h3>Ask. Don&apos;t click.</h3>
          <p>⌘K opens an AI bar. Type plain English. Charts render inline. No more SQL, no more analyst tickets.</p>
          <div className="f-cmd">
            <div className="ai">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="#fff"><path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" /></svg>
            </div>
            <div className="txt">top products Maadi this week<span className="cur" /></div>
            <span className="kbd">⌘K</span>
          </div>
        </div>

        <div className="fcard span3">
          <div className="ftag"><span className="dot" /> 04 · WHY DID THIS CHANGE?</div>
          <h3>Every metric decomposes into a cause.</h3>
          <p>Click any number. Get a waterfall of what moved it. Revenue down 18% = stockouts + AOV softness + staff changes. Not a mystery.</p>
          <div className="f-why">
            <div className="wr"><span className="lbl">Stockouts</span><div className="bar"><div className="z" /><div className="fill n" style={{ width: "25%" }} /></div><span className="v" style={{ color: "var(--red)" }}>−86K</span></div>
            <div className="wr"><span className="lbl">Foot traffic</span><div className="bar"><div className="z" /><div className="fill p" style={{ width: "8%" }} /></div><span className="v" style={{ color: "var(--green)" }}>+24K</span></div>
            <div className="wr"><span className="lbl">AOV softness</span><div className="bar"><div className="z" /><div className="fill n" style={{ width: "10%" }} /></div><span className="v" style={{ color: "var(--red)" }}>−31K</span></div>
            <div className="wr"><span className="lbl">Staff changes</span><div className="bar"><div className="z" /><div className="fill n" style={{ width: "5%" }} /></div><span className="v" style={{ color: "var(--red)" }}>−14K</span></div>
          </div>
        </div>

        <div className="fcard span3">
          <div className="ftag"><span className="dot" /> 05 · HORIZON MODE</div>
          <h3>Run the whole dashboard 90 days forward.</h3>
          <p>Flip one toggle. Every KPI morphs to its forecasted value with a confidence band. See the future of your P&amp;L, not charts buried on page four.</p>
          <div className="f-fore">
            <svg viewBox="0 0 400 120" preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
              <defs>
                <linearGradient id="el-ff1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#00c7f2" stopOpacity="0.4" />
                  <stop offset="1" stopColor="#00c7f2" stopOpacity="0" />
                </linearGradient>
                <linearGradient id="el-ff2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#7467f8" stopOpacity="0.3" />
                  <stop offset="1" stopColor="#7467f8" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d="M0 90 C40 80 70 65 100 60 C130 55 160 70 200 58 L200 120 L0 120 Z" fill="url(#el-ff1)" />
              <path d="M0 90 C40 80 70 65 100 60 C130 55 160 70 200 58" stroke="#00c7f2" strokeWidth="2.5" fill="none" strokeLinecap="round" />
              <path d="M200 58 C240 50 270 40 300 28 C330 20 360 14 400 8 L400 44 C360 50 330 56 300 64 C270 72 240 80 200 90 Z" fill="url(#el-ff2)" opacity="0.7" />
              <path d="M200 58 C240 50 270 40 300 28 C330 20 360 14 400 8" stroke="#7467f8" strokeWidth="2.5" fill="none" strokeDasharray="5 4" strokeLinecap="round" />
              <line x1="200" y1="8" x2="200" y2="112" stroke="#5cdfff" strokeDasharray="2 3" opacity="0.4" />
              <rect x="178" y="2" width="44" height="14" rx="3" fill="rgba(0,199,242,0.15)" stroke="rgba(0,199,242,0.5)" />
              <text x="200" y="12" textAnchor="middle" fill="#5cdfff" fontSize="8" fontFamily="JetBrains Mono" fontWeight="700">TODAY</text>
              <circle cx="200" cy="58" r="4" fill="#00c7f2" />
              <circle cx="400" cy="8" r="4" fill="#7467f8" />
            </svg>
          </div>
        </div>

        <div className="fcard span3">
          <div className="ftag"><span className="dot" /> 06 · MONEY MAP</div>
          <h3>Your branches, as living orbs.</h3>
          <p>Every branch pulses at the tempo of its revenue. Size = revenue. Color = margin. Connect the dots between distribution, stock, and P&amp;L — geographically.</p>
          <div style={{ marginTop: "auto", height: "120px", position: "relative" }}>
            <svg viewBox="0 0 300 120" style={{ width: "100%", height: "100%" }}>
              <path d="M 40 20 L 260 18 L 270 50 L 260 90 L 200 108 L 100 105 L 50 80 Z" fill="rgba(15,42,67,0.6)" stroke="rgba(0,199,242,0.25)" strokeDasharray="2 4" />
              <circle cx="180" cy="50" r="12" fill="rgba(29,212,139,0.2)" />
              <circle cx="180" cy="50" r="6" fill="#1dd48b" />
              <circle cx="150" cy="70" r="9" fill="rgba(0,199,242,0.2)" />
              <circle cx="150" cy="70" r="4" fill="#00c7f2" />
              <circle cx="210" cy="80" r="6" fill="rgba(255,123,123,0.25)" />
              <circle cx="210" cy="80" r="3" fill="#ff7b7b" />
              <circle cx="120" cy="50" r="5" fill="rgba(255,171,61,0.2)" />
              <circle cx="120" cy="50" r="2.5" fill="#ffab3d" />
            </svg>
          </div>
        </div>

        <div className="fcard span3">
          <div className="ftag"><span className="dot" /> 07 · BURNING CASH</div>
          <h3>Expiry risk, in a language everyone remembers.</h3>
          <p>Every batch is a column of inventory. As it approaches expiry, it shifts from green to amber to a red flame. Morbid. Unforgettable. Effective.</p>
          <div className="f-burn">
            <div className="bar g" />
            <div className="bar g" />
            <div className="bar a" />
            <div className="bar a" />
            <div className="bar r" />
            <div className="bar r" />
            <div className="bar a" />
            <div className="bar g" />
          </div>
        </div>
      </div>
    </section>
  );
}

function Check() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function Pricing() {
  return (
    <section className="pricing" id="pricing">
      <div className="pricing-inner">
        <div className="pricing-head">
          <span className="eyebrow"><span className="ldot" /> three characters, three plans</span>
          <h2>Pick the <em>plan</em> that sounds like <em>you.</em></h2>
          <p>We wrote these the way we wrote the product — as if we were sitting across the table from you at a kahwa in Zamalek.</p>
        </div>

        <div className="pricing-grid">
          <div className="plan">
            <div className="persona">For the solo pharmacist</div>
            <div className="subtitle">Chapter One</div>
            <div className="pname">Sahl <span className="ch">/sɑːhl/ · easy</span></div>
            <div className="price">
              <span className="cur">EGP</span><span className="big tabular">1,200</span><span className="per">/month</span>
            </div>
            <div className="pnote">One branch. Unlimited transactions. Everything we know, served simply.</div>

            <div className="plan-quote">
              You know your shop. You just want to know the <em>numbers</em> — without Excel, without a consultant, without an all-nighter every close-of-month.
            </div>

            <ul>
              <li><Check />The Morning Briefing · every day, 8am</li>
              <li><Check />All 6 <b>DataPulse</b> features</li>
              <li><Check />Up to 100K tx/month</li>
              <li><Check />Email support · 24h response</li>
              <li><Check />Egypt-hosted · bilingual (AR/EN)</li>
            </ul>

            <button className="cta secondary">Start the 14-day pilot</button>

            <div className="margin-note bot-left">
              <span className="arrow">↘</span> We keep this plan cheap on purpose. Nobody should pay EGP 50K/mo to see yesterday&apos;s revenue.
            </div>
          </div>

          <div className="plan featured">
            <div className="featured-badge">MOST CHOSEN · 64%</div>
            <div className="persona">For the 3–10 branch operator</div>
            <div className="subtitle">Chapter Two</div>
            <div className="pname">Nabḍ <span className="ch">/nabd/ · pulse</span></div>
            <div className="price">
              <span className="cur">EGP</span><span className="big tabular">4,800</span><span className="per">/month</span>
            </div>
            <div className="pnote">Up to 10 branches. Forecasting, Money Map, inter-branch transfers.</div>

            <div className="plan-quote">
              You have grown past the spreadsheet. Your managers call <em>you</em> at 11pm. You need one morning paragraph that tells you which three things are worth reading — and which thirty are not.
            </div>

            <ul>
              <li><Check /><b>Everything in Sahl</b>, plus</li>
              <li><Check /><b>Money Map</b> · live branch P&amp;L</li>
              <li><Check /><b>Horizon mode</b> · 30/60/90-day forecasting</li>
              <li><Check />Auto-suggested inter-branch transfers</li>
              <li><Check />Up to 1M tx/month · 5 users</li>
              <li><Check />Slack &amp; WhatsApp support · 4h SLA</li>
            </ul>

            <button className="cta primary">
              Start the 14-day pilot
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M5 12h14M13 5l7 7-7 7" /></svg>
            </button>

            <div className="margin-note top-right">
              <span className="arrow">↙</span> Most operators pay for this one. It pays for itself in the first stockout you catch before 8am.
            </div>
          </div>

          <div className="plan">
            <div className="persona">For the chain · 10+ branches</div>
            <div className="subtitle">Chapter Three</div>
            <div className="pname">Kubrā <span className="ch">/kub.rɑː/ · grand</span></div>
            <div className="price">
              <span className="big serif" style={{ fontStyle: "italic", fontWeight: 400, color: "var(--ink-2)", fontSize: "44px" }}>Let&apos;s talk.</span>
            </div>
            <div className="pnote">Custom. Dedicated infra. White-labeled. On-prem if you must.</div>

            <div className="plan-quote">
              You are running a network. You need <em>our engineers</em> in your Slack, your auditor&apos;s PDF format, and your operations meeting on Tuesdays.
            </div>

            <ul>
              <li><Check /><b>Everything in Nabḍ</b>, plus</li>
              <li><Check />Dedicated Postgres + Redis cluster</li>
              <li><Check />White-label · your brand, your colors</li>
              <li><Check />Custom dbt models, DAX, data connectors</li>
              <li><Check />Dedicated Slack channel · 1h SLA</li>
              <li><Check />On-prem deployment available</li>
            </ul>

            <button className="cta secondary">Book a 30-min call</button>
          </div>
        </div>
      </div>
    </section>
  );
}

function FooterCTA() {
  return (
    <section className="footer-cta">
      <h2>Tomorrow morning, <em>decide</em> <br />with one paragraph.</h2>
      <p>Join the 14-day Operations Pilot. We load your data in 48 hours. No credit card. No deck-ware.</p>
      <Link href="/dashboard" className="btn btn-primary">
        Open a live dashboard
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M5 12h14M13 5l7 7-7 7" /></svg>
      </Link>
      <div className="meta">1.1M+ transactions already flowing · Egypt-hosted · SOC 2 in progress</div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="el-footer">
      <Link href="/" className="brand" style={{ fontSize: "14px" }}>
        <LogoMark size={26} />
        DataPulse
      </Link>
      <span className="spacer" />
      <a href="#features">Product</a>
      <a href="#pricing">Pricing</a>
      <Link href="/docs">Docs</Link>
      <Link href="/privacy">Privacy</Link>
      <Link href="/terms">Terms</Link>
      <span>·</span>
      <span className="mono" style={{ fontSize: "11px", color: "var(--ink-4)" }}>
        © 2026 · Cairo · Built with dbt + FastAPI + Next.js
      </span>
    </footer>
  );
}

// ─── Root export ────────────────────────────────────────────────

export function EditorialLanding() {
  return (
    <div className="editorial-landing">
      <PulseBar />
      <Nav />
      <Hero />
      <Medallion />
      <TenantWall />
      <Features />
      <Pricing />
      <FooterCTA />
      <SiteFooter />
    </div>
  );
}
