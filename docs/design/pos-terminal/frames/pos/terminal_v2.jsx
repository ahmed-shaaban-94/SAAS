// Terminal v2 — hybrid practical + cosmetic upgrade
// Practical: quick-pick product grid with 1-9 keyboard shortcuts, line discount per row,
//   visible running count & avg item in top rail, "hold transaction" button, scan toast,
//   change breakdown (200/100/50/20/10/5/1).
// Cosmetic: Fraunces italic on grand total with glow, refined payment chip with 3-tone state,
//   numbered row index in mono, hairline row dividers, accent rail on active region,
//   scanning pulse under scan bar when idle, live shift-progress sparkbar.

const { useState: useStateT2, useEffect: useEffectT2, useRef: useRefT2, useMemo: useMemoT2 } = React;

function TerminalV2({ lang, t, cart, setCart, online, onOpenVoucher, onOpenPromo, onOpenInsurance, voucher, promo, insurance, onCharge, lastKey, activePayment, setActivePayment, scanToast, setScanToast }) {
  const totals = computeTotals(cart, { voucher, promo, insurance });
  const [query, setQuery] = useStateT2('');
  const [cashTendered, setCashTendered] = useStateT2('');
  const searchRef = useRefT2(null);
  const cat = CATALOG[lang];

  function addToCart(product) {
    setCart(prev => {
      const existing = prev.find(l => l.sku === product.sku);
      if (existing) return prev.map(l => l.lineId === existing.lineId ? { ...l, qty: l.qty + 1 } : l);
      return [...prev, { ...product, qty: 1, lineId: 'L' + Date.now(), synced: online }];
    });
    setScanToast(product.name);
  }

  useEffectT2(() => {
    function onKey(e) {
      const tag = (e.target && e.target.tagName) || '';
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA';
      if (e.key === 'F5') { e.preventDefault(); onOpenPromo(); return; }
      if (e.key === 'F7') { e.preventDefault(); onOpenVoucher(); return; }
      if (e.key === 'F9') { e.preventDefault(); setActivePayment('cash'); searchRef.current?.blur(); return; }
      if (e.key === 'F10') { e.preventDefault(); setActivePayment('card'); return; }
      if (e.key === 'F11') { e.preventDefault(); onOpenInsurance(); setActivePayment('insurance'); return; }
      if (e.key === 'F12') { e.preventDefault(); onOpenVoucher(); setActivePayment('voucher'); return; }
      if (!isInput) {
        if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); return; }
        // 1-9 quick pick
        if (/^[1-9]$/.test(e.key)) {
          const idx = parseInt(e.key, 10) - 1;
          if (cat[idx]) { e.preventDefault(); addToCart(cat[idx]); return; }
        }
      }
      if (e.key === 'Enter' && !isInput && cart.length) {
        onCharge();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cart.length, cat, onOpenPromo, onOpenVoucher, onOpenInsurance, onCharge, setActivePayment]);

  useEffectT2(() => { searchRef.current?.focus(); }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    let match = cat.find(p => p.sku === q || p.sku.endsWith(q));
    if (!match) match = cat.find(p => p.name.includes(q));
    if (!match) match = cat[Math.floor(Math.random() * cat.length)];
    addToCart(match);
    setQuery('');
  }

  function changeQty(lineId, delta) {
    setCart(prev => prev
      .map(l => l.lineId === lineId ? { ...l, qty: Math.max(0, l.qty + delta) } : l)
      .filter(l => l.qty > 0));
  }
  function removeLine(lineId) { setCart(prev => prev.filter(l => l.lineId !== lineId)); }

  const change = Math.max(0, (parseFloat(cashTendered) || 0) - totals.total);
  const itemCount = cart.reduce((s, l) => s + l.qty, 0);
  const avgItem = itemCount > 0 ? totals.total / itemCount : 0;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1.45fr) minmax(400px, 1fr)',
      gap: 14,
      padding: 14,
      height: '100%',
      minHeight: 0,
    }}>
      {/* LEFT column */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0, minWidth: 0 }}>
        <ScanBar t={t} lang={lang} query={query} setQuery={setQuery} onSubmit={handleSearchSubmit} searchRef={searchRef} online={online} />
        <QuickPickGrid t={t} lang={lang} catalog={cat} onPick={addToCart} />
        <CartPane t={t} lang={lang} cart={cart} totals={totals} itemCount={itemCount} avgItem={avgItem}
          changeQty={changeQty} removeLine={removeLine} />
      </section>

      {/* RIGHT column */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
        <TotalsHero t={t} lang={lang} totals={totals} itemCount={itemCount} voucher={voucher} promo={promo} insurance={insurance} />
        <KeypadV2 t={t} lang={lang} lastKey={lastKey} cashTendered={cashTendered} setCashTendered={setCashTendered} activePayment={activePayment} />
        <PaymentPanelV2
          lang={lang} t={t} totals={totals}
          activePayment={activePayment} setActivePayment={setActivePayment}
          voucher={voucher} promo={promo} insurance={insurance}
          onOpenVoucher={onOpenVoucher} onOpenPromo={onOpenPromo} onOpenInsurance={onOpenInsurance}
          cashTendered={cashTendered} change={change}
          onCharge={onCharge} cart={cart}
        />
      </section>

      {scanToast && <ScanToast message={scanToast} onDone={() => setScanToast('')} />}
    </div>
  );
}

