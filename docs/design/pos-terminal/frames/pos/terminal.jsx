// Terminal: cart-dominant left, keypad top-right, payment 2x2 bottom-right.
// Cashier never uses mouse — F-keys drive everything. Keypad echoes live keystrokes.

const { useState: useStateT, useEffect: useEffectT, useRef: useRefT, useMemo: useMemoT } = React;

function Terminal({ lang, t, cart, setCart, online, onOpenVoucher, onOpenPromo, onOpenInsurance, voucher, promo, insurance, onCharge, lastKey, activePayment, setActivePayment }) {
  const totals = computeTotals(cart, { voucher, promo, insurance });
  const [query, setQuery] = useStateT('');
  const searchRef = useRefT(null);
  const [cashTendered, setCashTendered] = useStateT('');

  // Global key handler: barcode scanner simulation (when focused in search) + F-keys
  useEffectT(() => {
    function onKey(e) {
      // F-keys
      const tag = (e.target && e.target.tagName) || '';
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA';
      if (e.key === 'F5') { e.preventDefault(); onOpenPromo(); return; }
      if (e.key === 'F7') { e.preventDefault(); onOpenVoucher(); return; }
      if (e.key === 'F9') { e.preventDefault(); setActivePayment('cash'); searchRef.current?.blur(); return; }
      if (e.key === 'F10') { e.preventDefault(); setActivePayment('card'); return; }
      if (e.key === 'F11') { e.preventDefault(); onOpenInsurance(); setActivePayment('insurance'); return; }
      if (e.key === 'F12') { e.preventDefault(); onOpenVoucher(); setActivePayment('voucher'); return; }
      // Letter shortcuts when NOT typing in an input
      if (!isInput) {
        if (e.key.toLowerCase() === 'v') { e.preventDefault(); onOpenVoucher(); return; }
        if (e.key.toLowerCase() === 'p') { e.preventDefault(); onOpenPromo(); return; }
        if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); return; }
      }
      if (e.key === 'Enter' && !isInput && cart.length) {
        onCharge();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cart.length, onOpenPromo, onOpenVoucher, onOpenInsurance, onCharge, setActivePayment]);

  // Auto-focus search on mount so every keystroke lands there (barcode scanner behavior)
  useEffectT(() => { searchRef.current?.focus(); }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    // Simulate scanner: if it's numeric and >10 chars, treat as barcode; else search by name
    const cat = CATALOG[lang];
    let match = cat.find(p => p.sku === q || p.sku.endsWith(q));
    if (!match) {
      match = cat.find(p => p.name.includes(q));
    }
    if (!match) {
      // Pick first catalog item as a demo fallback
      match = cat[Math.floor(Math.random() * cat.length)];
    }
    // Add to cart (new line or inc qty)
    setCart(prev => {
      const existing = prev.find(l => l.sku === match.sku && l.synced === online);
      if (existing) {
        return prev.map(l => l.lineId === existing.lineId ? { ...l, qty: l.qty + 1 } : l);
      }
      return [...prev, { ...match, qty: 1, lineId: 'L' + Date.now(), synced: online }];
    });
    setQuery('');
  }

  function changeQty(lineId, delta) {
    setCart(prev => prev
      .map(l => l.lineId === lineId ? { ...l, qty: Math.max(0, l.qty + delta) } : l)
      .filter(l => l.qty > 0));
  }
  function removeLine(lineId) {
    setCart(prev => prev.filter(l => l.lineId !== lineId));
  }

  const change = Math.max(0, (parseFloat(cashTendered) || 0) - totals.total);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1.55fr) minmax(380px, 1fr)',
      gap: 14,
      padding: 14,
      height: '100%',
      minHeight: 0,
    }}>
      {/* LEFT: search + cart */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0, minWidth: 0 }}>
        {/* Scan bar */}
        <form onSubmit={handleSearchSubmit} style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 16px',
          background: 'rgba(8,24,38,0.7)',
          border: '1.5px solid rgba(0,199,242,0.35)',
          borderRadius: 12,
          boxShadow: '0 0 0 1px rgba(0,199,242,0.08), 0 0 20px rgba(0,199,242,0.08)',
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0, color: 'var(--accent-hi)' }}>
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
            }}
          />
          <span className="mono" style={{
            fontSize: 10, fontWeight: 600, letterSpacing: '0.18em',
            color: 'var(--ink-4)', textTransform: 'uppercase',
          }}>{t('searchHint')}</span>
          <span className="kbd-lg">/</span>
        </form>

        {/* Cart */}
        <div style={{
          flex: 1, minHeight: 0,
          display: 'flex', flexDirection: 'column',
          background: 'rgba(8,24,38,0.5)',
          border: '1px solid var(--line)',
          borderRadius: 12,
          overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 90px 90px 110px 32px',
            padding: '10px 14px',
            borderBottom: '1px solid var(--line)',
            background: 'rgba(255,255,255,0.02)',
          }}>
            <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
              {t('cart')} · <span className="ltr-nums">{cart.length}</span> {cart.length === 1 ? t('item') : t('items')}
            </div>
            {[t('qty'), t('price'), t('lineTotal'), ''].map((h, i) => (
              <div key={i} className="mono" style={{
                fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em',
                color: 'var(--ink-3)', textTransform: 'uppercase',
                textAlign: lang === 'ar' ? 'left' : 'right',
              }}>{h}</div>
            ))}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {cart.length === 0 && (
              <div style={{
                height: '100%', minHeight: 220,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10,
                padding: 24, color: 'var(--ink-3)',
              }}>
                <div style={{
                  width: 64, height: 64, borderRadius: '50%',
                  background: 'rgba(0,199,242,0.06)',
                  border: '1.5px dashed rgba(0,199,242,0.3)',
                  display: 'grid', placeItems: 'center',
                  animation: 'dpFade 600ms ease-out',
                }}>
                  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--accent-hi)' }}>
                    <path d="M3 5v14M6 5v14M9 5v14M12 5v14M15 5v14M18 5v14M21 5v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                </div>
                <div style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 20, color: 'var(--ink)' }}>{t('empty')}</div>
                <div style={{ fontSize: 13 }}>{t('emptyHint')}</div>
              </div>
            )}
            {cart.map((line, idx) => {
              const unsynced = !line.synced;
              return (
                <div key={line.lineId}
                  className={unsynced ? 'stripe-provisional' : ''}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 90px 90px 110px 32px',
                    alignItems: 'center',
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
                  <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3, paddingInlineStart: unsynced ? 8 : 0 }}>
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
                  <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', display: 'flex', justifyContent: lang==='ar' ? 'flex-start' : 'flex-end', alignItems:'center', gap: 4 }}>
                    <button
                      onClick={() => changeQty(line.lineId, -1)}
                      aria-label="decrease"
                      style={{ width: 22, height: 22, borderRadius: 5, background: 'rgba(184,192,204,0.08)', border: '1px solid var(--line)', color: 'var(--ink-2)', fontSize: 14, lineHeight: 1 }}
                    >−</button>
                    <span style={{ minWidth: 22, textAlign: 'center', fontSize: 14, fontWeight: 600 }}>{line.qty}</span>
                    <button
                      onClick={() => changeQty(line.lineId, +1)}
                      aria-label="increase"
                      style={{ width: 22, height: 22, borderRadius: 5, background: 'rgba(0,199,242,0.1)', border: '1px solid rgba(0,199,242,0.3)', color: 'var(--accent-hi)', fontSize: 14, lineHeight: 1 }}
                    >+</button>
                  </div>
                  <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 13, color: 'var(--ink-2)' }}>
                    {fmtEGP(line.price)}
                  </div>
                  <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 14, fontWeight: 600 }}>
                    {fmtEGP(line.price * line.qty)}
                  </div>
                  <button onClick={() => removeLine(line.lineId)} aria-label="remove"
                    style={{ width: 24, height: 24, marginInlineStart: 'auto', color: 'var(--ink-4)', borderRadius: 5, fontSize: 14 }}
                    onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                    onMouseLeave={e => e.currentTarget.style.color = 'var(--ink-4)'}
                  >×</button>
                </div>
              );
            })}
          </div>

          {/* Totals ribbon */}
          <div style={{
            padding: '14px 18px',
            borderTop: '1px solid var(--line-strong)',
            background: 'linear-gradient(180deg, rgba(22,52,82,0.4), rgba(8,24,38,0.6))',
            display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1.4fr', gap: 16,
          }}>
            <TotalsCell label={t('subtotal')} value={fmtEGP(totals.subtotal)} />
            <TotalsCell label={t('vat')} value={fmtEGP(totals.vat)} />
            <TotalsCell label={t('discount')} value={totals.discount ? '−' + fmtEGP(totals.discount) : fmtEGP(0)} tone={totals.discount ? 'green' : 'muted'} />
            <TotalsCell label={t('total')} value={fmtEGP(totals.total)} big />
          </div>
        </div>
      </section>

      {/* RIGHT: keypad + payment */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
        <Keypad t={t} lastKey={lastKey} />
        <PaymentPanel
          lang={lang} t={t} totals={totals}
          activePayment={activePayment} setActivePayment={setActivePayment}
          voucher={voucher} promo={promo} insurance={insurance}
          onOpenVoucher={onOpenVoucher} onOpenPromo={onOpenPromo} onOpenInsurance={onOpenInsurance}
          cashTendered={cashTendered} setCashTendered={setCashTendered} change={change}
          onCharge={onCharge}
          cart={cart}
        />
      </section>
    </div>
  );
}

