import { useState, useMemo, useEffect, useCallback } from "react";

// ─── DEMO DATA GENERATOR ──────────────────────────────────────
function seededRandom(seed) {
  let s = seed;
  return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; };
}

const NIFTY_TICKERS = [
  "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN","BHARTIARTL",
  "ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT","MARUTI","SUNPHARMA",
  "TITAN","BAJFINANCE","DMART","NESTLEIND","NTPC","POWERGRID","ULTRACEMCO","WIPRO",
  "ONGC","JSWSTEEL","TATAMOTORS","ADANIENT","TATASTEEL","TECHM","HDFCLIFE",
  "BAJAJFINSV","GRASIM","INDUSINDBK","CIPLA","DIVISLAB","EICHERMOT","BPCL",
  "COALINDIA","DRREDDY","APOLLOHOSP","TATACONSUM","BRITANNIA","SBILIFE","M&M",
  "HEROMOTOCO","HINDALCO","ADANIPORTS","BAJAJ-AUTO","UPL","PIDILITIND","HAVELLS",
  "SHREECEM","AMBUJACEM","DLF","TRENT","GODREJCP","DABUR","MARICO","BERGEPAINT",
  "MUTHOOTFIN","LICI","IRCTC","ZOMATO","PAYTM","POLICYBZR","NYKAA","DELHIVERY",
  "PERSISTENT","COFORGE","LTIM","MPHASIS","NAVINFLUOR","ATUL","DEEPAKNTR",
  "PIIND","SRF","ASTRAL","POLYCAB","KEI","DIXON","AFFLE","HAPPSTMNDS",
  "ROUTE","KPITTECH","TATAELXSI","ANGELONE","CAMPUS","KAYNES","CLEAN",
  "SOLARINDS","AUROPHARMA","BIOCON","LUPIN","TORNTPHARM","ALKEM","IPCALAB",
  "LAURUSLABS","METROPOLIS","MAXHEALTH","FORTIS","MEDANTA","RAINBOW"
];

const EXIT_REASONS = {
  stop_loss: { label: "Stop Loss", color: "#ef4444" },
  trailing_stop_20ema: { label: "Trailing Stop (20 EMA)", color: "#f59e0b" },
  target_3r: { label: "Target 3R Hit", color: "#10b981" },
  target_2r: { label: "Target 2R Hit", color: "#22c55e" },
  time_stop: { label: "Time Stop", color: "#8b5cf6" },
  max_hold_120d: { label: "Max Hold (120d)", color: "#6b7280" },
  open: { label: "Open Position", color: "#3b82f6" },
};