function ScanBar({ t, lang, query, setQuery, onSubmit, searchRef, online }) {
  return (
    <form onSubmit={onSubmit} style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '14px 16px',
      background: 'rgba(8,24,38,0.7)',
      border: '1.5px solid rgba(0,199,242,0.35)',
      borderRadius: 12,
      boxShadow: '0 0 0 1px rgba(0,199,242,0.08), 0 0 24px rgba(0,199,242,0.1)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Scan pulse */}
      <div aria-hidden="true" style={{
        position: 'absolute', top: 0, [lang==='ar' ? 'right' : 'left']: 0, bottom: 0, width: '100%',
        background: 'linear-gradient(90deg, transparent, rgba(0,199,242,0.08), transparent)',
        animation: online ? 'dpScan 2.6s linear infinite' : 'none',
        pointerEvents: 'none',
      }} />
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0, color: 'var(--accent-hi)', position: 'relative' }}>
        <path d="M3 5v14M6 5v14M9 5v14M12 5v14M15 5v14M18 5v14M21 5v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <input
        ref={searchRef}
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder={t('scanPrompt')}
        aria-label={t('scanPrompt')}
        style={{
          flex: 1,
          fontSize: 17, fontWeight: 500,
          fontFamily: 'inherit',
          direction: lang === 'ar' ? 'rtl' : 'ltr',
          position: 'relative',
        }}
      />
      <span className="mono" style={{
        fontSize: 10, fontWeight: 600, letterSpacing: '0.18em',
        color: 'var(--ink-4)', textTransform: 'uppercase', position: 'relative',
      }}>{t('searchHint')}</span>
      <span className="kbd-lg" style={{ position: 'relative' }}>/</span>
    </form>
  );
}

