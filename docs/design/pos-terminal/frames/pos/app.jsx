// App glue — state, screen routing, tweaks protocol, persistence

const { useState: useStateA, useEffect: useEffectA, useRef: useRefA } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "lang": "ar",
  "online": true,
  "cartPreset": "three",
  "screen": "terminal",
  "openModal": "none"
}/*EDITMODE-END*/;

function App() {
  // Persist state through localStorage so refresh doesn't lose place
  const [state, setStateRaw] = useStateA(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('dp_pos_state') || 'null');
      return { ...TWEAK_DEFAULTS, ...(saved || {}) };
    } catch { return TWEAK_DEFAULTS; }
  });
  const setState = (updater) => {
    setStateRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      localStorage.setItem('dp_pos_state', JSON.stringify(next));
      // Inform host of changes to persist
      try {
        window.parent.postMessage({ type: '__edit_mode_set_keys', edits: next }, '*');
      } catch {}
      return next;
    });
  };

  const { lang, online, cartPreset, screen, openModal } = state;
  const t = useT(lang);

  // Set dir on <html>
  useEffectA(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }, [lang]);

  // Cart state — derived from preset, but user can mutate
  const [cart, setCart] = useStateA(() => makeCart(cartPreset, lang));
  // Reseed when preset or lang changes
  useEffectA(() => { setCart(makeCart(cartPreset, lang)); }, [cartPreset, lang]);

  // Apply online state to existing cart's sync flags
  useEffectA(() => {
    if (online) setCart(prev => prev.map(l => ({ ...l, synced: true })));
  }, [online]);

  const [voucher, setVoucher] = useStateA(null);
  const [promo, setPromo] = useStateA(null);
  const [insurance, setInsurance] = useStateA(null);
  const [activePayment, setActivePayment] = useStateA('cash');
  const [toast, setToast] = useStateA('');
  const [lastKey, setLastKey] = useStateA('');

  // Live keystroke echo on keypad
  useEffectA(() => {
    function onKey(e) {
      if (/^[0-9]$/.test(e.key)) setLastKey(e.key);
      else if (e.key === '.') setLastKey('.');
      else if (e.key === 'Backspace') setLastKey('⌫');
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Tweak mode protocol — listener first, then announce
  useEffectA(() => {
    function onMsg(e) {
      if (!e.data) return;
      if (e.data.type === '__activate_edit_mode') setEditVisible(true);
      if (e.data.type === '__deactivate_edit_mode') setEditVisible(false);
    }
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);
  const [editVisible, setEditVisible] = useStateA(false);

  const totals = computeTotals(cart, { voucher, promo, insurance });

  function openV() { setState(s => ({ ...s, openModal: 'voucher' })); }
  function openP() { setState(s => ({ ...s, openModal: 'promo' })); }
  function openI() { setState(s => ({ ...s, openModal: 'insurance' })); }
  function closeM() { setState(s => ({ ...s, openModal: 'none' })); }

  function onCharge() {
    if (!cart.length) return;
    setToast(lang==='ar' ? 'تمت العملية · طُبع الإيصال' : 'Charged · receipt printed');
    // Reset cart
    setCart([]);
    setVoucher(null); setPromo(null); setInsurance(null);
    setActivePayment('cash');
  }

  // F1/F2/F3 screen switching
  useEffectA(() => {
    function onKey(e) {
      if (e.key === 'F1') { e.preventDefault(); setState(s => ({ ...s, screen: 'terminal' })); }
      if (e.key === 'F2') { e.preventDefault(); setState(s => ({ ...s, screen: 'sync' })); }
      if (e.key === 'F3') { e.preventDefault(); setState(s => ({ ...s, screen: 'shift' })); }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const branch = lang==='ar' ? 'المعادي · POS-03' : 'Maadi · POS-03';
  const cashier = lang==='ar' ? 'نور محمد' : 'Nour Mohamed';
  const queue = online ? 0 : (cart.filter(l => !l.synced).length + 3);

  return (
    <div style={{
      height: '100vh', width: '100vw',
      display: 'flex', flexDirection: 'column',
      position: 'relative',
    }} data-screen-label={screen}>
      <TopBar lang={lang} t={t} online={online} queue={queue} branch={branch} cashier={cashier}
        screen={screen} setScreen={(s) => setState(prev => ({ ...prev, screen: s }))} />

      <main style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        <ProvisionalRail show={!online} lang={lang} />
        {screen === 'terminal' && (
          <Terminal
            lang={lang} t={t}
            cart={cart} setCart={setCart}
            online={online}
            voucher={voucher} promo={promo} insurance={insurance}
            activePayment={activePayment} setActivePayment={setActivePayment}
            onOpenVoucher={openV} onOpenPromo={openP} onOpenInsurance={openI}
            onCharge={onCharge}
            lastKey={lastKey}
          />
        )}
        {screen === 'sync' && <SyncIssues lang={lang} t={t} />}
        {screen === 'shift' && <ShiftClose lang={lang} t={t} />}
      </main>

      <VoucherModal open={openModal==='voucher'} onClose={closeM} lang={lang} t={t}
        onApply={(code) => { setVoucher(code); setActivePayment('voucher'); }}
        totals={totals} />
      <PromotionsModal open={openModal==='promo'} onClose={closeM} lang={lang} t={t}
        onApply={(p) => { setPromo(p); }} />
      <InsuranceModal open={openModal==='insurance'} onClose={closeM} lang={lang} t={t}
        onApply={(ins) => { setInsurance(ins); setActivePayment('insurance'); }}
        total={totals.total} />

      {toast && <Toast message={toast} onDone={() => setToast('')} />}

      <TweaksPanel state={state} setState={setState} visible={editVisible} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
