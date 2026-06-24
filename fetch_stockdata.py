#!/usr/bin/env python3
"""
HYPR data fetch job — Yahoo Finance via yfinance (free, no API key, no AI)
Usage:
  python fetch_stockdata.py all            # first run — fetches everything
  python fetch_stockdata.py prices         # runs every 15 min — price, change, market cap, charts
  python fetch_stockdata.py fundamentals   # runs once daily — revenue, margin, P/E
Merges into stockData.json.
"""
import json, sys, time, os
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed — run: pip install yfinance")
    sys.exit(1)

FILE = "stockData.json"

SYMBOLS = [
    "NVDA","GOOGL","AAPL","MSFT","AMZN","TSM","AVGO","TSLA","META","MU","LLY","WMT","AMD","JPM",
    "ORCL","V","ASML","XOM","INTC","JNJ","TCEHY","CSCO","MA","COST","CAT","LRCX","ABBV","ARM",
    "PLTR","BAC","CVX","NFLX","AMAT","UNH","KO","RHHBY","GE","PG","MS","HSBC","HD","GS","BABA",
    "MRK","NVS","AZN","TXN","PM","IBM","LVMUY","DELL","SFTBY","QCOM","RY","NSRGY","GEV","KLAC",
    "TM","SNDK","RTX","SIEGY","LRLCY","WFC","SHEL","LIN","PANW","BHP","AXP","C","SAP","MUFG",
    "APP","TMUS","NVO","ANET","VZ","ADI","MCD","PEP","STX",
]

CHART_SPECS = [
    ("1D",  "1d",  "5m"),
    ("5D",  "5d",  "30m"),
    ("1M",  "1mo", "1d"),
    ("6M",  "6mo", "1d"),
    ("YTD", "ytd", "1d"),
    ("1Y",  "1y",  "1wk"),
    ("5Y",  "5y",  "1mo"),
    ("MAX", "max", "3mo"),
]

def load():
    if os.path.exists(FILE):
        try:
            with open(FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f)

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def fetch_price(sym):
    t = yf.Ticker(sym)
    fi = t.fast_info
    price  = getattr(fi, "last_price", None)
    prev   = getattr(fi, "previous_close", None)
    mktcap = getattr(fi, "market_cap", None)
    change_pct = None
    if price is not None and prev and prev != 0:
        change_pct = round((price - prev) / prev * 100, 2)
    return {
        "price":     round(price, 2) if price else None,
        "changePct": change_pct,
        "marketCap": round(mktcap / 1e9, 1) if mktcap else None,
    }

def fetch_fundamentals(sym):
    info = yf.Ticker(sym).info
    revenue = info.get("totalRevenue")
    gm      = info.get("grossMargins")
    pe      = info.get("trailingPE")
    return {
        "revenueTTM":  round(revenue / 1e9, 1) if revenue else None,
        "grossMargin": round(gm * 100, 1)       if gm      else None,
        "peTTM":       round(pe, 1)              if pe      else None,
    }

def fetch_charts(sym):
    out = {}
    for app_range, period, interval in CHART_SPECS:
        try:
            df = yf.Ticker(sym).history(period=period, interval=interval, auto_adjust=True)
            closes = df["Close"].dropna().tolist()
            if closes:
                out[app_range] = [round(c, 2) for c in closes]
        except Exception:
            pass
        time.sleep(0.1)
    return out

def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    do_prices = mode in ("prices", "all")
    do_fund   = mode in ("fundamentals", "all")

    data = load()
    data.setdefault("stocks", {})
    data.setdefault("charts", {})

    for sym in SYMBOLS:
        try:
            cur = data["stocks"].get(sym, {})
            if do_prices:
                cur.update(fetch_price(sym))
                data["charts"][sym] = fetch_charts(sym)
            if do_fund:
                cur.update(fetch_fundamentals(sym))
            data["stocks"][sym] = cur
            print(f"ok   {sym}")
        except Exception as e:
            print(f"skip {sym} — {e}")
        time.sleep(0.3)

    if do_prices:
        data["pricesAsOf"] = now_iso()
    if do_fund:
        data["fundamentalsAsOf"] = now_iso()
    data["asOf"] = now_iso()

    save(data)
    print(f"wrote {FILE} [mode={mode}] ({len(data['stocks'])} stocks)")

if __name__ == "__main__":
    main()