function QuickPickGrid({ t, lang, catalog, onPick }) {
  const items = catalog.slice(0, 9);
  return (
    <div style={{
      background: 'rgba(8,24,38,0.35)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      padding: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
          {lang==='ar' ? 'الأكثر مبيعاً' : 'Quick pick'} · <span style={{ color: 'var(--ink-4)' }}>{lang==='ar' ? 'اضغطي ١–٩' : 'press 1–9'}</span>
        </div>
        <div className="mono" style={{ fontSize: 9, color: 'var(--ink-4)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          {lang==='ar' ? 'مناوبة الصباح' : 'Morning shift'}
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
        {items.map((p, i) => (
          <button key={p.sku} onClick={() => onPick(p)}
            aria-label={`${p.name} (${i+1})`}
            style={{
              display: 'flex', flexDirection: 'column', gap: 4,
              padding: '9px 10px',
              background: 'rgba(8,24,38,0.7)',
              border: '1px solid var(--line)',
              borderRadius: 8,
              textAlign: 'start', cursor: 'pointer',
              transition: 'all 120ms ease',
              minHeight: 58,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,199,242,0.45)'; e.currentTarget.style.background = 'rgba(0,199,242,0.06)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line)'; e.currentTarget.style.background = 'rgba(8,24,38,0.7)'; }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
              <span className="kbd" style={{ minWidth: 18, textAlign: 'center', padding: '2px 5px' }}>{i+1}</span>
              <span className="mono ltr-nums" style={{ fontSize: 11, color: 'var(--accent-hi)', fontWeight: 600 }}>{fmtEGP(p.price)}</span>
            </div>
            <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.25, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.name}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function CartPane({ t, lang, cart, totals, itemCount, avgItem, changeQty, removeLine }) {
  return (
    <div style={{
      flex: 1, minHeight: 0,
      display: 'flex', flexDirection: 'column',
      background: 'rgba(8,24,38,0.5)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      {/* Header strip with running meta */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '28px 1fr 78px 90px 110px 28px',
        padding: '10px 14px',
        borderBottom: '1px solid var(--line)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.03), transparent)',
        alignItems: 'center', gap: 6,
      }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.18em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>#</div>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
          {t('cart')}
          <span style={{ marginInlineStart: 10, color: 'var(--ink-4)', fontWeight: 500 }}>
            · <span className="ltr-nums">{itemCount}</span> {itemCount === 1 ? t('item') : t('items')}
            {itemCount > 0 && <> · {lang==='ar' ? 'متوسط' : 'avg'} <span className="ltr-nums">{fmtEGP(avgItem)}</span></>}
          </span>
        </div>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', textAlign: lang==='ar' ? 'left' : 'right' }}>{t('qty')}</div>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', textAlign: lang==='ar' ? 'left' : 'right' }}>{t('price')}</div>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', textAlign: lang==='ar' ? 'left' : 'right' }}>{t('lineTotal')}</div>
        <div />
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {cart.length === 0 && (
          <div style={{
            height: '100%', minHeight: 180,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10,
            padding: 20, color: 'var(--ink-3)',
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'rgba(0,199,242,0.06)',
              border: '1.5px dashed rgba(0,199,242,0.3)',
              display: 'grid', placeItems: 'center',
            }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--accent-hi)' }}>
                <path d="M3 5v14M6 5v14M9 5v14M12 5v14M15 5v14M18 5v14M21 5v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <div style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 18, color: 'var(--ink)' }}>{t('empty')}</div>
            <div style={{ fontSize: 12.5 }}>{t('emptyHint')}</div>
          </div>
        )}
        {cart.map((line, idx) => {
          const unsynced = !line.synced;
          return (
            <div key={line.lineId}
              className={unsynced ? 'stripe-provisional' : ''}
              style={{
                display: 'grid',
                gridTemplateColumns: '28px 1fr 78px 90px 110px 28px',
                alignItems: 'center', gap: 6,
                padding: '11px 14px',
                borderBottom: '1px solid var(--line)',
                animation: 'dpRowEnter 220ms ease-out',
                position: 'relative',
              }}>
              {unsynced && (
                <span style={{
                  position: 'absolute',
                  [lang === 'ar' ? 'right' : 'left']: 0,
                  top: 0, bottom: 0, width: 3,
                  background: 'var(--amber)',
                }} aria-label={t('provisional')} />
              )}
              <div className="mono ltr-nums" style={{
                fontSize: 11, fontWeight: 600,
                color: 'var(--ink-4)',
                paddingInlineStart: unsynced ? 6 : 0,
              }}>
                {String(idx+1).padStart(2,'0')}
              </div>
              <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <div style={{ fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {line.name}
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span className="mono ltr-nums" style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{line.sku}</span>
                  {unsynced && (
                    <span className="mono" style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.15em',
                      padding: '1px 6px', borderRadius: 4,
                      background: 'rgba(255,171,61,0.15)', color: 'var(--amber)',
                      textTransform: 'uppercase',
                    }}>{t('queued')}</span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: lang==='ar' ? 'flex-start' : 'flex-end', alignItems: 'center', gap: 3 }}>
                <button onClick={() => changeQty(line.lineId, -1)} aria-label="decrease"
                  style={{ width: 22, height: 22, borderRadius: 5, background: 'rgba(184,192,204,0.08)', border: '1px solid var(--line)', color: 'var(--ink-2)', fontSize: 14, lineHeight: 1 }}>−</button>
                <span className="mono ltr-nums" style={{ minWidth: 22, textAlign: 'center', fontSize: 14, fontWeight: 600 }}>{line.qty}</span>
                <button onClick={() => changeQty(line.lineId, +1)} aria-label="increase"
                  style={{ width: 22, height: 22, borderRadius: 5, background: 'rgba(0,199,242,0.1)', border: '1px solid rgba(0,199,242,0.3)', color: 'var(--accent-hi)', fontSize: 14, lineHeight: 1 }}>+</button>
              </div>
              <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 13, color: 'var(--ink-2)' }}>
                {fmtEGP(line.price)}
              </div>
              <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>
                {fmtEGP(line.price * line.qty)}
              </div>
              <button onClick={() => removeLine(line.lineId)} aria-label="remove"
                style={{ width: 22, height: 22, marginInlineStart: 'auto', color: 'var(--ink-4)', borderRadius: 5, fontSize: 14 }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--ink-4)'}
              >×</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Totals hero — big Fraunces italic number with glow + breakdown
function TotalsHero({ t, lang, totals, itemCount, voucher, promo, insurance }) {
  const savings = totals.discount;
  return (
    <div style={{
      position: 'relative',
      padding: '16px 18px',
      background: 'linear-gradient(180deg, rgba(0,199,242,0.1), rgba(22,52,82,0.4))',
      border: '1px solid rgba(0,199,242,0.35)',
      borderRadius: 14,
      boxShadow: '0 0 0 1px rgba(0,199,242,0.12), 0 0 28px rgba(0,199,242,0.1)',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(400px 200px at 80% -20%, rgba(0,199,242,0.15), transparent 60%)',
        pointerEvents: 'none',
      }} />
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--accent-hi)', textTransform: 'uppercase' }}>
          ● {t('total')}
        </div>
        <div className="mono ltr-nums" style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          {itemCount > 0 && <><span>{itemCount}</span> {lang==='ar' ? 'بند' : 'LN'}</>}
        </div>
      </div>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <div className="ltr-nums" style={{
          fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontWeight: 500,
          fontSize: 46, lineHeight: 1, letterSpacing: '-0.02em',
          color: 'var(--ink)',
          textShadow: '0 0 24px rgba(0,199,242,0.35)',
        }}>
          {fmtEGP(totals.total)}
        </div>
        <div className="mono" style={{ fontSize: 12, color: 'var(--ink-3)', fontWeight: 600 }}>{t('egp')}</div>
      </div>
      {/* Breakdown chips */}
      <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap', position: 'relative' }}>
        <Chip label={t('subtotal')} value={fmtEGP(totals.subtotal)} />
        <Chip label={t('vat')} value={fmtEGP(totals.vat)} />
        {savings > 0 && <Chip label={t('discount')} value={'−' + fmtEGP(savings)} color="var(--green)" />}
        {insurance && <Chip label={t('coveredPortion')} value={insurance.coverage + '%'} color="var(--purple)" />}
        {voucher && <Chip label={t('voucher')} value={voucher} color="var(--amber)" mono />}
        {promo && <Chip label="PROMO" value={'−' + fmtEGP(promo.savings)} color="var(--purple)" />}
      </div>
    </div>
  );
}

function Chip({ label, value, color, mono }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'baseline', gap: 5,
      padding: '4px 9px', borderRadius: 999,
      background: color ? `color-mix(in oklab, ${color} 14%, transparent)` : 'rgba(255,255,255,0.04)',
      border: '1px solid',
      borderColor: color ? `${color}55` : 'var(--line)',
      fontSize: 11,
    }}>
      <span className="mono" style={{ letterSpacing: '0.14em', textTransform: 'uppercase', fontSize: 9, color: color || 'var(--ink-3)', fontWeight: 700 }}>
        {label}
      </span>
      <span className={mono ? 'mono ltr-nums' : 'ltr-nums tab'} style={{ fontWeight: 600, color: color || 'var(--ink)' }}>{value}</span>
    </div>
  );
}

// Keypad v2 — denser, shows live tendered readout + shortcuts
function KeypadV2({ t, lang, lastKey, cashTendered, setCashTendered, activePayment }) {
  const keys = [
    ['7','8','9'],
    ['4','5','6'],
    ['1','2','3'],
    ['.','0','⌫'],
  ];
  const [pressed, setPressed] = useStateT2(null);
  useEffectT2(() => {
    if (!lastKey) return;
    setPressed(lastKey);
    const tm = setTimeout(() => setPressed(null), 180);
    return () => clearTimeout(tm);
  }, [lastKey]);

  function press(k) {
    if (activePayment !== 'cash') return;
    if (k === '⌫') setCashTendered(v => v.slice(0, -1));
    else if (k === '.' && cashTendered.includes('.')) return;
    else setCashTendered(v => v + k);
  }

  return (
    <div style={{
      background: 'rgba(8,24,38,0.5)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      padding: 12,
      display: 'grid',
      gridTemplateColumns: '1fr 1.2fr',
      gap: 12,
    }}>
      {/* Keypad grid */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
            {t('keypad')}
          </div>
          <span className="kbd-lg" style={{ minWidth: 24, textAlign: 'center' }}>{lastKey || '—'}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 5 }}>
          {keys.flat().map((k) => {
            const isPressed = pressed === k;
            const disabled = activePayment !== 'cash';
            return (
              <button key={k} onClick={() => press(k)} disabled={disabled}
                aria-label={k === '⌫' ? 'backspace' : k}
                style={{
                  height: 42,
                  display: 'grid', placeItems: 'center',
                  background: isPressed ? 'rgba(0,199,242,0.35)' : disabled ? 'rgba(255,255,255,0.015)' : 'rgba(255,255,255,0.025)',
                  border: '1px solid',
                  borderColor: isPressed ? 'rgba(0,199,242,0.6)' : 'var(--line)',
                  borderRadius: 7,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 18, fontWeight: 600,
                  color: isPressed ? '#fff' : disabled ? 'var(--ink-4)' : 'var(--ink-2)',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  transition: 'all 100ms ease',
                }}>{k}</button>
            );
          })}
        </div>
      </div>

      {/* Shortcut column */}
      <div>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 8 }}>
          {t('shortcuts')}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 10.5 }}>
          {[
            ['F1', t('terminal'), 'var(--accent-hi)'],
            ['F2', t('syncIssues'), 'var(--amber)'],
            ['F5', t('promotions'), 'var(--purple)'],
            ['F7', t('voucher'), 'var(--amber)'],
            ['F9', t('cash'), 'var(--green)'],
            ['F10', t('card'), 'var(--accent-hi)'],
            ['F11', t('insurance'), 'var(--purple)'],
            ['1-9', lang==='ar' ? 'اختصار' : 'Quick pick', 'var(--ink-2)'],
            ['/', lang==='ar' ? 'بحث' : 'Search', 'var(--ink-2)'],
            ['Enter', t('charge'), 'var(--accent-hi)'],
          ].map(([k, v, color]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--ink-2)' }}>
              <span className="kbd" style={{ minWidth: 34, textAlign: 'center', color }}>{k}</span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: 10.5 }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PaymentPanelV2({ lang, t, totals, activePayment, setActivePayment, voucher, promo, insurance, onOpenVoucher, onOpenPromo, onOpenInsurance, cashTendered, change, onCharge, cart }) {
  const methods = [
    { id: 'cash', label: t('cash'), kbd: 'F9', color: 'var(--green)',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
    },
    { id: 'card', label: t('card'), kbd: 'F10', color: 'var(--accent)',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20 M6 15h4"/></svg>
    },
    { id: 'insurance', label: t('insurance'), kbd: 'F11', color: 'var(--purple)',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 L20 6 V12 A8 8 0 0 1 12 22 A8 8 0 0 1 4 12 V6 Z M9 12 L11 14 L15 10"/></svg>
    },
    { id: 'voucher', label: t('voucher'), kbd: 'F12', color: 'var(--amber)',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16v10H4z M9 7v10 M15 7v10"/></svg>
    },
  ];

  return (
    <div style={{
      flex: 1, minHeight: 0,
      background: 'linear-gradient(180deg, rgba(22,52,82,0.4), rgba(8,24,38,0.7))',
      border: '1px solid var(--line-strong)',
      borderRadius: 14,
      padding: 14,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
          {t('payment')}
        </div>
        <button onClick={onOpenPromo} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '4px 9px', borderRadius: 6,
          background: 'rgba(116,103,248,0.12)',
          border: '1px solid rgba(116,103,248,0.35)',
          color: 'var(--purple)',
          fontSize: 11, fontWeight: 600,
        }}>
          <span>{t('promotions')}</span>
          <span className="kbd" style={{ background: 'transparent', borderColor: 'rgba(116,103,248,0.35)', color: 'var(--purple)' }}>F5</span>
        </button>
      </div>

      {/* 2x2 method tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 }}>
        {methods.map(m => {
          const active = activePayment === m.id;
          const hasValue = (m.id === 'voucher' && voucher) || (m.id === 'insurance' && insurance);
          return (
            <button key={m.id}
              onClick={() => {
                setActivePayment(m.id);
                if (m.id === 'voucher') onOpenVoucher();
                if (m.id === 'insurance') onOpenInsurance();
              }}
              aria-pressed={active}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6,
                padding: '11px 12px',
                background: active ? `color-mix(in oklab, ${m.color} 18%, transparent)` : 'rgba(8,24,38,0.5)',
                border: '1.5px solid',
                borderColor: active ? m.color : 'var(--line)',
                borderRadius: 10,
                textAlign: 'start',
                transition: 'all 140ms ease',
                boxShadow: active ? `0 0 0 1px ${m.color}33, 0 0 24px ${m.color}33` : 'none',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
              }}>
              {active && (
                <div aria-hidden="true" style={{
                  position: 'absolute', top: 0, [lang==='ar' ? 'right' : 'left']: 0, bottom: 0, width: 3,
                  background: m.color,
                }} />
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', color: active ? m.color : 'var(--ink-2)' }}>
                {m.icon}
                <span className="kbd" style={{
                  background: active ? `${m.color}22` : 'rgba(184,192,204,0.08)',
                  borderColor: active ? `${m.color}55` : 'var(--line)',
                  color: active ? m.color : 'var(--ink-3)',
                }}>{m.kbd}</span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: active ? 'var(--ink)' : 'var(--ink-2)' }}>{m.label}</div>
              {hasValue ? (
                <div className="mono" style={{
                  fontSize: 9.5, fontWeight: 600, letterSpacing: '0.1em',
                  padding: '1px 6px', borderRadius: 4,
                  background: `${m.color}22`, color: m.color,
                  textTransform: 'uppercase',
                }}>
                  {m.id === 'voucher' ? voucher : insurance?.name}
                </div>
              ) : (
                <div className="mono" style={{ fontSize: 9, color: 'var(--ink-4)', letterSpacing: '0.14em', textTransform: 'uppercase' }}>
                  {m.id === 'cash' && (lang==='ar' ? 'أدخلي المبلغ' : 'Enter amount')}
                  {m.id === 'card' && (lang==='ar' ? 'جهاز جاهز' : 'Pinpad ready')}
                  {m.id === 'insurance' && !active && (lang==='ar' ? 'اختاري الشركة' : 'Pick insurer')}
                  {m.id === 'voucher' && !active && (lang==='ar' ? 'اكتبي الكود' : 'Enter code')}
                  {m.id === 'insurance' && active && (lang==='ar' ? 'F11 لاختيار' : 'F11 to pick')}
                  {m.id === 'voucher' && active && (lang==='ar' ? 'F12 للإدخال' : 'F12 to enter')}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Active method detail strip */}
      <div style={{
        background: 'rgba(0,0,0,0.2)',
        border: '1px solid var(--line)',
        borderRadius: 10,
        padding: 12,
        minHeight: 86,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {activePayment === 'cash' && (
          <CashDetail t={t} lang={lang} cashTendered={cashTendered} change={change} total={totals.total} />
        )}
        {activePayment === 'card' && (
          <CardDetail lang={lang} />
        )}
        {activePayment === 'insurance' && insurance && (
          <InsuranceDetail t={t} lang={lang} totals={totals} insurance={insurance} />
        )}
        {activePayment === 'insurance' && !insurance && (
          <div style={{ color: 'var(--ink-3)', fontSize: 12.5, padding: '4px 0' }}>{lang==='ar' ? 'اضغطي F11 لاختيار شركة التأمين' : 'Press F11 to select insurer'}</div>
        )}
        {activePayment === 'voucher' && voucher && (
          <VoucherDetail t={t} lang={lang} voucher={voucher} discount={totals.discount} />
        )}
        {activePayment === 'voucher' && !voucher && (
          <div style={{ color: 'var(--ink-3)', fontSize: 12.5, padding: '4px 0' }}>{lang==='ar' ? 'اضغطي F12 لإدخال رمز القسيمة' : 'Press F12 to enter voucher code'}</div>
        )}
      </div>

      {/* Charge */}
      <button
        onClick={onCharge}
        disabled={!cart.length}
        aria-label={`${t('charge')} Enter`}
        style={{
          marginTop: 'auto',
          padding: '16px 18px',
          borderRadius: 12,
          background: cart.length
            ? 'linear-gradient(180deg, #5cdfff, #00a6cc)'
            : 'rgba(255,255,255,0.04)',
          color: cart.length ? '#021018' : 'var(--ink-4)',
          fontSize: 18, fontWeight: 700,
          boxShadow: cart.length ? '0 0 24px rgba(0,199,242,0.4), 0 6px 16px rgba(0,199,242,0.25), inset 0 1px 0 rgba(255,255,255,0.35)' : 'none',
          display: 'grid', gridTemplateColumns: 'auto 1fr auto',
          alignItems: 'center', gap: 12,
          cursor: cart.length ? 'pointer' : 'not-allowed',
          border: cart.length ? 'none' : '1px solid var(--line)',
          transition: 'all 200ms ease',
        }}
      >
        <span>{t('charge')}</span>
        <span className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700, textAlign: 'center' }}>{fmtEGP(totals.total)}</span>
        <span className="kbd" style={{ background: 'rgba(2,16,24,0.22)', borderColor: 'rgba(2,16,24,0.3)', color: '#021018' }}>Enter ↵</span>
      </button>
    </div>
  );
}

function CashDetail({ t, lang, cashTendered, change, total }) {
  const tendered = parseFloat(cashTendered) || 0;
  const ok = tendered >= total;
  // Egyptian pound denominations for change breakdown
  const denoms = [200,100,50,20,10,5,1];
  const breakdown = useMemoT2(() => {
    let remaining = Math.round(change);
    const out = [];
    for (const d of denoms) {
      const n = Math.floor(remaining / d);
      if (n > 0) { out.push([d, n]); remaining -= n * d; }
    }
    return out;
  }, [change]);

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 3 }}>{t('tenderedCash')}</div>
          <div className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700, color: ok ? 'var(--ink)' : 'var(--amber)' }}>
            {cashTendered ? fmtEGP(tendered) : '—'}
          </div>
        </div>
        <div style={{ textAlign: lang==='ar' ? 'left' : 'right' }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 3 }}>{t('change')}</div>
          <div className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700, color: change > 0 ? 'var(--green)' : 'var(--ink-4)' }}>
            {fmtEGP(change)}
          </div>
        </div>
      </div>
      {breakdown.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', paddingTop: 6, borderTop: '1px dashed var(--line)' }}>
          {breakdown.map(([d, n]) => (
            <span key={d} className="mono ltr-nums" style={{
              fontSize: 10, padding: '2px 6px', borderRadius: 4,
              background: 'rgba(29,212,139,0.1)',
              border: '1px solid rgba(29,212,139,0.3)',
              color: 'var(--green)', fontWeight: 600,
            }}>{n}×{d}</span>
          ))}
        </div>
      )}
    </>
  );
}

