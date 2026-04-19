// Tweaks panel: language, online/offline, cart preset, screen, density
const { useState: useStateTW, useEffect: useEffectTW } = React;

function TweaksPanel({ state, setState, visible }) {
  if (!visible) return null;
  function set(key, val) { setState(s => ({ ...s, [key]: val })); }

  const row = { display: 'flex', flexDirection: 'column', gap: 6, paddingBlock: 10, borderBottom: '1px solid rgba(255,255,255,0.06)' };
  const label = { fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: '#8597a8', textTransform: 'uppercase', fontFamily: 'JetBrains Mono, monospace' };
  const seg = (active) => ({
    flex: 1, padding: '7px 8px', fontSize: 11, fontWeight: 600,
    background: active ? 'rgba(0,199,242,0.18)' : 'rgba(255,255,255,0.03)',
    color: active ? '#5cdfff' : '#b8c0cc',
    border: '1px solid', borderColor: active ? 'rgba(0,199,242,0.45)' : 'rgba(51,80,107,0.45)',
    borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit',
  });

  return (
    <div className="tweak-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#f7fbff' }}>Tweaks</div>
        <div style={{ fontSize: 9.5, color: '#5a6b7c', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.18em', textTransform: 'uppercase' }}>POS</div>
      </div>

      <div style={row}>
        <div style={label}>Language</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button style={seg(state.lang==='ar')} onClick={() => set('lang', 'ar')}>العربية RTL</button>
          <button style={seg(state.lang==='en')} onClick={() => set('lang', 'en')}>English LTR</button>
        </div>
      </div>

      <div style={row}>
        <div style={label}>Connectivity</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button style={seg(state.online)} onClick={() => set('online', true)}>Online</button>
          <button style={{ ...seg(!state.online), color: !state.online ? '#ffd27a' : '#b8c0cc', background: !state.online ? 'rgba(255,171,61,0.18)' : 'rgba(255,255,255,0.03)', borderColor: !state.online ? 'rgba(255,171,61,0.5)' : 'rgba(51,80,107,0.45)' }} onClick={() => set('online', false)}>Offline</button>
        </div>
      </div>

      <div style={row}>
        <div style={label}>Cart preset</div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['empty','three','twelve'].map(p => (
            <button key={p} style={seg(state.cartPreset===p)} onClick={() => set('cartPreset', p)}>{p}</button>
          ))}
        </div>
      </div>

      <div style={row}>
        <div style={label}>Screen</div>
        <div style={{ display: 'flex', gap: 4 }}>
          {[['terminal','Terminal'],['sync','Sync'],['shift','Shift']].map(([k,l]) => (
            <button key={k} style={seg(state.screen===k)} onClick={() => set('screen', k)}>{l}</button>
          ))}
        </div>
      </div>

      <div style={{ ...row, borderBottom: 'none' }}>
        <div style={label}>Open modal</div>
        <div style={{ display: 'flex', gap: 4 }}>
          {[['voucher','Voucher'],['promo','Promos'],['insurance','Insurance'],['none','None']].map(([k,l]) => (
            <button key={k} style={seg(state.openModal===k)} onClick={() => set('openModal', k)}>{l}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { TweaksPanel });
