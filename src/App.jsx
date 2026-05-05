import { useState, useMemo, useEffect, useCallback } from "react";

const EXIT_META = {
  stop_loss:    { label: "Stop Loss (-8%)",    color: "#ef4444" },
  trail_20ema:  { label: "Trail 20 EMA",       color: "#f59e0b" },
  target_3r:    { label: "Target 3R",          color: "#10b981" },
  time_stop:    { label: "Time Stop (15d)",    color: "#8b5cf6" },
  max_hold:     { label: "Max Hold (120d)",    color: "#6b7280" },
};

function fmt(n) {
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// ─── Stat Card ───
function Stat({ label, value, sub, color }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 8, padding: "12px 14px", minWidth: 120, flex: "1 1 120px",
    }}>
      <div style={{ fontSize: 10, color: "#64748b", letterSpacing: 1, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color || "#e2e8f0", fontFamily: "mono", marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "#475569", marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

// ─── Signal Row ───
function Row({ s, open, toggle }) {
  const er = EXIT_META[s.bt.reason] || { label: s.bt.reason, color: "#888" };
  const pos = s.bt.return_pct > 0;
  return (
    <div style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div onClick={toggle} style={{
        display: "grid",
        gridTemplateColumns: "44px 100px 90px 60px 70px 100px 75px 50px",
        alignItems: "center", padding: "9px 14px", gap: 6, fontSize: 12.5,
        cursor: "pointer", background: open ? "rgba(255,255,255,0.03)" : "transparent",
      }}>
        <span style={{
          background: `hsl(${Math.min(s.score, 100) * 1.2},65%,22%)`,
          color: "#fff", borderRadius: 3, textAlign: "center",
          fontSize: 10, fontWeight: 700, padding: "2px 0", fontFamily: "mono",
        }}>{s.score.toFixed(0)}</span>
        <span style={{ fontWeight: 600, color: "#f1f5f9" }}>{s.ticker}</span>
        <span style={{ fontFamily: "mono", color: "#94a3b8" }}>₹{fmt(s.entry_price)}</span>
        <span style={{ fontFamily: "mono", color: "#64748b", fontSize: 11 }}>RS {s.tt.rs}</span>
        <span style={{ fontFamily: "mono", color: "#64748b", fontSize: 11 }}>{s.bo.vol_ratio}x</span>
        <span style={{
          fontSize: 9.5, padding: "2px 5px", borderRadius: 3, fontWeight: 600,
          background: er.color + "20", color: er.color, textAlign: "center",
        }}>{er.label}</span>
        <span style={{ fontFamily: "mono", fontWeight: 700, color: pos ? "#10b981" : "#ef4444" }}>
          {pos ? "+" : ""}{s.bt.return_pct}%
        </span>
        <span style={{ fontSize: 10, color: "#475569", textAlign: "right" }}>{s.bt.days}d</span>
      </div>

      {open && (
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10,
          padding: "0 14px 12px", fontSize: 11.5, color: "#94a3b8",
        }}>
          {[
            {
              title: "TREND TEMPLATE",
              rows: [
                `Close: ₹${fmt(s.tt.price)}`,
                `50 SMA: ₹${fmt(s.tt.sma50)}`,
                `150 SMA: ₹${fmt(s.tt.sma150)}`,
                `200 SMA: ₹${fmt(s.tt.sma200)}`,
                `52w High: ₹${fmt(s.tt.high_52w)} (${s.tt.pct_from_high}%)`,
                `52w Low: ₹${fmt(s.tt.low_52w)} (+${s.tt.pct_from_low}%)`,
              ],
            },
            {
              title: "VCP PATTERN",
              rows: [
                `Contractions: ${s.vcp.num_contractions}`,
                `Ranges: ${s.vcp.ranges.join("% → ")}%`,
                `Tightness: ${s.vcp.final_tightness}%`,
                `Pivot: ₹${fmt(s.vcp.pivot)}`,
                `Progressive: ${s.vcp.progressive ? "✓" : "✗"}`,
                `Vol declining: ${s.vcp.vol_declining ? "✓" : "✗"}`,
              ],
            },
            {
              title: "BACKTEST",
              rows: [
                `Entry: ₹${fmt(s.bt.entry_price || s.entry_price)}`,
                `Exit: ₹${fmt(s.bt.exit_price)} (${s.bt.exit_date})`,
                `Return: ${s.bt.return_pct > 0 ? "+" : ""}${s.bt.return_pct}%`,
                `Days held: ${s.bt.days}`,
                `Reason: ${er.label}`,
                `Volume: ${(s.bo.volume / 100000).toFixed(1)}L (${s.bo.vol_ratio}x avg)`,
              ],
            },
          ].map(sec => (
            <div key={sec.title} style={{ background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: 8 }}>
              <div style={{ fontSize: 9.5, fontWeight: 700, color: "#cbd5e1", letterSpacing: 1, marginBottom: 4 }}>{sec.title}</div>
              {sec.rows.map((r, i) => <div key={i}>{r}</div>)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main ───
export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selDate, setSelDate] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [tab, setTab] = useState("scanner");
  const [btFrom, setBtFrom] = useState("");
  const [btTo, setBtTo] = useState("");
  const [jsonText, setJsonText] = useState("");

  // Load data.json on mount
  useEffect(() => {
    fetch("/data.json")
      .then(r => {
        if (!r.ok) throw new Error("No data.json found. Run scanner.py first, or use Import tab.");
        return r.json();
      })
      .then(d => {
        loadParsed(d);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  function loadParsed(d) {
    const daily = d.daily || d.daily_signals || {};
    setData({ ...d, daily });
    const dates = Object.keys(daily).sort();
    if (dates.length) {
      setSelDate(dates[dates.length - 1]);
      const y1 = new Date(dates[dates.length - 1]);
      y1.setFullYear(y1.getFullYear() - 1);
      setBtFrom(y1.toISOString().split("T")[0]);
      setBtTo(dates[dates.length - 1]);
    }
    setError(null);
  }

  const allDates = useMemo(() => data ? Object.keys(data.daily).sort() : [], [data]);
  const signals = data && selDate ? (data.daily[selDate] || []) : [];

  const nav = useCallback((dir) => {
    const i = allDates.indexOf(selDate) + dir;
    if (i >= 0 && i < allDates.length) { setSelDate(allDates[i]); setExpanded(null); }
  }, [allDates, selDate]);

  // Backtest computation
  const bt = useMemo(() => {
    if (!data || !btFrom || !btTo) return null;
    const dates = allDates.filter(d => d >= btFrom && d <= btTo);
    const trades = dates.flatMap(d => data.daily[d] || []);
    if (!trades.length) return null;

    const rets = trades.map(t => t.bt.return_pct);
    const w = rets.filter(r => r > 0);
    const l = rets.filter(r => r <= 0);

    let eq = 100000;
    const curve = [];
    for (const d of dates) {
      const sigs = data.daily[d] || [];
      for (const s of sigs) {
        eq += eq * (1 / Math.max(sigs.length, 1)) * (s.bt.return_pct / 100);
      }
      curve.push({ d, eq: Math.round(eq) });
    }

    const reasons = {};
    trades.forEach(t => { reasons[t.bt.reason] = (reasons[t.bt.reason] || 0) + 1; });

    return {
      n: trades.length, days: dates.length,
      wr: (w.length / trades.length * 100).toFixed(1),
      avgRet: (rets.reduce((a,b) => a+b, 0) / rets.length).toFixed(2),
      avgW: w.length ? (w.reduce((a,b) => a+b, 0) / w.length).toFixed(2) : "0",
      avgL: l.length ? (l.reduce((a,b) => a+b, 0) / l.length).toFixed(2) : "0",
      best: Math.max(...rets).toFixed(2),
      worst: Math.min(...rets).toFixed(2),
      total: ((eq - 100000) / 1000).toFixed(1),
      eq, curve, reasons,
      pf: l.length ? (w.reduce((a,b)=>a+b,0) / Math.abs(l.reduce((a,b)=>a+b,0))).toFixed(2) : "∞",
    };
  }, [data, allDates, btFrom, btTo]);

  // ─── Render ───
  const tabBtn = (t, label) => (
    <button key={t} onClick={() => setTab(t)} style={{
      background: tab === t ? "rgba(16,185,129,0.15)" : "transparent",
      border: `1px solid ${tab === t ? "rgba(16,185,129,0.3)" : "rgba(255,255,255,0.06)"}`,
      color: tab === t ? "#10b981" : "#64748b",
      borderRadius: 5, padding: "5px 12px", cursor: "pointer",
      fontSize: 11.5, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5,
    }}>{label}</button>
  );

  return (
    <div style={{
      minHeight: "100vh", background: "#0a0e17", color: "#e2e8f0",
      fontFamily: "'DM Sans', -apple-system, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        background: "linear-gradient(180deg, rgba(16,185,129,0.05) 0%, transparent 100%)",
        borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "14px 20px",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
              <span style={{ color: "#10b981" }}>◆</span> VCP Breakout Scanner
            </h1>
            <p style={{ margin: 0, fontSize: 10, color: "#475569", letterSpacing: 0.5 }}>
              MINERVINI TREND TEMPLATE · VOLATILITY CONTRACTION · NIFTY 500
              {data && ` · ${data.universe} stocks · ${allDates.length} days`}
            </p>
          </div>
          <div style={{ display: "flex", gap: 3 }}>
            {tabBtn("scanner", "Scanner")}
            {tabBtn("backtest", "Backtest")}
            {tabBtn("import", "Import")}
          </div>
        </div>
      </div>

      <div style={{ padding: "14px 20px" }}>

        {/* Loading / Error */}
        {loading && <div style={{ textAlign: "center", padding: 60, color: "#475569" }}>Loading data.json...</div>}

        {error && !data && (
          <div style={{
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 8, padding: 20, textAlign: "center", color: "#f87171",
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{error}</div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>
              Use the <b>Import</b> tab to paste scanner output, or run <code style={{
                background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2,
              }}>python scanner.py</code> and commit <code style={{
                background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2,
              }}>public/data.json</code> to your repo.
            </div>
          </div>
        )}

        {/* SCANNER TAB */}
        {tab === "scanner" && data && (
          <>
            {/* Date nav */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
              <button onClick={() => nav(-1)} style={navBtnStyle}>←</button>
              <input type="date" value={selDate || ""} onChange={e => {
                const v = e.target.value;
                const closest = allDates.reduce((p, c) =>
                  Math.abs(new Date(c) - new Date(v)) < Math.abs(new Date(p) - new Date(v)) ? c : p
                );
                setSelDate(closest); setExpanded(null);
              }} style={dateInputStyle} />
              <button onClick={() => nav(1)} style={navBtnStyle}>→</button>
              <span style={{ fontSize: 11.5, color: "#475569" }}>
                {selDate && new Date(selDate).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
              </span>
              <span style={{
                marginLeft: "auto", fontSize: 12, fontWeight: 600,
                color: signals.length ? "#10b981" : "#ef4444",
              }}>
                {signals.length} signal{signals.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Day stats */}
            {signals.length > 0 && (
              <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
                <Stat label="Signals" value={signals.length} />
                <Stat label="Avg Score" value={(signals.reduce((a,s) => a+s.score,0)/signals.length).toFixed(0)} />
                <Stat label="Avg Return"
                  value={(signals.reduce((a,s)=>a+s.bt.return_pct,0)/signals.length).toFixed(1)+"%"}
                  color={signals.reduce((a,s)=>a+s.bt.return_pct,0) > 0 ? "#10b981" : "#ef4444"} />
                <Stat label="Win Rate"
                  value={(signals.filter(s=>s.bt.return_pct>0).length/signals.length*100).toFixed(0)+"%"}
                  color="#f59e0b" />
              </div>
            )}

            {/* Table */}
            <div style={{ border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, overflow: "hidden" }}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "44px 100px 90px 60px 70px 100px 75px 50px",
                padding: "7px 14px", gap: 6, fontSize: 9.5, color: "#475569",
                fontWeight: 700, letterSpacing: 1, textTransform: "uppercase",
                background: "rgba(255,255,255,0.02)", borderBottom: "1px solid rgba(255,255,255,0.04)",
              }}>
                <span>Score</span><span>Ticker</span><span>Entry</span><span>RS</span>
                <span>Vol</span><span>Exit</span><span>Return</span><span style={{textAlign:"right"}}>Days</span>
              </div>

              {signals.length === 0 ? (
                <div style={{ padding: 40, textAlign: "center", color: "#334155" }}>
                  <div style={{ fontSize: 28, marginBottom: 6 }}>∅</div>
                  <div style={{ fontSize: 13 }}>No VCP breakouts on this date</div>
                  <div style={{ fontSize: 11, marginTop: 3 }}>Use ← → to find dates with signals</div>
                </div>
              ) : signals.map((s, i) => (
                <Row key={s.ticker} s={s} open={expanded === i} toggle={() => setExpanded(expanded === i ? null : i)} />
              ))}
            </div>
          </>
        )}

        {/* BACKTEST TAB */}
        {tab === "backtest" && data && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <span style={labelStyle}>FROM</span>
              <input type="date" value={btFrom} onChange={e => setBtFrom(e.target.value)} style={dateInputStyle} />
              <span style={labelStyle}>TO</span>
              <input type="date" value={btTo} onChange={e => setBtTo(e.target.value)} style={dateInputStyle} />
              {[["1M",30],["3M",90],["6M",180],["1Y",365]].map(([l,d]) => (
                <button key={l} onClick={() => {
                  const to = allDates[allDates.length-1] || new Date().toISOString().split("T")[0];
                  const from = new Date(to); from.setDate(from.getDate()-d);
                  setBtFrom(from.toISOString().split("T")[0]); setBtTo(to);
                }} style={presetBtnStyle}>{l}</button>
              ))}
            </div>

            {bt && (
              <>
                <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
                  <Stat label="Total Trades" value={bt.n} sub={`${bt.days} days`} />
                  <Stat label="Win Rate" value={bt.wr + "%"} color="#f59e0b" />
                  <Stat label="Avg Return" value={bt.avgRet + "%"} color={+bt.avgRet > 0 ? "#10b981" : "#ef4444"} />
                  <Stat label="Profit Factor" value={bt.pf} color="#8b5cf6" />
                  <Stat label="Portfolio" value={bt.total + "K"}
                    color={bt.eq >= 100000 ? "#10b981" : "#ef4444"}
                    sub={`₹1L → ₹${fmt(bt.eq)}`} />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
                  <div style={cardStyle}>
                    <div style={cardTitle}>RETURNS</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 12.5 }}>
                      <div>Avg winner: <b style={{color:"#10b981"}}>+{bt.avgW}%</b></div>
                      <div>Avg loser: <b style={{color:"#ef4444"}}>{bt.avgL}%</b></div>
                      <div>Best: <b style={{color:"#10b981"}}>+{bt.best}%</b></div>
                      <div>Worst: <b style={{color:"#ef4444"}}>{bt.worst}%</b></div>
                    </div>
                  </div>
                  <div style={cardStyle}>
                    <div style={cardTitle}>EXIT REASONS</div>
                    {Object.entries(bt.reasons).sort((a,b) => b[1]-a[1]).map(([r, c]) => {
                      const m = EXIT_META[r] || { label: r, color: "#888" };
                      return (
                        <div key={r} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
                          <span style={{ color: m.color }}>{m.label}</span>
                          <span style={{ fontFamily: "mono", color: "#64748b" }}>{c} ({(c/bt.n*100).toFixed(0)}%)</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Equity curve */}
                <div style={cardStyle}>
                  <div style={cardTitle}>EQUITY CURVE (₹1,00,000 START)</div>
                  <div style={{ height: 100, display: "flex", alignItems: "flex-end", gap: 1 }}>
                    {(() => {
                      const c = bt.curve;
                      const step = Math.max(1, Math.floor(c.length / 100));
                      const s = c.filter((_, i) => i % step === 0);
                      const mn = Math.min(...s.map(p => p.eq));
                      const mx = Math.max(...s.map(p => p.eq));
                      const rng = mx - mn || 1;
                      return s.map((p, i) => (
                        <div key={i} title={`${p.d}: ₹${fmt(p.eq)}`} style={{
                          flex: 1, minWidth: 2, borderRadius: "2px 2px 0 0",
                          height: Math.max(2, ((p.eq - mn) / rng) * 95),
                          background: p.eq >= 100000
                            ? `rgba(16,185,129,${0.3 + (p.eq-mn)/rng*0.7})`
                            : `rgba(239,68,68,${0.3 + (mx-p.eq)/rng*0.7})`,
                        }} />
                      ));
                    })()}
                  </div>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:10, color:"#475569", marginTop:4 }}>
                    <span>{btFrom}</span>
                    <span>₹{fmt(bt.eq)}</span>
                    <span>{btTo}</span>
                  </div>
                </div>

                <div style={{ ...cardStyle, marginTop: 10, fontSize: 11.5, color: "#64748b", lineHeight: 1.8 }}>
                  <div style={{ ...cardTitle, marginBottom: 4 }}>EXIT RULES</div>
                  <span style={{color:"#ef4444"}}>■</span> Stop Loss: 8% below entry ·{" "}
                  <span style={{color:"#10b981"}}>■</span> Target: 3R (risk × 3) ·{" "}
                  <span style={{color:"#f59e0b"}}>■</span> Trailing: 20 EMA after 2R ·{" "}
                  <span style={{color:"#8b5cf6"}}>■</span> Time: 15d no progress ·{" "}
                  <span style={{color:"#6b7280"}}>■</span> Max: 120 days
                </div>
              </>
            )}
          </>
        )}

        {/* IMPORT TAB */}
        {tab === "import" && (
          <div style={cardStyle}>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Import Scanner Output</div>
            <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 14px", lineHeight: 1.6 }}>
              Run <code style={codeStyle}>python scanner.py</code> locally, then paste contents
              of <code style={codeStyle}>vcp_scan_results.json</code> below.
            </p>
            <textarea value={jsonText} onChange={e => setJsonText(e.target.value)}
              placeholder="Paste JSON output here..."
              style={{
                width: "100%", height: 180, background: "rgba(0,0,0,0.3)",
                border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6,
                color: "#94a3b8", padding: 10, fontSize: 12, fontFamily: "monospace",
                resize: "vertical", boxSizing: "border-box",
              }}
            />
            <button onClick={() => {
              try {
                const parsed = JSON.parse(jsonText);
                loadParsed(parsed);
                setTab("scanner");
              } catch { alert("Invalid JSON"); }
            }} style={{
              marginTop: 10, background: "rgba(16,185,129,0.15)",
              border: "1px solid rgba(16,185,129,0.3)", color: "#10b981",
              borderRadius: 5, padding: "7px 18px", cursor: "pointer", fontSize: 12, fontWeight: 600,
            }}>Load Data</button>

            <div style={{
              marginTop: 18, padding: 14, background: "rgba(0,0,0,0.2)",
              borderRadius: 6, fontSize: 12, color: "#64748b", lineHeight: 1.8,
            }}>
              <div style={{ fontWeight: 700, color: "#94a3b8", marginBottom: 4, letterSpacing: 1, fontSize: 10.5 }}>SETUP</div>
              1. <code style={codeStyle}>pip install yfinance pandas numpy</code><br/>
              2. <code style={codeStyle}>python scanner.py</code> (takes 15-30 min for 200+ stocks)<br/>
              3. Copy <code style={codeStyle}>vcp_scan_results.json</code> contents → paste above → Load<br/>
              <br/>
              <b>For auto-updates:</b> Push <code style={codeStyle}>public/data.json</code> to GitHub.
              Vercel auto-deploys. Use GitHub Actions to automate the scanner daily.
            </div>
          </div>
        )}
      </div>

      <div style={{
        padding: "10px 20px", borderTop: "1px solid rgba(255,255,255,0.03)",
        fontSize: 9.5, color: "#1e293b", textAlign: "center", marginTop: 16,
      }}>
        VCP Scanner · Minervini Trend Template + Volatility Contraction · yfinance daily close + volume · Educational only · Not financial advice
      </div>
    </div>
  );
}

// ─── Shared styles ───
const navBtnStyle = {
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
  color: "#94a3b8", borderRadius: 5, padding: "5px 11px", cursor: "pointer", fontSize: 15,
};
const dateInputStyle = {
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
  color: "#e2e8f0", borderRadius: 5, padding: "5px 10px", fontSize: 13,
  fontFamily: "monospace", colorScheme: "dark",
};
const labelStyle = { fontSize: 11, color: "#64748b", fontWeight: 600 };
const presetBtnStyle = {
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
  color: "#94a3b8", borderRadius: 4, padding: "3px 9px", cursor: "pointer",
  fontSize: 10.5, fontWeight: 600,
};
const cardStyle = {
  background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: 8, padding: 14,
};
const cardTitle = {
  fontSize: 9.5, fontWeight: 700, color: "#475569", letterSpacing: 1, marginBottom: 8,
};
const codeStyle = {
  background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2, fontSize: 11,
};
