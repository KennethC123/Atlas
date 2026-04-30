import asyncio
import json
import os
import shutil
import sys
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LAT S4 Leaderboard")

APP_DIR = Path(__file__).parent
CACHE_DIR = Path(os.environ.get("CACHE_DIR", str(APP_DIR / "cache")))
CACHE_PATH = CACHE_DIR / "leaderboard.json"
TRADES_CACHE_PATH = CACHE_DIR / "trades.json"
SNAPSHOT_PATH = CACHE_DIR / "snapshot_24h.json"
SNAPSHOT_PREV_PATH = CACHE_DIR / "snapshot_24h_prev.json"
HISTORY_PATH = CACHE_DIR / "history.json"
STATIC_PATH = APP_DIR / "static"
NANSEN_CMD = ["npx", "nansen-cli"]
COMPETITION_START = datetime(2026, 3, 20, tzinfo=timezone.utc)
COMPETITION_END = datetime(2026, 5, 31, tzinfo=timezone.utc)
STARTING_BALANCE = 100.0
CACHE_TTL = 3600  # 1 hour
_refresh_lock = asyncio.Lock()
_last_refresh: float = 0
_avatar_cache: dict = {}

# ─── PARTICIPANTS ─────────────────────────────────────────────────────────────
# (name, claw_label, claw_slack_id, evm_address, solana_address)
PARTICIPANTS = [
    ("Kenneth",       "@KenKlaw",             "U0AGK05TDLH", "0xf5a9D19Ac0ED6158Fc75fbaD17f9808C004A4b53", "AAMjuoF5wE1UE4GLTu5m6tyr4VCc7DJQ1WkEvqPRwcK"),
    ("Nicolai",       "@Cabanel",             "U0AGHJ49GH0", "",                                            "J97dDQ8EgeeD87bVTQ6fRR6SFN7CEU7TBQ1agER89LgF"),
    ("Hector",        "@Iroh",                "",            "0xFa712c255A206dFF40caD3496BcBBe87f21Ee4fB", "8YHcqF6XXME1P7H7PrncAVnzA44tiNXCf98wXbwYEaui"),
    ("Javier",        "@Javierito",           "U0AG058419R", "0xD8cA735D0fb813db135eFe6279d091FE2d2a8787", "BmrfTn2gK2jBoi9pPqJMCBUXiYpANhN6G6h3AZyUD5sZ"),
    ("Davide",        "@Lulu",                "",            "0x2b7a2251f4EeBe51fbc569D85dDEfAF6A4E0ffF4", "7zz48X77cjH7n5BKGVp3AqUeQCVf3BuQzS1vECWXodaL"),
    ("Hans_Olav",     "@Samson",              "U0AD4RSK2TG", "0x72A87bb67a1406BbaD62476b40B3D914f5F41145", "HPHmmDcWwxATQukqpeqoSoTzruc63D8pTGn7tM92YyXb"),
    ("Jon",           "@Kilat",               "U0AGEJNN7ML", "0xE4e80238d43800D85146e9aDF98669c86A342851", "FKNBV2Bk8Kj6rEuStFtrXQ5SXrUF1KoQ8nqtunute8Qq"),
    ("Tarvi",         "@Bender",              "U0AFPSY7XLP", "0x4B8671472fBA20FBE54a183a496dae4fEB3A708A", "D2D5XsCgU2qKP6D27w538aLvKdsewuyjyrZ3AN3ThASU"),
    ("Morten",        "@Gekko",               "U0AG1J90ADD", "0x61AB9e72f7c85E6783F70b7aFe4d9ED9700B4D14", "AsP5Mm4cPWwiRWiURLByWJKw9RvWsrhVPEkWioc6WfeW"),
    ("Akshay",        "@Rook",                "U0AF4SGU6R3", "0x49Ae2bC5d93E9c4DE0a53F8E141Ff01c10F5a096", "GDdubyRCd6bHr5XwkeJhowQeDt9NwS6Mxmcwcc7pNpup"),
    ("Ko",            "@Koma",                "U0AHJJ41D32", "0xd7154f24da982E6437fadaB7c3DF1115C0830900", "HPBSgPtXX2oBNB6AiXLENjR86Uj9BnQNU8Cwj1mS8tpE"),
    ("Aurelie",       "@Chuntaro",            "",            "0x0adbd6A1215b5898A58C72a3EBba519B4571c34b", "FmbhXVVNW41X7Vn82Ye9dWamR3BZxr2ZtrLYGzxxTXWs"),
    ("Shan_Li",       "@Baifern",             "U0AGTM50MR9", "0x116Ae19d9A5a6dDd348e5d1cAe72DBc0F21016f5", "FhXoADDzJFAfiFG9oSoFKZ2vtWVZ51PexsjHNbS7hgHS"),
    ("Tumi",          "@Tom Snow",            "U0AGBHYSZB5", "0xfc05803B38fB7B8A429dD651852B97C794A2C419", "CPb6jm5bqgeDhgCZ7ZT3LySzpe6Di5PhuBnq4moD2XuF"),
    ("James",         "@James Claw",          "U0AFQ4P7879", "0x84beF6dbb7FD4cf772Bba76ce6E2D319F3C28BFa", "7sV85onr6ADgy4J6py3S5usUQvhJuqdYuUr6tRQ4oNu"),
    ("Niklas",        "@Niks Claw",           "U0AHMPT4J49", "0x163D42aacF5335EFc76A4C71370c671aa93Bf7A8", "9ZhJjYSuEn6o37msz24iXb48c8956HRtenmKKRvfAxhd"),
    ("Oana",          "@Claudia",             "",            "0xD8c8bA7Cb09Ef2516E49C2aC71c4ce95b167C70d", "47fYhaBLWKgpwinNQEWBqaHGvQZUSS7QR5MKCCXMGBSH"),
    ("Tim",           "@tims-clawd-bot",      "",            "0xd0665648337b2B7b3Df4689E5671750f998580d3", "2PSfch5ip65GUpBsuugtx9Kh2jJDnemJhZYtMVJFS62z"),
    ("Felipe",        "@SlackXBT",            "",            "0xe649eE070970334194F8C9BE00a04380E80B69B3", "GW9GjE7uGuyn7n4ThhQXPBw3U16GmGrjLpdjyDc4NwXV"),
    ("Csaba",         "@H.E.R.B.I.E.",        "",            "0x4059D4e7107BB03EF8A109fB3CB97975E636C519", "4CJonNNpMyTNDap2TaLTmLWcsAVyndXr59dHLbD4xNwb"),
    ("Jake",          "@Openclaw - Jake",     "",            "0x5939390b74E8216fF52E750DC3d8c70df303C94E", "9ScBPCkvAx4nDgKBcvXREkq8dNxnnw57RVqjza1Npq9k"),
    ("Kristine",      "@kawaii",              "",            "0xC37B26248fdD49AdcC499c963f7829E01984C0d1", "87QfLLhhrQzniKSLTR2EvpKtZkPwgnVCq1a7B7Mp8tf3"),
    ("Poh",           "@wukong",              "",            "0x344b186f33aD695e019D28E5fF71cbff24956944", "rChc8T9sYmVpW2qPGkZt57E7X4cAMcjCkUmq7YkQ4go"),
    ("Tum",           "@Kirua",               "",            "0x928De9cd98813DD7F21a0d84D4710B2F1EF84a49", "8V26uTguw5A6UVNH95QmTe2HPKCThcKPstkBZLe85FKm"),
    ("Shuan_Yang",    "@Krabbs",              "",            "0x6d0A2E3aAc306767F07CFEd746942802668596D4", "BRBgWs1peYQRFwjpya9Et5jUK43y1tJrq1ygM9YCbpTi"),
    ("George",        "@Claw McCraw",         "",            "0x37E497b9D3A28AD35A36F73C4d14f41d826AD0ca", "7QVBk5zMsQatbgC3eL3dBuGszJz6SSqWJNUPbUPyYsDJ"),
    ("Alex_Svanevik", "@Winnie",              "",            "0xEA6C009AA96e1a94825963c7A41FD5cB4819C113", "EifSJKppdqPG5oSjj1weGgS3y9wkee1tCDXdEFzikyPW"),
    ("Ingrid",        "@Clawdia Bot",         "",            "0xFd0e3E8984717476F27324F90ab367CB809B168e", "HMNM28YuusfDE2V6U3TNDHuWxUFfr1gUPc3JdSyiJsqB"),
    ("Tan",           "@Markus",              "",            "0xAaD429Bd93858D322D917598276B0e0dAe1A337f", "5WW2J2WRbtc3xYZ7qxviUpptpJshpkUboDnbinYkJHzS"),
    ("Laveen",        "@Ari",                 "",            "0xa72406D6E08E69a82aC4240E5C7492809101a402", "816iXvL28S5FUUMgiFYVrtgL6ejPaanf7665h5hA1sH7"),
    ("Michelle",      "@KEI",                 "",            "0xCccFb28A120Ec90365fB6088f9e5BEDcA93315e4", "gxfJQBVNrpSB5jVepq1gQXqckkZrVBk3G873bhhkobq"),
    ("Letice",        "@Vera",                "",            "0xb72871c73476257D1E830c0F81947B91aB0593B9", "8tWqo7Mhd1MfZyZ4dDhGbVuFHB5D6V5uit93C7UdmBbv"),
    ("Pepe",          "@Bluga",               "",            "0x041e3884094a27023935478F6ecCB32a181e10fC", "6mDDY47Z8oNr6R6aKP2LWXQLBe3vg1d8kJcDQYJKN3h4"),
    ("Alex_Karsten",  "@Arc",                 "",            "0xefd4295Ef93A82A259e686840B54Bb837fd79DFd", "2QLRP9F7bryfwBKxqjchNq8DFxSYBUw6cxrj3zcWu7HZ"),
    ("Lars",          "@Lars Language Model", "",            "0x4ab30A1D658172798e9CD046825513De86827405", "9ZzFGPgwJrk3VdYzHiMdSMCk2UH8XUP4efZvBJM7JqjP"),
    ("Hurcan",        "@Rex",                 "",            "0x067Af45012075e2De32AF24eB72978fe100e0162", "8NpLbRmCNDfaenppmJAwJjKnRPrb8ws17vSRqQ3EutWr"),
    ("Harry",         "@Titan",               "",            "0x01e9e654451dB010ec4B3ece4FC6F18F5ef4b071", "2nHLW5CWPH9kf8KQwKYtbCPy79hhANLSbopi56jqCov1"),
    ("Leyou",         "@Leyou's Openclaw",    "U07KVQBLBPB", "0x4d5AC571f1858DA7F90F83514703D7e32e9A9a09", "5fYKrhoae1SZWhy9jwgNL3vp3LaUvvCyHhqwxPUadLHS"),
    ("Oscar",         "@oscar2",              "U0AG5EGD9H8", "0xAf9582d9141dE534eD43579a501463C46Caa0E25", "3LnyTBJsbDfwiC2b3ikjSPyRkpkPCMqZawNPChaV8nfr"),
    ("Timothy",       "@Beans",               "U0AFR2VDMBN", "0xA588CB54Fb623193ff094A6eF26Eb19380294541", "46PfEkeCK5BfnH2Tg3wg9Xv5zFaDdFUNwwCDVMu82S6p"),
    ("Marius",        "@Seb",                 "U0AG91FL78C", "0x82B001D5A1b440263e5527E6d399C84010E5788c", "BNCt3xNTteUaPfM4vnm6tsTz7zEk7z5HChABz6Bnac8b"),
    ("Saurabh",       "@SBot",                "",            "0x4256bbf87bE564EC54d3087775840D48a9e0971b", "F8pofX6vh7TJn7ZsSU6K7jGSuVcrG81pWv3vinhJpEta"),
]