function TotalsCell({ label, value, big, tone }) {
  const color = tone === 'green' ? 'var(--green)' : tone === 'muted' ? 'var(--ink-4)' : 'var(--ink)';
  return (
    <div>
      <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 4 }}>
        {label}
      </div>
      <div className="mono ltr-nums" style={{
        fontSize: big ? 26 : 15, fontWeight: big ? 700 : 600,
        color: big ? 'var(--accent-hi)' : color,
        textShadow: big ? '0 0 14px rgba(0,199,242,0.35)' : 'none',
      }}>{value}</div>
    </div>
  );
}

function Keypad({ t, lastKey }) {
  const keys = [
    ['7','8','9'],
    ['4','5','6'],
    ['1','2','3'],
    ['0','.','⌫'],
  ];
  const [pressed, setPressed] = useStateT(null);
  useEffectT(() => {
    if (!lastKey) return;
    setPressed(lastKey);
    const t = setTimeout(() => setPressed(null), 180);
    return () => clearTimeout(t);
  }, [lastKey]);

  return (
    <div style={{
      background: 'rgba(8,24,38,0.5)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      padding: 12,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
          {t('keypad')}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono" style={{ fontSize: 9.5, color: 'var(--ink-4)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>{t('lastKey')}</span>
          <span className="kbd-lg" style={{ minWidth: 28, textAlign: 'center', display: 'inline-block' }}>{lastKey || '—'}</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
        {keys.flat().map((k) => {
          const isPressed = pressed === k;
          return (
            <div key={k} aria-hidden="true" style={{
              height: 52,
              display: 'grid', placeItems: 'center',
              background: isPressed ? 'rgba(0,199,242,0.35)' : 'rgba(255,255,255,0.025)',
              border: '1px solid',
              borderColor: isPressed ? 'rgba(0,199,242,0.6)' : 'var(--line)',
              borderRadius: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 22, fontWeight: 600,
              color: isPressed ? '#fff' : 'var(--ink-2)',
              transition: 'all 120ms ease',
              animation: isPressed ? 'dpKeyPulse 400ms ease-out' : 'none',
            }}>{k}</div>
          );
        })}
      </div>
      {/* Shortcut legend */}
      <div style={{ marginTop: 4, paddingTop: 10, borderTop: '1px dashed var(--line)' }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 8 }}>
          {t('shortcuts')}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 5, fontSize: 11, color: 'var(--ink-2)' }}>
          {[
            ['F1', t('terminal')],
            ['F2', t('syncIssues')],
            ['F3', t('shiftClose')],
            ['F5', t('promotions')],
            ['F7', t('voucher')],
            ['F9', t('cash')],
            ['F10', t('card')],
            ['F11', t('insurance')],
            ['Enter', t('charge')],
            ['/', t('scanPrompt').split(' ')[0]],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="kbd" style={{ minWidth: 34, textAlign: 'center' }}>{k}</span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PaymentPanel({ lang, t, totals, activePayment, setActivePayment, voucher, promo, insurance, onOpenVoucher, onOpenPromo, onOpenInsurance, cashTendered, setCashTendered, change, onCharge, cart }) {
  const methods = [
    { id: 'cash', label: t('cash'), kbd: 'F9', color: 'var(--green)', icon: 'M3 7h18v10H3z M3 12h18' },
    { id: 'card', label: t('card'), kbd: 'F10', color: 'var(--accent)', icon: 'M2 7h20v10H2z M2 11h20' },
    { id: 'insurance', label: t('insurance'), kbd: 'F11', color: 'var(--purple)', icon: 'M12 2 L20 6 V12 A8 8 0 0 1 12 22 A8 8 0 0 1 4 12 V6 Z' },
    { id: 'voucher', label: t('voucher'), kbd: 'F12', color: 'var(--amber)', icon: 'M4 7h16v10H4z M8 7v10 M16 7v10' },
  ];

  return (
    <div style={{
      flex: 1, minHeight: 0,
      background: 'linear-gradient(180deg, rgba(22,52,82,0.4), rgba(8,24,38,0.6))',
      border: '1px solid var(--line-strong)',
      borderRadius: 12,
      padding: 14,
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
          {t('payment')}
        </div>
        <button onClick={onOpenPromo} style={{
          display: 'flex', alignItems: 'center', gap: 6,
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

      {/* 2x2 grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
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
              aria-label={`${m.label} ${m.kbd}`}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8,
                padding: '14px 14px',
                background: active ? `color-mix(in oklab, ${m.color} 18%, transparent)` : 'rgba(8,24,38,0.5)',
                border: '1.5px solid',
                borderColor: active ? m.color : 'var(--line)',
                borderRadius: 10,
                textAlign: 'start',
                transition: 'all 140ms ease',
                position: 'relative',
                boxShadow: active ? `0 0 0 1px ${m.color}33, 0 0 20px ${m.color}33` : 'none',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? m.color : 'var(--ink-2)'} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d={m.icon} />
                </svg>
                <span className="kbd" style={{
                  background: active ? `${m.color}22` : 'rgba(184,192,204,0.08)',
                  borderColor: active ? `${m.color}55` : 'var(--line)',
                  color: active ? m.color : 'var(--ink-3)',
                }}>{m.kbd}</span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: active ? 'var(--ink)' : 'var(--ink-2)' }}>{m.label}</div>
              {hasValue && (
                <div className="mono" style={{
                  fontSize: 10, fontWeight: 600, letterSpacing: '0.1em',
                  padding: '2px 6px', borderRadius: 4,
                  background: `${m.color}22`, color: m.color,
                  textTransform: 'uppercase',
                }}>
                  {m.id === 'voucher' ? voucher : insurance?.name}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Active method details */}
      <div style={{
        background: 'rgba(8,24,38,0.5)',
        border: '1px solid var(--line)',
        borderRadius: 10,
        padding: 12,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {activePayment === 'cash' && (
          <>
            <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
              {t('tenderedCash')}
            </div>
            <input
              value={cashTendered}
              onChange={e => setCashTendered(e.target.value.replace(/[^0-9.]/g, ''))}
              placeholder="0.00"
              className="mono ltr-nums"
              aria-label={t('tenderedCash')}
              style={{
                fontSize: 24, fontWeight: 700,
                padding: '10px 12px',
                background: 'rgba(0,0,0,0.25)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                textAlign: lang === 'ar' ? 'right' : 'left',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 6 }}>
              <span className="mono" style={{ fontSize: 10, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>{t('change')}</span>
              <span className="mono ltr-nums" style={{ fontSize: 20, fontWeight: 700, color: change > 0 ? 'var(--green)' : 'var(--ink-2)' }}>
                {fmtEGP(change)}
              </span>
            </div>
          </>
        )}
        {activePayment === 'card' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '4px 0' }}>
            <div style={{ width: 38, height: 38, borderRadius: 8, background: 'rgba(0,199,242,0.12)', border: '1px solid rgba(0,199,242,0.35)', display: 'grid', placeItems: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-hi)" strokeWidth="1.8" aria-hidden="true">
                <rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" />
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{lang==='ar' ? 'مرري البطاقة على الجهاز' : 'Tap or swipe card on pinpad'}</div>
              <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)', marginTop: 2 }}>Ingenico iCT220 · COM3</div>
            </div>
          </div>
        )}
        {activePayment === 'insurance' && insurance && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: 'var(--ink-3)' }}>{t('coveredPortion')} ({insurance.coverage}%)</span>
              <span className="mono ltr-nums" style={{ color: 'var(--purple)', fontWeight: 600 }}>{fmtEGP(totals.insurerPays)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, paddingTop: 6, borderTop: '1px dashed var(--line)' }}>
              <span>{t('patientPortion')}</span>
              <span className="mono ltr-nums" style={{ color: 'var(--accent-hi)', fontSize: 18 }}>{fmtEGP(totals.patientPays)}</span>
            </div>
          </>
        )}
        {activePayment === 'insurance' && !insurance && (
          <div style={{ color: 'var(--ink-3)', fontSize: 12.5, padding: '4px 0' }}>{lang==='ar' ? 'اضغطي F11 لاختيار شركة التأمين' : 'Press F11 to select insurer'}</div>
        )}
        {activePayment === 'voucher' && voucher && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems:'center' }}>
            <div>
              <div className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--amber)', textTransform: 'uppercase' }}>{t('voucherValid')}</div>
              <div className="mono ltr-nums" style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{voucher}</div>
            </div>
            <div className="mono ltr-nums" style={{ fontSize: 18, fontWeight: 700, color: 'var(--amber)' }}>−{fmtEGP(totals.discount)}</div>
          </div>
        )}
        {activePayment === 'voucher' && !voucher && (
          <div style={{ color: 'var(--ink-3)', fontSize: 12.5, padding: '4px 0' }}>{lang==='ar' ? 'اضغطي F12 لإدخال رمز القسيمة' : 'Press F12 to enter voucher code'}</div>
        )}
      </div>

      {/* Charge button */}
      <button
        onClick={onCharge}
        disabled={!cart.length}
        aria-label={`${t('charge')} Enter`}
        style={{
          marginTop: 'auto',
          padding: '18px 20px',
          borderRadius: 12,
          background: cart.length
            ? 'linear-gradient(180deg, #00c7f2, #00a6cc)'
            : 'rgba(255,255,255,0.04)',
          color: cart.length ? '#021018' : 'var(--ink-4)',
          fontSize: 20, fontWeight: 700,
          boxShadow: cart.length ? '0 0 20px rgba(0,199,242,0.4), 0 6px 16px rgba(0,199,242,0.25)' : 'none',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
          cursor: cart.length ? 'pointer' : 'not-allowed',
          border: cart.length ? 'none' : '1px solid var(--line)',
          transition: 'all 200ms ease',
        }}
      >
        <span>{t('charge')}</span>
        <span className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700 }}>{fmtEGP(totals.total)}</span>
        <span className="kbd" style={{ background: 'rgba(2,16,24,0.2)', borderColor: 'rgba(2,16,24,0.3)', color: '#021018' }}>Enter</span>
      </button>
    </div>
  );
}

Object.assign(window, { Terminal });
