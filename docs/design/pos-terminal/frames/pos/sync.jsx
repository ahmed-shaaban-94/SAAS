// Sync Issues screen + 3 action modals (retry-override, record-loss, corrective-void)

const { useState: useStateS, useEffect: useEffectS, useRef: useRefS } = React;

function SyncIssues({ lang, t }) {
  const [issues, setIssues] = useStateS(SYNC_ISSUES[lang]);
  const [action, setAction] = useStateS(null); // { type, issue }
  const [selectedIdx, setSelectedIdx] = useStateS(0);

  useEffectS(() => { setIssues(SYNC_ISSUES[lang]); }, [lang]);

  useEffectS(() => {
    function onKey(e) {
      if (action) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(issues.length-1, i+1)); }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setSelectedIdx(i => Math.max(0, i-1)); }
      if (e.key.toLowerCase() === 'o' && issues[selectedIdx]) setAction({ type: 'override', issue: issues[selectedIdx] });
      if (e.key.toLowerCase() === 'l' && issues[selectedIdx]) setAction({ type: 'loss', issue: issues[selectedIdx] });
      if (e.key.toLowerCase() === 'r' && issues[selectedIdx]) setAction({ type: 'void', issue: issues[selectedIdx] });
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [issues, selectedIdx, action]);

  function resolve(issueId) {
    setIssues(prev => prev.filter(i => i.id !== issueId));
    setAction(null);
  }

  const reasonColors = {
    PRICE_MISMATCH: 'var(--amber)',
    STOCK_NEGATIVE: 'var(--red)',
    EXPIRED_VOUCHER: 'var(--amber)',
    INSURANCE_REJECT: 'var(--red)',
    DUPLICATE_BARCODE: 'var(--purple)',
  };

  return (
    <div style={{ padding: 18, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 14 }}>
        <div>
          <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--amber)', textTransform: 'uppercase', marginBottom: 6 }}>
            ● {t('syncTitle')}
          </div>
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: 28, fontWeight: 500, letterSpacing: '-0.01em', marginBottom: 4 }}>
            {lang==='ar' ? '٥ معاملات تحتاج قراراً' : '5 transactions need a decision'}
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', maxWidth: 620 }}>
            {t('syncSub')}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 11 }}>
          <LegendChip kbd="↑↓" label={lang==='ar' ? 'تنقل' : 'Navigate'} />
          <LegendChip kbd="O" label={t('override')} color="var(--amber)" />
          <LegendChip kbd="L" label={t('loss')} color="var(--red)" />
          <LegendChip kbd="R" label={t('void')} color="var(--purple)" />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {issues.map((is, i) => {
          const selected = i === selectedIdx;
          const c = reasonColors[is.reasonTag] || 'var(--ink-3)';
          return (
            <article key={is.id}
              onClick={() => setSelectedIdx(i)}
              tabIndex={0}
              aria-label={`${is.id} ${is.reason}`}
              style={{
                position: 'relative',
                padding: '16px 18px 16px 22px',
                background: selected ? 'rgba(22,52,82,0.55)' : 'rgba(8,24,38,0.5)',
                border: '1px solid',
                borderColor: selected ? 'var(--line-strong)' : 'var(--line)',
                borderRadius: 12,
                display: 'grid',
                gridTemplateColumns: 'auto 1fr auto auto',
                gap: 18,
                alignItems: 'center',
                cursor: 'pointer',
                boxShadow: selected ? '0 0 0 1px rgba(0,199,242,0.2)' : 'none',
                transition: 'all 140ms ease',
                animation: 'dpRowEnter 260ms ease-out',
              }}>
              <div style={{
                position: 'absolute',
                [lang==='ar' ? 'right' : 'left']: 0, top: 8, bottom: 8, width: 3,
                background: c, borderRadius: 2,
              }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 180 }}>
                <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.18em', color: c, textTransform: 'uppercase' }}>
                  {is.reasonTag.replace(/_/g, ' ')}
                </span>
                <span className="mono ltr-nums" style={{ fontSize: 11, color: 'var(--ink-4)' }}>{is.id}</span>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 3 }}>{is.reason}</div>
                <div style={{ display: 'flex', gap: 14, fontSize: 11.5, color: 'var(--ink-3)' }}>
                  <span>{t('cashier')}: <span className="mono" style={{ color: 'var(--ink-2)' }}>{is.cashier}</span></span>
                  <span>{lang==='ar' ? 'بنود' : 'Lines'}: <span className="mono ltr-nums" style={{ color: 'var(--ink-2)' }}>{is.lines}</span></span>
                  <span>{t('rejectedAt')}: <span className="mono ltr-nums" style={{ color: 'var(--amber)' }}>{is.time}</span></span>
                </div>
              </div>
              <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right' }}>
                <div style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>{t('total')}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink)' }}>{fmtEGP(is.amount)}</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <ActionBtn color="var(--amber)" kbd="O" label={t('override')} onClick={(e) => { e.stopPropagation(); setAction({ type: 'override', issue: is }); }} />
                <ActionBtn color="var(--red)" kbd="L" label={t('loss')} onClick={(e) => { e.stopPropagation(); setAction({ type: 'loss', issue: is }); }} />
                <ActionBtn color="var(--purple)" kbd="R" label={t('void')} onClick={(e) => { e.stopPropagation(); setAction({ type: 'void', issue: is }); }} />
              </div>
            </article>
          );
        })}
        {issues.length === 0 && (
          <div style={{
            padding: '40px 24px', textAlign: 'center',
            background: 'rgba(29,212,139,0.06)',
            border: '1px dashed rgba(29,212,139,0.35)',
            borderRadius: 12,
            color: 'var(--green)', fontSize: 14,
          }}>
            {lang==='ar' ? '✓ كل المعاملات متزامنة' : '✓ All transactions synced'}
          </div>
        )}
      </div>

      <SyncActionModal action={action} onClose={() => setAction(null)} onResolve={resolve} lang={lang} t={t} />
    </div>
  );
}