STABLES = {"USDC", "USDT", "DAI", "BUSD", "USDP", "LUSD", "FRAX", "AUSD", "GHO", "EURC", "EURCV"}
# Quote tokens: treated like stables for trade classification (buy/sell base)
QUOTE_TOKENS = STABLES | {"SOL", "WSOL", "ETH", "WETH"}
# Tokens excluded from "Most Traded" leaderboard (base assets, LSTs, gas tokens)
TOP_TOKEN_EXCLUDE = STABLES | {
    # Major base assets
    "SOL", "ETH", "BTC", "WETH", "WBTC", "WSOL",
    # Liquid staking tokens (ETH)
    "STETH", "WSTETH", "RETH", "CBETH", "FRXETH", "SFRXETH", "OSETH", "OETH",
    "ANKRETH", "SWETH", "METH", "EZETH", "WEETH", "RSETH", "PUFETH",
    # Liquid staking tokens (SOL)
    "MSOL", "JITOSOL", "BSOL", "LSTSOL", "SCNSOL", "HSOL", "JSOL",
    # Other gas/wrapped
    "MATIC", "WMATIC", "AVAX", "WAVAX", "BNB", "WBNB", "OP", "ARB",
}


async def _fetch_slack_avatar(slack_id: str) -> Optional[str]:
    """Fetch Slack profile image_72 URL for a user, with in-process caching."""
    if not slack_id:
        return None
    if slack_id in _avatar_cache:
        return _avatar_cache[slack_id]
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        _avatar_cache[slack_id] = None
        return None
    try:
        url = f"https://slack.com/api/users.info?user={urllib.parse.quote(slack_id)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        loop = asyncio.get_event_loop()

        def _do_fetch():
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())

        data = await loop.run_in_executor(None, _do_fetch)
        avatar = data.get("user", {}).get("profile", {}).get("image_72") if data.get("ok") else None
        _avatar_cache[slack_id] = avatar
        return avatar
    except Exception:
        _avatar_cache[slack_id] = None
        return None


