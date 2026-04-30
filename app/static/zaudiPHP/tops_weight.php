<?php
header('Content-Type: text/html; charset=utf-8');
require_once 'config.php';
require_once 'session_auth.php';
date_default_timezone_set('America/Edmonton');

function get_all_weights(PDO $db): array {
    try {
        $stmt = $db->query("SELECT weigh_id, weighed_at, weight_lbs, notes FROM weigh_ins ORDER BY weighed_at ASC");
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) { return []; }
}

function already_weighed_this_week(PDO $db): bool {
    try {
        $stmt = $db->prepare("SELECT COUNT(*) FROM weigh_ins WHERE YEARWEEK(weighed_at, 1) = YEARWEEK(CURDATE(), 1)");
        $stmt->execute();
        return (int) $stmt->fetchColumn() > 0;
    } catch (Exception $e) { return false; }
}

$saved = null; $error = null;

try {
    $db = get_db();
    $weights      = get_all_weights($db);
    $weighed_week = already_weighed_this_week($db);
} catch (Exception $e) {
    $weights = []; $weighed_week = false;
    $error = 'DB: ' . $e->getMessage();
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $weight_lbs = trim($_POST['weight_lbs'] ?? '');
    $notes      = trim($_POST['notes']      ?? '') ?: null;
    $weighed_at = trim($_POST['weighed_at'] ?? date('Y-m-d'));
    if (!$weight_lbs || !is_numeric($weight_lbs)) {
        $error = 'Please enter a valid weight.';
    } else {
        try {
            $weigh_id = 'wi-' . round(microtime(true) * 1000);
            $db->prepare("INSERT INTO weigh_ins (weigh_id, weighed_at, weight_lbs, notes) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE weight_lbs = VALUES(weight_lbs), notes = VALUES(notes)")
               ->execute([$weigh_id, $weighed_at, (float)$weight_lbs, $notes]);
            $saved = ['weight_lbs' => (float)$weight_lbs, 'weighed_at' => $weighed_at];
            $weights = get_all_weights($db);
            $weighed_week = true;
        } catch (Exception $e) { $error = $e->getMessage(); }
    }
}

