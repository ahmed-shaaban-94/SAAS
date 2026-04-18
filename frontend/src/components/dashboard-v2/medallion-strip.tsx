"use client";

/**
 * Medallion Strip — compact bronze/silver/gold pipeline health widget for
 * the dashboard. Clicking any cell deep-links to the full pipeline health
 * page with that layer filtered.
 */

import Link from "next/link";

export function MedallionStrip() {
  return (
    <div className="viz-panel w-span-12">
      <div className="widget-head">
        <span className="tag">PIPELINE HEALTH</span>
        <h3>Medallion pipeline</h3>
        <span className="spacer" />
        <Link
          href="/pipeline-health"
          style={{ fontSize: 12, color: "var(--accent)", fontWeight: 600 }}
        >
          Full report →
        </Link>
      </div>

      <div className="medallion-strip">
        <Link href="/pipeline-health?layer=bronze" className="med-cell b">
          <div className="step">1 · BRONZE · RAW</div>
          <h4>Every row, as-is.</h4>
          <p>Bronze loader streamed 2.27M rows from 4 sources.</p>
          <div className="metric">
            <span>Last run:</span> <span className="ok">8m 42s</span> · <span>Rows: 28K/s</span>
          </div>
        </Link>

        <Link href="/pipeline-health?layer=silver" className="med-cell s">
          <div className="step">2 · SILVER · CLEANED</div>
          <h4>Every row, trusted.</h4>
          <p>dbt staging: 7 tests gate every column. Dedupe rate 99.7%.</p>
          <div className="metric">
            <span>dbt tests:</span> <span className="ok">7/7 ✓</span>
          </div>
        </Link>

        <Link href="/pipeline-health?layer=gold" className="med-cell g">
          <div className="step">3 · GOLD · DECISION</div>
          <h4>Every row, a story.</h4>
          <p>Star schema: 6 dims, 1 fact, 8 aggregations, 99 DAX measures.</p>
          <div className="metric">
            <span>Gold tests:</span> <span className="ok">154/154 ✓</span>
          </div>
        </Link>
      </div>
    </div>
  );
}