def _extract_balance(data: dict) -> float:
    """Extract USD balance by summing value_usd across token list from Nansen profiler balance."""
    if not isinstance(data, dict):
        return 0.0

    # Handle nested or flat data
    inner = data.get("data", {})
    token_list = []
    if isinstance(inner, dict):
        token_list = inner.get("data", [])
        if not token_list: token_list = inner.get("tokens", [])
    elif isinstance(inner, list):
        token_list = inner

    if isinstance(token_list, list) and token_list:
        total = 0.0
        for t in token_list:
            try:
                # Handle value_usd or usd_value
                v = float(t.get("value_usd", t.get("usd_value", 0)) or 0)
                if v > 0:
                    total += v
            except (TypeError, ValueError):
                pass
        return total

    # Fallback: try flat keys
    for key in ["total_usd_value", "portfolio_usd_value", "total_value_usd", "totalUsdValue"]:
        if key in data and data[key] is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                pass
    return 0.0


async def _run_nansen(args: list[str], timeout: int = 60) -> Optional[dict]:
    """Run nansen CLI and return parsed JSON, or None on failure."""
    api_key = os.environ.get("NANSEN_API_KEY", "")
    cmd_args = list(NANSEN_CMD) + args
    if api_key:
        cmd_args.extend(["--apiKey", api_key])
        
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0 and stdout:
            raw = stdout.decode().strip()
            # Find JSON in output (sometimes prefixed with log lines)
            for line in raw.split("\n"):
                line = line.strip()
                if line.startswith("{") or line.startswith("["):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        pass
            # Try full output
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
    except (asyncio.TimeoutError, Exception):
        pass
    return None


