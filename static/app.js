/* Atlas — app.js */

const TABS = [
  { id: 'overview',  label: 'Overview',  icon: '📊' },
  { id: 'finance',   label: 'Finance',   icon: '🏦' },
  { id: 'lat-s4',    label: 'LAT S4',    icon: '📈' },
  { id: 'cron',      label: 'Cron',      icon: '⏰' },
  { id: 'screener',  label: 'Screener',  icon: '🔍' },
  { id: 'research',  label: 'Research',  icon: '🧪' },
  { id: 'chat',      label: 'Chat',      icon: '💬' },
  { id: 'notes',     label: 'Notes',     icon: '📝' },
];

let currentTab = null;
let refreshTimers = {};

// ── Init ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildSidebar();
  const hash = location.hash.slice(1) || 'overview';
  switchTab(TABS.find(t => t.id === hash) ? hash : 'overview');
});

// ── Sidebar ─────────────────────────────────────────
function buildSidebar() {
  const list = document.getElementById('nav-list');
  list.innerHTML = TABS.map(t => `
    <li class="nav-item" data-tab="${t.id}" onclick="switchTab('${t.id}')">
      <span class="nav-icon">${t.icon}</span>
      <span class="nav-label">${t.label}</span>
    </li>
  `).join('');
}

function setActiveNav(tabId) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tabId);
  });
}

// ── Tab switching ────────────────────────────────────
async function switchTab(tabId) {
  if (currentTab === tabId) return;
  currentTab = tabId;
  location.hash = tabId;
  setActiveNav(tabId);

  // Cancel existing refresh timers
  Object.values(refreshTimers).forEach(clearInterval);
  refreshTimers = {};

  const content = document.getElementById('content');
  showLoading(content);

  const tab = TABS.find(t => t.id === tabId);
  const title = tab ? `${tab.icon} ${tab.label}` : tabId;

  try {
    switch (tabId) {
      case 'overview': {
        const data = await api('/api/overview');
        render(content, renderOverview(data, title));
        refreshTimers.overview = setInterval(async () => {
          if (currentTab !== 'overview') return;
          const d = await api('/api/overview').catch(() => null);
          if (d) render(content, renderOverview(d, title));
        }, 60000);
        break;
      }
      case 'finance': {
        const data = await api('/api/finance');
        render(content, renderFinance(data, title));
        break;
      }
      case 'lat-s4': {
        const data = await api('/api/lat-s4');
        render(content, renderLatS4(data, title));
        refreshTimers.lats4 = setInterval(async () => {
          if (currentTab !== 'lat-s4') return;
          const d = await api('/api/lat-s4').catch(() => null);
          if (d) render(content, renderLatS4(d, title));
        }, 60000);
        break;
      }
      case 'cron': {
        const data = await api('/api/crons');
        render(content, renderCron(data, title));
        break;
      }
      case 'screener': {
        render(content, renderScreener(null, title));
        break;
      }
      case 'research': {
        render(content, renderResearch(title));
        break;
      }
      case 'chat': {
        const data = await api('/api/sessions');
        render(content, renderChat(data, title));
        break;
      }
      case 'notes': {
        const data = await api('/api/notes');
        render(content, renderNotes(data, title));
        break;
      }
      default:
        render(content, `<div class="empty-state">Unknown tab: ${tabId}</div>`);
    }
  } catch (err) {
    render(content, `
      <div class="tab-header"><h1 class="tab-title">${title}</h1></div>
      ${errorCard(err.message)}
    `);
  }
}

// ── API helper ───────────────────────────────────────
// Resolve API paths relative to the page base (handles reverse proxy sub-paths)
const BASE = window.location.pathname.replace(/\/$/, '');
async function api(url, opts = {}) {
  const resolvedUrl = url.startsWith('/api/') ? BASE + url : url;
  const res = await fetch(resolvedUrl, opts);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt.slice(0, 200)}`);
  }
  return res.json();
}

// ── Render helpers ───────────────────────────────────
function render(el, html) { el.innerHTML = html; }
function showLoading(el) { el.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>'; }
function errorCard(msg) { return `<div class="error-card">⚠ ${esc(msg)}</div>`; }
function emptyState(msg) { return `<div class="empty-state">${msg}</div>`; }

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtPnl(pct) {
  if (pct == null || isNaN(pct)) return `<span class="neu">—</span>`;
  const sign = pct >= 0 ? '+' : '';
  const cls = pct > 0 ? 'pos' : pct < 0 ? 'neg' : 'neu';
  return `<span class="${cls}">${sign}${Number(pct).toFixed(2)}%</span>`;
}

function fmtUsd(v) {
  if (v == null) return '—';
  return '$' + Number(v).toFixed(2);
}

function relTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d)) return esc(ts);
  const secs = Math.floor((Date.now() - d) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs/60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs/3600)}h ago`;
  return `${Math.floor(secs/86400)}d ago`;
}