$trend_note = '';
if (count($weights) >= 2) {
    $first = (float) $weights[0]['weight_lbs'];
    $last  = (float) end($weights)['weight_lbs'];
    $diff  = round($last - $first, 1);
    $trend_note = $diff < 0 ? abs($diff) . ' lbs lost overall' : ($diff > 0 ? $diff . ' lbs gained overall' : 'No change overall');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>TOPS &mdash; Weigh-in</title>
<link rel="icon" href="https://zaudi.com/favicon.ico" type="image/x-icon">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
    --bg:#0e0f11; --surface:#16181c; --surface2:#1e2026; --border:#2a2d35;
    --text:#e2e4e9; --muted:#6b7280; --accent:#4f8ef7;
    --success:#22c55e; --warn:#facc15; --danger:#f87171;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body { background: var(--bg); color: var(--text); font-family: 'Syne', sans-serif; font-size: 15px; min-height: 100vh; padding-bottom: 40px; }
header { position: sticky; top: 0; z-index: 10; background: var(--bg); border-bottom: 1px solid var(--border); padding: 14px 16px 10px; display: flex; align-items: baseline; gap: 10px; }
header h1 { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
header .links { margin-left: auto; display: flex; gap: 12px; }
header a { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); text-decoration: none; }
.wrap { padding: 20px 16px; }
.section { margin-bottom: 24px; }
.section-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }
.weighed-banner { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.3); border-radius: 10px; padding: 10px 14px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--success); margin-bottom: 16px; }
.confirm-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 20px; }
.confirm-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--success); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 14px; }
.big-weight { padding: 24px 16px; text-align: center; border-bottom: 1px solid var(--border); }
.big-weight-val { font-family: 'JetBrains Mono', monospace; font-size: 48px; font-weight: 600; line-height: 1; }
.big-weight-unit { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--muted); margin-top: 6px; }
.field { margin-bottom: 16px; }
label { display: block; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px; }
input[type="number"], input[type="date"], input[type="text"] { width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 14px; padding: 12px 14px; outline: none; transition: border-color 0.15s; appearance: none; -webkit-appearance: none; }
input:focus { border-color: var(--accent); }
.submit-btn {
    display: flex; align-items: center; justify-content: center;
    width: 100%; min-height: 52px; padding: 0 15px;
    background: var(--accent); border: none; border-radius: 12px; color: #fff;
    font-family: 'Syne', sans-serif; font-size: 16px; font-weight: 700;
    cursor: pointer; transition: opacity 0.15s; text-decoration: none;
}
.submit-btn:active { opacity: 0.8; }
.error-bar { background: rgba(239,68,68,0.12); border: 1px solid var(--danger); border-radius: 10px; color: var(--danger); font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 10px 14px; margin-bottom: 16px; }
.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 24px; }
.chart-meta { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); margin-top: 8px; text-align: center; }
.history-list { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 24px; }
.history-row { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--border); }
.history-row:last-child { border-bottom: none; }
.history-date { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); flex: 1; }
.history-wt { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 600; }
.history-delta { font-family: 'JetBrains Mono', monospace; font-size: 11px; min-width: 50px; text-align: right; }
.nav-btn {
    display: flex; align-items: center; justify-content: center;
    width: 100%; min-height: 48px; padding: 0 13px; margin-bottom: 10px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    color: var(--muted); font-family: 'Syne', sans-serif; font-size: 14px;
    text-decoration: none; cursor: pointer;
}
.empty { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); padding: 20px; text-align: center; }
@media (min-width: 600px) { body { max-width: 480px; margin: 0 auto; } }
</style>
</head>
<body>
<header>
    <h1>TOPS &mdash; Weigh-in</h1>
    <div class="links">
        <a href="/tops">&#x2190; Log</a>
        <a href="/tops_dash">&#x2022;&#x2022;&#x2022;</a>
    </div>
</header>

<div class="wrap">
    <?php if ($saved): ?>
    <div class="confirm-label">&#x2713; Logged</div>
    <div class="confirm-card">
        <div class="big-weight">
            <div class="big-weight-val"><?= number_format($saved['weight_lbs'], 1) ?></div>
            <div class="big-weight-unit">lbs &middot; <?= date('M j, Y', strtotime($saved['weighed_at'])) ?></div>
        </div>
    </div>
    <?php else: ?>
    <?php if ($error): ?><div class="error-bar">&#x26A0; <?= htmlspecialchars($error) ?></div><?php endif ?>
    <?php if ($weighed_week && !$error): ?><div class="weighed-banner">&#x2713; Already weighed in this week &mdash; updating is fine.</div><?php endif ?>
    <div class="section">
        <form method="POST" action="">
            <div class="field">
                <label>Weight (lbs)</label>
                <input type="number" name="weight_lbs" step="0.1" min="50" max="500" placeholder="e.g. 187.5" autofocus value="<?= htmlspecialchars($_POST['weight_lbs'] ?? '') ?>">
            </div>
            <div class="field">
                <label>Date</label>
                <input type="date" name="weighed_at" value="<?= htmlspecialchars($_POST['weighed_at'] ?? date('Y-m-d')) ?>">
            </div>
            <div class="field">
                <label>Notes <span style="color:var(--muted);font-size:10px">(optional)</span></label>
                <input type="text" name="notes" placeholder="e.g. after workout, morning" value="<?= htmlspecialchars($_POST['notes'] ?? '') ?>">
            </div>
            <button type="submit" class="submit-btn">Record weight</button>
        </form>
    </div>
    <?php endif ?>

    <?php if (count($weights) >= 2): ?>
    <div class="section">
        <div class="section-label">Trend</div>
        <div class="chart-wrap">
            <svg id="trend-chart" width="100%" height="140" viewBox="0 0 340 140" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"></svg>
            <?php if ($trend_note): ?><div class="chart-meta"><?= htmlspecialchars($trend_note) ?></div><?php endif ?>
        </div>
    </div>
    <?php endif ?>

    <?php if (!empty($weights)): ?>
    <div class="section">
        <div class="section-label">History</div>
        <div class="history-list">
            <?php foreach (array_reverse($weights) as $w): ?>
            <div class="history-row">
                <span class="history-date"><?= date('M j, Y', strtotime($w['weighed_at'])) ?></span>
                <span class="history-wt"><?= number_format((float)$w['weight_lbs'], 1) ?> lbs</span>
                <span class="history-delta"></span>
            </div>
            <?php endforeach ?>
        </div>
    </div>
    <?php endif ?>

    <a class="nav-btn" href="/tops">&#x2190; Back to log</a>