async def _fetch_balance_pair(name: str, evm: str, sol: str) -> dict:
    """Fetch balances for one participant (both chains)."""
    tasks = []
    if evm:
        tasks.append(_run_nansen(["research", "profiler", "balance", "--address", evm, "--chain", "base"]))
    else:
        tasks.append(asyncio.sleep(0, result=None))

    if sol:
        tasks.append(_run_nansen(["research", "profiler", "balance", "--address", sol, "--chain", "solana"]))
    else:
        tasks.append(asyncio.sleep(0, result=None))

    base_data, sol_data = await asyncio.gather(*tasks)

    base_usd = _extract_balance(base_data) if base_data else 0.0
    sol_usd = _extract_balance(sol_data) if sol_data else 0.0

    return {
        "name": name,
        "base_usd": base_usd,
        "sol_usd": sol_usd,
        "total_usd": base_usd + sol_usd,
        "has_data": (base_usd > 0 or sol_usd > 0),
    }


async def _fetch_transactions_pair(name: str, claw: str, evm: str, sol: str) -> list[dict]:
    """Fetch full competition window transactions for one participant."""
    comp_days = str(max(1, (datetime.now(timezone.utc) - COMPETITION_START).days + 1))
    tasks = []
    if evm:
        tasks.append(_run_nansen(["research", "profiler", "transactions", "--address", evm, "--chain", "base", "--days", comp_days], timeout=60))
    else:
        tasks.append(asyncio.sleep(0, result=None))
    if sol:
        tasks.append(_run_nansen(["research", "profiler", "transactions", "--address", sol, "--chain", "solana", "--days", comp_days], timeout=60))
    else:
        tasks.append(asyncio.sleep(0, result=None))

    base_txs, sol_txs = await asyncio.gather(*tasks)
    trades = []

    for chain, tx_data in [("Base", base_txs), ("Solana", sol_txs)]:
        if not tx_data:
            continue
        # Response shape: {"success": true, "data": {"data": [...txs...], "pagination": {...}}}
        if isinstance(tx_data, list):
            txs = tx_data
        elif isinstance(tx_data, dict):
            inner = tx_data.get("data", {})
            txs = inner.get("data", []) if isinstance(inner, dict) else inner if isinstance(inner, list) else []
        else:
            txs = []
        if not isinstance(txs, list):
            continue
        for tx in txs:
            tokens_sent = tx.get("tokens_sent", [])
            tokens_received = tx.get("tokens_received", [])
            if not tokens_sent or not tokens_received:
                continue
            sent_syms = [t.get("token_symbol", t.get("symbol", "?")).upper() for t in tokens_sent]
            recv_syms = [t.get("token_symbol", t.get("symbol", "?")).upper() for t in tokens_received]
            # Skip stable-to-stable
            if all(s in STABLES for s in sent_syms + recv_syms):
                continue
            usd_value = 0.0
            vol = tx.get("volume_usd") or 0
            try:
                usd_value = float(vol)
            except (TypeError, ValueError):
                pass
            if usd_value == 0:
                for t in tokens_sent + tokens_received:
                    try:
                        usd_value = max(usd_value, float(t.get("value_usd") or t.get("usd_value") or 0))
                    except (TypeError, ValueError):
                        pass
            trades.append({
                "name": name,
                "claw": claw,
                "chain": chain,
                "sent": ", ".join(sent_syms),
                "received": ", ".join(recv_syms),
                "usd_value": round(usd_value, 2),
                "timestamp": tx.get("block_timestamp") or tx.get("block_time") or tx.get("timestamp") or "",
                "tx_hash": tx.get("transaction_hash") or tx.get("tx_hash") or tx.get("hash") or "",
            })
    return trades