function fmtTs(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d)) return esc(ts);
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
}

function truncHash(h) {
  if (!h) return '—';
  return h.length > 16 ? h.slice(0, 8) + '…' + h.slice(-6) : h;
}

function tabHeader(title, actions = '') {
  return `<div class="tab-header"><h1 class="tab-title">${title}</h1><div class="tab-actions">${actions}</div></div>`;
}

// ── Overview ─────────────────────────────────────────
function renderOverview(data, title) {
  const statusClass =
    data.agent_status === 'ok' || data.agent_status === 'running' || data.agent_status === 'healthy'
      ? 'status-ok'
      : data.agent_status === 'unknown' || data.agent_status === 'error'
        ? 'status-err'
        : 'status-warn';

  const cronLabel = data.cron_count > 0
    ? `${data.cron_active} / ${data.cron_count} active`
    : 'no crons';

  const items = Array.isArray(data.open_items) ? data.open_items : [];

  return `
    ${tabHeader(title, `<button class="btn btn-sm" onclick="switchTab('overview')">↺ Refresh</button>`)}
    <div class="card-grid">
      <div class="card">
        <div class="card-label">Agent Status</div>
        <div class="card-value mt-4">
          <span class="status-pill ${statusClass}">
            <span class="status-dot"></span>${esc(data.agent_status || 'unknown')}
          </span>
        </div>
      </div>
      <div class="card">
        <div class="card-label">Last Heartbeat</div>
        <div class="card-value" style="font-size:15px;margin-top:6px">${relTime(data.last_heartbeat)}</div>
        <div class="card-sub mono">${fmtTs(data.last_heartbeat)}</div>
      </div>
      <div class="card">
        <div class="card-label">Cron Jobs</div>
        <div class="card-value" style="font-size:18px;margin-top:6px">${cronLabel}</div>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <span class="section-title">Open Items</span>
        <span class="badge badge-accent">${items.length}</span>
      </div>
      <div class="card">
        ${items.length
          ? `<ul class="open-items">${items.map(i => `<li class="open-item">${esc(i)}</li>`).join('')}</ul>`
          : emptyState('No open items')}
      </div>
    </div>
  `;
}

