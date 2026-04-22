"use client";

/**
 * ReceiptPaper — shared 80mm thermal receipt shell + sub-components (issue #634, C1).
 *
 * Uses `.pos-omni` design tokens and the `.pos-receipt` CSS class shipped in
 * PR #615. Sub-components are exported here so variant files can compose them.
 *
 * QR and barcode blocks in this file are CSS placeholders only.
 * C2 replaces them with qrcode.react + bwip-js.
 */

import type { ReactNode } from "react";
import type { ReceiptData, ReceiptItem, InsuranceInfo, DeliveryInfo } from "./receipt-mock";

// ─── Shared helpers ────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function amountToWords(n: number): string {
  const whole = Math.floor(n);
  const cents = Math.round((n - whole) * 100);
  return `${whole} EGP & ${String(cents).padStart(2, "0")}/100`;
}

// ─── Shell ────────────────────────────────────────────────────────────────────

interface ReceiptPaperProps {
  children: ReactNode;
  /** Suppress torn-edge pseudo-elements (used for print preview mode). */
  flatEdges?: boolean;
}

export function ReceiptPaper({ children, flatEdges = false }: ReceiptPaperProps) {
  return (
    <div className="pos-omni" dir="rtl">
      <div
        className={`pos-receipt${flatEdges ? " pos-receipt--flat" : ""}`}
        data-testid="receipt-paper"
      >
        {children}
      </div>
    </div>
  );
}

// ─── BrandBlock ───────────────────────────────────────────────────────────────

interface BrandBlockProps {
  siteNameAr: string;
  siteAddress?: string;
}

export function BrandBlock({ siteNameAr, siteAddress }: BrandBlockProps) {
  return (
    <div className="mb-3 pb-3" style={{ borderBottom: "1px dashed var(--pos-paper-ink-2)" }}>
      <div className="flex items-center justify-center gap-2 mb-1">
        <div
          className="flex h-[38px] w-[38px] items-center justify-center"
          style={{
            border: "2px solid var(--pos-paper-ink)",
            borderRadius: 10,
            fontSize: 14,
            fontWeight: 900,
            fontFamily: "var(--font-jetbrains-mono, monospace)",
          }}
          aria-hidden="true"
        >
          DP
        </div>
        <span style={{ fontSize: 13, fontWeight: 900, letterSpacing: "0.04em" }}>
          DataPulse Omni
        </span>
      </div>
      <div
        className="text-center"
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 12,
          fontWeight: 600,
          color: "var(--pos-paper-ink)",
        }}
      >
        {siteNameAr}
      </div>
      {siteAddress && (
        <div
          className="text-center"
          style={{
            fontFamily: "var(--font-jetbrains-mono, monospace)",
            fontSize: 9,
            color: "var(--pos-paper-ink-2)",
            marginTop: 2,
          }}
        >
          {siteAddress}
        </div>
      )}
    </div>
  );
}

// ─── MetaGrid ─────────────────────────────────────────────────────────────────

interface MetaGridProps {
  invoiceNumber: string;
  date: string;
  time: string;
  shiftId: string;
  cashierName: string;
}