async def _do_refresh():
    """Pull all balances in parallel (max 10 concurrent), update cache."""
    global _last_refresh

    sem = asyncio.Semaphore(10)

    async def _bounded(name, evm, sol):
        async with sem:
            return await _fetch_balance_pair(name, evm, sol)

    tasks = [_bounded(name, evm, sol) for name, claw, slack_id, evm, sol in PARTICIPANTS]
    results = await asyncio.gather(*tasks)

    # Build leaderboard
    leaderboard = []
    for i, (entry, (name, claw, slack_id, evm, sol)) in enumerate(zip(results, PARTICIPANTS)):
        total = entry["total_usd"]
        pct = (total / STARTING_BALANCE - 1) * 100 if entry["has_data"] else None
        leaderboard.append({
            "name": name,
            "claw": claw,
            "total_usd": round(total, 2),
            "pct_change": round(pct, 2) if pct is not None else None,
            "base_usd": round(entry["base_usd"], 2),
            "sol_usd": round(entry["sol_usd"], 2),
            "has_data": entry["has_data"],
        })

    # Sort: has_data with pct_change desc, then no-data at bottom
    leaderboard.sort(key=lambda x: (0 if x["has_data"] else 1, -(x["pct_change"] or -999)))
    for rank, entry in enumerate(leaderboard, 1):
        entry["rank"] = rank

    now = datetime.now(timezone.utc).isoformat()
    cache_data = {
        "leaderboard": leaderboard,
        "refreshed_at": now,
        "participant_count": len(PARTICIPANTS),
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache_data, indent=2))
    _last_refresh = time.time()

    # Also refresh trades
    async def _bounded_tx(name, claw, evm, sol):
        async with sem:
            return await _fetch_transactions_pair(name, claw, evm, sol)

    tx_tasks = [_bounded_tx(name, claw, evm, sol) for name, claw, slack_id, evm, sol in PARTICIPANTS]
    tx_results = await asyncio.gather(*tx_tasks)
    all_trades = []
    for trades in tx_results:
        all_trades.extend(trades)
    # Sort by timestamp desc
    all_trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # realized pnl matching
    buy_stacks: dict = defaultdict(list)
    for t in reversed(all_trades):
        sent_syms = [s.strip().upper() for s in t.get("sent", "").split(", ") if s.strip()]
        recv_syms = [s.strip().upper() for s in t.get("received", "").split(", ") if s.strip()]
        sent_ns = [s for s in sent_syms if s not in QUOTE_TOKENS]
        recv_ns = [s for s in recv_syms if s not in QUOTE_TOKENS]
        tname = t.get("name", "")

        if recv_ns and not sent_ns:
            t["trade_type"] = "buy"
            t["realized_pnl"] = None
            for sym in recv_ns: buy_stacks[(tname, sym)].append(t["usd_value"])
        elif sent_ns and not recv_ns:
            t["trade_type"] = "sell"
            sym = sent_ns[0]
            key = (tname, sym)
            if buy_stacks[key]:
                buy_usd = buy_stacks[key].pop()
                t["realized_pnl"] = round(t["usd_value"] - buy_usd, 2)
            else: t["realized_pnl"] = None
        elif sent_ns and recv_ns:
            t["trade_type"] = "swap"
            sell_sym = sent_ns[0]
            sell_key = (tname, sell_sym)
            if buy_stacks[sell_key]:
                buy_usd = buy_stacks[sell_key].pop()
                t["realized_pnl"] = round(t["usd_value"] - buy_usd, 2)
            else: t["realized_pnl"] = None
            for sym in recv_ns: buy_stacks[(tname, sym)].append(t["usd_value"])
        else:
            t["trade_type"] = "swap"
            t["realized_pnl"] = None

    TRADES_CACHE_PATH.write_text(json.dumps({"trades": all_trades, "refreshed_at": now}, indent=2))

    # 24h stats
    now_epoch = datetime.now(timezone.utc).timestamp()
    cutoff_24h = now_epoch - 86400
    trades_24h_counts: dict[str, int] = {}
    for t in all_trades:
        ts_str = t.get("timestamp", "")
        if not ts_str: continue
        try:
            ts_epoch = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            if ts_epoch >= cutoff_24h:
                n = t.get("name", "")
                trades_24h_counts[n] = trades_24h_counts.get(n, 0) + 1
        except Exception: pass

    # Top token
    token_buy_counts: dict[str, int] = {}
    for t in all_trades:
        for sym in t.get("received", "").split(", "):
            sym = sym.strip().upper()
            if sym and sym not in TOP_TOKEN_EXCLUDE:
                token_buy_counts[sym] = token_buy_counts.get(sym, 0) + 1
    top_token = max(token_buy_counts, key=lambda k: token_buy_counts[k]) if token_buy_counts else None
    top_token_count = token_buy_counts[top_token] if top_token else 0

    # Risk Metrics
    history = _load_history()
    for entry in leaderboard:
        snaps = history["participants"].get(entry["name"], [])
        if len(snaps) > 5:
            balances = [s["balance"] for s in snaps]
            pct_changes = [(balances[i] / balances[i-1] - 1) for i in range(1, len(balances))]
            avg = sum(pct_changes) / len(pct_changes)
            variance = sum((x - avg)**2 for x in pct_changes) / len(pct_changes)
            entry["volatility"] = round((variance**0.5) * 100, 2)
            peak = balances[0]
            max_dd = 0.0
            for b in balances:
                if b > peak: peak = b
                dd = (peak - b) / peak if peak > 0 else 0
                if dd > max_dd: max_dd = dd
            entry["max_drawdown"] = round(max_dd * 100, 2)
        else:
            entry["volatility"] = None
            entry["max_drawdown"] = None

    # Portfolio Composition
    for entry in leaderboard:
        participant = next((p for p in PARTICIPANTS if p[0] == entry["name"]), None)
        if participant:
            _, _, _, evm, sol = participant
            comp = {"stables": 0.0, "majors": 0.0, "memes": 0.0, "other": 0.0}
            MAJORS = {"ETH", "SOL", "BTC", "WETH", "WSOL", "WBTC"}
            MEMES = {"WIF", "BONK", "PEPE", "PNUT", "MOODENG", "DOGE", "VIRTUAL", "AERO"}
            
            tasks = []
            if evm: tasks.append(_run_nansen(["research", "profiler", "balance", "--address", evm, "--chain", "base"], timeout=30))
            if sol: tasks.append(_run_nansen(["research", "profiler", "balance", "--address", sol, "--chain", "solana"], timeout=30))
            if tasks:
                bal_results = await asyncio.gather(*tasks)
                for chain_data in bal_results:
                    if not chain_data: continue
                    inner = chain_data.get("data", {})
                    tokens = []
                    if isinstance(inner, dict):
                        tokens = inner.get("data", []) or inner.get("tokens", [])
                    elif isinstance(inner, list): tokens = inner
                    for t in tokens:
                        sym = (t.get("token_symbol") or t.get("symbol") or "").upper()
                        val = float(t.get("value_usd", t.get("usd_value", 0)) or 0)
                        if val < 0.1: continue
                        if sym in STABLES: comp["stables"] += val
                        elif sym in MAJORS: comp["majors"] += val
                        elif sym in MEMES: comp["memes"] += val
                        else: comp["other"] += val
                total_bal = sum(comp.values())
                entry["composition"] = {k: round(v/total_bal * 100, 1) for k, v in comp.items()} if total_bal > 0 else None

    # Annotate leaderboard
    trade_counts: dict[str, int] = {}
    unique_tickers: dict[str, set] = {}
    for t in all_trades:
        name = t.get("name", "")
        trade_counts[name] = trade_counts.get(name, 0) + 1
        tickers = unique_tickers.setdefault(name, set())
        for sym in t.get("received", "").split(", "):
            sym = sym.strip().upper()
            if sym and sym not in STABLES: tickers.add(sym)
    
    for entry in leaderboard:
        n = entry["name"]
        entry["trade_count"] = trade_counts.get(n, 0)
        entry["unique_tickers"] = len(unique_tickers.get(n, set()))
        entry["trades_24h"] = trades_24h_counts.get(n, 0)

    # 24h pct change
    now_ts = datetime.now(timezone.utc)
    prev_balances: dict[str, float] = {}
    if SNAPSHOT_PATH.exists():
        try:
            snap = json.loads(SNAPSHOT_PATH.read_text())
            snap_ts = datetime.fromisoformat(snap.get("timestamp", "1970-01-01T00:00:00+00:00"))
            if (now_ts - snap_ts).total_seconds() / 3600 >= 23:
                SNAPSHOT_PREV_PATH.write_text(SNAPSHOT_PATH.read_text())
                SNAPSHOT_PATH.write_text(json.dumps({"timestamp": now_ts.isoformat(), "balances": {e["name"]: e["total_usd"] for e in leaderboard}}, indent=2))
                prev_balances = snap.get("balances", {})
            else:
                if SNAPSHOT_PREV_PATH.exists(): prev_balances = json.loads(SNAPSHOT_PREV_PATH.read_text()).get("balances", {})
        except Exception: pass
    else: SNAPSHOT_PATH.write_text(json.dumps({"timestamp": now_ts.isoformat(), "balances": {e["name"]: e["total_usd"] for e in leaderboard}}, indent=2))

    for entry in leaderboard:
        prev = prev_balances.get(entry["name"])
        entry["pct_change_24h"] = round((entry["total_usd"] / prev - 1) * 100, 2) if prev and prev > 0 and entry["has_data"] else None

    # Aggregate stats
    max_t24h = max((e.get("trades_24h", 0) for e in leaderboard), default=0)
    most_active = next((e for e in leaderboard if e.get("trades_24h", 0) == max_t24h and max_t24h > 0), None)
    with_24h = [e for e in leaderboard if e.get("pct_change_24h") is not None]
    top_gainer = max(with_24h, key=lambda e: e["pct_change_24h"], default=None)
    largest_loss = min(with_24h, key=lambda e: e["pct_change_24h"], default=None)

    cache_data.update({
        "leaderboard": leaderboard, "top_token": top_token, "top_token_count": top_token_count,
        "max_trades_24h": max_t24h, "most_active_claw": most_active["claw"] if most_active else None,
        "most_active_trades": max_t24h, "top_gainer_claw": top_gainer["claw"] if top_gainer else None,
        "top_gainer_pct": top_gainer["pct_change_24h"] if top_gainer else None,
        "largest_loss_claw": largest_loss["claw"] if largest_loss else None,
        "largest_loss_pct": largest_loss["pct_change_24h"] if largest_loss else None,
    })
    CACHE_PATH.write_text(json.dumps(cache_data, indent=2))

    # History update
    for entry in leaderboard:
        name = entry["name"]
        if name not in history["participants"]: history["participants"][name] = []
        history["participants"][name].append({"ts": now, "balance": entry["total_usd"]})
        history["participants"][name] = history["participants"][name][-168:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2))


