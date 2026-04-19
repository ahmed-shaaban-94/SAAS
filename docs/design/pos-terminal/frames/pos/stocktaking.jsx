// Stocktaking sheet — printable physical-count worksheet.
// Opens as an overlay with a "Print" action. Uses @media print to strip chrome.

const { useState: useStateS, useMemo: useMemoS } = React;

function StocktakingModal({ open, onClose, lang, t }) {
  if (!open) return null;
  const cat = CATALOG[lang];
  const today = new Date().toLocaleDateString(lang === 'ar' ? 'ar-EG' : 'en-GB');
  const docNo = 'STK-' + new Date().toISOString().slice(2,10).replace(/-/g,'') + '-01';

  const rows = useMemoS(() => cat.map((p, i) => {
    const enRow = CATALOG.en[i];
    const s = STOCK[p.sku] || { qty: 0 };
    return {
      sku: p.sku,
      name: p.name,
      nameEn: enRow?.name,
      system: s.qty,
      shelf: s.shelf || '—',
      batch: s.batch || '—',
      expiry: s.expiry || '—',
      price: p.price,
    };
  }).sort((a,b) => (a.shelf||'').localeCompare(b.shelf||'')), [cat]);

  const totalSystem = rows.reduce((s, r) => s + r.system, 0);
  const totalValue = rows.reduce((s, r) => s + r.system * r.price, 0);

  function doPrint() {
    window.print();
  }

  return (
    <div className="stk-root" style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(2,10,18,0.72)',
      backdropFilter: 'blur(10px)',
      display: 'grid', placeItems: 'center',
      padding: 20,
    }}>
      <style>{`
        @media print {
          html, body { background: #fff !important; }
          body > *:not(.stk-root) { display: none !important; }
          .stk-root { position: static !important; background: #fff !important; padding: 0 !important; backdrop-filter: none !important; }
          .stk-chrome { display: none !important; }
          .stk-paper { box-shadow: none !important; border: none !important; max-width: none !important; width: 100% !important; max-height: none !important; overflow: visible !important; color: #000 !important; background: #fff !important; }
          .stk-paper * { color: #000 !important; border-color: #000 !important; }
          .stk-paper .ink-muted { color: #555 !important; }
          .stk-paper .box { background: #fff !important; border: 1px solid #000 !important; }
          .stk-paper .row-alt:nth-child(even) { background: #f4f4f4 !important; }
          @page { size: A4; margin: 12mm; }
        }
      `}</style>

      {/* Chrome */}
      <div className="stk-chrome" style={{
        position: 'absolute', top: 16, insetInlineEnd: 16,
        display: 'flex', gap: 8, zIndex: 2,
      }}>
        <button onClick={doPrint} style={{
          padding: '9px 14px', borderRadius: 8,
          background: 'linear-gradient(180deg, #5cdfff, #00a6cc)',
          color: '#021018', fontSize: 13, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 8,
          boxShadow: '0 0 16px rgba(0,199,242,0.35)', cursor: 'pointer', border: 0,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9V3h12v6 M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2 M6 14h12v7H6z"/></svg>
          {lang==='ar' ? 'طباعة' : 'Print'}
        </button>
        <button onClick={onClose} style={{
          padding: '9px 14px', borderRadius: 8,
          background: 'rgba(255,255,255,0.06)', color: 'var(--ink-2)',
          fontSize: 13, fontWeight: 600, border: '1px solid var(--line)', cursor: 'pointer',
        }}>
          {lang==='ar' ? 'إغلاق (Esc)' : 'Close (Esc)'}
        </button>
      </div>

      {/* Paper */}
      <div className="stk-paper" style={{
        background: '#fbfaf7', color: '#0b1a29',
        width: 'min(900px, 100%)', maxHeight: '92vh', overflow: 'auto',
        borderRadius: 6, boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
        padding: '28px 32px',
        fontFamily: lang === 'ar' ? 'inherit' : 'Inter, sans-serif',
      }}>
        {/* Letterhead */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', borderBottom: '2px solid #0b1a29', paddingBottom: 12, marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 22, fontWeight: 600 }}>
              {lang==='ar' ? 'صيدلية داتا پالس — المعادي' : 'DataPulse Pharmacy — Maadi'}
            </div>
            <div className="ink-muted" style={{ fontSize: 11, marginTop: 2, color: '#555' }}>
              {lang==='ar' ? '١٢ ش. الشهيد صبحي الصالح · المعادي · القاهرة · سجل تجاري ٤٢٨٨٩٣' : '12 Sobhi Saleh St · Maadi · Cairo · CR 428893'}
            </div>
          </div>
          <div style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 11 }}>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: 12 }}>{docNo}</div>
            <div className="ink-muted" style={{ color: '#555' }}>{today}</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
          <h2 style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontWeight: 500, fontSize: 28, margin: 0, letterSpacing: '-0.02em' }}>
            {lang==='ar' ? 'ورقة جرد المخزون' : 'Stocktaking Worksheet'}
          </h2>
          <div style={{ fontSize: 11 }} className="ink-muted">
            <span style={{ color: '#555' }}>
              {lang==='ar' ? 'فارغة للملء اليدوي · أعيديها للمُشرف بعد التوقيع' : 'Blank sheet for manual count · return to supervisor signed'}
            </span>
          </div>
        </div>

        {/* Meta grid */}
        <div className="box" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0, border: '1px solid #0b1a29', marginBottom: 18, fontSize: 11 }}>
          <MetaCell label={lang==='ar' ? 'اسم المسؤول عن الجرد' : 'Counted by'} />
          <MetaCell label={lang==='ar' ? 'الشاهد' : 'Witness'} />
          <MetaCell label={lang==='ar' ? 'التاريخ والوقت' : 'Date / Time'} prefilled={today} />
          <MetaCell label={lang==='ar' ? 'ممر / قسم' : 'Aisle / Section'} />
          <MetaCell label={lang==='ar' ? 'درجة الحرارة (°C)' : 'Temperature (°C)'} />
          <MetaCell label={lang==='ar' ? 'رقم الوردية' : 'Shift #'} prefilled="AM-03" />
        </div>

        {/* Table */}
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10.5 }}>
          <thead>
            <tr style={{ background: '#0b1a29', color: '#fbfaf7' }}>
              <Th w="28">#</Th>
              <Th w="60" align="start">{lang==='ar' ? 'الرف' : 'Shelf'}</Th>
              <Th w="120" align="start">{lang==='ar' ? 'الباركود' : 'Barcode'}</Th>
              <Th align="start">{lang==='ar' ? 'الصنف' : 'Item'}</Th>
              <Th w="70" align="start">{lang==='ar' ? 'الدفعة' : 'Batch'}</Th>
              <Th w="60" align="start">{lang==='ar' ? 'الصلاحية' : 'Expiry'}</Th>
              <Th w="48" align="end">{lang==='ar' ? 'النظام' : 'System'}</Th>
              <Th w="70" align="center">{lang==='ar' ? 'فعلي' : 'Counted'}</Th>
              <Th w="50" align="end">{lang==='ar' ? 'الفرق' : 'Δ'}</Th>
              <Th w="40" align="center">{lang==='ar' ? '✓' : '✓'}</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.sku} className="row-alt" style={{
                borderBottom: '0.5px solid #bbb',
                background: i % 2 === 1 ? 'rgba(11,26,41,0.04)' : 'transparent',
              }}>
                <Td align="center" mono>{String(i+1).padStart(2,'0')}</Td>
                <Td mono>{r.shelf}</Td>
                <Td mono style={{ fontSize: 10 }}>{r.sku}</Td>
                <Td>
                  <div style={{ fontWeight: 600 }}>{r.name}</div>
                  {r.nameEn && lang === 'ar' && <div className="ink-muted" style={{ fontSize: 9.5, color: '#555' }}>{r.nameEn}</div>}
                </Td>
                <Td mono>{r.batch}</Td>
                <Td mono>{r.expiry}</Td>
                <Td align="end" mono><b>{r.system}</b></Td>
                <Td align="center" style={{ height: 26, borderInline: '1px solid #0b1a29', background: '#fff' }} />
                <Td align="end" style={{ borderInline: '1px solid #0b1a29', background: '#fff' }} />
                <Td align="center" style={{ borderInline: '1px solid #0b1a29', background: '#fff' }} />
              </tr>
            ))}
            {/* Totals row */}
            <tr style={{ borderTop: '2px solid #0b1a29' }}>
              <Td />
              <Td colSpan={5} style={{ fontWeight: 700 }}>
                {lang==='ar' ? `الإجمالي — ${rows.length} أصناف · قيمة المخزون حسب النظام ${fmtEGP(totalValue)}` : `Totals — ${rows.length} SKUs · system value ${fmtEGP(totalValue)}`}
              </Td>
              <Td align="end" mono><b>{totalSystem}</b></Td>
              <Td />
              <Td />
              <Td />
            </tr>
          </tbody>
        </table>

        {/* Legend + signatures */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 24 }}>
          <div style={{ fontSize: 10, lineHeight: 1.55 }} className="ink-muted">
            <div style={{ fontWeight: 700, color: '#0b1a29', marginBottom: 4 }}>
              {lang==='ar' ? 'تعليمات الجرد' : 'Counting instructions'}
            </div>
            <div style={{ color: '#555' }}>
              {lang==='ar'
                ? '١. اعدّي كل صنف بصوت عالٍ أمام الشاهد. ٢. سجّلي الكمية الفعلية في خانة «فعلي». ٣. احسبي الفرق (فعلي − النظام). ٤. علِّمي ✓ بعد المطابقة. ٥. ارفعي الورقة إلى المشرف قبل ساعة من إغلاق الوردية.'
                : '1. Count each SKU aloud with witness present. 2. Record physical count in "Counted". 3. Compute Δ (Counted − System). 4. Tick ✓ once reconciled. 5. Submit to supervisor at least one hour before shift close.'}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <SignatureLine label={lang==='ar' ? 'توقيع المسؤول' : 'Counter signature'} />
            <SignatureLine label={lang==='ar' ? 'توقيع المشرف' : 'Supervisor signature'} />
          </div>
        </div>

        <div style={{ borderTop: '1px dashed #888', marginTop: 24, paddingTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: 9.5 }} className="ink-muted">
          <span style={{ color: '#555' }}>DataPulse POS · {docNo}</span>
          <span style={{ color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>{lang==='ar' ? 'ص ١/١' : 'p 1/1'}</span>
        </div>
      </div>
    </div>
  );
}