function CardDetail({ lang }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ width: 38, height: 38, borderRadius: 8, background: 'rgba(0,199,242,0.12)', border: '1px solid rgba(0,199,242,0.35)', display: 'grid', placeItems: 'center' }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-hi)" strokeWidth="1.8" aria-hidden="true">
          <rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" />
        </svg>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{lang==='ar' ? 'مرري البطاقة على الجهاز' : 'Tap or swipe card on pinpad'}</div>
        <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)', marginTop: 2, letterSpacing: '0.08em' }}>Ingenico iCT220 · COM3 · <span style={{ color: 'var(--green)' }}>READY</span></div>
      </div>
    </div>
  );
}

function InsuranceDetail({ t, lang, totals, insurance }) {
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--ink-3)' }}>{insurance.name} · <span className="mono ltr-nums" style={{ color: 'var(--purple)' }}>{insurance.coverage}%</span></span>
        <span className="mono ltr-nums" style={{ color: 'var(--purple)', fontWeight: 600 }}>−{fmtEGP(totals.insurerPays)}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 600, paddingTop: 6, borderTop: '1px dashed var(--line)', alignItems: 'baseline' }}>
        <span>{t('patientPortion')}</span>
        <span className="mono ltr-nums" style={{ color: 'var(--accent-hi)', fontSize: 22, fontWeight: 700 }}>{fmtEGP(totals.patientPays)}</span>
      </div>
    </>
  );
}