def _load_cache() -> Optional[dict]:
    if CACHE_PATH.exists():
        try: return json.loads(CACHE_PATH.read_text())
        except Exception: pass
    return None

def _load_history() -> dict:
    if HISTORY_PATH.exists():
        try: return json.loads(HISTORY_PATH.read_text())
        except Exception: pass
    return {"participants": {}}

def _cache_is_fresh() -> bool:
    if not CACHE_PATH.exists(): return False
    return (time.time() - CACHE_PATH.stat().st_mtime) < CACHE_TTL

def _competition_day() -> int:
    return max(1, (datetime.now(timezone.utc) - COMPETITION_START).days + 1)

@app.on_event("startup")
async def startup():
    api_key = os.environ.get("NANSEN_API_KEY", "")
    if api_key:
        nansen_cfg_path = Path.home() / ".nansen" / "config.json"
        nansen_cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = {"apiKey": api_key}
        nansen_cfg_path.write_text(json.dumps(cfg, indent=2))
    if not CACHE_PATH.exists(): asyncio.create_task(_do_refresh())

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_PATH / "index.html"
    if html_path.exists(): return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>LAT S4 Dashboard</h1><p>Loading...</p>")

@app.get("/api/leaderboard")
async def get_leaderboard():
    cache = _load_cache()
    if not _cache_is_fresh(): asyncio.create_task(_do_refresh())
    if not cache: return JSONResponse({"leaderboard": [], "refreshed_at": None, "loading": True})
    history = _load_history()
    for entry in cache.get("leaderboard", []):
        snaps = history["participants"].get(entry["name"], [])
        entry["history"] = [snap["balance"] for snap in snaps]
    return JSONResponse(cache)

