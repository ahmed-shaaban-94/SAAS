// Shared shell: top bar with pulse line, branch, queue-depth chip, online state, nav.
// Renders every screen; children slot into main area.

const { useState, useEffect, useRef, useMemo, useCallback } = React;

function MiniPulseLine({ online, height = 26 }) {
  // Canvas-free pulse: animated SVG path that shifts.
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!online) return;
    const t = setInterval(() => setTick(x => x + 1), 1200);
    return () => clearInterval(t);
  }, [online]);

  const points = useMemo(() => {
    const n = 60;
    const arr = [];
    for (let i = 0; i < n; i++) {
      const x = (i / (n-1)) * 100;
      // Pseudo-random but stable per tick
      const seed = Math.sin((i + tick*3) * 1.3) * Math.cos((i - tick*2) * 0.7);
      const spike = i === (n-5) ? 1.6 : (i === (n-4) ? -0.8 : 0);
      const y = 50 + seed * 10 + spike * 8;
      arr.push([x, y]);
    }
    return arr;
  }, [tick]);

  const flatPoints = useMemo(() => {
    const n = 60; const arr = [];
    for (let i = 0; i < n; i++) arr.push([(i/(n-1))*100, 50]);
    return arr;
  }, []);

  const pts = online ? points : flatPoints;
  const d = 'M ' + pts.map(p => `${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' L ');

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height, display: 'block' }} aria-hidden="true">
      <defs>
        <linearGradient id="pulseGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#00c7f2" stopOpacity="0.2" />
          <stop offset="50%" stopColor="#00c7f2" stopOpacity="1" />
          <stop offset="100%" stopColor="#5cdfff" stopOpacity="1" />
        </linearGradient>
      </defs>
      <path d={d} fill="none" stroke={online ? 'url(#pulseGrad)' : 'rgba(255,171,61,0.6)'} strokeWidth="1.2" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
      {online && <circle cx={pts[pts.length-1][0]} cy={pts[pts.length-1][1]} r="1.6" fill="#5cdfff" />}
    </svg>
  );
}

function TopBar({ lang, t, online, queue, branch, screen, setScreen, cashier }) {
  const tabs = [
    { id: 'terminal', label: t('terminal'), kbd: 'F1' },
    { id: 'drugs', label: t('drugs'), kbd: 'F4' },
    { id: 'sync', label: t('syncIssues'), kbd: 'F2', badge: 5 },
    { id: 'shift', label: t('shiftClose'), kbd: 'F3' },
  ];
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  const [liveTime, setLiveTime] = useState(timeStr);
  useEffect(() => {
    const t = setInterval(() => setLiveTime(new Date().toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' })), 20000);
    return () => clearInterval(t);
  }, []);

  return (
    <header style={{
      display: 'grid',
      gridTemplateColumns: 'auto 1fr auto auto',
      alignItems: 'center',
      gap: 18,
      padding: '10px 20px',
      borderBottom: '1px solid var(--line)',
      background: 'linear-gradient(180deg, rgba(5,14,23,0.95), rgba(8,24,38,0.9))',
      backdropFilter: 'blur(16px)',
      position: 'relative',
      zIndex: 10,
    }}>
      {/* Brand + branch */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 26, height: 26, borderRadius: 7,
            background: 'radial-gradient(circle at 30% 30%, #5cdfff, #00c7f2 60%, #7467f8)',
            boxShadow: '0 0 14px rgba(0,199,242,0.5)',
          }} aria-hidden="true" />
          <div style={{ fontFamily: 'Fraunces, serif', fontSize: 17, fontWeight: 500, letterSpacing: '-0.01em' }}>
            DataPulse<span style={{ color: 'var(--ink-3)', fontWeight: 400 }}> · POS</span>
          </div>
        </div>
        <div style={{ width: 1, height: 22, background: 'var(--line)' }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>
            {t('branch')}
          </div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{branch}</div>
        </div>
      </div>

      {/* Pulse + live label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: online ? 'var(--green)' : 'var(--amber)',
            animation: online ? 'heartbeat 1.6s infinite' : 'heartbeat-amber 1.8s infinite',
          }} aria-hidden="true" />
          <span className="mono" style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.2em', textTransform: 'uppercase', color: online ? 'var(--green)' : 'var(--amber)' }}>
            {online ? t('live') : t('offline')}
          </span>
        </div>
        <div style={{ flex: 1, minWidth: 120, maxWidth: 380 }}>
          <MiniPulseLine online={online} />
        </div>
        <span className="mono ltr-nums tab" style={{ fontSize: 11, color: 'var(--ink-3)', whiteSpace: 'nowrap' }}>
          {online ? '12.8K' : '0.0'} {t('txPerMin')}
        </span>
      </div>

      {/* Queue / provisional chip */}
      <QueueChip lang={lang} t={t} online={online} queue={queue} />

      {/* Cashier + time */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ textAlign: lang === 'ar' ? 'right' : 'left' }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>
            {t('cashier')}
          </div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{cashier}</div>
        </div>
        <div className="mono ltr-nums" style={{
          fontSize: 12, fontWeight: 600, color: 'var(--ink-2)',
          padding: '6px 9px', border: '1px solid var(--line)', borderRadius: 6,
        }}>{liveTime}</div>
      </div>

      {/* Nav strip — second row */}
      <nav style={{ gridColumn: '1 / -1', display: 'flex', gap: 6, marginTop: 4 }} aria-label="Primary">
        {tabs.map(tab => {
          const active = screen === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setScreen(tab.id)}
              aria-current={active ? 'page' : undefined}
              aria-label={`${tab.label} (${tab.kbd})`}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '7px 12px', borderRadius: 8,
                background: active ? 'rgba(0,199,242,0.12)' : 'transparent',
                border: '1px solid',
                borderColor: active ? 'rgba(0,199,242,0.45)' : 'var(--line)',
                color: active ? 'var(--accent-hi)' : 'var(--ink-2)',
                fontSize: 12.5, fontWeight: 600,
                transition: 'all 120ms ease',
              }}
            >
              <span>{tab.label}</span>
              <span className="kbd" style={{
                background: active ? 'rgba(0,199,242,0.18)' : 'rgba(184,192,204,0.08)',
                color: active ? 'var(--accent-hi)' : 'var(--ink-3)',
                borderColor: active ? 'rgba(0,199,242,0.35)' : 'var(--line)',
              }}>{tab.kbd}</span>
              {tab.badge && (
                <span className="mono ltr-nums" style={{
                  fontSize: 9.5, fontWeight: 700,
                  padding: '2px 6px', borderRadius: 999,
                  background: 'rgba(255,123,123,0.15)', color: 'var(--red)',
                  border: '1px solid rgba(255,123,123,0.4)',
                }}>{tab.badge}</span>
              )}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

function QueueChip({ lang, t, online, queue }) {
  const showAmber = !online || queue > 0;
  if (!showAmber) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '6px 10px', borderRadius: 999,
        background: 'rgba(29,212,139,0.08)',
        border: '1px solid rgba(29,212,139,0.3)',
        fontSize: 11, fontWeight: 600, color: 'var(--green)',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }} aria-hidden="true" />
        <span>{t('confirmed')}</span>
      </div>
    );
  }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 10px', borderRadius: 999,
      background: 'rgba(255,171,61,0.1)',
      border: '1px solid rgba(255,171,61,0.4)',
      fontSize: 11, fontWeight: 600, color: 'var(--amber)',
    }}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 2 L14 10 L22 10 L16 15 L18 22 L12 18 L6 22 L8 15 L2 10 L10 10 Z" fill="currentColor" opacity="0.9" />
      </svg>
      <span>{t('provisional')}</span>
      <span className="mono ltr-nums" style={{
        fontSize: 10, fontWeight: 700,
        padding: '2px 6px', borderRadius: 5,
        background: 'rgba(255,171,61,0.2)',
      }}>Q·{queue}</span>
    </div>
  );
}

// Skinny persistent offline rail along left edge of content when offline.
function ProvisionalRail({ show, lang }) {
  if (!show) return null;
  return (
    <div style={{
      position: 'absolute',
      top: 0, bottom: 0,
      [lang === 'ar' ? 'right' : 'left']: 0,
      width: 4,
      background: 'repeating-linear-gradient(135deg, var(--amber) 0, var(--amber) 8px, rgba(255,171,61,0.2) 8px, rgba(255,171,61,0.2) 16px)',
      opacity: 0.9,
      pointerEvents: 'none',
      zIndex: 5,
    }} aria-label="offline indicator" />
  );
}

Object.assign(window, { TopBar, QueueChip, MiniPulseLine, ProvisionalRail });