function generateDemoData() {
  const data = {};
  const today = new Date();
  const rng = seededRandom(42);

  for (let d = 365; d >= 0; d--) {
    const date = new Date(today);
    date.setDate(date.getDate() - d);
    if (date.getDay() === 0 || date.getDay() === 6) continue;

    const dateStr = date.toISOString().split("T")[0];
    const signalCount = Math.floor(rng() * 8);
    if (signalCount === 0 && rng() > 0.3) continue;

    const usedTickers = new Set();
    const signals = [];

    for (let i = 0; i < Math.min(signalCount, 10); i++) {
      let ticker;
      do { ticker = NIFTY_TICKERS[Math.floor(rng() * NIFTY_TICKERS.length)]; }
      while (usedTickers.has(ticker));
      usedTickers.add(ticker);

      const basePrice = 200 + rng() * 4800;
      const entryPrice = Math.round(basePrice * 100) / 100;
      const stopPct = 0.07 + rng() * 0.02;
      const stopPrice = Math.round(entryPrice * (1 - stopPct) * 100) / 100;
      const risk = entryPrice - stopPrice;

      const outcomeRoll = rng();
      let exitReason, returnPct, holdingDays, exitPrice;

      if (outcomeRoll < 0.15) {
        exitReason = "target_3r"; returnPct = 20 + rng() * 15;
        holdingDays = 15 + Math.floor(rng() * 40);
      } else if (outcomeRoll < 0.35) {
        exitReason = "trailing_stop_20ema"; returnPct = 8 + rng() * 20;
        holdingDays = 10 + Math.floor(rng() * 50);
      } else if (outcomeRoll < 0.55) {
        exitReason = "stop_loss"; returnPct = -(6 + rng() * 3);
        holdingDays = 1 + Math.floor(rng() * 8);
      } else if (outcomeRoll < 0.7) {
        exitReason = "time_stop"; returnPct = -3 + rng() * 6;
        holdingDays = 15;
      } else if (d < 30) {
        exitReason = "open"; returnPct = -5 + rng() * 15;
        holdingDays = d;
      } else {
        exitReason = "trailing_stop_20ema"; returnPct = 5 + rng() * 12;
        holdingDays = 8 + Math.floor(rng() * 30);
      }

      exitPrice = Math.round(entryPrice * (1 + returnPct / 100) * 100) / 100;
      const exitDate = new Date(date);
      exitDate.setDate(exitDate.getDate() + holdingDays);

      const rs = 70 + Math.floor(rng() * 28);
      const volRatio = 1.3 + rng() * 1.5;
      const contrRanges = [
        Math.round((15 + rng() * 10) * 10) / 10,
        Math.round((6 + rng() * 8) * 10) / 10,
        Math.round((2 + rng() * 5) * 10) / 10,
      ];
      const score = rs * 0.3 + (10 - contrRanges[2]) * 3 + volRatio * 10 + 40;

      signals.push({
        ticker,
        date: dateStr,
        entry_price: entryPrice,
        score: Math.round(score * 10) / 10,
        trend_template: {
          close: entryPrice,
          sma50: Math.round(entryPrice * (0.95 + rng() * 0.03) * 100) / 100,
          sma150: Math.round(entryPrice * (0.88 + rng() * 0.06) * 100) / 100,
          sma200: Math.round(entryPrice * (0.82 + rng() * 0.08) * 100) / 100,
          rs_rating: rs,
          criteria_met: 8,
        },
        vcp: {
          contractions: 3,
          ranges: contrRanges,
          final_tightness: contrRanges[2],
          pivot: Math.round((entryPrice * 0.99) * 100) / 100,
          progressive: true,
          vol_declining: rng() > 0.3,
          atr_contracting: rng() > 0.4,
        },
        breakout: {
          close: entryPrice,
          volume: Math.floor(500000 + rng() * 5000000),
          avg_volume_50: Math.floor(400000 + rng() * 3000000),
          volume_ratio: Math.round(volRatio * 100) / 100,
        },
        backtest: {
          entry_price: entryPrice,
          exit_price: exitPrice,
          return_pct: Math.round(returnPct * 100) / 100,
          holding_days: holdingDays,
          exit_reason: exitReason,
          exit_date: exitDate.toISOString().split("T")[0],
          stop_price: stopPrice,
          target_2r: Math.round((entryPrice + 2 * risk) * 100) / 100,
          target_3r: Math.round((entryPrice + 3 * risk) * 100) / 100,
        },
      });
    }

    if (signals.length > 0) {
      signals.sort((a, b) => b.score - a.score);
      data[dateStr] = signals.slice(0, 10);
    }
  }
  return data;
}

