/**
 * Mock data for ReceiptPaper visual review.
 * No real transactions wired here — C3/C4 replace this with live data.
 */

export interface ReceiptItem {
  drug_name: string;
  drug_name_ar: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  batch_number?: string;
}

export interface ReceiptCustomer {
  name_ar: string;
  phone?: string;
  national_id?: string;
  loyalty_points?: number;
  loyalty_balance?: number;
}

export interface ReceiptMeta {
  invoice_number: string;
  date: string;
  time: string;
  shift_id: string;
  cashier_name: string;
  site_name_ar: string;
  site_address?: string;
}

export interface ReceiptTotals {
  subtotal: number;
  discount: number;
  vat: number;
  grand_total: number;
  payment_method: string;
}

export interface InsuranceInfo {
  company_name: string;
  plan_name: string;
  approval_code: string;
  auth_time: string;
  insurer_pct: number;
  insurer_amount: number;
  patient_pct: number;
  patient_amount: number;
}

export interface DeliveryInfo {
  address: string;
  landmark?: string;
  rider_name: string;
  rider_phone: string;
  eta_minutes: number;
}

export interface ReceiptData {
  meta: ReceiptMeta;
  customer: ReceiptCustomer;
  items: ReceiptItem[];
  totals: ReceiptTotals;
  counseling_text?: string;
  cross_sell?: string[];
  insurance?: InsuranceInfo;
  delivery?: DeliveryInfo;
}

export const MOCK_SALES_RECEIPT: ReceiptData = {
  meta: {
    invoice_number: "INV-38291",
    date: "22 أبريل 2026",
    time: "11:42:07",
    shift_id: "SHF-2841",
    cashier_name: "أحمد محمود",
    site_name_ar: "صيدلية الشفاء — المعادي",
    site_address: "٢٣ ش النيل، المعادي، القاهرة",
  },
  customer: {
    name_ar: "سارة خالد عبد الرحمن",
    phone: "01012345678",
    loyalty_points: 42,
    loyalty_balance: 342,
  },
  items: [
    { drug_name_ar: "أوجمنتين ٦٢٥ مجم", drug_name: "Augmentin 625mg", quantity: 1, unit_price: 130, line_total: 130 },
    { drug_name_ar: "باراسيتامول ٥٠٠ مجم", drug_name: "Paracetamol 500mg", quantity: 2, unit_price: 18, line_total: 36 },
    { drug_name_ar: "فيتامين ج ١٠٠٠ مجم", drug_name: "Vitamin C 1000mg", quantity: 3, unit_price: 45, line_total: 135 },
    { drug_name_ar: "ريفوتريل ٢ مجم", drug_name: "Rivotril 2mg", quantity: 1, unit_price: 120, line_total: 120 },
  ],
  totals: { subtotal: 421, discount: 21.05, vat: 0, grand_total: 399.95, payment_method: "Visa •••• 4219" },
  counseling_text: "تناول أوجمنتين مع الطعام لتقليل الأعراض المعوية. أكمل الجرعة الكاملة حتى لو تحسنت الأعراض مبكراً.",
  cross_sell: ["جيفيتيوم ب-كومبليكس", "لاكتوباسيلوس سيبة"],
};

export const MOCK_INSURANCE_RECEIPT: ReceiptData = {
  meta: {
    invoice_number: "INV-38292",
    date: "22 أبريل 2026",
    time: "11:58:33",
    shift_id: "SHF-2841",
    cashier_name: "أحمد محمود",
    site_name_ar: "صيدلية الشفاء — المعادي",
  },
  customer: {
    name_ar: "محمد عبد العزيز",
    phone: "01098765432",
    national_id: "29901010XXXXX",
  },
  items: [
    { drug_name_ar: "أتورفاستاتين ٤٠ مجم", drug_name: "Atorvastatin 40mg", quantity: 2, unit_price: 185, line_total: 370 },
    { drug_name_ar: "مترفورمين ٥٠٠ مجم", drug_name: "Metformin 500mg", quantity: 3, unit_price: 55, line_total: 165 },
    { drug_name_ar: "أسبرين ٨١ مجم", drug_name: "Aspirin 81mg", quantity: 1, unit_price: 35, line_total: 35 },
    { drug_name_ar: "ليسينوبريل ١٠ مجم", drug_name: "Lisinopril 10mg", quantity: 2, unit_price: 95, line_total: 190 },
    { drug_name_ar: "لانسوبرازول ٣٠ مجم", drug_name: "Lansoprazole 30mg", quantity: 1, unit_price: 51, line_total: 51 },
  ],
  totals: { subtotal: 811, discount: 0, vat: 0, grand_total: 162.20, payment_method: "Cash" },
  counseling_text: "تناول أتورفاستاتين في المساء. راقب مستوى الجلوكوز أثناء تناول مترفورمين.",
  insurance: {
    company_name: "AXA Gulf",
    plan_name: "Platinum",
    approval_code: "AXA-884-3291-KX",
    auth_time: "09:10:44",
    insurer_pct: 80,
    insurer_amount: 648.80,
    patient_pct: 20,
    patient_amount: 162.20,
  },
};

export const MOCK_DELIVERY_RECEIPT: ReceiptData = {
  meta: {
    invoice_number: "DLV-5427",
    date: "22 أبريل 2026",
    time: "13:05:12",
    shift_id: "SHF-2841",
    cashier_name: "أحمد محمود",
    site_name_ar: "صيدلية الشفاء — المعادي",
  },
  customer: {
    name_ar: "هالة إبراهيم منصور",
    phone: "01155667788",
  },
  items: [
    { drug_name_ar: "أوميبرازول ٢٠ مجم", drug_name: "Omeprazole 20mg", quantity: 2, unit_price: 65, line_total: 130 },
    { drug_name_ar: "كلوتريمازول كريم", drug_name: "Clotrimazole Cream", quantity: 1, unit_price: 48, line_total: 48 },
  ],
  totals: { subtotal: 178, discount: 0, vat: 0, grand_total: 213, payment_method: "Cash on delivery" },
  counseling_text: "ضعي كريم كلوتريمازول مرة يومياً لمدة أسبوعين.",
  delivery: {
    address: "٤٥ ش الحرية، شقة ٣، الدور الثاني\nالمعادي الجديدة، القاهرة",
    landmark: "بجوار مسجد النور",
    rider_name: "علي حسن",
    rider_phone: "01011112222",
    eta_minutes: 22,
  },
};