function LegendChip({ kbd, label, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: color || 'var(--ink-3)' }}>
      <span className="kbd" style={{ background: color ? `${color}1a` : 'rgba(184,192,204,0.08)', borderColor: color ? `${color}55` : 'var(--line)', color: color || 'var(--ink-3)' }}>{kbd}</span>
      <span>{label}</span>
    </div>
  );
}

function ActionBtn({ color, kbd, label, onClick }) {
  return (
    <button onClick={onClick}
      aria-label={`${label} (${kbd})`}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
        padding: '8px 12px', borderRadius: 7,
        background: `${color}12`, border: `1px solid ${color}50`,
        color, fontSize: 11.5, fontWeight: 600, minWidth: 64,
        cursor: 'pointer',
      }}>
      <span>{label}</span>
      <span className="kbd" style={{ background: `${color}22`, borderColor: `${color}55`, color, fontSize: 9 }}>{kbd}</span>
    </button>
  );
}

function SyncActionModal({ action, onClose, onResolve, lang, t }) {
  const [approvalCode, setApprovalCode] = useStateS('');
  const [reason, setReason] = useStateS('');
  useEffectS(() => { setApprovalCode(''); setReason(''); }, [action]);
  if (!action) return null;
  const { type, issue } = action;
  const config = {
    override: { color: 'var(--amber)', title: t('retryOverride'), requiresCode: true, placeholder: lang==='ar' ? 'كود ٦ أرقام من المشرف' : '6-digit supervisor code' },
    loss:     { color: 'var(--red)',   title: t('recordLoss'),    requiresCode: false, reasonLabel: t('lossReason'), reasonPh: lang==='ar' ? 'مثال: كسر في العبوة' : 'e.g. packaging damage' },
    void:     { color: 'var(--purple)',title: t('correctiveVoid'),requiresCode: true, reasonLabel: t('voidReason'), reasonPh: lang==='ar' ? 'مثال: تصحيح سعر بعد اعتماد المشرف' : 'e.g. price correction after supervisor approval' },
  }[type];

  const canConfirm = (config.requiresCode ? approvalCode.length >= 4 : true) && (type === 'override' || reason.trim().length >= 3);

  return (
    <ModalShell open={!!action} onClose={onClose} title={config.title} accent={config.color} badge={issue.id}
      sub={issue.reason} width={520}
      icon={
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          {type==='override' && <path d="M3 12 A9 9 0 1 1 12 21 M3 12 L3 6 M3 12 L9 12" />}
          {type==='loss' && <path d="M12 2 L22 20 L2 20 Z M12 10 L12 15 M12 17.5 L12 18.5" />}
          {type==='void' && <path d="M6 6 L18 18 M18 6 L6 18" />}
        </svg>
      }>
      <div style={{
        padding: 12, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--line)', borderRadius: 10,
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 12,
      }}>
        <div><span style={{ color: 'var(--ink-3)' }}>{t('txnId')}</span><br/><span className="mono ltr-nums" style={{ fontWeight: 600 }}>{issue.id}</span></div>
        <div><span style={{ color: 'var(--ink-3)' }}>{t('total')}</span><br/><span className="mono ltr-nums" style={{ fontWeight: 600 }}>{fmtEGP(issue.amount)} <span style={{ color:'var(--ink-3)', fontWeight: 400 }}>{t('egp')}</span></span></div>
        <div><span style={{ color: 'var(--ink-3)' }}>{t('cashier')}</span><br/><span className="mono" style={{ fontWeight: 600 }}>{issue.cashier}</span></div>
        <div><span style={{ color: 'var(--ink-3)' }}>{t('rejectedAt')}</span><br/><span className="mono ltr-nums" style={{ fontWeight: 600, color: 'var(--amber)' }}>{issue.time}</span></div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
        {config.requiresCode && (
          <Field label={t('approvalCode')}>
            <input value={approvalCode} onChange={e => setApprovalCode(e.target.value.replace(/[^0-9]/g,''))} placeholder={config.placeholder}
              inputMode="numeric" autoFocus maxLength={6}
              className="mono ltr-nums"
              style={{ ...fieldInput, fontSize: 20, letterSpacing: '0.4em', textAlign: 'center' }}
            />
          </Field>
        )}
        {type !== 'override' && (
          <Field label={config.reasonLabel}>
            <textarea value={reason} onChange={e => setReason(e.target.value)} placeholder={config.reasonPh}
              rows={3}
              style={{ ...fieldInput, resize: 'vertical', minHeight: 64, fontFamily: 'inherit' }} />
          </Field>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={onClose} style={{
          flex: 1, padding: '12px', borderRadius: 10,
          background: 'transparent', border: '1px solid var(--line)',
          color: 'var(--ink-2)', fontSize: 13, fontWeight: 600,
        }}>{t('cancel')}</button>
        <button disabled={!canConfirm}
          onClick={() => onResolve(issue.id)}
          style={{
            flex: 2, padding: '12px', borderRadius: 10,
            background: canConfirm ? `linear-gradient(180deg, ${config.color}, color-mix(in oklab, ${config.color} 70%, black))` : 'rgba(255,255,255,0.04)',
            color: canConfirm ? '#0a0500' : 'var(--ink-4)',
            fontSize: 13, fontWeight: 700,
            border: canConfirm ? 'none' : '1px solid var(--line)',
            cursor: canConfirm ? 'pointer' : 'not-allowed',
          }}>{t('confirmAction')}</button>
      </div>
    </ModalShell>
  );
}

Object.assign(window, { SyncIssues });