// ─── COMPONENTS ────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 10,
      padding: "14px 18px",
      minWidth: 130,
    }}>
      <div style={{ fontSize: 11, color: "#888", letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: accent || "#e2e8f0", fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#666", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function ReturnBadge({ pct }) {
  const color = pct > 0 ? "#10b981" : pct < 0 ? "#ef4444" : "#888";
  return (
    <span style={{
      color,
      fontWeight: 700,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 13,
    }}>
      {pct > 0 ? "+" : ""}{pct.toFixed(2)}%
    </span>
  );
}

function SignalRow({ signal, expanded, onToggle }) {
  const bt = signal.backtest;
  const er = EXIT_REASONS[bt.exit_reason] || EXIT_REASONS.open;
  return (
    <div style={{
      background: expanded ? "rgba(255,255,255,0.04)" : "transparent",
      borderBottom: "1px solid rgba(255,255,255,0.04)",
      cursor: "pointer",
      transition: "background 0.15s",
    }}
      onClick={onToggle}
      onMouseEnter={e => { if(!expanded) e.currentTarget.style.background = "rgba(255,255,255,0.02)"; }}
      onMouseLeave={e => { if(!expanded) e.currentTarget.style.background = "transparent"; }}
    >
      <div style={{
        display: "grid",
        gridTemplateColumns: "50px 110px 95px 75px 80px 90px 75px 1fr",
        alignItems: "center",
        padding: "10px 16px",
        gap: 8,
        fontSize: 13,
      }}>
        <span style={{
          background: `hsl(${Math.min(signal.score, 100) * 1.2}, 70%, 25%)`,
          color: "#fff",
          borderRadius: 4,
          padding: "2px 6px",
          fontSize: 11,
          fontWeight: 700,
          textAlign: "center",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {signal.score.toFixed(0)}
        </span>
        <span style={{ fontWeight: 600, color: "#f1f5f9", letterSpacing: 0.5 }}>{signal.ticker}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#94a3b8" }}>₹{signal.entry_price.toLocaleString('en-IN')}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#64748b" }}>RS {signal.trend_template.rs_rating}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#64748b" }}>{signal.breakout.volume_ratio}x vol</span>
        <span style={{
          fontSize: 10,
          padding: "2px 6px",
          borderRadius: 3,
          background: er.color + "22",
          color: er.color,
          fontWeight: 600,
          textAlign: "center",
          whiteSpace: "nowrap",
        }}>
          {er.label}
        </span>
        <ReturnBadge pct={bt.return_pct} />
        <span style={{ fontSize: 11, color: "#475569", textAlign: "right" }}>
          {bt.holding_days}d · {expanded ? "▲" : "▼"}
        </span>
      </div>

      {expanded && (
        <div style={{
          padding: "0 16px 14px 16px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
          fontSize: 12,
          color: "#94a3b8",
        }}>
          <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: 10 }}>
            <div style={{ fontWeight: 700, color: "#cbd5e1", marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>TREND TEMPLATE</div>
            <div>50 SMA: ₹{signal.trend_template.sma50}</div>
            <div>150 SMA: ₹{signal.trend_template.sma150}</div>
            <div>200 SMA: ₹{signal.trend_template.sma200}</div>
            <div>Criteria: {signal.trend_template.criteria_met}/8 ✓</div>
          </div>
          <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: 10 }}>
            <div style={{ fontWeight: 700, color: "#cbd5e1", marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>VCP PATTERN</div>
            <div>Contractions: {signal.vcp.contractions}</div>
            <div>Ranges: {signal.vcp.ranges.join("% → ")}%</div>
            <div>Tightness: {signal.vcp.final_tightness}%</div>
            <div>Pivot: ₹{signal.vcp.pivot}</div>
          </div>
          <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 6, padding: 10 }}>
            <div style={{ fontWeight: 700, color: "#cbd5e1", marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>BACKTEST</div>
            <div>Entry: ₹{bt.entry_price} → Exit: ₹{bt.exit_price}</div>
            <div>Stop: ₹{bt.stop_price} | 2R: ₹{bt.target_2r}</div>
            <div>Exit: {bt.exit_date}</div>
            <div style={{ color: bt.return_pct > 0 ? "#10b981" : "#ef4444", fontWeight: 700 }}>
              Return: {bt.return_pct > 0 ? "+" : ""}{bt.return_pct}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── MAIN APP ──────────────────────────────────────────────────

export default function VCPDashboard() {
  const [demoData] = useState(() => generateDemoData());
  const [selectedDate, setSelectedDate] = useState(() => {
    const dates = Object.keys(demoData).sort();
    return dates[dates.length - 1] || new Date().toISOString().split("T")[0];
  });
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [backtestFrom, setBacktestFrom] = useState(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().split("T")[0];
  });
  const [backtestTo, setBacktestTo] = useState(() => new Date().toISOString().split("T")[0]);
  const [tab, setTab] = useState("scanner");
  const [jsonInput, setJsonInput] = useState("");
  const [liveData, setLiveData] = useState(null);

  const activeData = liveData || demoData;
  const allDates = useMemo(() => Object.keys(activeData).sort(), [activeData]);
  const signals = activeData[selectedDate] || [];

  // Navigate dates
  const navDate = useCallback((dir) => {
    const idx = allDates.indexOf(selectedDate);
    const next = idx + dir;
    if (next >= 0 && next < allDates.length) {
      setSelectedDate(allDates[next]);
      setExpandedIdx(null);
    }
  }, [allDates, selectedDate]);

  // Backtest stats
  const backtestStats = useMemo(() => {
    const filtered = allDates.filter(d => d >= backtestFrom && d <= backtestTo);
    const trades = filtered.flatMap(d => activeData[d] || []);
    if (trades.length === 0) return null;

    const returns = trades.map(t => t.backtest.return_pct);
    const winners = returns.filter(r => r > 0);
    const losers = returns.filter(r => r <= 0);

    // Compute equity curve (start with 100000)
    let equity = 100000;
    const curve = [{ date: backtestFrom, equity }];
    for (const d of filtered) {
      const sigs = activeData[d] || [];
      for (const s of sigs) {
        const allocPct = 1 / Math.max(sigs.length, 1);
        const tradeReturn = s.backtest.return_pct / 100;
        equity += equity * allocPct * tradeReturn;
      }
      curve.push({ date: d, equity: Math.round(equity) });
    }

    const exitReasonCounts = {};
    trades.forEach(t => {
      const r = t.backtest.exit_reason;
      exitReasonCounts[r] = (exitReasonCounts[r] || 0) + 1;
    });

    return {
      totalTrades: trades.length,
      winRate: (winners.length / trades.length * 100).toFixed(1),
      avgReturn: (returns.reduce((a,b) => a+b, 0) / returns.length).toFixed(2),
      avgWinner: winners.length ? (winners.reduce((a,b) => a+b, 0) / winners.length).toFixed(2) : "0",
      avgLoser: losers.length ? (losers.reduce((a,b) => a+b, 0) / losers.length).toFixed(2) : "0",
      best: Math.max(...returns).toFixed(2),
      worst: Math.min(...returns).toFixed(2),
      totalReturn: ((equity - 100000) / 100000 * 100).toFixed(2),
      finalEquity: Math.round(equity),
      profitFactor: losers.length ? (
        winners.reduce((a,b) => a+b, 0) / Math.abs(losers.reduce((a,b) => a+b, 0))
      ).toFixed(2) : "∞",
      exitReasons: exitReasonCounts,
      curve,
      days: filtered.length,
    };
  }, [activeData, allDates, backtestFrom, backtestTo]);

  // Load JSON data
  const loadJsonData = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (parsed.daily_signals) {
        setLiveData(parsed.daily_signals);
        const dates = Object.keys(parsed.daily_signals).sort();
        if (dates.length) setSelectedDate(dates[dates.length - 1]);
        setTab("scanner");
      }
    } catch (e) {
      alert("Invalid JSON. Please paste the output of vcp_scanner.py");
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0e17",
      color: "#e2e8f0",
      fontFamily: "'Satoshi', 'DM Sans', -apple-system, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        background: "linear-gradient(180deg, rgba(16,185,129,0.06) 0%, transparent 100%)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        padding: "16px 24px",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>
              <span style={{ color: "#10b981" }}>◆</span> VCP Breakout Scanner
            </h1>
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "#475569", letterSpacing: 0.5 }}>
              MINERVINI TREND TEMPLATE + VOLATILITY CONTRACTION · NIFTY 500
            </p>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {["scanner", "backtest", "import"].map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                background: tab === t ? "rgba(16,185,129,0.15)" : "transparent",
                border: tab === t ? "1px solid rgba(16,185,129,0.3)" : "1px solid rgba(255,255,255,0.06)",
                color: tab === t ? "#10b981" : "#64748b",
                borderRadius: 6,
                padding: "6px 14px",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: 0.5,
              }}>
                {t}
              </button>
            ))}
          </div>
        </div>

        {liveData && (
          <div style={{
            marginTop: 8,
            fontSize: 11,
            color: "#10b981",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
            Live data loaded · {allDates.length} trading days
            <button onClick={() => { setLiveData(null); setTab("scanner"); }} style={{
              background: "none", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444",
              borderRadius: 4, padding: "1px 8px", cursor: "pointer", fontSize: 10, marginLeft: 8,
            }}>Reset to Demo</button>
          </div>
        )}
      </div>

      {/* SCANNER TAB */}
      {tab === "scanner" && (
        <div style={{ padding: "16px 24px" }}>
          {/* Date Navigation */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 16,
            flexWrap: "wrap",
          }}>
            <button onClick={() => navDate(-1)} style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
              color: "#94a3b8", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 16,
            }}>←</button>

            <input
              type="date"
              value={selectedDate}
              onChange={e => {
                const v = e.target.value;
                const closest = allDates.reduce((p, c) => Math.abs(new Date(c) - new Date(v)) < Math.abs(new Date(p) - new Date(v)) ? c : p);
                setSelectedDate(closest);
                setExpandedIdx(null);
              }}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#e2e8f0",
                borderRadius: 6,
                padding: "6px 12px",
                fontSize: 14,
                fontFamily: "'JetBrains Mono', monospace",
                colorScheme: "dark",
              }}
            />

            <button onClick={() => navDate(1)} style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
              color: "#94a3b8", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 16,
            }}>→</button>

            <span style={{ fontSize: 12, color: "#475569" }}>
              {new Date(selectedDate).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short", year: "numeric" })}
            </span>

            <span style={{
              marginLeft: "auto",
              fontSize: 12,
              color: signals.length > 0 ? "#10b981" : "#ef4444",
              fontWeight: 600,
            }}>
              {signals.length} signal{signals.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Quick Stats */}
          {signals.length > 0 && (
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <StatCard label="Signals" value={signals.length} sub="max 10" />
              <StatCard
                label="Avg Score"
                value={(signals.reduce((a,s) => a + s.score, 0) / signals.length).toFixed(0)}
              />
              <StatCard
                label="Avg Return"
                value={(signals.reduce((a,s) => a + s.backtest.return_pct, 0) / signals.length).toFixed(1) + "%"}
                accent={signals.reduce((a,s) => a + s.backtest.return_pct, 0) > 0 ? "#10b981" : "#ef4444"}
              />
              <StatCard
                label="Win Rate"
                value={(signals.filter(s => s.backtest.return_pct > 0).length / signals.length * 100).toFixed(0) + "%"}
                accent="#f59e0b"
              />
              <StatCard
                label="Best"
                value={Math.max(...signals.map(s => s.backtest.return_pct)).toFixed(1) + "%"}
                accent="#10b981"
              />
            </div>
          )}

          {/* Signal Table */}
          <div style={{
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10,
            overflow: "hidden",
          }}>
            {/* Header */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "50px 110px 95px 75px 80px 90px 75px 1fr",
              padding: "8px 16px",
              gap: 8,
              fontSize: 10,
              color: "#475569",
              fontWeight: 700,
              letterSpacing: 1,
              textTransform: "uppercase",
              background: "rgba(255,255,255,0.02)",
              borderBottom: "1px solid rgba(255,255,255,0.04)",
            }}>
              <span>Score</span><span>Ticker</span><span>Entry</span><span>RS</span>
              <span>Volume</span><span>Exit Type</span><span>Return</span><span style={{ textAlign: "right" }}>Hold</span>
            </div>

            {signals.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", color: "#334155" }}>
                <div style={{ fontSize: 36, marginBottom: 8 }}>∅</div>
                <div style={{ fontSize: 14 }}>No VCP breakout signals on this date</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>Use ← → to navigate to dates with signals</div>
              </div>
            ) : (
              signals.map((s, i) => (
                <SignalRow
                  key={s.ticker + s.date}
                  signal={s}
                  expanded={expandedIdx === i}
                  onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)}
                />
              ))
            )}
          </div>
        </div>
      )}

      {/* BACKTEST TAB */}
      {tab === "backtest" && (
        <div style={{ padding: "16px 24px" }}>
          {/* Date Range Selection */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 20,
            flexWrap: "wrap",
          }}>
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>FROM</span>
            <input type="date" value={backtestFrom} onChange={e => setBacktestFrom(e.target.value)} style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#e2e8f0", borderRadius: 6, padding: "6px 12px", fontSize: 13,
              fontFamily: "'JetBrains Mono', monospace", colorScheme: "dark",
            }} />
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>TO</span>
            <input type="date" value={backtestTo} onChange={e => setBacktestTo(e.target.value)} style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#e2e8f0", borderRadius: 6, padding: "6px 12px", fontSize: 13,
              fontFamily: "'JetBrains Mono', monospace", colorScheme: "dark",
            }} />
            {/* Quick presets */}
            {[
              { label: "1M", days: 30 },
              { label: "3M", days: 90 },
              { label: "6M", days: 180 },
              { label: "1Y", days: 365 },
            ].map(p => (
              <button key={p.label} onClick={() => {
                const to = new Date();
                const from = new Date();
                from.setDate(from.getDate() - p.days);
                setBacktestFrom(from.toISOString().split("T")[0]);
                setBacktestTo(to.toISOString().split("T")[0]);
              }} style={{
                background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                color: "#94a3b8", borderRadius: 4, padding: "4px 10px", cursor: "pointer", fontSize: 11,
                fontWeight: 600,
              }}>
                {p.label}
              </button>
            ))}
          </div>

          {backtestStats && (
            <>
              {/* Key Metrics */}
              <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
                <StatCard label="Total Trades" value={backtestStats.totalTrades} sub={`${backtestStats.days} trading days`} />
                <StatCard label="Win Rate" value={backtestStats.winRate + "%"} accent="#f59e0b" />
                <StatCard label="Avg Return" value={backtestStats.avgReturn + "%"}
                  accent={parseFloat(backtestStats.avgReturn) > 0 ? "#10b981" : "#ef4444"} />
                <StatCard label="Profit Factor" value={backtestStats.profitFactor} accent="#8b5cf6" />
                <StatCard
                  label="Portfolio Return"
                  value={backtestStats.totalReturn + "%"}
                  accent={parseFloat(backtestStats.totalReturn) > 0 ? "#10b981" : "#ef4444"}
                  sub={`INR 1L → INR ${(backtestStats.finalEquity / 1000).toFixed(0)}K`}
                />
              </div>

              {/* Detail Cards */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
                marginBottom: 16,
              }}>
                <div style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 10,
                  padding: 16,
                }}>
                  <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: 1, marginBottom: 10 }}>RETURN DISTRIBUTION</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                    <div>Avg Winner: <span style={{ color: "#10b981", fontWeight: 700 }}>+{backtestStats.avgWinner}%</span></div>
                    <div>Avg Loser: <span style={{ color: "#ef4444", fontWeight: 700 }}>{backtestStats.avgLoser}%</span></div>
                    <div>Best Trade: <span style={{ color: "#10b981", fontWeight: 700 }}>+{backtestStats.best}%</span></div>
                    <div>Worst Trade: <span style={{ color: "#ef4444", fontWeight: 700 }}>{backtestStats.worst}%</span></div>
                  </div>
                </div>

                <div style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 10,
                  padding: 16,
                }}>
                  <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: 1, marginBottom: 10 }}>EXIT REASONS</div>
                  <div style={{ fontSize: 12 }}>
                    {Object.entries(backtestStats.exitReasons).sort((a,b) => b[1] - a[1]).map(([reason, count]) => {
                      const er = EXIT_REASONS[reason] || { label: reason, color: "#888" };
                      return (
                        <div key={reason} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ color: er.color }}>{er.label}</span>
                          <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#64748b" }}>
                            {count} ({(count / backtestStats.totalTrades * 100).toFixed(0)}%)
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Equity Curve (ASCII-style bar chart) */}
              <div style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 10,
                padding: 16,
              }}>
                <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: 1, marginBottom: 12 }}>
                  EQUITY CURVE (INR 1,00,000 START)
                </div>
                <div style={{ height: 120, display: "flex", alignItems: "flex-end", gap: 1 }}>
                  {(() => {
                    const curve = backtestStats.curve;
                    const step = Math.max(1, Math.floor(curve.length / 80));
                    const sampled = curve.filter((_, i) => i % step === 0);
                    const min = Math.min(...sampled.map(p => p.equity));
                    const max = Math.max(...sampled.map(p => p.equity));
                    const range = max - min || 1;
                    return sampled.map((p, i) => (
                      <div key={i} style={{
                        flex: 1,
                        minWidth: 2,
                        height: Math.max(2, ((p.equity - min) / range) * 110),
                        background: p.equity >= 100000
                          ? `rgba(16,185,129,${0.3 + (p.equity - min) / range * 0.7})`
                          : `rgba(239,68,68,${0.3 + (max - p.equity) / range * 0.7})`,
                        borderRadius: "2px 2px 0 0",
                        transition: "height 0.3s",
                      }}
                        title={`${p.date}: INR ${p.equity.toLocaleString('en-IN')}`}
                      />
                    ));
                  })()}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#475569", marginTop: 4 }}>
                  <span>{backtestFrom}</span>
                  <span>INR {backtestStats.finalEquity.toLocaleString('en-IN')}</span>
                  <span>{backtestTo}</span>
                </div>
              </div>

              {/* Strategy Info */}
              <div style={{
                marginTop: 16,
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.04)",
                borderRadius: 10,
                padding: 16,
                fontSize: 12,
                color: "#64748b",
                lineHeight: 1.8,
              }}>
                <div style={{ fontWeight: 700, color: "#94a3b8", marginBottom: 6, fontSize: 11, letterSpacing: 1 }}>EXIT STRATEGY RULES</div>
                <span style={{ color: "#ef4444" }}>■</span> Stop Loss: 7-8% below entry price ·{" "}
                <span style={{ color: "#10b981" }}>■</span> Target: 2R-3R risk-reward ratio ·{" "}
                <span style={{ color: "#f59e0b" }}>■</span> Trailing Stop: 20-day EMA (activated after 2R reached) ·{" "}
                <span style={{ color: "#8b5cf6" }}>■</span> Time Stop: Exit if no progress in 15 trading days ·{" "}
                <span style={{ color: "#6b7280" }}>■</span> Max Hold: 120 trading days
              </div>
            </>
          )}
        </div>
      )}

      {/* IMPORT TAB */}
      {tab === "import" && (
        <div style={{ padding: "16px 24px" }}>
          <div style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10,
            padding: 20,
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Import Live Scanner Data</div>
            <p style={{ fontSize: 12, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
              Run <code style={{ background: "rgba(255,255,255,0.08)", padding: "2px 6px", borderRadius: 3, fontSize: 11 }}>
              python vcp_scanner.py</code> locally, then paste the contents of <code style={{
                background: "rgba(255,255,255,0.08)", padding: "2px 6px", borderRadius: 3, fontSize: 11,
              }}>vcp_scan_results.json</code> below.
            </p>

            <textarea
              value={jsonInput}
              onChange={e => setJsonInput(e.target.value)}
              placeholder='Paste JSON here...'
              style={{
                width: "100%",
                height: 200,
                background: "rgba(0,0,0,0.3)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#94a3b8",
                padding: 12,
                fontSize: 12,
                fontFamily: "'JetBrains Mono', monospace",
                resize: "vertical",
                boxSizing: "border-box",
              }}
            />

            <button onClick={loadJsonData} style={{
              marginTop: 12,
              background: "rgba(16,185,129,0.15)",
              border: "1px solid rgba(16,185,129,0.3)",
              color: "#10b981",
              borderRadius: 6,
              padding: "8px 20px",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}>
              Load Data
            </button>

            <div style={{
              marginTop: 20,
              padding: 16,
              background: "rgba(0,0,0,0.2)",
              borderRadius: 8,
              fontSize: 12,
              color: "#64748b",
              lineHeight: 1.8,
            }}>
              <div style={{ fontWeight: 700, color: "#94a3b8", marginBottom: 6, letterSpacing: 1, fontSize: 11 }}>SETUP INSTRUCTIONS</div>
              1. Install dependencies: <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2 }}>pip install yfinance niftystocks pandas numpy</code><br/>
              2. Run scanner: <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2 }}>python vcp_scanner.py</code><br/>
              3. Copy contents of <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 4px", borderRadius: 2 }}>vcp_scan_results.json</code> and paste above<br/>
              4. Click "Load Data" to switch from demo to live data<br/>
              <br/>
              <span style={{ color: "#f59e0b" }}>⚠</span> Scanner takes 15-30 mins for full Nifty 500 scan. Schedule via cron for daily updates.
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        padding: "12px 24px",
        borderTop: "1px solid rgba(255,255,255,0.04)",
        fontSize: 10,
        color: "#334155",
        textAlign: "center",
        marginTop: 20,
      }}>
        Minervini VCP Scanner · Trend Template (8-point) + Volatility Contraction Pattern + Volume Breakout · Exit: 8% SL / 2R-3R Target / 20 EMA Trail / 15d Time Stop · Educational purposes only · Not financial advice
      </div>
    </div>
  );
}