function MetaCell({ label, prefilled }) {
  return (
    <div style={{ padding: '8px 10px', borderInline: '0.5px solid #0b1a29', borderBlock: '0.5px solid #0b1a29' }}>
      <div style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 700, color: '#555', marginBottom: 4 }}>{label}</div>
      <div style={{ minHeight: 16, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 600, borderBottom: '1px solid #0b1a29' }}>
        {prefilled || ''}
      </div>
    </div>
  );
}

function Th({ children, w, align }) {
  return <th style={{ padding: '6px 6px', width: w, fontSize: 9.5, letterSpacing: '0.16em', textTransform: 'uppercase', textAlign: align || 'center', fontWeight: 700, border: '0.5px solid #0b1a29' }}>{children}</th>;
}
function Td({ children, align, mono, style, colSpan }) {
  return <td colSpan={colSpan} style={{
    padding: '5px 6px', textAlign: align || 'start',
    fontFamily: mono ? 'JetBrains Mono, monospace' : 'inherit',
    fontSize: mono ? 10 : 10.5,
    verticalAlign: 'middle',
    ...(style || {}),
  }}>{children}</td>;
}
function SignatureLine({ label }) {
  return (
    <div>
      <div style={{ borderBottom: '1px solid #0b1a29', minHeight: 36 }} />
      <div style={{ fontSize: 9.5, color: '#555', letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: 4 }}>{label}</div>
    </div>
  );
}

Object.assign(window, { StocktakingModal });
