// Invoice frame — full A4 tax-invoice modal with itemized details, VAT breakdown, signatures, printable.
// Triggered from Terminal's Charge button (via onChargeWithInvoice) or from the toolbar.

const { useMemo: useMemoI } = React;

function InvoiceModal({ open, onClose, lang, t, cart, totals, voucher, promo, insurance, paymentMethod, branch, cashier }) {
  if (!open) return null;
  const today = new Date();
  const dateStr = today.toLocaleDateString(lang==='ar' ? 'ar-EG' : 'en-GB');
  const timeStr = today.toLocaleTimeString(lang==='ar' ? 'ar-EG' : 'en-GB', { hour:'2-digit', minute:'2-digit' });
  const invNo = 'INV-' + today.toISOString().slice(2,10).replace(/-/g,'') + '-' + String(Math.floor(Math.random()*9000)+1000);
  const ref = 'REF-' + Math.random().toString(36).slice(2,10).toUpperCase();

  const methodLabel = {
    cash: lang==='ar' ? 'نقدي' : 'Cash',
    card: lang==='ar' ? 'بطاقة ائتمان' : 'Credit card',
    insurance: lang==='ar' ? 'تأمين طبي' : 'Medical insurance',
    voucher: lang==='ar' ? 'قسيمة' : 'Voucher',
  }[paymentMethod] || paymentMethod;

  function doPrint() { window.print(); }

  return (
    <div className="inv-root" style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(2,10,18,0.72)',
      backdropFilter: 'blur(10px)',
      display: 'grid', placeItems: 'center',
      padding: 20,
    }}>
      <style>{`
        @media print {
          html, body { background: #fff !important; }
          body > *:not(.inv-root) { display: none !important; }
          .inv-root { position: static !important; background: #fff !important; padding: 0 !important; backdrop-filter: none !important; }
          .inv-chrome { display: none !important; }
          .inv-paper { box-shadow: none !important; max-width: none !important; width: 100% !important; max-height: none !important; overflow: visible !important; }
          .inv-paper * { color: #000 !important; border-color: #000 !important; }
          .inv-paper .ink-muted { color: #555 !important; }
          .inv-paper .brand-ribbon { background: #0b1a29 !important; color: #fff !important; }
          .inv-paper .brand-ribbon * { color: #fff !important; }
          .inv-paper .row-alt:nth-child(even) { background: #f4f4f4 !important; }
          .inv-paper .totals-box { background: #f1ede4 !important; }
          .inv-paper .totals-box .grand { color: #0b1a29 !important; }
          @page { size: A4; margin: 12mm; }
        }
      `}</style>

      {/* Chrome */}
      <div className="inv-chrome" style={{
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
          {lang==='ar' ? 'إغلاق' : 'Close'}
        </button>
      </div>

      {/* Paper */}
      <div className="inv-paper" style={{
        background: '#fbfaf7', color: '#0b1a29',
        width: 'min(880px, 100%)', maxHeight: '92vh', overflow: 'auto',
        borderRadius: 6, boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
        fontFamily: lang === 'ar' ? 'inherit' : 'Inter, sans-serif',
      }}>
        {/* Brand ribbon */}
        <div className="brand-ribbon" style={{
          background: 'linear-gradient(90deg, #0b1a29, #163452)',
          color: '#fbfaf7',
          padding: '18px 28px',
          display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 16,
          position: 'relative', overflow: 'hidden',
        }}>
          <div aria-hidden="true" style={{
            position: 'absolute', top: -30, insetInlineEnd: -30, width: 160, height: 160, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(0,199,242,0.35), transparent 60%)',
          }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, position: 'relative' }}>
            <div style={{
              width: 42, height: 42, borderRadius: 10,
              background: 'radial-gradient(circle at 30% 30%, #5cdfff, #00c7f2 60%, #7467f8)',
              boxShadow: '0 0 20px rgba(0,199,242,0.6)',
            }} />
            <div>
              <div style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontWeight: 500, fontSize: 24, letterSpacing: '-0.01em' }}>
                DataPulse Pharmacy
              </div>
              <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.85 }}>
                {lang==='ar' ? 'فاتورة ضريبية مبسَّطة' : 'Simplified tax invoice'}
              </div>
            </div>
          </div>
          <div style={{ textAlign: lang==='ar' ? 'left' : 'right', fontFamily: 'JetBrains Mono, monospace', position: 'relative' }}>
            <div style={{ fontSize: 18, fontWeight: 700 }}>{invNo}</div>
            <div style={{ fontSize: 10.5, opacity: 0.85 }}>{dateStr} · {timeStr}</div>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '24px 28px' }}>
          {/* Meta grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: 18, marginBottom: 18 }}>
            <MetaBlock label={lang==='ar' ? 'صادر عن' : 'Issued by'}>
              <div style={{ fontWeight: 700 }}>{branch || (lang==='ar' ? 'صيدلية المعادي · POS-03' : 'Maadi branch · POS-03')}</div>
              <div className="ink-muted" style={{ fontSize: 10.5, color: '#555', marginTop: 2 }}>
                {lang==='ar' ? '١٢ ش. الشهيد صبحي الصالح · القاهرة' : '12 Sobhi Saleh St · Cairo'}
              </div>
              <div className="ink-muted" style={{ fontSize: 10.5, color: '#555' }}>
                {lang==='ar' ? 'الرقم الضريبي' : 'Tax no.'} <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>428-893-011</span>
              </div>
            </MetaBlock>
            <MetaBlock label={lang==='ar' ? 'العميل' : 'Customer'}>
              <div style={{ fontWeight: 700 }}>{lang==='ar' ? 'عميل نقدي' : 'Walk-in customer'}</div>
              {insurance && (
                <>
                  <div className="ink-muted" style={{ fontSize: 10.5, color: '#555', marginTop: 2 }}>
                    {lang==='ar' ? 'تأمين' : 'Insurer'}: <b style={{ color: '#0b1a29' }}>{insurance.name}</b>
                  </div>
                  <div className="ink-muted" style={{ fontSize: 10.5, color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>
                    {lang==='ar' ? 'تغطية' : 'Coverage'} {insurance.coverage}%
                  </div>
                </>
              )}
            </MetaBlock>
            <MetaBlock label={lang==='ar' ? 'تفاصيل المعاملة' : 'Transaction'}>
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 10, rowGap: 2, fontSize: 10.5 }}>
                <span className="ink-muted" style={{ color: '#555' }}>{lang==='ar' ? 'الصرَّافة' : 'Cashier'}</span>
                <span style={{ fontWeight: 600 }}>{cashier || 'Nour Mohamed'}</span>
                <span className="ink-muted" style={{ color: '#555' }}>{lang==='ar' ? 'الدفع' : 'Method'}</span>
                <span style={{ fontWeight: 600 }}>{methodLabel}</span>
                <span className="ink-muted" style={{ color: '#555' }}>{lang==='ar' ? 'مرجع' : 'Ref'}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{ref}</span>
              </div>
            </MetaBlock>
          </div>

          {/* Items table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
            <thead>
              <tr style={{ background: '#0b1a29', color: '#fbfaf7' }}>
                <InvTh w="28" align="center">#</InvTh>
                <InvTh w="100" align="start">{lang==='ar' ? 'الباركود' : 'SKU'}</InvTh>
                <InvTh align="start">{lang==='ar' ? 'الصنف' : 'Description'}</InvTh>
                <InvTh w="48" align="end">{lang==='ar' ? 'الكمية' : 'Qty'}</InvTh>
                <InvTh w="80" align="end">{lang==='ar' ? 'سعر (قبل ض)' : 'Unit ex-VAT'}</InvTh>
                <InvTh w="68" align="end">{lang==='ar' ? 'ض ١٤٪' : 'VAT 14%'}</InvTh>
                <InvTh w="90" align="end">{lang==='ar' ? 'الإجمالي' : 'Line total'}</InvTh>
              </tr>
            </thead>
            <tbody>
              {cart.map((l, i) => {
                const lineIncl = l.price * l.qty;
                const lineEx = lineIncl / 1.14;
                const vat = lineIncl - lineEx;
                return (
                  <tr key={l.lineId} className="row-alt" style={{ borderBottom: '0.5px solid #bbb' }}>
                    <InvTd align="center" mono>{String(i+1).padStart(2,'0')}</InvTd>
                    <InvTd mono style={{ fontSize: 10 }}>{l.sku}</InvTd>
                    <InvTd>
                      <div style={{ fontWeight: 600 }}>{l.name}</div>
                      <div className="ink-muted" style={{ fontSize: 9.5, color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>
                        {lang==='ar' ? 'وحدة' : 'Unit'} {fmtEGP(l.price)} {lang==='ar' ? '· شامل ض' : '· incl. VAT'}
                      </div>
                    </InvTd>
                    <InvTd align="end" mono><b>{l.qty}</b></InvTd>
                    <InvTd align="end" mono>{fmtEGP(l.price / 1.14)}</InvTd>
                    <InvTd align="end" mono>{fmtEGP(vat)}</InvTd>
                    <InvTd align="end" mono><b>{fmtEGP(lineIncl)}</b></InvTd>
                  </tr>
                );
              })}
              {cart.length === 0 && (
                <tr><InvTd colSpan={7} align="center" style={{ padding: '14px 0', color: '#888' }}>—</InvTd></tr>
              )}
            </tbody>
          </table>

          {/* Totals + payment split */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
            <div>
              <div style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 700, color: '#555', marginBottom: 8 }}>
                {lang==='ar' ? 'ملاحظات' : 'Notes'}
              </div>
              <ul className="ink-muted" style={{ fontSize: 10.5, lineHeight: 1.6, paddingInlineStart: 16, margin: 0, color: '#555' }}>
                <li>{lang==='ar' ? 'الأسعار تشمل ضريبة القيمة المضافة ١٤٪.' : 'Prices are inclusive of 14% VAT.'}</li>
                <li>{lang==='ar' ? 'لا يُرد الدواء بعد مغادرة الصيدلية إلا في حالات العيب أو سوء التخزين.' : 'No returns once the medication leaves the pharmacy, except for defects.'}</li>
                <li>{lang==='ar' ? 'يحتفظ العميل بهذه الفاتورة للمطالبات التأمينية وفترة الضمان.' : 'Retain this invoice for insurance claims and warranty periods.'}</li>
                {voucher && <li style={{ fontWeight: 600, color: '#0b1a29' }}>{lang==='ar' ? 'تم تطبيق قسيمة' : 'Voucher applied'}: <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{voucher}</span></li>}
                {promo && <li style={{ fontWeight: 600, color: '#0b1a29' }}>{lang==='ar' ? 'عرض' : 'Promotion'}: {promo.title || promo}</li>}
              </ul>
            </div>

            <div className="totals-box" style={{
              background: '#f1ede4',
              border: '1px solid #0b1a29',
              borderRadius: 4,
              padding: '14px 16px',
            }}>
              <TotalRow label={lang==='ar' ? 'الإجمالي قبل الضريبة' : 'Subtotal ex-VAT'} value={fmtEGP(totals.subtotal)} />
              <TotalRow label={lang==='ar' ? 'ضريبة القيمة المضافة (١٤٪)' : 'VAT (14%)'} value={fmtEGP(totals.vat)} />
              {totals.discount > 0 && <TotalRow label={lang==='ar' ? 'الخصومات' : 'Discounts'} value={'−' + fmtEGP(totals.discount)} negative />}
              {insurance && <TotalRow label={`${lang==='ar' ? 'تحمُّل التأمين' : 'Insurer pays'} (${insurance.coverage}%)`} value={'−' + fmtEGP(totals.insurerPays)} negative />}
              <div style={{ borderTop: '1.5px solid #0b1a29', margin: '10px 0 8px' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 700, color: '#555' }}>
                  {insurance ? (lang==='ar' ? 'حصة المريض' : 'Patient pays') : (lang==='ar' ? 'الإجمالي المستحق' : 'Amount due')}
                </span>
                <span className="grand" style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 26, fontWeight: 500, color: '#0b1a29' }}>
                  {fmtEGP(insurance ? totals.patientPays : totals.total)}
                </span>
              </div>
            </div>
          </div>

          {/* Signatures + footer */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, marginTop: 28 }}>
            <InvSig label={lang==='ar' ? 'توقيع الصرَّافة' : 'Cashier signature'} prefilled={cashier || 'Nour Mohamed'} />
            <InvSig label={lang==='ar' ? 'ختم الصيدلية' : 'Pharmacy stamp'} />
            <InvSig label={lang==='ar' ? 'توقيع العميل' : 'Customer signature'} />
          </div>

          <div style={{ borderTop: '1px dashed #888', marginTop: 24, paddingTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 9.5 }} className="ink-muted">
            <span style={{ color: '#555' }}>{lang==='ar' ? 'شكراً لاختياركم صيدلية داتا پالس · خط المريض ١٩٢٤٨' : 'Thank you · patient hotline 19248'}</span>
            <span style={{ color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>{invNo} · p 1/1</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetaBlock({ label, children }) {
  return (
    <div style={{ padding: '10px 12px', background: 'rgba(11,26,41,0.04)', border: '0.5px solid rgba(11,26,41,0.3)', borderRadius: 4 }}>
      <div style={{ fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', fontWeight: 700, color: '#555', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 12 }}>{children}</div>
    </div>
  );
}
function InvTh({ children, w, align }) {
  return <th style={{ padding: '7px 7px', width: w, fontSize: 9.5, letterSpacing: '0.16em', textTransform: 'uppercase', textAlign: align || 'center', fontWeight: 700 }}>{children}</th>;
}
function InvTd({ children, align, mono, style, colSpan }) {
  return <td colSpan={colSpan} style={{ padding: '7px 7px', textAlign: align || 'start', fontFamily: mono ? 'JetBrains Mono, monospace' : 'inherit', fontSize: mono ? 10.5 : 11, verticalAlign: 'middle', ...(style||{}) }}>{children}</td>;
}
function TotalRow({ label, value, negative }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '3px 0', fontSize: 11.5 }}>
      <span style={{ color: '#555' }}>{label}</span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, color: negative ? '#0b7a4b' : '#0b1a29' }}>{value}</span>
    </div>
  );
}
function InvSig({ label, prefilled }) {
  return (
    <div>
      <div style={{ borderBottom: '1px solid #0b1a29', minHeight: 38, display: 'flex', alignItems: 'flex-end', paddingInlineStart: 4, fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 14, color: '#0b1a29' }}>
        {prefilled || ''}
      </div>
      <div style={{ fontSize: 9.5, color: '#555', letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: 4 }}>{label}</div>
    </div>
  );
}

Object.assign(window, { InvoiceModal });