</div>

<script>
const pts = <?= json_encode(array_map(fn($w) => ['date' => $w['weighed_at'], 'wt' => (float)$w['weight_lbs']], $weights)) ?>;
if (pts.length >= 2) {
    const svg = document.getElementById('trend-chart');
    const W=340,H=140,pad=16;
    const wts=pts.map(p=>p.wt);
    const minW=Math.min(...wts),maxW=Math.max(...wts),range=maxW-minW||1;
    const toX=i=>pad+(i/(pts.length-1))*(W-pad*2);
    const toY=wt=>H-pad-((wt-minW)/range)*(H-pad*2);
    let area=`M ${toX(0)} ${H-pad}`;
    pts.forEach((p,i)=>{area+=` L ${toX(i)} ${toY(p.wt)}`;});
    area+=` L ${toX(pts.length-1)} ${H-pad} Z`;
    const fill=document.createElementNS('http://www.w3.org/2000/svg','path');
    fill.setAttribute('d',area);fill.setAttribute('fill','rgba(79,142,247,0.12)');svg.appendChild(fill);
    let d='';
    pts.forEach((p,i)=>{d+=(i===0?'M':'L')+` ${toX(i)} ${toY(p.wt)} `;});
    const line=document.createElementNS('http://www.w3.org/2000/svg','path');
    line.setAttribute('d',d);line.setAttribute('fill','none');
    line.setAttribute('stroke','#4f8ef7');line.setAttribute('stroke-width','2');
    line.setAttribute('stroke-linejoin','round');line.setAttribute('stroke-linecap','round');
    svg.appendChild(line);
    pts.forEach((p,i)=>{
        const isLast=i===pts.length-1;
        const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
        c.setAttribute('cx',toX(i));c.setAttribute('cy',toY(p.wt));
        c.setAttribute('r',isLast?4:3);c.setAttribute('fill',isLast?'#4f8ef7':'#2a2d35');
        c.setAttribute('stroke','#4f8ef7');c.setAttribute('stroke-width','2');svg.appendChild(c);
    });
    [[wts.indexOf(maxW),maxW,-8],[wts.indexOf(minW),minW,14]].forEach(([idx,val,dy])=>{
        const t=document.createElementNS('http://www.w3.org/2000/svg','text');
        t.setAttribute('x',toX(idx));t.setAttribute('y',toY(val)+dy);
        t.setAttribute('text-anchor','middle');t.setAttribute('font-size','9');
        t.setAttribute('fill','#6b7280');t.setAttribute('font-family','JetBrains Mono, monospace');
        t.textContent=val.toFixed(1);svg.appendChild(t);
    });
}
const allWts=<?= json_encode(array_map(fn($w)=>(float)$w['weight_lbs'],$weights)) ?>;
const rev=[...allWts].reverse();
document.querySelectorAll('.history-delta').forEach((el,i)=>{
    if(i>=rev.length-1)return;
    const diff=Math.round((rev[i]-rev[i+1])*10)/10;
    el.textContent=diff>0?'+'+diff:diff===0?'':String(diff);
    el.style.color=diff<0?'#22c55e':diff>0?'#f87171':'#6b7280';
});
</script>
</body>
</html>