// ── LAT S4 ───────────────────────────────────────────
function renderLatS4(data, title) {
  const b = data.balances || {};
  const p = data.portfolio || {};
  const trades = Array.isArray(data.trade_log) ? data.trade_log : [];
  const positions = data.positions || {};

  const posCount = p.open_positions || 0;
  const liquidUsdc = p.liquid_usdc ?? 0;
  const pnlPct = p.total_pnl_pct ?? 0;

  const tradeRows = trades.slice().reverse().map(t => {
    const isExit = t.type === 'exit';
    const typeBadge = isExit
      ? `<span class="neg" style="font-size:10px;padding:1px 5px;border:1px solid;border-radius:4px">EXIT</span>`
      : `<span class="pos" style="font-size:10px;padding:1px 5px;border:1px solid;border-radius:4px">ENTRY</span>`;
    return `
      <tr>
        <td class="text-muted">${relTime(t.timestamp)}</td>
        <td>${typeBadge}</td>
        <td><strong>${esc(t.token || '—')}</strong></td>
        <td>${esc(t.chain || '—')}</td>
        <td class="num">${t.price_usd != null ? '$' + Number(t.price_usd).toFixed(6) : '—'}</td>
        <td class="num">${fmtUsd(t.usdc_amount)}</td>
        <td class="num">${isExit ? fmtPnl(t.pnl_pct) : '<span class="neu">—</span>'}</td>
        <td class="truncate text-muted" title="${esc(t.reason || '')}">${esc((t.reason || '').slice(0, 40))}</td>
        <td class="mono text-muted">${truncHash(t.tx_hash)}</td>
      </tr>
    `;
  }).join('');

  const posEntries = Object.entries(positions);

  return `
    ${tabHeader(title, `<button class="btn btn-sm" onclick="switchTab('lat-s4')">↺ Refresh</button>`)}
    <div class="card-grid">
      <div class="card">
        <div class="card-label">Base USDC</div>
        <div class="card-value">${fmtUsd(b.base_usdc)}</div>
      </div>
      <div class="card">
        <div class="card-label">Base ETH</div>
        <div class="card-value" style="font-size:18px;margin-top:4px">${Number(b.base_eth || 0).toFixed(4)}</div>
        <div class="card-sub">ETH</div>
      </div>
      <div class="card">
        <div class="card-label">Sol USDC</div>
        <div class="card-value">${fmtUsd(b.sol_usdc)}</div>
      </div>
      <div class="card">
        <div class="card-label">Sol SOL</div>
        <div class="card-value" style="font-size:18px;margin-top:4px">${Number(b.sol_sol || 0).toFixed(4)}</div>
        <div class="card-sub">SOL</div>
      </div>
      <div class="card">
        <div class="card-label">Liquid USDC</div>
        <div class="card-value">${fmtUsd(liquidUsdc)}</div>
        <div class="card-sub">${posCount} open position${posCount !== 1 ? 's' : ''}</div>
      </div>
      <div class="card">
        <div class="card-label">PnL vs $100</div>
        <div class="card-value" style="font-size:22px;margin-top:4px">${fmtPnl(pnlPct)}</div>
        <div class="card-sub">start: $100.00</div>
      </div>
    </div>

    ${posEntries.length > 0 ? `
    <div class="section">
      <div class="section-header">
        <span class="section-title">Open Positions</span>
        <span class="badge badge-accent">${posEntries.length}</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Token</th><th>Chain</th><th class="num">Entry Price</th><th class="num">USDC</th><th class="num">Tokens</th><th>Reason</th></tr></thead>
          <tbody>
            ${posEntries.map(([tok, pos]) => `
              <tr>
                <td><strong>${esc(tok)}</strong></td>
                <td>${esc(pos.chain || '—')}</td>
                <td class="num">${pos.entry_price ? '$' + Number(pos.entry_price).toFixed(6) : '—'}</td>
                <td class="num">${fmtUsd(pos.usdc_amount)}</td>
                <td class="num">${pos.token_amount != null ? Number(pos.token_amount).toFixed(2) : '—'}</td>
                <td class="truncate text-muted">${esc((pos.reason || '').slice(0, 50))}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
    ` : ''}

    <div class="section">
      <div class="section-header">
        <span class="section-title">Trade Log</span>
        <span class="badge">${trades.length} trades</span>
      </div>
      ${trades.length === 0
        ? emptyState('No trades yet — live_log.jsonl is empty or missing')
        : `<div class="table-wrap">
            <table>
              <thead><tr><th>When</th><th>Type</th><th>Token</th><th>Chain</th><th class="num">Price</th><th class="num">USDC</th><th class="num">PnL</th><th>Reason</th><th>Tx</th></tr></thead>
              <tbody>${tradeRows}</tbody>
            </table>
          </div>`
      }
    </div>
  `;
}

// ── Finance ──────────────────────────────────────────
function renderFinance(data, title) {
  const prs = Array.isArray(data.prs) ? data.prs : [];
  const issues = Array.isArray(data.issues) ? data.issues : [];

  const prRows = prs.map(pr => `
    <tr>
      <td class="mono"><a href="${esc(pr.url)}" target="_blank">#${pr.number}</a></td>
      <td class="truncate">${esc(pr.title)}</td>
      <td>${esc(pr.author?.login || pr.author || '—')}</td>
      <td class="text-muted">${relTime(pr.createdAt)}</td>
      <td><a href="${esc(pr.url)}" target="_blank" class="btn btn-sm">Open</a></td>
    </tr>
  `).join('');

  const issueRows = issues.map(issue => {
    const labels = Array.isArray(issue.labels)
      ? issue.labels.map(l => `<span class="badge" style="background:rgba(108,99,255,0.1);border-color:var(--accent)">${esc(l.name || l)}</span>`).join(' ')
      : '';
    return `
      <tr>
        <td class="mono"><a href="${esc(issue.url)}" target="_blank">#${issue.number}</a></td>
        <td class="truncate">${esc(issue.title)}</td>
        <td>${labels || '<span class="text-muted">—</span>'}</td>
        <td class="text-muted">${relTime(issue.createdAt)}</td>
        <td><a href="${esc(issue.url)}" target="_blank" class="btn btn-sm">Open</a></td>
      </tr>
    `;
  }).join('');

  return `
    ${tabHeader(title, `<button class="btn btn-sm" onclick="switchTab('finance')">↺ Refresh</button>`)}
    ${data.pr_error ? errorCard('PRs: ' + data.pr_error) : ''}
    ${data.issue_error ? errorCard('Issues: ' + data.issue_error) : ''}

    <div class="section">
      <div class="section-header">
        <span class="section-title">Open PRs</span>
        <span class="badge badge-accent">${prs.length}</span>
      </div>
      ${prs.length === 0
        ? emptyState(data.pr_error ? 'Could not load PRs' : 'No open PRs')
        : `<div class="table-wrap">
            <table>
              <thead><tr><th>#</th><th>Title</th><th>Author</th><th>Opened</th><th></th></tr></thead>
              <tbody>${prRows}</tbody>
            </table>
          </div>`}
    </div>

    <div class="section">
      <div class="section-header">
        <span class="section-title">Open Issues</span>
        <span class="badge badge-accent">${issues.length}</span>
      </div>
      ${issues.length === 0
        ? emptyState(data.issue_error ? 'Could not load issues' : 'No open issues')
        : `<div class="table-wrap">
            <table>
              <thead><tr><th>#</th><th>Title</th><th>Labels</th><th>Opened</th><th></th></tr></thead>
              <tbody>${issueRows}</tbody>
            </table>
          </div>`}
    </div>
  `;
}

// ── Cron ─────────────────────────────────────────────
function renderCron(data, title) {
  if (data && data.error) {
    return tabHeader(title) + errorCard(data.error);
  }
  const jobs = Array.isArray(data) ? data : [];

  const rows = jobs.map(job => {
    const id = job.id || job.name;
    const enabled = job.enabled !== false && job.active !== false && job.status !== 'disabled';
    const toggleClass = enabled ? 'btn-on' : 'btn-off';
    const toggleLabel = enabled ? '● On' : '○ Off';

    return `
      <tr>
        <td class="mono">${esc(String(id))}</td>
        <td>${esc(job.name || job.description || '—')}</td>
        <td class="mono text-muted">${esc(job.schedule || job.cron || '—')}</td>
        <td class="text-muted">${relTime(job.last_run || job.lastRun || job.last_ran)}</td>
        <td><span class="badge ${enabled ? 'badge-accent' : ''}">${job.status || (enabled ? 'active' : 'disabled')}</span></td>
        <td>
          <button class="btn btn-sm ${toggleClass}" onclick="cronToggle('${esc(String(id))}', this)">${toggleLabel}</button>
        </td>
        <td>
          <button class="btn btn-sm btn-run" onclick="cronRun('${esc(String(id))}', this)">▶ Run</button>
        </td>
      </tr>
    `;
  }).join('');

  return `
    ${tabHeader(title, `<button class="btn btn-sm" onclick="switchTab('cron')">↺ Refresh</button>`)}
    ${jobs.length === 0
      ? emptyState('No cron jobs found')
      : `<div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Schedule</th><th>Last Run</th><th>Status</th><th>Toggle</th><th>Run</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`}
  `;
}

async function cronToggle(jobId, btn) {
  btn.disabled = true;
  btn.textContent = '…';
  try {
    const res = await api(`/api/crons/${encodeURIComponent(jobId)}/toggle`, { method: 'POST' });
    if (res.ok) {
      switchTab('cron');
    } else {
      alert('Toggle failed: ' + (res.error || 'unknown error'));
      btn.disabled = false;
    }
  } catch (e) {
    alert('Toggle failed: ' + e.message);
    btn.disabled = false;
  }
}

async function cronRun(jobId, btn) {
  btn.disabled = true;
  btn.textContent = '…';
  try {
    const res = await api(`/api/crons/${encodeURIComponent(jobId)}/run`, { method: 'POST' });
    if (res.ok) {
      btn.textContent = '✓ Done';
      setTimeout(() => { btn.textContent = '▶ Run'; btn.disabled = false; }, 3000);
    } else {
      alert('Run failed: ' + (res.error || 'unknown'));
      btn.textContent = '▶ Run';
      btn.disabled = false;
    }
  } catch (e) {
    alert('Run failed: ' + e.message);
    btn.textContent = '▶ Run';
    btn.disabled = false;
  }
}

// ── Screener ─────────────────────────────────────────
function renderScreener(data, title) {
  let body = '';
  if (data === null) {
    body = `<div class="empty-state">Click "Run Scan" to fetch signals.</div>`;
  } else if (data && data.error) {
    body = errorCard(data.error);
  } else if (data) {
    body = renderScreenerData(data);
  }

  return `
    ${tabHeader(title, `<button class="btn btn-accent" id="scan-btn" onclick="runScreenerScan()">▶ Run Scan</button>`)}
    <div id="screener-results">${body}</div>
  `;
}

function renderScreenerData(data) {
  const longs  = Array.isArray(data.longs)  ? data.longs  : [];
  const shorts = Array.isArray(data.shorts) ? data.shorts : [];

  // Handle flat array format
  if (!data.longs && !data.shorts && Array.isArray(data)) {
    return `<div class="table-wrap"><table>
      <thead><tr><th>Token</th><th>Chain</th><th>Signal</th><th>Score</th></tr></thead>
      <tbody>${data.map(s => `
        <tr>
          <td><strong>${esc(s.token || s.symbol || '—')}</strong></td>
          <td>${esc(s.chain || '—')}</td>
          <td>${esc(s.signal || s.type || '—')}</td>
          <td class="num">${s.score != null ? Number(s.score).toFixed(2) : '—'}</td>
        </tr>
      `).join('')}</tbody>
    </table></div>`;
  }

  function signalList(signals) {
    if (!signals.length) return emptyState('No signals');
    return `<ul class="signal-list">${signals.map(s => `
      <li class="signal-item">
        <span>
          <span class="signal-token">${esc(s.token || s.symbol || '—')}</span>
          <span class="signal-chain">${esc(s.chain || '')}</span>
        </span>
        <span class="signal-score ${s.score > 0 ? 'pos' : 'neg'}">
          ${s.score != null ? (s.score > 0 ? '+' : '') + Number(s.score).toFixed(2) : esc(s.reason || '')}
        </span>
      </li>
    `).join('')}</ul>`;
  }

  return `
    <div class="two-col">
      <div>
        <div class="section-header"><span class="section-title pos">▲ Longs</span><span class="badge badge-accent">${longs.length}</span></div>
        <div class="card" style="padding:0">${signalList(longs)}</div>
      </div>
      <div>
        <div class="section-header"><span class="section-title neg">▼ Shorts</span><span class="badge">${shorts.length}</span></div>
        <div class="card" style="padding:0">${signalList(shorts)}</div>
      </div>
    </div>
  `;
}

async function runScreenerScan() {
  const btn = document.getElementById('scan-btn');
  const results = document.getElementById('screener-results');
  if (!btn || !results) return;
  btn.disabled = true;
  btn.textContent = '⏳ Scanning…';
  results.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';
  try {
    const data = await api('/api/screener', { method: 'POST' });
    results.innerHTML = renderScreenerData(data);
  } catch (e) {
    results.innerHTML = errorCard(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ Run Scan';
  }
}

// ── Research ─────────────────────────────────────────
function renderResearch(title) {
  const tiles = [
    {
      icon: '📈',
      name: 'LAT S4',
      desc: 'Live trading strategy. RSI + EMA filter on Base + Solana.',
      status: '🟢 Running',
      path: '~/workspace/backtests/lat-s4/',
    },
    {
      icon: '🔍',
      name: 'Strategy 3 Screener',
      desc: 'Node.js screener — runs on-demand, outputs longs/shorts signals.',
      status: '⚡ On-demand',
      path: '~/workspace/strategy3-screener/',
    },
    {
      icon: '🏦',
      name: 'Finance Ops',
      desc: 'nansen-finance-restricted — bookkeeping, payroll, invoices.',
      status: '📋 See Finance tab',
      path: 'github.com/nansen-ai/nansen-finance-restricted',
    },
    {
      icon: '🤖',
      name: 'OpenClaw',
      desc: 'AI agent infra. Cron scheduler, session management, gateway proxy.',
      status: '✅ Active',
      path: 'port 18790',
    },
    {
      icon: '📝',
      name: 'Notes',
      desc: 'Personal scratchpad. Markdown, auto-saved.',
      status: '💾 ~/workspace/kk-control/notes.md',
      path: '',
    },
    {
      icon: '🧮',
      name: 'GST / Tax',
      desc: 'Crypto transaction review for GST obligations. Pending.',
      status: '🟡 In progress',
      path: '',
    },
  ];

  return `
    ${tabHeader(title)}
    <div class="tile-grid">
      ${tiles.map(t => `
        <div class="tile">
          <div class="tile-icon">${t.icon}</div>
          <div class="tile-name">${esc(t.name)}</div>
          <div class="tile-desc">${esc(t.desc)}</div>
          <div class="tile-status text-muted">${esc(t.status)}</div>
          ${t.path ? `<div class="tile-status mono" style="font-size:10px;margin-top:4px;color:var(--muted)">${esc(t.path)}</div>` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

// ── Chat (Sessions) ──────────────────────────────────
function renderChat(data, title) {
  if (data && data.error) {
    return tabHeader(title) + errorCard(data.error);
  }
  const sessions = Array.isArray(data) ? data : [];

  const items = sessions.map(s => {
    const id = s.id || s.session_id || s.name || '—';
    const model = s.model || s.agent || '—';
    const created = s.created_at || s.createdAt || s.started_at || s.timestamp;
    const msgs = s.message_count || s.messages || s.turns || null;
    const status = s.status || '';

    return `
      <div class="session-item">
        <div>
          <div class="session-id">${esc(String(id).slice(0, 40))}</div>
          <div class="session-meta">${esc(model)} ${msgs != null ? `· ${msgs} msgs` : ''} ${status ? `· ${esc(status)}` : ''}</div>
        </div>
        <div class="text-muted" style="font-size:11px;text-align:right">
          ${relTime(created)}<br>
          <span class="mono" style="font-size:10px">${fmtTs(created)}</span>
        </div>
      </div>
    `;
  }).join('');

  return `
    ${tabHeader(title, `<button class="btn btn-sm" onclick="switchTab('chat')">↺ Refresh</button>`)}
    <div class="section">
      <div class="section-header">
        <span class="section-title">Recent Sessions</span>
        <span class="badge">${sessions.length}</span>
      </div>
      ${sessions.length === 0
        ? emptyState('No sessions found')
        : `<div class="card" style="padding:0">${items}</div>`}
    </div>
  `;
}

// ── Notes ────────────────────────────────────────────
function renderNotes(data, title) {
  const content = data && !data.error ? (data.content || '') : '';
  const errHtml = data && data.error ? errorCard(data.error) : '';

  // Defer binding to after DOM insert
  setTimeout(() => {
    const ta = document.getElementById('notes-ta');
    const saved = document.getElementById('notes-saved');
    if (!ta) return;
    let saveTimer = null;
    ta.addEventListener('input', () => {
      if (saved) saved.textContent = '';
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => saveNotes(ta.value, saved), 1500);
    });
    ta.addEventListener('blur', () => {
      clearTimeout(saveTimer);
      saveNotes(ta.value, saved);
    });
  }, 0);

  return `
    ${tabHeader(title)}
    ${errHtml}
    <div class="notes-wrap">
      <textarea id="notes-ta" class="notes-area" placeholder="Jot things down…">${esc(content)}</textarea>
      <div id="notes-saved" class="notes-saved"></div>
    </div>
  `;
}

async function saveNotes(content, savedEl) {
  try {
    await fetch(BASE + '/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: content,
    });
    if (savedEl) {
      savedEl.textContent = '✓ Saved';
      setTimeout(() => { if (savedEl) savedEl.textContent = ''; }, 2000);
    }
  } catch (e) {
    if (savedEl) savedEl.textContent = '✗ Save failed';
  }
}
