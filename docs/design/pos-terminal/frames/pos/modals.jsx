// Three modals: voucher, promotions, insurance. All match the bottom-sheet pattern.
// Close with Esc. First input autofocuses.

const { useState: useStateM, useEffect: useEffectM, useRef: useRefM } = React;

function ModalShell({ open, onClose, title, sub, children, width = 520, accent = 'var(--accent)', badge, icon }) {
  useEffectM(() => {
    if (!open) return;
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      role="dialog" aria-modal="true" aria-label={title}
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        display: 'grid', placeItems: 'center',
        background: 'rgba(5,14,23,0.75)',
        backdropFilter: 'blur(8px)',
        animation: 'dpFade 200ms ease-out',
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width, maxWidth: '92vw', maxHeight: '88vh',
          background: 'linear-gradient(180deg, rgba(22,52,82,0.98), rgba(8,24,38,0.98))',
          border: '1px solid var(--line-strong)',
          borderRadius: 18,
          boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px ${accent}22`,
          padding: 22,
          display: 'flex', flexDirection: 'column', gap: 14,
          animation: 'dpSlideUp 280ms cubic-bezier(.2,.9,.3,1.1)',
          overflow: 'hidden',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 11,
            background: `color-mix(in oklab, ${accent} 18%, transparent)`,
            border: `1px solid ${accent}`,
            display: 'grid', placeItems: 'center',
            flexShrink: 0,
            color: accent,
          }}>
            {icon}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            {badge && (
              <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.22em', color: accent, textTransform: 'uppercase', marginBottom: 4 }}>
                {badge}
              </div>
            )}
            <div style={{ fontFamily: 'Fraunces, serif', fontSize: 20, fontWeight: 500, letterSpacing: '-0.01em' }}>
              {title}
            </div>
            {sub && <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 3 }}>{sub}</div>}
          </div>
          <button onClick={onClose} aria-label="Close (Esc)" style={{
            padding: '4px 10px', borderRadius: 6, border: '1px solid var(--line)',
            color: 'var(--ink-3)', fontSize: 11,
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <span>Esc</span>
          </button>
        </div>
        <div style={{ overflowY: 'auto', minHeight: 0 }}>{children}</div>
      </div>
    </div>
  );
}

function VoucherModal({ open, onClose, lang, t, onApply, totals }) {
  const [code, setCode] = useStateM('');
  const [status, setStatus] = useStateM('idle'); // idle | valid | invalid
  const [match, setMatch] = useStateM(null);
  const inputRef = useRefM(null);
  useEffectM(() => { if (open) { setCode(''); setStatus('idle'); setMatch(null); setTimeout(() => inputRef.current?.focus(), 80); } }, [open]);

  function validate() {
    const c = code.trim().toUpperCase();
    const v = VOUCHERS[c];
    if (v) { setStatus('valid'); setMatch({ code: c, ...v }); }
    else { setStatus('invalid'); setMatch(null); }
  }

  const discountEst = match ? (match.type === 'PCT' ? totals.subtotalIncl * (match.value/100) : match.value) : 0;

  return (
    <ModalShell open={open} onClose={onClose} title={t('voucherTitle')} sub={t('voucherSub')}
      accent="var(--amber)" badge={t('voucher')}
      icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M4 7h16v10H4z M8 7v10 M16 7v10" /></svg>}
    >
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          ref={inputRef}
          value={code}
          onChange={e => { setCode(e.target.value.toUpperCase()); setStatus('idle'); }}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); validate(); } }}
          placeholder="RAMADAN25"
          aria-label={t('voucherCode')}
          className="mono"
          style={{
            flex: 1,
            fontSize: 18, fontWeight: 600,
            letterSpacing: '0.08em',
            padding: '14px 14px',
            background: 'rgba(0,0,0,0.3)',
            border: '1.5px solid',
            borderColor: status==='invalid' ? 'var(--red)' : status==='valid' ? 'var(--green)' : 'var(--line)',
            borderRadius: 10,
            direction: 'ltr',
          }}
        />
        <button onClick={validate} style={{
          padding: '0 18px', borderRadius: 10,
          background: 'rgba(255,171,61,0.18)',
          border: '1px solid var(--amber)',
          color: 'var(--amber)',
          fontSize: 13, fontWeight: 600,
        }}>{t('validate')}</button>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
        {['RAMADAN25','NEW100','LOYALTY10'].map(c => (
          <button key={c} onClick={() => { setCode(c); setStatus('idle'); }}
            className="mono"
            style={{
              fontSize: 10, padding: '3px 8px', borderRadius: 5,
              background: 'rgba(184,192,204,0.06)', border: '1px solid var(--line)',
              color: 'var(--ink-3)', letterSpacing: '0.08em',
            }}>{c}</button>
        ))}
      </div>
      {status === 'invalid' && (
        <div style={{
          marginTop: 14, padding: 12, borderRadius: 10,
          background: 'rgba(255,123,123,0.08)',
          border: '1px solid rgba(255,123,123,0.3)',
          color: 'var(--red)', fontSize: 12.5, fontWeight: 500,
        }}>
          {lang==='ar' ? 'رمز القسيمة غير صالح أو منتهي الصلاحية.' : 'Voucher code invalid or expired.'}
        </div>
      )}
      {status === 'valid' && match && (
        <div style={{
          marginTop: 14,
          background: 'rgba(29,212,139,0.06)',
          border: '1px solid rgba(29,212,139,0.35)',
          borderRadius: 12,
          padding: 14,
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--green)' }} aria-hidden="true" />
            <span className="mono" style={{ fontSize: 10, letterSpacing: '0.2em', color: 'var(--green)', textTransform: 'uppercase', fontWeight: 700 }}>
              {t('voucherValid')}
            </span>
          </div>
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: 17, fontStyle: 'italic', color: 'var(--ink)' }}>
            {match.label[lang]}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: 8, borderTop: '1px dashed var(--line)' }}>
            <span className="mono" style={{ fontSize: 10, letterSpacing: '0.18em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
              {t('voucherOff')}
            </span>
            <span className="mono ltr-nums" style={{ fontSize: 24, fontWeight: 700, color: 'var(--amber)' }}>
              −{fmtEGP(discountEst)} <span style={{ fontSize: 12, color: 'var(--ink-3)', fontWeight: 500 }}>{t('egp')}</span>
            </span>
          </div>
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={onClose} style={{
          flex: 1, padding: '12px', borderRadius: 10,
          background: 'transparent', border: '1px solid var(--line)',
          color: 'var(--ink-2)', fontSize: 13, fontWeight: 600,
        }}>{t('voucherCancel')}</button>
        <button
          onClick={() => { if (match) { onApply(match.code); onClose(); } }}
          disabled={!match}
          style={{
            flex: 2, padding: '12px', borderRadius: 10,
            background: match ? 'linear-gradient(180deg, var(--amber), #e08f20)' : 'rgba(255,255,255,0.04)',
            color: match ? '#1a0c00' : 'var(--ink-4)',
            fontSize: 13, fontWeight: 700,
            border: match ? 'none' : '1px solid var(--line)',
            cursor: match ? 'pointer' : 'not-allowed',
            display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
          }}>
          <span>{t('voucherConfirm')}</span>
          <span className="kbd" style={{ background: 'rgba(26,12,0,0.18)', borderColor: 'rgba(26,12,0,0.3)', color: '#1a0c00' }}>Enter</span>
        </button>
      </div>
    </ModalShell>
  );
}

function PromotionsModal({ open, onClose, lang, t, onApply }) {
  const promos = PROMOS[lang];
  const [selected, setSelected] = useStateM(0);
  useEffectM(() => { if (open) setSelected(0); }, [open]);

  useEffectM(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(promos.length-1, s+1)); }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setSelected(s => Math.max(0, s-1)); }
      if (/^[1-9]$/.test(e.key)) {
        const i = parseInt(e.key,10) - 1;
        if (i < promos.length) setSelected(i);
      }
      if (e.key === 'Enter') { e.preventDefault(); onApply(promos[selected]); onClose(); }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, selected, promos, onApply, onClose]);

  return (
    <ModalShell open={open} onClose={onClose} title={t('promoTitle')} sub={t('promoSub')} width={600}
      accent="var(--purple)" badge={t('promotions')}
      icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M20 12 L12 20 L4 12 L12 4 Z M8 12 L16 12 M12 8 L12 16" /></svg>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {promos.map((p, i) => {
          const active = i === selected;
          return (
            <button key={p.id}
              onClick={() => setSelected(i)}
              onDoubleClick={() => { onApply(p); onClose(); }}
              aria-pressed={active}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 14px', borderRadius: 12,
                background: active ? 'rgba(116,103,248,0.1)' : 'rgba(8,24,38,0.5)',
                border: '1.5px solid',
                borderColor: active ? 'var(--purple)' : 'var(--line)',
                textAlign: 'start', cursor: 'pointer',
                boxShadow: active ? '0 0 20px rgba(116,103,248,0.2)' : 'none',
                transition: 'all 140ms ease',
                position: 'relative',
              }}>
              <div style={{
                width: 3, alignSelf: 'stretch',
                background: 'var(--purple)',
                borderRadius: 2,
                position: 'absolute',
                [lang==='ar' ? 'right' : 'left']: 0,
                top: 8, bottom: 8,
                opacity: active ? 1 : 0.4,
              }} />
              <div style={{ width: 28, height: 28, borderRadius: 6, background: 'rgba(116,103,248,0.15)', color: 'var(--purple)', display: 'grid', placeItems: 'center', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700 }}>
                {i+1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.18em', color: 'var(--purple)', textTransform: 'uppercase' }}>
                    {p.type}
                  </span>
                  <span className="mono" style={{ fontSize: 9, letterSpacing: '0.18em', color: 'var(--green)', textTransform: 'uppercase', padding: '1px 5px', borderRadius: 3, background: 'rgba(29,212,139,0.12)', border: '1px solid rgba(29,212,139,0.3)' }}>
                    {t('promoEligible')}
                  </span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{p.title}</div>
                <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 2 }}>{p.sub}</div>
              </div>
              <div style={{ textAlign: lang==='ar' ? 'left' : 'right' }}>
                <div className="mono" style={{ fontSize: 9, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>{t('promoSavings')}</div>
                <div className="mono ltr-nums" style={{ fontSize: 18, fontWeight: 700, color: 'var(--purple)' }}>−{fmtEGP(p.savings)}</div>
              </div>
            </button>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button onClick={onClose} style={{
          flex: 1, padding: '12px', borderRadius: 10,
          background: 'transparent', border: '1px solid var(--line)',
          color: 'var(--ink-2)', fontSize: 13, fontWeight: 600,
        }}>{t('cancel')}</button>
        <button onClick={() => { onApply(promos[selected]); onClose(); }}
          style={{
            flex: 2, padding: '12px', borderRadius: 10,
            background: 'linear-gradient(180deg, var(--purple), #5a4fe0)',
            color: '#fff', fontSize: 13, fontWeight: 700,
            display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
          }}>
          <span>{t('promoApply')}</span>
          <span className="kbd" style={{ background: 'rgba(0,0,0,0.25)', borderColor: 'rgba(0,0,0,0.3)', color: '#fff' }}>Enter</span>
        </button>
      </div>
    </ModalShell>
  );
}

function InsuranceModal({ open, onClose, lang, t, onApply, total }) {
  const insurers = INSURERS[lang];
  const [selected, setSelected] = useStateM(0);
  const [policy, setPolicy] = useStateM('P-2026-');
  const [coverage, setCoverage] = useStateM(insurers[0].coverage);
  const [preauth, setPreauth] = useStateM('');
  const inputRef = useRefM(null);
  useEffectM(() => {
    if (open) {
      setSelected(0); setPolicy('P-2026-'); setCoverage(insurers[0].coverage); setPreauth('');
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  useEffectM(() => { setCoverage(insurers[selected].coverage); }, [selected]);

  const insurerPays = total * coverage/100;
  const patientPays = total - insurerPays;

  return (
    <ModalShell open={open} onClose={onClose} title={t('insTitle')} sub=""
      accent="var(--purple)" badge={t('insurance')} width={560}
      icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M12 2 L20 6 V12 A8 8 0 0 1 12 22 A8 8 0 0 1 4 12 V6 Z M9 12 L11 14 L15 10" /></svg>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Insurer grid */}
        <div>
          <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', marginBottom: 7 }}>
            {t('insurer')}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {insurers.map((ins, i) => {
              const active = i === selected;
              return (
                <button key={ins.id} onClick={() => setSelected(i)} aria-pressed={active}
                  style={{
                    padding: '10px 12px', borderRadius: 8,
                    background: active ? 'rgba(116,103,248,0.15)' : 'rgba(8,24,38,0.5)',
                    border: '1.5px solid', borderColor: active ? 'var(--purple)' : 'var(--line)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    fontSize: 12.5, fontWeight: 600, textAlign: 'start',
                  }}>
                  <span>{ins.name}</span>
                  <span className="mono ltr-nums" style={{ fontSize: 10, color: active ? 'var(--purple)' : 'var(--ink-3)', fontWeight: 700 }}>{ins.coverage}%</span>
                </button>
              );
            })}
          </div>
        </div>
        {/* Policy + pre-auth */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Field label={t('policy')}>
            <input ref={inputRef} value={policy} onChange={e => setPolicy(e.target.value)} className="mono" style={fieldInput} />
          </Field>
          <Field label={t('preauth')}>
            <input value={preauth} onChange={e => setPreauth(e.target.value)} placeholder="—" className="mono" style={fieldInput} />
          </Field>
        </div>
        {/* Coverage slider */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
              {t('coverage')}
            </span>
            <span className="mono ltr-nums" style={{ fontSize: 14, fontWeight: 700, color: 'var(--purple)' }}>{coverage}%</span>
          </div>
          <input type="range" min="0" max="100" step="5" value={coverage} onChange={e => setCoverage(parseInt(e.target.value))}
            style={{ width: '100%', accentColor: '#7467f8' }} />
        </div>
        {/* Computed portions */}
        <div style={{
          background: 'rgba(116,103,248,0.06)',
          border: '1px solid rgba(116,103,248,0.3)',
          borderRadius: 10,
          padding: 14,
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14,
        }}>
          <div>
            <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--purple)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 4 }}>
              {t('coveredPortion')}
            </div>
            <div className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700, color: 'var(--purple)' }}>{fmtEGP(insurerPays)}</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--accent-hi)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 4 }}>
              {t('patientPortion')}
            </div>
            <div className="mono ltr-nums" style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-hi)', textShadow: '0 0 10px rgba(0,199,242,0.4)' }}>{fmtEGP(patientPays)}</div>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={onClose} style={{
          flex: 1, padding: '12px', borderRadius: 10,
          background: 'transparent', border: '1px solid var(--line)',
          color: 'var(--ink-2)', fontSize: 13, fontWeight: 600,
        }}>{t('cancel')}</button>
        <button
          onClick={() => { onApply({ ...insurers[selected], policy, coverage, preauth }); onClose(); }}
          style={{
            flex: 2, padding: '12px', borderRadius: 10,
            background: 'linear-gradient(180deg, var(--purple), #5a4fe0)',
            color: '#fff', fontSize: 13, fontWeight: 700,
            display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
          }}>
          <span>{t('insConfirm')}</span>
          <span className="kbd" style={{ background: 'rgba(0,0,0,0.25)', borderColor: 'rgba(0,0,0,0.3)', color: '#fff' }}>Enter</span>
        </button>
      </div>
    </ModalShell>
  );
}

const fieldInput = {
  width: '100%',
  fontSize: 14, fontWeight: 500,
  padding: '10px 10px',
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid var(--line)',
  borderRadius: 8,
  letterSpacing: '0.04em',
};

function Field({ label, children }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
        {label}
      </span>
      {children}
    </label>
  );
}

// Success toast after charge
function Toast({ message, onDone }) {
  useEffectM(() => {
    const t = setTimeout(onDone, 2400);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div role="status" aria-live="polite" style={{
      position: 'fixed', bottom: 26, left: '50%', transform: 'translateX(-50%)',
      background: 'rgba(29,212,139,0.15)',
      border: '1px solid rgba(29,212,139,0.5)',
      color: '#c0f5dc',
      padding: '12px 20px', borderRadius: 999,
      display: 'flex', alignItems: 'center', gap: 10,
      boxShadow: '0 10px 30px rgba(29,212,139,0.2)',
      animation: 'dpSlideUp 260ms cubic-bezier(.2,.9,.3,1.1)',
      zIndex: 300,
      fontSize: 13, fontWeight: 600,
    }}>
      <span style={{ width: 18, height: 18, borderRadius: '50%', background: 'var(--green)', display: 'grid', placeItems: 'center', color: '#021810' }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12 L10 17 L19 7" /></svg>
      </span>
      {message}
    </div>
  );
}

Object.assign(window, { VoucherModal, PromotionsModal, InsuranceModal, Toast, ModalShell });