export function MetaGrid({ invoiceNumber, date, time, shiftId, cashierName }: MetaGridProps) {
  const mono: React.CSSProperties = {
    fontFamily: "var(--font-jetbrains-mono, monospace)",
    fontSize: 10.5,
  };
  const label: React.CSSProperties = { ...mono, color: "var(--pos-paper-ink-2)" };
  const value: React.CSSProperties = { ...mono, color: "var(--pos-paper-ink)", fontWeight: 600 };

  return (
    <div className="mb-3" style={{ borderBottom: "1px dashed var(--pos-paper-ink-2)", paddingBottom: 8 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2px 8px" }}>
        <span style={label}>رقم الفاتورة</span>
        <span style={value}>{invoiceNumber}</span>
        <span style={label}>التاريخ</span>
        <span style={value}>{date}</span>
        <span style={label}>الوقت</span>
        <span style={value}>{time}</span>
        <span style={label}>الوردية</span>
        <span style={value}>{shiftId}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
        <span style={label}>الكاشير</span>
        <span style={value}>{cashierName}</span>
      </div>
    </div>
  );
}

// ─── CustomerBlock ────────────────────────────────────────────────────────────

interface CustomerBlockProps {
  nameAr: string;
  phone?: string;
  nationalId?: string;
  eyebrow?: string;
}

export function CustomerBlock({ nameAr, phone, nationalId, eyebrow = "العميل" }: CustomerBlockProps) {
  return (
    <div className="mb-3" style={{ borderBottom: "1px dashed var(--pos-paper-ink-faint)", paddingBottom: 8 }}>
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          color: "var(--pos-paper-ink-2)",
          marginBottom: 4,
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 13,
          fontWeight: 700,
          color: "var(--pos-paper-ink)",
        }}
      >
        {nameAr}
      </div>
      {phone && (
        <div style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 10, color: "var(--pos-paper-ink-2)", marginTop: 2 }} dir="ltr">
          {phone}
        </div>
      )}
      {nationalId && (
        <div style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 9, color: "var(--pos-paper-ink-faint)", marginTop: 1 }} dir="ltr">
          ID: {nationalId}
        </div>
      )}
    </div>
  );
}

// ─── SectionHead ─────────────────────────────────────────────────────────────

interface SectionHeadProps {
  label: string;
}

export function SectionHead({ label }: SectionHeadProps) {
  return (
    <div
      className="mb-2 flex items-center gap-2"
      style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 9, letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--pos-paper-ink-2)" }}
    >
      <span>{label}</span>
      <span style={{ flex: 1, borderBottom: "1px dashed var(--pos-paper-ink-faint)", height: 0, display: "block" }} />
    </div>
  );
}

// ─── ItemList ─────────────────────────────────────────────────────────────────

interface ItemListProps {
  items: ReceiptItem[];
}

export function ItemList({ items }: ItemListProps) {
  return (
    <div className="mb-3" style={{ borderBottom: "1px dashed var(--pos-paper-ink-faint)", paddingBottom: 8 }}>
      <SectionHead label={`الأصناف · ${items.length}`} />
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((item, i) => (
          <div key={i}>
            <div
              style={{
                fontFamily: "var(--font-plex-arabic, sans-serif)",
                fontSize: 12.5,
                fontWeight: 700,
                color: "var(--pos-paper-ink)",
              }}
            >
              {item.drug_name_ar}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span
                style={{
                  fontFamily: "var(--font-jetbrains-mono, monospace)",
                  fontSize: 10.5,
                  color: "var(--pos-paper-ink)",
                  fontWeight: 700,
                }}
              >
                {fmt(item.line_total)}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-jetbrains-mono, monospace)",
                  fontSize: 10,
                  color: "var(--pos-paper-ink-2)",
                }}
                dir="ltr"
              >
                {item.quantity} × {fmt(item.unit_price)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── TotalsBlock ──────────────────────────────────────────────────────────────

interface TotalsBlockProps {
  subtotal: number;
  discount: number;
  vat?: number;
}

export function TotalsBlock({ subtotal, discount, vat = 0 }: TotalsBlockProps) {
  const row: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    fontFamily: "var(--font-jetbrains-mono, monospace)",
    fontSize: 10.5,
    color: "var(--pos-paper-ink)",
    marginBottom: 2,
  };
  return (
    <div className="mb-3" style={{ borderBottom: "1px dashed var(--pos-paper-ink-2)", paddingBottom: 8 }}>
      <div style={row}>
        <span>المجموع الفرعي</span>
        <span>{fmt(subtotal)}</span>
      </div>
      {discount > 0 && (
        <div style={{ ...row, color: "var(--pos-paper-red)" }}>
          <span>خصم VIP (5%)</span>
          <span>- {fmt(discount)}</span>
        </div>
      )}
      {vat > 0 && (
        <div style={{ ...row, fontSize: 10, color: "var(--pos-paper-ink-faint)" }}>
          <span>ضريبة القيمة المضافة (14%)</span>
          <span>{fmt(vat)}</span>
        </div>
      )}
    </div>
  );
}

// ─── GrandTotalBlock ──────────────────────────────────────────────────────────

interface GrandTotalBlockProps {
  total: number;
  label?: string;
}

export function GrandTotalBlock({ total, label = "الإجمالي المستحق" }: GrandTotalBlockProps) {
  return (
    <div className="mb-3 text-center" style={{ padding: "8px 0" }}>
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          color: "var(--pos-paper-ink-2)",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-fraunces, serif)",
          fontSize: 38,
          fontWeight: 800,
          color: "var(--pos-paper-ink)",
          lineHeight: 1,
        }}
      >
        <span style={{ fontSize: 13, verticalAlign: "super", marginLeft: 4 }}>EGP</span>
        {fmt(total)}
      </div>
      <div
        style={{
          fontFamily: "var(--font-fraunces, serif)",
          fontStyle: "italic",
          fontSize: 10,
          color: "var(--pos-paper-ink-2)",
          marginTop: 3,
        }}
      >
        {amountToWords(total)}
      </div>
    </div>
  );
}