@app.get("/api/stats")
async def get_stats():
    cache = _load_cache()
    day, total_days = _competition_day(), 73
    if not cache or not cache.get("leaderboard"):
        return JSONResponse({"day": day, "total_days": total_days, "participant_count": len(PARTICIPANTS), "loading": True})
    lb = cache["leaderboard"]
    with_data = [e for e in lb if e["has_data"]]
    green = sum(1 for e in with_data if (e["pct_change"] or 0) > 0)
    red = sum(1 for e in with_data if (e["pct_change"] or 0) < 0)
    collective = sum(e["total_usd"] for e in with_data)
    collective_pct = (collective / (len(with_data) * STARTING_BALANCE) - 1) * 100 if with_data else 0
    leader = lb[0] if lb else None
    return JSONResponse({
        "day": day, "total_days": total_days, "participant_count": len(PARTICIPANTS),
        "green_count": green, "red_count": red, "collective_usd": round(collective, 2),
        "collective_pct": round(collective_pct, 2), "leader_name": leader["name"] if leader else None,
        "leader_claw": leader["claw"] if leader else None, "leader_pct": leader["pct_change"] if leader else None,
        "refreshed_at": cache.get("refreshed_at"), "loading": False,
        "top_token": cache.get("top_token"), "top_token_count": cache.get("top_token_count", 0),
        "most_active_claw": cache.get("most_active_claw"), "most_active_trades": cache.get("most_active_trades", 0),
        "top_gainer_claw": cache.get("top_gainer_claw"), "top_gainer_pct": cache.get("top_gainer_pct"),
        "largest_loss_claw": cache.get("largest_loss_claw"), "largest_loss_pct": cache.get("largest_loss_pct"),
    })

