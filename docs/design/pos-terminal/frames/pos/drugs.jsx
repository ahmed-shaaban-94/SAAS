// Drugs tab — searchable inventory with stock-on-hand and quantity-aware add-to-cart.
// Practical: keyword/SKU search, sortable columns, stock badges (out/low/watch/ok),
//   inline qty stepper per row, "Add" disabled when out of stock,
//   keyboard: / focus search, Enter add top-result, ↑/↓ navigate.
// Cosmetic: thermal-style header, hairline rows, color-coded stock pills,
//   Fraunces italic on the running stock-value summary.

const { useState: useStateD, useEffect: useEffectD, useRef: useRefD, useMemo: useMemoD } = React;

function DrugsScreen({ lang, t, cart, setCart, online, setScreen, setScanToast, onOpenStocktaking }) {
  const cat = CATALOG[lang];
  const [query, setQuery] = useStateD('');
  const [sort, setSort] = useStateD({ key: 'name', dir: 'asc' });
  const [stockFilter, setStockFilter] = useStateD('all'); // all | low | out
  const [rxFilter, setRxFilter] = useStateD('all'); // all | rx | otc
  const [qtyMap, setQtyMap] = useStateD({}); // sku -> intended qty
  const [activeIdx, setActiveIdx] = useStateD(0);
  const searchRef = useRefD(null);
  const tableRef = useRefD(null);

  useEffectD(() => { searchRef.current?.focus(); }, []);

  // Merge catalog + stock for display
  const rows = useMemoD(() => {
    return cat.map((p, i) => {
      const enRow = CATALOG.en[i];
      const s = stockStatus(p.sku);
      return {
        ...p,
        nameSecondary: lang === 'ar' ? enRow?.name : null, // bilingual hint when Arabic
        ...s,
      };
    });
  }, [cat, lang]);

  const filtered = useMemoD(() => {
    const q = query.trim().toLowerCase();
    let out = rows.filter(r => {
      if (stockFilter === 'low' && r.tag !== 'low' && r.tag !== 'out') return false;
      if (stockFilter === 'out' && r.tag !== 'out') return false;
      if (rxFilter === 'rx' && !r.rx) return false;
      if (rxFilter === 'otc' && r.rx) return false;
      if (!q) return true;
      return r.name.toLowerCase().includes(q)
        || r.sku.includes(q)
        || (r.nameSecondary && r.nameSecondary.toLowerCase().includes(q))
        || r.category?.toLowerCase().includes(q)
        || r.mfr?.toLowerCase().includes(q);
    });
    out.sort((a, b) => {
      const dir = sort.dir === 'asc' ? 1 : -1;
      const av = a[sort.key]; const bv = b[sort.key];
      if (typeof av === 'number') return (av - bv) * dir;
      return String(av).localeCompare(String(bv), lang) * dir;
    });
    return out;
  }, [rows, query, sort, stockFilter, rxFilter, lang]);

  useEffectD(() => { setActiveIdx(0); }, [query, stockFilter, rxFilter]);

  function getQty(sku) {
    return qtyMap[sku] ?? 1;
  }
  function setQty(sku, n) {
    setQtyMap(m => ({ ...m, [sku]: Math.max(1, Math.min(99, n)) }));
  }

  function addRow(row, n) {
    if (row.qty === 0) return;
    const want = n ?? getQty(row.sku);
    setCart(prev => {
      const existing = prev.find(l => l.sku === row.sku);
      if (existing) return prev.map(l => l.lineId === existing.lineId ? { ...l, qty: l.qty + want } : l);
      return [...prev, { sku: row.sku, name: row.name, price: row.price, vatRate: row.vatRate, qty: want, lineId: 'L' + Date.now() + Math.random().toFixed(3).slice(2), synced: online }];
    });
    setScanToast(`+${want} · ${row.name}`);
    setQtyMap(m => ({ ...m, [row.sku]: 1 }));
  }

  // Keyboard nav
  useEffectD(() => {
    function onKey(e) {
      const tag = (e.target && e.target.tagName) || '';
      const isInput = tag === 'INPUT';
      if (e.key === '/' && !isInput) { e.preventDefault(); searchRef.current?.focus(); return; }
      if (e.key === 'Escape' && isInput) { searchRef.current?.blur(); return; }
      if (e.key === 'ArrowDown' && (isInput || e.target.tagName === 'BODY')) {
        e.preventDefault();
        setActiveIdx(i => Math.min(filtered.length - 1, i + 1));
      }
      if (e.key === 'ArrowUp' && (isInput || e.target.tagName === 'BODY')) {
        e.preventDefault();
        setActiveIdx(i => Math.max(0, i - 1));
      }
      if (e.key === 'Enter' && isInput && filtered[activeIdx]) {
        e.preventDefault();
        addRow(filtered[activeIdx]);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [filtered, activeIdx]);

  // Summary
  const totalSkus = rows.length;
  const totalUnits = rows.reduce((s, r) => s + r.qty, 0);
  const stockValue = rows.reduce((s, r) => s + r.qty * r.price, 0);
  const lowCount = rows.filter(r => r.tag === 'low').length;
  const outCount = rows.filter(r => r.tag === 'out').length;
  const cartItems = cart.reduce((s, l) => s + l.qty, 0);

  function toggleSort(key) {
    setSort(s => s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' });
  }
  function sortIndicator(key) {
    if (sort.key !== key) return null;
    return <span style={{ marginInlineStart: 4, color: 'var(--accent-hi)' }}>{sort.dir === 'asc' ? '↑' : '↓'}</span>;
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 320px',
      gap: 14, padding: 14,
      height: '100%', minHeight: 0,
    }}>
      {/* LEFT — search + table */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0, minWidth: 0 }}>
        <SearchBar lang={lang} t={t} query={query} setQuery={setQuery} searchRef={searchRef}
          stockFilter={stockFilter} setStockFilter={setStockFilter}
          rxFilter={rxFilter} setRxFilter={setRxFilter}
          resultCount={filtered.length} totalCount={totalSkus}
          onOpenStocktaking={onOpenStocktaking} />
        <DrugTable lang={lang} t={t} rows={filtered}
          activeIdx={activeIdx} setActiveIdx={setActiveIdx}
          getQty={getQty} setQty={setQty} addRow={addRow}
          sort={sort} toggleSort={toggleSort} sortIndicator={sortIndicator}
          tableRef={tableRef} />
      </section>

      {/* RIGHT — summary + cart preview */}
      <aside style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
        <InventorySummary lang={lang} t={t}
          totalSkus={totalSkus} totalUnits={totalUnits}
          stockValue={stockValue} lowCount={lowCount} outCount={outCount} />
        <FocusedDrug lang={lang} t={t} row={filtered[activeIdx]} addRow={addRow} getQty={getQty} setQty={setQty} />
        <CartGoTo lang={lang} t={t} cart={cart} cartItems={cartItems} setScreen={setScreen} />
      </aside>
    </div>
  );
}

function SearchBar({ lang, t, query, setQuery, searchRef, stockFilter, setStockFilter, rxFilter, setRxFilter, resultCount, totalCount, onOpenStocktaking }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 10,
      padding: '14px 16px',
      background: 'rgba(8,24,38,0.7)',
      border: '1.5px solid rgba(0,199,242,0.35)',
      borderRadius: 12,
      boxShadow: '0 0 0 1px rgba(0,199,242,0.08), 0 0 24px rgba(0,199,242,0.1)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-hi)" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
        </svg>
        <input
          ref={searchRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={lang === 'ar' ? 'ابحثي بالاسم أو الكود أو الصنف أو المُصنِّع…' : 'Search by name, SKU, category, or manufacturer…'}
          aria-label={t('searchHint')}
          style={{
            flex: 1, fontSize: 16, fontWeight: 500, fontFamily: 'inherit',
            direction: lang === 'ar' ? 'rtl' : 'ltr',
          }}
        />
        <span className="mono" style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>
          {resultCount}<span style={{ color: 'var(--ink-4)' }}>/{totalCount}</span>
        </span>
        <span className="kbd-lg">/</span>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <FilterChip label={lang==='ar' ? 'الكل' : 'All'} active={stockFilter==='all'} onClick={() => setStockFilter('all')} />
        <FilterChip label={lang==='ar' ? 'منخفض' : 'Low stock'} active={stockFilter==='low'} onClick={() => setStockFilter('low')} color="var(--amber)" />
        <FilterChip label={lang==='ar' ? 'منتهي' : 'Out of stock'} active={stockFilter==='out'} onClick={() => setStockFilter('out')} color="var(--red)" />
        <div style={{ width: 1, alignSelf: 'stretch', background: 'var(--line)' }} />
        <FilterChip label={lang==='ar' ? 'كل الأنواع' : 'Any'} active={rxFilter==='all'} onClick={() => setRxFilter('all')} />
        <FilterChip label={lang==='ar' ? 'بوصفة' : 'Rx only'} active={rxFilter==='rx'} onClick={() => setRxFilter('rx')} color="var(--purple)" />
        <FilterChip label={lang==='ar' ? 'بدون وصفة' : 'OTC'} active={rxFilter==='otc'} onClick={() => setRxFilter('otc')} color="var(--accent-hi)" />
        <button onClick={onOpenStocktaking} style={{
          marginInlineStart: 'auto',
          padding: '6px 12px', borderRadius: 999,
          background: 'linear-gradient(180deg, rgba(116,103,248,0.18), rgba(116,103,248,0.08))',
          border: '1px solid rgba(116,103,248,0.5)',
          color: 'var(--purple)',
          fontSize: 11, fontWeight: 700, letterSpacing: '0.04em',
          display: 'inline-flex', alignItems: 'center', gap: 7, cursor: 'pointer',
          boxShadow: '0 0 14px rgba(116,103,248,0.2)',
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 8h6 M9 12h6 M9 16h4"/></svg>
          <span>{lang==='ar' ? 'ورقة جرد للطباعة' : 'Stocktaking sheet'}</span>
          <span className="kbd" style={{ background: 'rgba(116,103,248,0.15)', borderColor: 'rgba(116,103,248,0.4)', color: 'var(--purple)' }}>F6</span>
        </button>
      </div>
    </div>
  );
}

function FilterChip({ label, active, onClick, color }) {
  const c = color || 'var(--accent-hi)';
  return (
    <button onClick={onClick} aria-pressed={active}
      style={{
        padding: '5px 10px', borderRadius: 999,
        background: active ? `color-mix(in oklab, ${c} 18%, transparent)` : 'rgba(255,255,255,0.03)',
        border: '1px solid',
        borderColor: active ? c : 'var(--line)',
        color: active ? c : 'var(--ink-3)',
        fontSize: 11, fontWeight: 600, cursor: 'pointer',
        transition: 'all 120ms ease',
      }}>
      {label}
    </button>
  );
}

function DrugTable({ lang, t, rows, activeIdx, setActiveIdx, getQty, setQty, addRow, sort, toggleSort, sortIndicator, tableRef }) {
  return (
    <div style={{
      flex: 1, minHeight: 0,
      background: 'rgba(8,24,38,0.5)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Sticky header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.6fr 130px 100px 100px 132px 76px',
        gap: 8,
        padding: '10px 14px',
        borderBottom: '1px solid var(--line)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.03), transparent)',
        alignItems: 'center',
      }}>
        <SortHeader label={lang==='ar' ? 'الصنف' : 'Item'} k="name" sort={sort} onClick={() => toggleSort('name')} indicator={sortIndicator('name')} />
        <SortHeader label={lang==='ar' ? 'كود الباركود' : 'Barcode / SKU'} k="sku" sort={sort} onClick={() => toggleSort('sku')} indicator={sortIndicator('sku')} />
        <SortHeader label={lang==='ar' ? 'المخزون' : 'On hand'} k="qty" sort={sort} onClick={() => toggleSort('qty')} indicator={sortIndicator('qty')} align="end" />
        <SortHeader label={lang==='ar' ? 'السعر' : 'Price'} k="price" sort={sort} onClick={() => toggleSort('price')} indicator={sortIndicator('price')} align="end" />
        <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)', textTransform: 'uppercase', textAlign: 'center' }}>
          {lang==='ar' ? 'كم تريدين' : 'Add qty'}
        </div>
        <div />
      </div>

      <div ref={tableRef} style={{ flex: 1, overflowY: 'auto' }}>
        {rows.length === 0 && (
          <div style={{
            height: '100%', minHeight: 180,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8,
            color: 'var(--ink-3)',
          }}>
            <div style={{ fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontSize: 18, color: 'var(--ink)' }}>
              {lang==='ar' ? 'لا توجد نتائج' : 'No matches'}
            </div>
            <div style={{ fontSize: 12.5 }}>
              {lang==='ar' ? 'جرّبي كلمة بحث أخرى' : 'Try a different query'}
            </div>
          </div>
        )}

        {rows.map((row, idx) => {
          const active = idx === activeIdx;
          const out = row.tag === 'out';
          const qty = getQty(row.sku);
          return (
            <div key={row.sku}
              onClick={() => setActiveIdx(idx)}
              style={{
                display: 'grid',
                gridTemplateColumns: '1.6fr 130px 100px 100px 132px 76px',
                gap: 8,
                padding: '11px 14px',
                borderBottom: '1px solid var(--line)',
                background: active ? 'rgba(0,199,242,0.06)' : 'transparent',
                borderInlineStart: active ? '3px solid var(--accent-hi)' : '3px solid transparent',
                paddingInlineStart: active ? 11 : 14,
                alignItems: 'center',
                cursor: 'pointer',
                transition: 'background 100ms ease',
                opacity: out ? 0.7 : 1,
              }}>
              {/* Name + meta */}
              <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {row.name}
                  </span>
                  {row.rx && (
                    <span className="mono" style={{
                      fontSize: 8.5, fontWeight: 700, letterSpacing: '0.18em',
                      padding: '1px 5px', borderRadius: 3,
                      background: 'rgba(116,103,248,0.15)', color: 'var(--purple)',
                      textTransform: 'uppercase', flexShrink: 0,
                    }}>Rx</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 10.5, color: 'var(--ink-4)' }}>
                  <span className="mono" style={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}>{row.category}</span>
                  <span>·</span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.mfr}</span>
                  {row.shelf && <><span>·</span><span className="mono ltr-nums" style={{ color: 'var(--ink-3)' }}>{lang==='ar' ? 'رف' : 'Shelf'} {row.shelf}</span></>}
                </div>
              </div>

              {/* SKU */}
              <div className="mono ltr-nums" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{row.sku}</div>

              {/* Stock */}
              <StockPill row={row} lang={lang} />

              {/* Price */}
              <div className="mono ltr-nums" style={{ textAlign: lang==='ar' ? 'left' : 'right', fontSize: 13, fontWeight: 600 }}>
                {fmtEGP(row.price)}
              </div>

              {/* Qty stepper */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                <button onClick={(e) => { e.stopPropagation(); setQty(row.sku, qty - 1); }}
                  disabled={out}
                  aria-label="decrease quantity"
                  style={{
                    width: 26, height: 26, borderRadius: 5,
                    background: 'rgba(184,192,204,0.08)', border: '1px solid var(--line)',
                    color: 'var(--ink-2)', fontSize: 14, lineHeight: 1,
                    cursor: out ? 'not-allowed' : 'pointer',
                  }}>−</button>
                <input
                  type="number"
                  value={qty}
                  onChange={(e) => setQty(row.sku, parseInt(e.target.value || '1', 10))}
                  onClick={e => e.stopPropagation()}
                  disabled={out}
                  className="mono ltr-nums"
                  style={{
                    width: 40, height: 26, textAlign: 'center',
                    background: 'rgba(8,24,38,0.7)', border: '1px solid var(--line)', borderRadius: 5,
                    color: 'var(--ink)', fontSize: 13, fontWeight: 600,
                    fontFamily: 'JetBrains Mono, monospace',
                  }} />
                <button onClick={(e) => { e.stopPropagation(); setQty(row.sku, qty + 1); }}
                  disabled={out}
                  aria-label="increase quantity"
                  style={{
                    width: 26, height: 26, borderRadius: 5,
                    background: out ? 'rgba(184,192,204,0.06)' : 'rgba(0,199,242,0.1)',
                    border: '1px solid', borderColor: out ? 'var(--line)' : 'rgba(0,199,242,0.3)',
                    color: out ? 'var(--ink-4)' : 'var(--accent-hi)', fontSize: 14, lineHeight: 1,
                    cursor: out ? 'not-allowed' : 'pointer',
                  }}>+</button>
              </div>

              {/* Add */}
              <button onClick={(e) => { e.stopPropagation(); addRow(row); }}
                disabled={out}
                aria-label={out ? 'out of stock' : `add ${qty} × ${row.name}`}
                style={{
                  padding: '7px 10px', borderRadius: 6,
                  background: out ? 'rgba(255,255,255,0.04)' : 'linear-gradient(180deg, #5cdfff, #00a6cc)',
                  color: out ? 'var(--ink-4)' : '#021018',
                  border: out ? '1px solid var(--line)' : 'none',
                  fontSize: 12, fontWeight: 700,
                  cursor: out ? 'not-allowed' : 'pointer',
                  boxShadow: out ? 'none' : '0 0 12px rgba(0,199,242,0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
                  transition: 'transform 80ms ease',
                }}
                onMouseDown={e => !out && (e.currentTarget.style.transform = 'scale(0.97)')}
                onMouseUp={e => (e.currentTarget.style.transform = 'scale(1)')}
                onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
              >
                {out ? (lang==='ar' ? 'منتهي' : 'Out') : (lang==='ar' ? 'إضافة' : 'Add')}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SortHeader({ label, onClick, indicator, align }) {
  return (
    <button onClick={onClick} className="mono"
      style={{
        background: 'transparent', border: 0, padding: 0, cursor: 'pointer',
        fontSize: 9.5, fontWeight: 700, letterSpacing: '0.2em', color: 'var(--ink-3)',
        textTransform: 'uppercase', textAlign: align === 'end' ? 'end' : 'start',
        display: 'flex', justifyContent: align === 'end' ? 'flex-end' : 'flex-start',
        alignItems: 'center',
        fontFamily: 'JetBrains Mono, monospace',
      }}>
      {label}
      {indicator}
    </button>
  );
}

function StockPill({ row, lang }) {
  const palette = {
    out:   { color: 'var(--red)',     bg: 'rgba(255,123,123,0.14)', border: 'rgba(255,123,123,0.4)' },
    low:   { color: 'var(--amber)',   bg: 'rgba(255,171,61,0.14)',  border: 'rgba(255,171,61,0.4)' },
    watch: { color: '#e8c46b',        bg: 'rgba(232,196,107,0.1)',  border: 'rgba(232,196,107,0.3)' },
    ok:    { color: 'var(--green)',   bg: 'rgba(29,212,139,0.1)',   border: 'rgba(29,212,139,0.3)' },
  };
  const p = palette[row.tag] || palette.ok;
  const labelByTag = {
    out:   lang==='ar' ? 'منتهي' : 'Out',
    low:   lang==='ar' ? 'منخفض' : 'Low',
    watch: lang==='ar' ? 'مراقبة' : 'Watch',
    ok:    lang==='ar' ? 'متوفر' : 'OK',
  };
  return (
    <div style={{
      display: 'inline-flex', flexDirection: 'column', gap: 3,
      padding: '4px 8px', borderRadius: 6,
      background: p.bg, border: '1px solid', borderColor: p.border,
      minWidth: 78,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
        <span className="mono ltr-nums" style={{ fontSize: 14, fontWeight: 700, color: p.color }}>{row.qty}</span>
        <span className="mono" style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.15em', color: p.color, textTransform: 'uppercase' }}>
          {labelByTag[row.tag]}
        </span>
      </div>
      {row.reorder && (
        <div className="mono ltr-nums" style={{ fontSize: 9, color: 'var(--ink-4)', letterSpacing: '0.05em' }}>
          {lang==='ar' ? 'إعادة طلب' : 'reorder'} {row.reorder}
        </div>
      )}
    </div>
  );
}

function InventorySummary({ lang, t, totalSkus, totalUnits, stockValue, lowCount, outCount }) {
  return (
    <div style={{
      padding: '14px 16px',
      background: 'linear-gradient(180deg, rgba(0,199,242,0.1), rgba(22,52,82,0.4))',
      border: '1px solid rgba(0,199,242,0.35)',
      borderRadius: 14,
      boxShadow: '0 0 0 1px rgba(0,199,242,0.12), 0 0 28px rgba(0,199,242,0.1)',
    }}>
      <div className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--accent-hi)', textTransform: 'uppercase', marginBottom: 10 }}>
        ● {lang==='ar' ? 'حالة المخزون' : 'Stock snapshot'}
      </div>
      <div className="ltr-nums" style={{
        fontFamily: 'Fraunces, serif', fontStyle: 'italic', fontWeight: 500,
        fontSize: 30, lineHeight: 1, letterSpacing: '-0.02em',
        color: 'var(--ink)', textShadow: '0 0 24px rgba(0,199,242,0.35)',
      }}>
        {fmtEGP(stockValue)}
      </div>
      <div className="mono" style={{ fontSize: 10, color: 'var(--ink-3)', letterSpacing: '0.16em', textTransform: 'uppercase', marginTop: 4 }}>
        {lang==='ar' ? 'قيمة المخزون' : 'On-hand value'}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 14 }}>
        <SummaryStat label={lang==='ar' ? 'أصناف' : 'SKUs'} value={totalSkus} />
        <SummaryStat label={lang==='ar' ? 'وحدات' : 'Units'} value={totalUnits} />
        <SummaryStat label={lang==='ar' ? 'منخفض' : 'Low'} value={lowCount} color="var(--amber)" />
        <SummaryStat label={lang==='ar' ? 'منتهي' : 'Out'} value={outCount} color="var(--red)" />
      </div>
    </div>
  );
}

function SummaryStat({ label, value, color }) {
  return (
    <div style={{
      padding: '8px 10px', borderRadius: 8,
      background: 'rgba(8,24,38,0.5)', border: '1px solid var(--line)',
    }}>
      <div className="mono ltr-nums" style={{ fontSize: 18, fontWeight: 700, color: color || 'var(--ink)' }}>{value}</div>
      <div className="mono" style={{ fontSize: 9, color: 'var(--ink-3)', letterSpacing: '0.16em', textTransform: 'uppercase', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function FocusedDrug({ lang, t, row, addRow, getQty, setQty }) {
  if (!row) return null;
  const out = row.tag === 'out';
  const qty = getQty(row.sku);
  return (
    <div style={{
      padding: '12px 14px',
      background: 'rgba(8,24,38,0.6)',
      border: '1px solid var(--line)',
      borderRadius: 12,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.22em', color: 'var(--ink-3)', textTransform: 'uppercase' }}>
        {lang==='ar' ? 'الصنف المحدد' : 'Selected'}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.3 }}>{row.name}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
        <DetailRow label={lang==='ar' ? 'باركود' : 'SKU'} value={row.sku} mono />
        <DetailRow label={lang==='ar' ? 'دفعة' : 'Batch'} value={row.batch} mono />
        <DetailRow label={lang==='ar' ? 'انتهاء' : 'Expiry'} value={row.expiry} mono />
        <DetailRow label={lang==='ar' ? 'موقع' : 'Shelf'} value={row.shelf} mono />
      </div>
      <button onClick={() => addRow(row, qty)} disabled={out}
        style={{
          marginTop: 4, padding: '10px 12px', borderRadius: 8,
          background: out ? 'rgba(255,255,255,0.04)' : 'linear-gradient(180deg, #5cdfff, #00a6cc)',
          color: out ? 'var(--ink-4)' : '#021018',
          border: out ? '1px solid var(--line)' : 'none',
          fontSize: 13, fontWeight: 700,
          display: 'grid', gridTemplateColumns: 'auto 1fr auto', alignItems: 'center', gap: 10,
          cursor: out ? 'not-allowed' : 'pointer',
          boxShadow: out ? 'none' : '0 0 18px rgba(0,199,242,0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
        }}>
        <span>{out ? (lang==='ar' ? 'غير متاح' : 'Unavailable') : (lang==='ar' ? 'أضيفي للسلة' : 'Add to cart')}</span>
        <span className="mono ltr-nums" style={{ fontSize: 14, textAlign: 'center' }}>×{qty}</span>
        <span className="mono ltr-nums" style={{ fontSize: 13 }}>{fmtEGP(row.price * qty)}</span>
      </button>
    </div>
  );
}

function DetailRow({ label, value, mono }) {
  return (
    <div>
      <div className="mono" style={{ fontSize: 9, color: 'var(--ink-4)', letterSpacing: '0.16em', textTransform: 'uppercase' }}>{label}</div>
      <div className={mono ? 'mono ltr-nums' : ''} style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-2)', marginTop: 2 }}>{value || '—'}</div>
    </div>
  );
}

function CartGoTo({ lang, t, cart, cartItems, setScreen }) {
  const total = cart.reduce((s, l) => s + l.price * l.qty, 0);
  return (
    <button onClick={() => setScreen('terminal')}
      style={{
        marginTop: 'auto',
        padding: '12px 14px', borderRadius: 10,
        background: cartItems > 0 ? 'rgba(29,212,139,0.1)' : 'rgba(255,255,255,0.03)',
        border: '1px solid',
        borderColor: cartItems > 0 ? 'rgba(29,212,139,0.4)' : 'var(--line)',
        color: cartItems > 0 ? 'var(--green)' : 'var(--ink-3)',
        textAlign: 'start',
        cursor: 'pointer',
        display: 'grid', gridTemplateColumns: 'auto 1fr auto', alignItems: 'center', gap: 10,
      }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 4h2l2 13h11l2-9H7" /><circle cx="9" cy="20" r="1.5" /><circle cx="17" cy="20" r="1.5" />
      </svg>
      <div>
        <div style={{ fontSize: 12.5, fontWeight: 700 }}>
          {cartItems > 0
            ? (lang==='ar' ? `في السلة: ${cartItems} ${cartItems === 1 ? 'صنف' : 'أصناف'}` : `In cart: ${cartItems} item${cartItems === 1 ? '' : 's'}`)
            : (lang==='ar' ? 'السلة فارغة' : 'Cart is empty')}
        </div>
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--ink-4)', letterSpacing: '0.18em', textTransform: 'uppercase', marginTop: 2 }}>
          {lang==='ar' ? 'F1 للعودة للطرفية' : 'F1 to terminal'}
        </div>
      </div>
      <span className="mono ltr-nums" style={{ fontSize: 13, fontWeight: 700 }}>{fmtEGP(total)}</span>
    </button>
  );
}

Object.assign(window, { DrugsScreen });
