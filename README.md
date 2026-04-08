# KK Control Panel

Ken's personal OpenClaw ops dashboard. Runs on port 3201 inside the VM, reverse-proxied by the OpenClaw gateway at `/webserver/3201/`.

## What It Does

A single-tab browser dashboard kept open throughout the day. Built around Ken's actual workflow: finance team ops, LAT S4 live trading, cron management, and agent oversight.

## Acceptance Criteria

"Done" means:
1. The server starts with `python3 server.py` and responds at `http://localhost:3201/`
2. All 8 tabs render without JS errors in the browser console
3. Each tab loads its data (from local files or `gh` CLI or `openclaw` CLI) and displays it within 5 seconds
4. The LAT S4 tab shows: portfolio balance (Base + Solana), PnL vs $100 start, and a trade log with entry/exit/PnL/tx hash/reason per trade
5. The Finance tab shows: open PRs (title, number, author, status) and open issues — clearly segmented
6. The Cron tab shows: all scheduled jobs, their last run time/status, with toggle and run-now buttons
7. The Overview tab shows: my agent status, last heartbeat, today's API spend, pending action items
8. The server handles errors gracefully (shows an error state in the tab, never crashes)
9. Autostart: `~/autostart.sh` contains the startup command

## Stack

- **Server:** Python 3 + FastAPI (`uv run` for deps)
- **Frontend:** Vanilla JS + HTML/CSS — no build step
- **Data sources:** Local files (`live_log.jsonl`, `live_state.json`), `gh` CLI, `openclaw` CLI, `openclaw cron list`
- **Port:** 3201
- **Base path:** `/` (served at root, gateway handles the proxy)

## Project Structure

```
kk-control/
├── server.py          # FastAPI app — all routes
├── pyproject.toml     # uv deps (fastapi, uvicorn)
├── static/
│   ├── index.html     # Single-page app shell
│   ├── app.js         # Tab routing + data fetching
│   └── style.css      # Dark theme styles
├── README.md
└── CLAUDE.md
```

## Tabs

| Tab | Data Source | Notes |
|-----|------------|-------|
| Overview | `openclaw status`, cron list, session logs | Agent heartbeat, spend, open items |
| Finance | `gh pr list`, `gh issue list` on nansen-finance-restricted | PRs and issues segmented |
| LAT S4 | `~/workspace/backtests/lat-s4/live_log.jsonl`, `live_state.json` | Balances, PnL, trade log |
| Cron | `openclaw cron list` | Toggle + run-now via API |
| Screener | `node ~/workspace/strategy3-screener/screener.js --json` | Trigger scan, show signals |
| Research | Static config + local file existence checks | Project status tiles |
| Chat | `openclaw sessions list` | Recent sessions |
| Notes | `~/workspace/kk-control/notes.md` | Markdown scratchpad, auto-save |

## Running

```bash
# Install deps (one-time)
uv sync

# Start server
uv run uvicorn server:app --host 0.0.0.0 --port 3201 --reload
```

Access at: `http://localhost:3201/` or via gateway at `/webserver/3201/`