// ─── PaymentRow ───────────────────────────────────────────────────────────────

interface PaymentRowProps {
  method: string;
  amount: number;
}

export function PaymentRow({ method, amount }: PaymentRowProps) {
  return (
    <div
      className="mb-3"
      style={{
        display: "flex",
        justifyContent: "space-between",
        fontFamily: "var(--font-jetbrains-mono, monospace)",
        fontSize: 10.5,
        borderBottom: "1px dashed var(--pos-paper-ink-faint)",
        paddingBottom: 8,
      }}
    >
      <span style={{ color: "var(--pos-paper-ink)", fontWeight: 700 }} dir="ltr">{method}</span>
      <span style={{ color: "var(--pos-paper-ink)" }}>{fmt(amount)}</span>
    </div>
  );
}

// ─── CounselingBlock ──────────────────────────────────────────────────────────

interface CounselingBlockProps {
  text: string;
  eyebrow?: string;
}

export function CounselingBlock({ text, eyebrow = "إرشادات الصيدلاني" }: CounselingBlockProps) {
  return (
    <div
      className="pos-ink-block mb-3"
      style={{ borderRadius: 6, padding: "10px 12px" }}
    >
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          opacity: 0.6,
          marginBottom: 6,
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 11,
          lineHeight: 1.6,
        }}
      >
        {text}
      </div>
    </div>
  );
}

// ─── CrossSellList ────────────────────────────────────────────────────────────

interface CrossSellListProps {
  items: string[];
}

export function CrossSellList({ items }: CrossSellListProps) {
  if (items.length === 0) return null;
  return (
    <div
      className="mb-3"
      style={{
        border: "1px dashed var(--pos-paper-ink-faint)",
        borderRadius: 4,
        padding: "8px 10px",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--pos-paper-ink-2)",
          marginBottom: 6,
        }}
      >
        قد تحتاج أيضاً · You may also need
      </div>
      {items.map((item, i) => (
        <div
          key={i}
          style={{
            fontFamily: "var(--font-plex-arabic, sans-serif)",
            fontSize: 11,
            color: "var(--pos-paper-ink)",
            paddingBottom: 4,
            borderBottom: i < items.length - 1 ? "1px dashed var(--pos-paper-ink-faint)" : undefined,
            marginBottom: i < items.length - 1 ? 4 : 0,
          }}
        >
          {item}
        </div>
      ))}
    </div>
  );
}

// ─── LoyaltyBand ─────────────────────────────────────────────────────────────

interface LoyaltyBandProps {
  pointsEarned: number;
  balance: number;
}

export function LoyaltyBand({ pointsEarned, balance }: LoyaltyBandProps) {
  return (
    <div
      className="mb-3"
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontFamily: "var(--font-jetbrains-mono, monospace)",
        fontSize: 10,
        borderBottom: "1px dashed var(--pos-paper-ink-faint)",
        paddingBottom: 8,
      }}
    >
      <span style={{ color: "var(--pos-paper-ink-2)" }}>نقاط الولاء المكتسبة</span>
      <span style={{ color: "#4a9e4a", fontWeight: 700 }}>+{pointsEarned}</span>
      <span style={{ color: "var(--pos-paper-ink-2)" }}>الرصيد {balance} pts</span>
    </div>
  );
}

