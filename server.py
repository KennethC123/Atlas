import json
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Atlas")

WORKSPACE = Path.home() / ".openclaw" / "workspace"
NOTES_PATH = WORKSPACE / "kk-control" / "notes.md"
LAT_LOG = WORKSPACE / "backtests" / "lat-s4" / "live_log.jsonl"
LAT_STATE = WORKSPACE / "backtests" / "lat-s4" / "live_state.json"
SCREENER = WORKSPACE / "strategy3-screener" / "screener.js"

OPEN_ITEMS = [
    "PRs #32, #56, #68 in finance repo",
    "Issue #69 O-1 — overlapping bs_accounts (raise with Morten)",
    "Anthropic invoices Jan/Feb reclassification",
    "GST crypto transactions review",
    "Lattice review pending submission",
]


def run_cmd(cmd: list, timeout: int = 30) -> tuple[bool, any]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return True, json.loads(result.stdout)
        err = result.stderr.strip() or result.stdout.strip() or "Command failed"
        return False, {"error": err}
    except subprocess.TimeoutExpired:
        return False, {"error": f"Command timed out after {timeout}s"}
    except json.JSONDecodeError as e:
        return False, {"error": f"Invalid JSON: {e}", "raw": result.stdout[:500] if result else ""}
    except FileNotFoundError:
        return False, {"error": f"Command not found: {cmd[0]}"}
    except Exception as e:
        return False, {"error": str(e)}


@app.get("/api/overview")
def get_overview():
    ok, status = run_cmd(["openclaw", "status", "--json"])
    if ok and isinstance(status, dict):
        agent_status = status.get("status", "unknown")
        last_heartbeat = status.get("last_heartbeat") or status.get("heartbeat") or status.get("updated_at")
    else:
        agent_status = "unknown"
        last_heartbeat = None

    ok2, crons = run_cmd(["openclaw", "cron", "list", "--json"])
    if ok2 and isinstance(crons, list):
        cron_count = len(crons)
        cron_active = sum(
            1 for c in crons
            if c.get("enabled") is True or c.get("active") is True or c.get("status") == "active"
        )
    else:
        cron_count = 0
        cron_active = 0

    return {
        "agent_status": agent_status,
        "last_heartbeat": last_heartbeat,
        "cron_count": cron_count,
        "cron_active": cron_active,
        "open_items": OPEN_ITEMS,
    }


@app.get("/api/lat-s4")
def get_lat_s4():
    state = {}
    if LAT_STATE.exists():
        try:
            state = json.loads(LAT_STATE.read_text())
        except Exception:
            pass

    balances = state.get("balances", {})
    positions = state.get("positions", {})

    base_usdc = float(balances.get("base_usdc", 0))
    base_eth = float(balances.get("base_eth", 0))
    sol_usdc = float(balances.get("sol_usdc", 0))
    sol_sol = float(balances.get("sol_sol", 0))

    trades = []
    if LAT_LOG.exists():
        for line in LAT_LOG.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    trades.append(json.loads(line))
                except Exception:
                    pass

    liquid_usdc = base_usdc + sol_usdc
    START_BALANCE = 100.0
    total_pnl_pct = round((liquid_usdc - START_BALANCE) / START_BALANCE * 100, 2)

    return {
        "balances": {
            "base_usdc": round(base_usdc, 2),
            "base_eth": round(base_eth, 6),
            "sol_usdc": round(sol_usdc, 2),
            "sol_sol": round(sol_sol, 6),
        },
        "portfolio": {
            "liquid_usdc": round(liquid_usdc, 2),
            "total_pnl_pct": total_pnl_pct,
            "open_positions": len(positions) if isinstance(positions, dict) else 0,
        },
        "positions": positions,
        "trade_log": trades,
    }


@app.get("/api/finance")
def get_finance():
    ok1, prs = run_cmd([
        "gh", "pr", "list",
        "--repo", "nansen-ai/nansen-finance-restricted",
        "--state", "open",
        "--json", "number,title,author,createdAt,url",
    ])
    ok2, issues = run_cmd([
        "gh", "issue", "list",
        "--repo", "nansen-ai/nansen-finance-restricted",
        "--state", "open",
        "--json", "number,title,labels,createdAt,url",
    ])
    return {
        "prs": prs if ok1 else [],
        "issues": issues if ok2 else [],
        "pr_error": None if ok1 else prs.get("error"),
        "issue_error": None if ok2 else issues.get("error"),
    }


@app.get("/api/crons")
def get_crons():
    ok, crons = run_cmd(["openclaw", "cron", "list", "--json"])
    if ok:
        return crons
    return {"error": crons.get("error", "Failed to list crons")}


@app.post("/api/crons/{job_id}/toggle")
def toggle_cron(job_id: str):
    ok, crons = run_cmd(["openclaw", "cron", "list", "--json"])
    if not ok or not isinstance(crons, list):
        return JSONResponse(status_code=500, content={"error": "Could not read cron state"})

    job = next(
        (c for c in crons if str(c.get("id")) == job_id or c.get("name") == job_id),
        None,
    )
    if not job:
        return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})

    is_enabled = job.get("enabled", True)
    action = "disable" if is_enabled else "enable"

    ok2, result = run_cmd(["openclaw", "cron", action, job_id])
    if ok2:
        return {"ok": True, "action": action, "job_id": job_id}
    return {"ok": False, "error": result.get("error", "Toggle failed")}


@app.post("/api/crons/{job_id}/run")
def run_cron(job_id: str):
    ok, result = run_cmd(["openclaw", "cron", "run", job_id])
    if ok:
        return {"ok": True, "result": result}
    return {"ok": False, "error": result.get("error", "Run failed")}


def _run_screener():
    if not SCREENER.exists():
        return {"error": f"Screener not found at {SCREENER}"}
    ok, result = run_cmd(["node", str(SCREENER), "--json"], timeout=60)
    if ok:
        return result
    return {"error": result.get("error", "Screener failed")}


@app.get("/api/screener")
def get_screener():
    return _run_screener()


@app.post("/api/screener")
def run_screener():
    return _run_screener()


@app.get("/api/sessions")
def get_sessions():
    ok, sessions = run_cmd(["openclaw", "sessions", "list", "--json"])
    if ok:
        return sessions
    return {"error": sessions.get("error", "Failed to list sessions")}


@app.get("/api/notes")
def get_notes():
    try:
        if not NOTES_PATH.exists():
            NOTES_PATH.write_text("")
        return {"content": NOTES_PATH.read_text()}
    except Exception as e:
        return {"content": "", "error": str(e)}


@app.post("/api/notes")
async def save_notes(request: Request):
    try:
        body = await request.body()
        NOTES_PATH.write_text(body.decode("utf-8"))
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# Must be last — catches all unmatched paths for the SPA
app.mount("/", StaticFiles(directory="static", html=True), name="static")
