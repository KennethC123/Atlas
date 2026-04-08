# CLAUDE.md — KK Control Panel

AI agent instructions for working on this codebase.

## What This Is

KK Control Panel is Ken's personal OpenClaw ops dashboard. FastAPI + vanilla JS, runs on port 3201.
Read README.md for full context including acceptance criteria, stack, and tab descriptions.

## Key Paths (on the VM)

- **LAT S4 live log:** `~/workspace/backtests/lat-s4/live_log.jsonl`
- **LAT S4 live state:** `~/workspace/backtests/lat-s4/live_state.json`
- **Strategy 3 screener:** `~/workspace/strategy3-screener/screener.js`
- **Finance repo:** `~/workspace/nansen-finance-restricted/`
- **Workspace root:** `~/workspace/` (i.e. `~/.openclaw/workspace/`)
- **Notes file:** `~/workspace/kk-control/notes.md`

## CLI Tools Available

- `gh` — GitHub CLI (authed as KennethC123, has access to nansen-ai repos)
- `openclaw` — OpenClaw CLI
- `openclaw cron list --json` — list all cron jobs
- `openclaw sessions list --json` — list recent sessions
- `openclaw status` — agent health
- `node ~/workspace/strategy3-screener/screener.js --json` — screener signals

## LAT S4 Data Format

`live_log.jsonl` — one JSON object per line, each is a trade event:
```json
{"timestamp": "...", "type": "entry|exit", "token": "PYTH", "chain": "solana|base",
 "price_usd": 0.123, "usdc_amount": 10.0, "token_amount": 81.3, "tx_hash": "...",
 "reason": "RSI<40 + EMA filter", "pnl_pct": null}
```
Exit events include: `pnl_pct`, `exit_price_usd`, `hold_hours`

`live_state.json` — current positions + wallet balances:
```json
{"positions": {...}, "balances": {"base_usdc": 42.74, "base_eth": 4.34, "sol_usdc": 45.25, "sol_sol": 4.03}}
```
Starting balance: $100 ($50 Base + $50 Solana)

## GitHub Queries

```bash
# Finance PRs
gh pr list --repo nansen-ai/nansen-finance-restricted --state open --json number,title,author,createdAt,url

# Finance issues
gh issue list --repo nansen-ai/nansen-finance-restricted --state open --json number,title,labels,assignees,createdAt,url
```

## Cron Management

```bash
# List crons (JSON)
openclaw cron list --json

# Enable/disable/run via API — use OpenClaw gateway REST API
# POST http://localhost:18790/api/cron/{id}/enable
# POST http://localhost:18790/api/cron/{id}/disable  
# POST http://localhost:18790/api/cron/{id}/run
```

## Style Guide

- **Dark theme:** background `#0d0d0f`, surface `#141416`, border `#2a2a2d`
- **Accent:** `#6c63ff` (purple) for active states, `#22c55e` green / `#ef4444` red for PnL
- **Font:** `-apple-system, 'SF Mono', 'Consolas', monospace` for data; system sans-serif for labels
- **Density:** Compact. This is a dashboard kept open all day.
- **PnL:** Always show sign (+ or -), green for positive, red for negative
- **Timestamps:** Relative ("2 min ago") for live data; `YYYY-MM-DD HH:mm UTC` for logs
- **Numbers:** Right-aligned in tables. Dollar amounts to 2dp. Percentages to 2dp with ± sign.
- **Tabs:** Left sidebar nav. Active tab has accent border-left.
- **Loading:** Show spinner/skeleton, never blank white space
- **Errors:** Show inline error badge in the panel — never crash the page

## Orca (Parallel Workers)

This project has Orca installed. To spawn sub-workers:
```
orca spawn "<task>" -b cc -d /path/to/repo --orchestrator openclaw --spawned-by "$ORCA_WORKER_NAME"
```

## Quality Bar

- No JS errors in browser console on page load
- All API endpoints return JSON (never HTML on error)
- All data panels handle empty/missing data gracefully
- PnL calculations: verified against `live_log.jsonl` manually
- Server must not crash on missing files — return empty state instead