// ─── QrBlock (CSS placeholder — C2 replaces with qrcode.react) ───────────────

interface QrBlockProps {
  invoiceId: string;
}

export function QrBlock({ invoiceId }: QrBlockProps) {
  return (
    <div className="mb-3 flex flex-col items-center gap-1">
      {/* Decorative CSS QR placeholder — NOT scannable. Replace in C2. */}
      <div
        aria-label="QR code placeholder"
        data-invoice={invoiceId}
        style={{
          width: 80,
          height: 80,
          background:
            "conic-gradient(var(--pos-paper-ink) 0deg 90deg, transparent 90deg 180deg, var(--pos-paper-ink) 180deg 270deg, transparent 270deg 360deg)",
          opacity: 0.12,
          borderRadius: 2,
          outline: "2px solid var(--pos-paper-ink)",
        }}
      />
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 9,
          color: "var(--pos-paper-ink-faint)",
          textAlign: "center",
        }}
      >
        امسح للحصول على الإيصال الرقمي
      </div>
    </div>
  );
}

// ─── BarcodeBlock (font placeholder — C2 replaces with bwip-js) ──────────────

interface BarcodeBlockProps {
  value: string;
}

export function BarcodeBlock({ value }: BarcodeBlockProps) {
  return (
    <div className="mb-3 flex flex-col items-center gap-1">
      {/* Barcode font placeholder — rendered visually but NOT scannable. Replace in C2. */}
      <div
        style={{
          fontFamily: "'Libre Barcode 128', monospace",
          fontSize: 56,
          lineHeight: 1,
          color: "var(--pos-paper-ink)",
          letterSpacing: 0,
        }}
        dir="ltr"
        aria-hidden="true"
      >
        {value}
      </div>
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 10,
          color: "var(--pos-paper-ink-2)",
        }}
        dir="ltr"
      >
        {value}
      </div>
    </div>
  );
}

// ─── ThanksFooter ─────────────────────────────────────────────────────────────

export function ThanksFooter() {
  return (
    <div className="flex flex-col items-center gap-1 pt-2" style={{ paddingBottom: 26 }}>
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 13,
          fontWeight: 700,
          color: "var(--pos-paper-ink)",
        }}
      >
        شكراً لثقتكم
      </div>
      <div
        style={{
          fontFamily: "var(--font-fraunces, serif)",
          fontStyle: "italic",
          fontSize: 10,
          color: "var(--pos-paper-ink-2)",
        }}
      >
        Thank you for choosing DataPulse Omni
      </div>
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          color: "var(--pos-paper-ink-faint)",
          marginTop: 4,
        }}
      >
        datapulse.health
      </div>
    </div>
  );
}

// ─── InsurancePanel ───────────────────────────────────────────────────────────

interface InsurancePanelProps {
  info: InsuranceInfo;
}

export function InsurancePanel({ info }: InsurancePanelProps) {
  return (
    <div
      className="mb-3"
      style={{
        border: "2px solid var(--pos-paper-ink)",
        borderRadius: 4,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "6px 10px",
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9.5,
          borderBottom: "1px solid var(--pos-paper-ink)",
        }}
      >
        <span style={{ textTransform: "uppercase", letterSpacing: "0.14em" }}>Insurance breakdown</span>
        <span style={{ color: "var(--pos-paper-ink-2)" }}>{info.company_name} · {info.plan_name}</span>
      </div>
      <div style={{ display: "flex" }}>
        {/* Insurer box — inverted */}
        <div
          className="pos-ink-block"
          style={{ flex: 1, padding: "8px 10px", textAlign: "center" }}
        >
          <div style={{ fontSize: 9, letterSpacing: "0.14em", opacity: 0.7, marginBottom: 4 }}>
            يتحمل التأمين · {info.insurer_pct}%
          </div>
          <div style={{ fontFamily: "var(--font-fraunces, serif)", fontSize: 22, fontWeight: 800 }}>
            {fmt(info.insurer_amount)}
          </div>
        </div>
        {/* Patient box */}
        <div
          style={{
            flex: 1,
            padding: "8px 10px",
            textAlign: "center",
            border: "1px solid var(--pos-paper-ink)",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-jetbrains-mono, monospace)",
              fontSize: 9,
              letterSpacing: "0.14em",
              color: "var(--pos-paper-ink-2)",
              marginBottom: 4,
            }}
          >
            على المريض · {info.patient_pct}%
          </div>
          <div style={{ fontFamily: "var(--font-fraunces, serif)", fontSize: 22, fontWeight: 800, color: "var(--pos-paper-ink)" }}>
            {fmt(info.patient_amount)}
          </div>
        </div>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "6px 10px",
          borderTop: "1px dashed var(--pos-paper-ink)",
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          color: "var(--pos-paper-ink-2)",
        }}
        dir="ltr"
      >
        <span>Approval: {info.approval_code}</span>
        <span>Auth {info.auth_time}</span>
      </div>
    </div>
  );
}