@app.get("/api/trades")
async def get_trades():
    if TRADES_CACHE_PATH.exists():
        try: return JSONResponse(json.loads(TRADES_CACHE_PATH.read_text()))
        except Exception: pass
    return JSONResponse({"trades": [], "refreshed_at": None})

@app.get("/api/refresh")
async def trigger_refresh():
    global _last_refresh
    now = time.time()
    if now - _last_refresh < 3600:
        return JSONResponse({"status": "rate_limited", "retry_in_seconds": int(3600 - (now - _last_refresh))})
    async with _refresh_lock:
        if time.time() - _last_refresh < 3600: return JSONResponse({"status": "already_refreshing"})
        asyncio.create_task(_do_refresh())
    return JSONResponse({"status": "refresh_triggered"})

@app.get("/api/holdings/{name}")
async def get_holdings(name: str):
    participant = next((p for p in PARTICIPANTS if p[0] == name), None)
    if not participant: return JSONResponse({"holdings": [], "error": "not found"}, status_code=404)
    _, claw, slack_id, evm, sol = participant
    def _extract_tokens(data: dict, chain: str) -> list[dict]:
        if not data: return []
        inner = data.get("data", {})
        token_list = []
        if isinstance(inner, dict): token_list = inner.get("data", []) or inner.get("tokens", [])
        elif isinstance(inner, list): token_list = inner
        results = []
        for t in token_list:
            try: usd = float(t.get("value_usd", t.get("usd_value", 0)) or 0)
            except (TypeError, ValueError): usd = 0.0
            if usd < 0.01: continue
            results.append({"symbol": t.get("token_symbol") or t.get("symbol") or "?", "amount": t.get("token_amount") or t.get("balance") or 0, "usd_value": round(usd, 4), "chain": chain})
        return results
    tasks = []
    if evm: tasks.append(_run_nansen(["research", "profiler", "balance", "--address", evm, "--chain", "base"], timeout=30))
    if sol: tasks.append(_run_nansen(["research", "profiler", "balance", "--address", sol, "--chain", "solana"], timeout=30))
    if not tasks: return JSONResponse({"name": name, "holdings": []})
    bal_results = await asyncio.gather(*tasks)
    holdings = []
    for i, chain in enumerate(["Base", "Solana"]):
        if i < len(bal_results): holdings.extend(_extract_tokens(bal_results[i], chain))
    holdings.sort(key=lambda x: x["usd_value"], reverse=True)
    return JSONResponse({"name": name, "holdings": holdings, "evm_address": evm, "sol_address": sol})

@app.get("/api/podium")
async def get_podium():
    cache = _load_cache()
    if not cache or not cache.get("leaderboard"): return JSONResponse({"podium": []})
    top3 = [e for e in cache["leaderboard"] if e["has_data"]][:3]
    slack_ids = {name: slack_id for name, claw, slack_id, evm, sol in PARTICIPANTS}
    async def _enrich(entry):
        slack_id = slack_ids.get(entry["name"], "")
        avatar_url = await _fetch_slack_avatar(slack_id)
        return {"rank": entry["rank"], "name": entry["name"], "claw": entry["claw"], "total_usd": entry["total_usd"], "pct_change": entry["pct_change"], "avatar_url": avatar_url}
    podium = await asyncio.gather(*[_enrich(e) for e in top3])
    return JSONResponse({"podium": list(podium)})