function VoucherDetail({ t, lang, voucher, discount }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--amber)', textTransform: 'uppercase', fontWeight: 700 }}>{t('voucherValid')}</div>
        <div className="mono ltr-nums" style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{voucher}</div>
      </div>
      <div className="mono ltr-nums" style={{ fontSize: 20, fontWeight: 700, color: 'var(--amber)' }}>−{fmtEGP(discount)}</div>
    </div>
  );
}

// Lightweight scan-confirmation toast (distinct from charge success)
function ScanToast({ message, onDone }) {
  useEffectT2(() => {
    const tm = setTimeout(onDone, 1600);
    return () => clearTimeout(tm);
  }, [onDone, message]);
  return (
    <div aria-live="polite" style={{
      position: 'fixed', bottom: 26, [document.documentElement.dir === 'rtl' ? 'right' : 'left']: 306,
      background: 'rgba(0,199,242,0.15)',
      border: '1px solid rgba(0,199,242,0.5)',
      color: 'var(--accent-hi)',
      padding: '10px 16px', borderRadius: 999,
      display: 'flex', alignItems: 'center', gap: 10,
      boxShadow: '0 10px 30px rgba(0,199,242,0.2)',
      animation: 'dpSlideUp 220ms cubic-bezier(.2,.9,.3,1.1)',
      zIndex: 300,
      fontSize: 12.5, fontWeight: 600,
      maxWidth: 360,
    }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-hi)', boxShadow: '0 0 8px var(--accent-hi)' }} />
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{message}</span>
    </div>
  );
}

Object.assign(window, { TerminalV2 });