// ─── DeliveryBlock ────────────────────────────────────────────────────────────

interface DeliveryBlockProps {
  info: DeliveryInfo;
}

export function DeliveryBlock({ info }: DeliveryBlockProps) {
  return (
    <div
      className="pos-ink-block mb-3"
      style={{ borderRadius: 6, padding: "10px 12px" }}
    >
      <div
        style={{
          fontFamily: "var(--font-jetbrains-mono, monospace)",
          fontSize: 9,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          opacity: 0.6,
          marginBottom: 6,
        }}
      >
        تفاصيل التوصيل
      </div>
      <div
        style={{
          fontFamily: "var(--font-plex-arabic, sans-serif)",
          fontSize: 12,
          fontWeight: 600,
          whiteSpace: "pre-line",
        }}
      >
        {info.address}
      </div>
      {info.landmark && (
        <div
          style={{
            fontFamily: "var(--font-fraunces, serif)",
            fontStyle: "italic",
            fontSize: 10,
            opacity: 0.75,
            marginTop: 3,
          }}
        >
          {info.landmark}
        </div>
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 8,
          paddingTop: 6,
          borderTop: "1px solid rgba(255,255,255,0.2)",
        }}
      >
        <span style={{ fontFamily: "var(--font-plex-arabic, sans-serif)", fontSize: 11 }}>
          {info.rider_name}
        </span>
        <span style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 10 }} dir="ltr">
          {info.rider_phone}
        </span>
      </div>
      <div style={{ textAlign: "center", marginTop: 8 }}>
        <span
          style={{
            fontFamily: "var(--font-fraunces, serif)",
            fontSize: 24,
            fontWeight: 800,
            color: "var(--pos-paper-highlight)",
          }}
        >
          {info.eta_minutes} min
        </span>
      </div>
    </div>
  );
}

// ─── SignatureBlock (delivery only) ───────────────────────────────────────────

export function SignatureBlock() {
  return (
    <div
      className="mb-3"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 12,
        paddingBottom: 8,
        borderBottom: "1px dashed var(--pos-paper-ink-faint)",
      }}
    >
      {(["Rider · توقيع", "Customer · توقيع"] as const).map((label) => (
        <div key={label}>
          <div
            style={{
              borderBottom: "1px solid var(--pos-paper-ink)",
              height: 28,
              marginBottom: 4,
            }}
          />
          <div
            style={{
              fontFamily: "var(--font-jetbrains-mono, monospace)",
              fontSize: 8,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--pos-paper-ink-2)",
            }}
          >
            {label}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Composite receipt ────────────────────────────────────────────────────────

interface CompositeReceiptProps {
  data: ReceiptData;
}

/** Full receipt body without variant-specific sections. Used internally. */
export function BaseReceiptBody({ data }: CompositeReceiptProps) {
  return (
    <>
      <BrandBlock siteNameAr={data.meta.site_name_ar} siteAddress={data.meta.site_address} />
      <MetaGrid
        invoiceNumber={data.meta.invoice_number}
        date={data.meta.date}
        time={data.meta.time}
        shiftId={data.meta.shift_id}
        cashierName={data.meta.cashier_name}
      />
      <CustomerBlock nameAr={data.customer.name_ar} phone={data.customer.phone} nationalId={data.customer.national_id} />
      <ItemList items={data.items} />
      <TotalsBlock subtotal={data.totals.subtotal} discount={data.totals.discount} />
    </>
  );
}
