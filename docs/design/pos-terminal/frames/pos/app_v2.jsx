// App glue v2 — same as v1 but renders TerminalV2 and adds scanToast state

const { useState: useStateA2, useEffect: useEffectA2, useRef: useRefA2 } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "lang": "ar",
  "online": true,
  "cartPreset": "three",
  "screen": "terminal",
  "openModal": "none"
}/*EDITMODE-END*/;

function AppV2() {
  const [state, setStateRaw] = useStateA2(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('dp_pos_state_v2') || 'null');
      return { ...TWEAK_DEFAULTS, ...(saved || {}) };
    } catch { return TWEAK_DEFAULTS; }
  });
  const setState = (updater) => {
    setStateRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      localStorage.setItem('dp_pos_state_v2', JSON.stringify(next));
      try { window.parent.postMessage({ type: '__edit_mode_set_keys', edits: next }, '*'); } catch {}
      return next;
    });
  };

  const { lang, online, cartPreset, screen, openModal } = state;
  const t = useT(lang);

  const [showStocktaking, setShowStocktaking] = useStateA2(false);
  const [showInvoice, setShowInvoice] = useStateA2(false);
  const [lastReceipt, setLastReceipt] = useStateA2(null);

  useEffectA2(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }, [lang]);

  const [cart, setCart] = useStateA2(() => makeCart(cartPreset, lang));
  useEffectA2(() => { setCart(makeCart(cartPreset, lang)); }, [cartPreset, lang]);
  useEffectA2(() => { if (online) setCart(prev => prev.map(l => ({ ...l, synced: true }))); }, [online]);

  const [voucher, setVoucher] = useStateA2(null);
  const [promo, setPromo] = useStateA2(null);
  const [insurance, setInsurance] = useStateA2(null);
  const [activePayment, setActivePayment] = useStateA2('cash');
  const [toast, setToast] = useStateA2('');
  const [scanToast, setScanToast] = useStateA2('');
  const [lastKey, setLastKey] = useStateA2('');

  useEffectA2(() => {
    function onKey(e) {
      if (/^[0-9]$/.test(e.key)) setLastKey(e.key);
      else if (e.key === '.') setLastKey('.');
      else if (e.key === 'Backspace') setLastKey('⌫');
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffectA2(() => {
    function onMsg(e) {
      if (!e.data) return;
      if (e.data.type === '__activate_edit_mode') setEditVisible(true);
      if (e.data.type === '__deactivate_edit_mode') setEditVisible(false);
    }
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);
  const [editVisible, setEditVisible] = useStateA2(false);

  const totals = computeTotals(cart, { voucher, promo, insurance });

  function openV() { setState(s => ({ ...s, openModal: 'voucher' })); }
  function openP() { setState(s => ({ ...s, openModal: 'promo' })); }
  function openI() { setState(s => ({ ...s, openModal: 'insurance' })); }
  function closeM() { setState(s => ({ ...s, openModal: 'none' })); }

  function onCharge() {
    if (!cart.length) return;
    // Snapshot for invoice
    setLastReceipt({
      cart: cart.slice(),
      totals: computeTotals(cart, { voucher, promo, insurance }),
      voucher, promo, insurance,
      paymentMethod: activePayment,
    });
    setShowInvoice(true);
    setToast(lang==='ar' ? 'تمت العملية · الفاتورة جاهزة' : 'Charged · invoice ready');
    setCart([]);
    setVoucher(null); setPromo(null); setInsurance(null);
    setActivePayment('cash');
  }

  useEffectA2(() => {
    function onKey(e) {
      if (e.key === 'F6') { e.preventDefault(); setShowStocktaking(true); }
      if (e.key === 'Escape') {
        if (showStocktaking) setShowStocktaking(false);
        if (showInvoice) setShowInvoice(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showStocktaking, showInvoice]);

  useEffectA2(() => {
    function onKey(e) {
      if (e.key === 'F1') { e.preventDefault(); setState(s => ({ ...s, screen: 'terminal' })); }
      if (e.key === 'F2') { e.preventDefault(); setState(s => ({ ...s, screen: 'sync' })); }
      if (e.key === 'F3') { e.preventDefault(); setState(s => ({ ...s, screen: 'shift' })); }
      if (e.key === 'F4') { e.preventDefault(); setState(s => ({ ...s, screen: 'drugs' })); }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const branch = lang==='ar' ? 'المعادي · POS-03' : 'Maadi · POS-03';
  const cashier = lang==='ar' ? 'نور محمد' : 'Nour Mohamed';
  const queue = online ? 0 : (cart.filter(l => !l.synced).length + 3);

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', position: 'relative' }} data-screen-label={screen}>
      <TopBar lang={lang} t={t} online={online} queue={queue} branch={branch} cashier={cashier}
        screen={screen} setScreen={(s) => setState(prev => ({ ...prev, screen: s }))} />

      <main style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        <ProvisionalRail show={!online} lang={lang} />
        {screen === 'terminal' && (
          <TerminalV2
            lang={lang} t={t}
            cart={cart} setCart={setCart}
            online={online}
            voucher={voucher} promo={promo} insurance={insurance}
            activePayment={activePayment} setActivePayment={setActivePayment}
            onOpenVoucher={openV} onOpenPromo={openP} onOpenInsurance={openI}
            onCharge={onCharge}
            lastKey={lastKey}
            scanToast={scanToast} setScanToast={setScanToast}
          />
        )}
        {screen === 'drugs' && (
          <>
            <DrugsScreen lang={lang} t={t}
              cart={cart} setCart={setCart} online={online}
              setScreen={(s) => setState(prev => ({ ...prev, screen: s }))}
              setScanToast={setScanToast}
              onOpenStocktaking={() => setShowStocktaking(true)} />
            {scanToast && <ScanToast message={scanToast} onDone={() => setScanToast('')} />}
          </>
        )}
        {screen === 'sync' && <SyncIssues lang={lang} t={t} />}
        {screen === 'shift' && <ShiftClose lang={lang} t={t} />}
      </main>

      <VoucherModal open={openModal==='voucher'} onClose={closeM} lang={lang} t={t}
        onApply={(code) => { setVoucher(code); setActivePayment('voucher'); }} totals={totals} />
      <PromotionsModal open={openModal==='promo'} onClose={closeM} lang={lang} t={t} onApply={(p) => { setPromo(p); }} />
      <InsuranceModal open={openModal==='insurance'} onClose={closeM} lang={lang} t={t}
        onApply={(ins) => { setInsurance(ins); setActivePayment('insurance'); }} total={totals.total} />

      {toast && <Toast message={toast} onDone={() => setToast('')} />}

      <StocktakingModal open={showStocktaking} onClose={() => setShowStocktaking(false)} lang={lang} t={t} />
      <InvoiceModal open={showInvoice && !!lastReceipt} onClose={() => setShowInvoice(false)}
        lang={lang} t={t}
        cart={lastReceipt?.cart || []} totals={lastReceipt?.totals || {}}
        voucher={lastReceipt?.voucher} promo={lastReceipt?.promo} insurance={lastReceipt?.insurance}
        paymentMethod={lastReceipt?.paymentMethod}
        branch={branch} cashier={cashier} />

      <TweaksPanel state={state} setState={setState} visible={editVisible} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<AppV2 />);
