// Shift close summary — cash variance reconciliation + 80mm thermal receipt preview

const { useState: useStateSH, useEffect: useEffectSH } = React;

function ShiftClose({ lang, t }) {
  const [counted, setCounted] = useStateSH('12840');
  const opening = 2000;
  const cashSales = 10842.50;
  const expected = opening + cashSales;
  const variance = parseFloat(counted || '0') - expected;
  const absVar = Math.abs(variance);
  const varColor = absVar < 1 ? 'var(--green)' : absVar < 20 ? 'var(--amber)' : 'var(--red)';

  return (
    <div style={{ padding: 18, height: '100%', overflowY: 'auto', display: 'grid', gridTemplateColumns: '1fr 380px', gap: 18, alignItems: 'start' }}>
      {/* LEFT: reconciliation */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--accent-hi)', textTransform: 'uppercase', marginBottom: 6 }}>
            ● {t('shiftTitle')}
          </div>
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: 28, fontWeight: 500, letterSpacing: '-0.01em' }}>
            {lang==='ar' ? 'طابقي الصندوق، اطبعي التقرير' : 'Reconcile cash, print the report'}
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 4 }}>{t('shiftSub')}</div>
        </div>

        {/* Reconcile grid */}
        <div style={{
          background: 'rgba(8,24,38,0.5)', border: '1px solid var(--line)', borderRadius: 12, padding: 18,
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <ReconRow label={t('openingFloat')} value={fmtEGP(opening)} />
          <ReconRow label={t('cashSales')} value={'+ ' + fmtEGP(cashSales)} tone="accent" />
          <div style={{ height: 1, background: 'var(--line)', margin: '2px 0' }} />
          <ReconRow label={t('expectedCash')} value={fmtEGP(expected)} bold />

          <div style={{
            marginTop: 6, padding: 14,
            background: 'rgba(0,0,0,0.25)',
            border: '1px solid var(--line-strong)', borderRadius: 10,
            display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
                {t('countedCash')}
              </span>
              <input value={counted} onChange={e => setCounted(e.target.value.replace(/[^0-9.]/g,''))}
                className="mono ltr-nums"
                style={{
                  fontSize: 28, fontWeight: 700,
                  padding: '10px 12px',
                  background: 'rgba(0,0,0,0.4)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  textAlign: lang==='ar' ? 'right' : 'left',
                }}
              />
            </label>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 4 }}>
              <span className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
                {t('variance')}
              </span>
              <span className="mono ltr-nums" style={{ fontSize: 24, fontWeight: 700, color: varColor, textShadow: `0 0 14px ${varColor}40` }}>
                {variance >= 0 ? '+' : '−'}{fmtEGP(Math.abs(variance))}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <button style={{
              flex: 1, padding: '13px', borderRadius: 10,
              background: 'transparent', border: '1px solid var(--line)',
              color: 'var(--ink-2)', fontSize: 13, fontWeight: 600,
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8,
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><rect x="6" y="9" width="12" height="8" /><path d="M8 9 V5 h8 V9 M8 17 V21 h8 V17" /></svg>
              <span>{t('printReceipt')}</span>
              <span className="kbd">F4</span>
            </button>
            <button style={{
              flex: 2, padding: '13px', borderRadius: 10,
              background: 'linear-gradient(180deg, #00c7f2, #00a6cc)',
              color: '#021018', fontSize: 14, fontWeight: 700,
              boxShadow: '0 0 20px rgba(0,199,242,0.35)',
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
            }}>
              <span>{t('finalize')}</span>
              <span className="kbd" style={{ background: 'rgba(2,16,24,0.2)', borderColor: 'rgba(2,16,24,0.3)', color: '#021018' }}>Enter</span>
            </button>
          </div>
        </div>

        {/* Breakdown mini */}
        <div style={{
          background: 'rgba(8,24,38,0.5)', border: '1px solid var(--line)', borderRadius: 12, padding: 16,
        }}>
          <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 12 }}>
            {lang==='ar' ? 'ملخص الوردية' : 'Shift summary'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {[
              [lang==='ar' ? 'معاملات' : 'Transactions', '184', 'accent'],
              [lang==='ar' ? 'مبيعات' : 'Sales', fmtEGP(24382.75), 'ink'],
              [lang==='ar' ? 'قسائم' : 'Vouchers', '12', 'amber'],
              [lang==='ar' ? 'تأمين' : 'Insurance', '27', 'purple'],
            ].map(([l, v, c]) => (
              <div key={l}>
                <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>{l}</div>
                <div className="mono ltr-nums" style={{
                  fontSize: 20, fontWeight: 700, marginTop: 4,
                  color: c==='accent' ? 'var(--accent-hi)' : c==='amber' ? 'var(--amber)' : c==='purple' ? 'var(--purple)' : 'var(--ink)',
                }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* RIGHT: Thermal receipt preview */}
      <section>
        <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 8 }}>
          {lang==='ar' ? 'معاينة الإيصال · ٨٠ ملم' : 'Receipt preview · 80mm'}
        </div>
        <ThermalReceipt lang={lang} t={t} counted={counted} expected={expected} variance={variance} />
      </section>
    </div>
  );
}

function ReconRow({ label, value, tone, bold }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
      <span className="mono" style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.16em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>{label}</span>
      <span className="mono ltr-nums" style={{
        fontSize: bold ? 22 : 16, fontWeight: bold ? 700 : 600,
        color: tone==='accent' ? 'var(--accent-hi)' : 'var(--ink)',
      }}>{value}</span>
    </div>
  );
}

// 80mm thermal-style receipt (monospace, hairlines)
function ThermalReceipt({ lang, t, counted, expected, variance }) {
  const items = [
    { n: 'Amoxicillin 500mg', qty: 1, price: 48.00 },
    { n: 'Panadol Extra x24', qty: 2, price: 32.50 },
    { n: 'Ventolin Inhaler', qty: 1, price: 78.00 },
  ];
  const itemsAr = [
    { n: 'أموكسيسيلين ٥٠٠', qty: 1, price: 48.00 },
    { n: 'پانادول اكسترا', qty: 2, price: 32.50 },
    { n: 'فنتولين بخاخ', qty: 1, price: 78.00 },
  ];
  const list = lang==='ar' ? itemsAr : items;
  const total = list.reduce((s, i) => s + i.qty * i.price, 0);

  const rcptStyle = {
    background: '#f4efe6',
    color: '#0a0a0a',
    width: 320, maxWidth: '100%',
    padding: '20px 22px',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 11.5, lineHeight: 1.5,
    fontVariantNumeric: 'tabular-nums',
    borderRadius: 4,
    boxShadow: '0 20px 50px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(0,0,0,0.08)',
    margin: '0 auto',
    position: 'relative',
  };

  const dotted = { borderTop: '1px dashed #0a0a0a', margin: '8px 0' };

  return (
    <div style={{ position: 'relative', padding: '0 14px 40px' }}>
      <div style={rcptStyle}>
        {/* perforation top */}
        <div style={{ position: 'absolute', left: 0, right: 0, top: -6, height: 12, background: `radial-gradient(circle at 8px 6px, transparent 4px, #f4efe6 4.5px)`, backgroundSize: '16px 12px' }} />
        <div style={{ textAlign: 'center', marginBottom: 10 }}>
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: 17, fontWeight: 600 }}>{t('receiptHeader')}</div>
          <div style={{ fontSize: 10 }}>{lang==='ar' ? 'فرع المعادي · ش ٩ ميدان الحرية' : 'Maadi Branch · 9 Horreya Sq.'}</div>
          <div style={{ fontSize: 10 }}>{t('taxNo')}: 345-678-901</div>
        </div>
        <div style={dotted} />
        <div style={{ fontSize: 10, display: 'flex', justifyContent: 'space-between' }}>
          <span>{lang==='ar' ? 'إيصال' : 'Receipt'} #24-0418-184</span>
          <span>2026-04-18 14:32</span>
        </div>
        <div style={{ fontSize: 10, display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
          <span>{t('cashier')}: Nour.M</span>
          <span>POS-03</span>
        </div>
        <div style={dotted} />

        {list.map((it, i) => (
          <div key={i} style={{ marginBottom: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', direction: lang==='ar' ? 'rtl' : 'ltr' }}>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.n}</span>
              <span className="ltr-nums">{(it.qty * it.price).toFixed(2)}</span>
            </div>
            <div style={{ fontSize: 10, color: '#444', direction: 'ltr', display: 'flex', gap: 6 }}>
              <span>{it.qty} × {it.price.toFixed(2)}</span>
            </div>
          </div>
        ))}

        <div style={dotted} />
        <div style={{ fontSize: 10 }}>
          <Line l={t('subtotal')} r={total.toFixed(2)} />
          <Line l={t('vat') + ' (incl.)'} r={(total - total/1.14).toFixed(2)} />
          <Line l={t('discount')} r={'−20.00'} />
        </div>
        <div style={dotted} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 700 }}>
          <span>{t('total')}</span>
          <span className="ltr-nums">{(total - 20).toFixed(2)} EGP</span>
        </div>
        <div style={dotted} />
        <div style={{ fontSize: 10 }}>
          <Line l={t('cash')} r={counted} />
          <Line l={t('change')} r={((parseFloat(counted)||0) - (total-20)).toFixed(2)} />
        </div>
        <div style={dotted} />
        <div style={{ textAlign: 'center', fontSize: 10, marginTop: 6 }}>
          {t('thanks')}<br/>datapulse.health / r / 184
        </div>
        {/* Fake barcode */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 1.5, marginTop: 10 }}>
          {Array.from({length: 42}).map((_,i) => (
            <div key={i} style={{ width: [1,2,1,3,1,2][i%6], height: 32, background: '#0a0a0a' }} />
          ))}
        </div>
        <div style={{ textAlign: 'center', fontSize: 9, marginTop: 4, letterSpacing: '0.12em' }}>24-0418-184</div>
        {/* bottom perforation */}
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: -6, height: 12, background: `radial-gradient(circle at 8px 6px, transparent 4px, #f4efe6 4.5px)`, backgroundSize: '16px 12px' }} />
      </div>
      <div style={{ textAlign: 'center', fontSize: 10, color: 'var(--ink-4)', marginTop: 10, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.12em' }}>
        {lang==='ar' ? 'مطابق للطباعة الحرارية ٨٠ ملم' : 'Parity with 80mm thermal output'}
      </div>
    </div>
  );
}

function Line({ l, r }) {
  return <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>{l}</span><span className="ltr-nums">{r}</span></div>;
}

Object.assign(window, { ShiftClose });
