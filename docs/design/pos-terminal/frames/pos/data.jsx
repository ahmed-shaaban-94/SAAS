// Seed data for the POS prototype. Real catalog lives on server; this is demo-only.
const CATALOG = {
  ar: [
    { sku: '6223001234567', name: 'أموكسيسيلين ٥٠٠ ملجم ×٢١', price: 48.00, vatRate: 0.14 },
    { sku: '6223009876543', name: 'پانادول اكسترا ×٢٤', price: 32.50, vatRate: 0.14 },
    { sku: '6223004455667', name: 'فنتولين بخاخ ١٠٠ مكجم', price: 78.00, vatRate: 0.14 },
    { sku: '6223007788990', name: 'جلوكوفاج ٥٠٠ ملجم ×٣٠', price: 24.75, vatRate: 0.14 },
    { sku: '6223002233445', name: 'كونكور ٥ ملجم ×٣٠', price: 112.00, vatRate: 0.14 },
    { sku: '6223005566778', name: 'سيتال أقراص ×٢٠', price: 18.50, vatRate: 0.14 },
    { sku: '6223008899001', name: 'نو سبا ٤٠ ملجم ×٢٠', price: 26.00, vatRate: 0.14 },
    { sku: '6223003344556', name: 'زيثروماكس ٥٠٠ ×٣', price: 94.00, vatRate: 0.14 },
    { sku: '6223006677889', name: 'جونسون شامپو أطفال ٢٠٠مل', price: 52.00, vatRate: 0.14 },
    { sku: '6223009900112', name: 'ترمومتر رقمي', price: 145.00, vatRate: 0.14 },
    { sku: '6223001122334', name: 'كمامات طبية ×٥٠', price: 88.00, vatRate: 0.14 },
    { sku: '6223004433221', name: 'فيتامين سي فوَّار ×٢٠', price: 64.00, vatRate: 0.14 },
  ],
  en: [
    { sku: '6223001234567', name: 'Amoxicillin 500mg ×21', price: 48.00, vatRate: 0.14 },
    { sku: '6223009876543', name: 'Panadol Extra ×24', price: 32.50, vatRate: 0.14 },
    { sku: '6223004455667', name: 'Ventolin Inhaler 100mcg', price: 78.00, vatRate: 0.14 },
    { sku: '6223007788990', name: 'Glucophage 500mg ×30', price: 24.75, vatRate: 0.14 },
    { sku: '6223002233445', name: 'Concor 5mg ×30', price: 112.00, vatRate: 0.14 },
    { sku: '6223005566778', name: 'Cetal tablets ×20', price: 18.50, vatRate: 0.14 },
    { sku: '6223008899001', name: 'No-Spa 40mg ×20', price: 26.00, vatRate: 0.14 },
    { sku: '6223003344556', name: 'Zithromax 500 ×3', price: 94.00, vatRate: 0.14 },
    { sku: '6223006677889', name: 'Johnson Baby Shampoo 200ml', price: 52.00, vatRate: 0.14 },
    { sku: '6223009900112', name: 'Digital Thermometer', price: 145.00, vatRate: 0.14 },
    { sku: '6223001122334', name: 'Medical Masks ×50', price: 88.00, vatRate: 0.14 },
    { sku: '6223004433221', name: 'Vitamin C Effervescent ×20', price: 64.00, vatRate: 0.14 },
  ],
};

// Preset carts used by the tweak panel
function makeCart(preset, lang) {
  const cat = CATALOG[lang];
  if (preset === 'empty') return [];
  if (preset === 'three') {
    return [
      { ...cat[0], qty: 1, lineId: 'L1', synced: true },
      { ...cat[1], qty: 2, lineId: 'L2', synced: true },
      { ...cat[3], qty: 1, lineId: 'L3', synced: false }, // provisional
    ];
  }
  // twelve
  return cat.slice(0, 9).map((p, i) => ({
    ...p,
    qty: [1,2,1,3,1,1,2,1,1][i] || 1,
    lineId: 'L' + (i+1),
    synced: i < 6,
  }));
}

// Promotions eligible for cart (hardcoded for demo)
const PROMOS = {
  ar: [
    { id: 'P1', title: 'باي-ون-جت-ون پانادول', sub: 'اشتري ٢ احصلي على ٣', savings: 32.50, type: 'BOGO' },
    { id: 'P2', title: 'خصم ١٥٪ على مضادات حيوية', sub: 'حملة أبريل — أموكسيسيلين', savings: 7.20, type: 'PCT' },
    { id: 'P3', title: 'خصم فئة فيتامينات', sub: '٢٠ ج.م عند الشراء فوق ١٠٠', savings: 20.00, type: 'FIXED' },
  ],
  en: [
    { id: 'P1', title: 'Buy-one-get-one Panadol', sub: 'Buy 2 get 3', savings: 32.50, type: 'BOGO' },
    { id: 'P2', title: '15% off antibiotics', sub: 'April campaign — Amoxicillin', savings: 7.20, type: 'PCT' },
    { id: 'P3', title: 'Vitamins category discount', sub: 'EGP 20 off above 100', savings: 20.00, type: 'FIXED' },
  ],
};

// Insurers (Egyptian)
const INSURERS = {
  ar: [
    { id: 'MISR', name: 'مصر للتأمين', coverage: 80 },
    { id: 'ALLNZ', name: 'أليانز', coverage: 70 },
    { id: 'AXA', name: 'أكسا', coverage: 75 },
    { id: 'BUPA', name: 'بوبا', coverage: 90 },
    { id: 'GOVT', name: 'التأمين الصحي الشامل', coverage: 100 },
  ],
  en: [
    { id: 'MISR', name: 'Misr Insurance', coverage: 80 },
    { id: 'ALLNZ', name: 'Allianz', coverage: 70 },
    { id: 'AXA', name: 'AXA', coverage: 75 },
    { id: 'BUPA', name: 'Bupa', coverage: 90 },
    { id: 'GOVT', name: 'Universal Health Insurance', coverage: 100 },
  ],
};

// Sync issues seed
const SYNC_ISSUES = {
  ar: [
    { id: 'TXN-24-0418-A01', reasonTag: 'PRICE_MISMATCH', reason: 'سعر مختلف عن المرجعي — أموكسيسيلين ٥٠٠', time: '09:14', amount: 96.00, lines: 3, cashier: 'نور.م' },
    { id: 'TXN-24-0418-A07', reasonTag: 'STOCK_NEGATIVE', reason: 'المخزون سيصبح سالباً — فنتولين بخاخ', time: '09:42', amount: 234.00, lines: 2, cashier: 'نور.م' },
    { id: 'TXN-24-0418-A12', reasonTag: 'EXPIRED_VOUCHER', reason: 'قسيمة منتهية — VCHR-MADI-23', time: '10:03', amount: 488.50, lines: 6, cashier: 'سارة.ك' },
    { id: 'TXN-24-0418-A18', reasonTag: 'INSURANCE_REJECT', reason: 'رفض شركة التأمين — بوليصة غير نشطة', time: '10:28', amount: 712.25, lines: 4, cashier: 'نور.م' },
    { id: 'TXN-24-0418-A22', reasonTag: 'DUPLICATE_BARCODE', reason: 'باركود مسح مزدوج — كونكور ٥', time: '11:11', amount: 112.00, lines: 1, cashier: 'سارة.ك' },
  ],
  en: [
    { id: 'TXN-24-0418-A01', reasonTag: 'PRICE_MISMATCH', reason: 'Price differs from reference — Amoxicillin 500', time: '09:14', amount: 96.00, lines: 3, cashier: 'Nour.M' },
    { id: 'TXN-24-0418-A07', reasonTag: 'STOCK_NEGATIVE', reason: 'Stock would go negative — Ventolin Inhaler', time: '09:42', amount: 234.00, lines: 2, cashier: 'Nour.M' },
    { id: 'TXN-24-0418-A12', reasonTag: 'EXPIRED_VOUCHER', reason: 'Voucher expired — VCHR-MADI-23', time: '10:03', amount: 488.50, lines: 6, cashier: 'Sara.K' },
    { id: 'TXN-24-0418-A18', reasonTag: 'INSURANCE_REJECT', reason: 'Insurer rejected — policy inactive', time: '10:28', amount: 712.25, lines: 4, cashier: 'Nour.M' },
    { id: 'TXN-24-0418-A22', reasonTag: 'DUPLICATE_BARCODE', reason: 'Duplicate barcode scan — Concor 5', time: '11:11', amount: 112.00, lines: 1, cashier: 'Sara.K' },
  ],
};

// Vouchers (for the modal demo lookup)
const VOUCHERS = {
  'RAMADAN25': { type: 'PCT', value: 25, label: { ar: 'خصم رمضان ٢٥٪', en: 'Ramadan 25% off' } },
  'NEW100':     { type: 'FIXED', value: 100, label: { ar: 'خصم ١٠٠ ج.م', en: 'EGP 100 off' } },
  'LOYALTY10':  { type: 'PCT', value: 10, label: { ar: 'عميل وفيّ ١٠٪', en: 'Loyalty 10% off' } },
};

function computeTotals(cart, { voucher, promo, insurance }) {
  const subtotalIncl = cart.reduce((s, l) => s + l.price * l.qty, 0);
  // Our prices include VAT already in Egypt pharmacy practice — split back out.
  const vatRate = 0.14;
  const subtotal = subtotalIncl / (1 + vatRate);
  const vat = subtotalIncl - subtotal;
  let discount = 0;
  if (voucher) {
    const v = VOUCHERS[voucher];
    if (v) discount += v.type === 'PCT' ? subtotalIncl * (v.value/100) : v.value;
  }
  if (promo) discount += promo.savings;
  const total = Math.max(0, subtotalIncl - discount);
  const coverage = insurance ? insurance.coverage/100 : 0;
  const insurerPays = total * coverage;
  const patientPays = total - insurerPays;
  return { subtotal, vat, subtotalIncl, discount, total, insurerPays, patientPays };
}

// Stock-on-hand keyed by SKU. Same numbers across languages.
const STOCK = {
  '6223001234567': { qty: 142, reorder: 40, expiry: '2026-08', shelf: 'A-12', batch: 'B240118', mfr: 'GlaxoSmithKline', rx: true,  category: 'antibiotic' },
  '6223009876543': { qty: 28,  reorder: 60, expiry: '2027-03', shelf: 'B-04', batch: 'P240312', mfr: 'GSK Consumer',    rx: false, category: 'analgesic' },
  '6223004455667': { qty: 6,   reorder: 25, expiry: '2026-11', shelf: 'C-21', batch: 'V240507', mfr: 'GSK',             rx: true,  category: 'respiratory' },
  '6223007788990': { qty: 88,  reorder: 30, expiry: '2027-06', shelf: 'A-08', batch: 'G240221', mfr: 'Merck',           rx: true,  category: 'diabetes' },
  '6223002233445': { qty: 0,   reorder: 20, expiry: '2026-09', shelf: 'A-15', batch: 'C240115', mfr: 'Merck',           rx: true,  category: 'cardiac' },
  '6223005566778': { qty: 220, reorder: 80, expiry: '2027-12', shelf: 'B-02', batch: 'C240402', mfr: 'EIPICO',          rx: false, category: 'analgesic' },
  '6223008899001': { qty: 64,  reorder: 30, expiry: '2026-12', shelf: 'B-09', batch: 'N240228', mfr: 'CHEMIPHARM',      rx: false, category: 'antispasmodic' },
  '6223003344556': { qty: 12,  reorder: 20, expiry: '2025-08', shelf: 'A-13', batch: 'Z240105', mfr: 'Pfizer',          rx: true,  category: 'antibiotic' },
  '6223006677889': { qty: 56,  reorder: 30, expiry: '2027-01', shelf: 'D-07', batch: 'J240315', mfr: 'Johnson & J',     rx: false, category: 'baby care' },
  '6223009900112': { qty: 18,  reorder: 10, expiry: '—',       shelf: 'E-02', batch: 'TH24001', mfr: 'Omron',           rx: false, category: 'devices' },
  '6223001122334': { qty: 412, reorder: 100, expiry: '2028-04', shelf: 'E-11', batch: 'M240118', mfr: 'Domty Med',      rx: false, category: 'PPE' },
  '6223004433221': { qty: 41,  reorder: 30, expiry: '2026-10', shelf: 'D-03', batch: 'V240220', mfr: 'Bayer',           rx: false, category: 'vitamin' },
};

function stockStatus(sku) {
  const s = STOCK[sku];
  if (!s) return { tag: 'unknown', qty: 0 };
  if (s.qty === 0) return { ...s, tag: 'out' };
  if (s.qty < s.reorder) return { ...s, tag: 'low' };
  if (s.qty < s.reorder * 1.5) return { ...s, tag: 'watch' };
  return { ...s, tag: 'ok' };
}

Object.assign(window, { CATALOG, PROMOS, INSURERS, SYNC_ISSUES, VOUCHERS, STOCK, stockStatus, makeCart, computeTotals });
