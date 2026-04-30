<?php
header('Content-Type: text/html; charset=utf-8');
require_once 'config.php';
require_once 'session_auth.php';
date_default_timezone_set('America/Edmonton');

$daily_target = defined('DAILY_CALORIES') ? DAILY_CALORIES : 1800;

function get_today_entries(PDO $db): array {
    try {
        $stmt = $db->prepare("SELECT log_id, logged_at, category, venue, item, portion_pct, est_calories, notes FROM food_log WHERE DATE(logged_at) = CURDATE() ORDER BY logged_at ASC");
        $stmt->execute();
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) { return []; }
}

function get_week_entries(PDO $db): array {
    try {
        $stmt = $db->prepare("SELECT DATE(logged_at) as day, COALESCE(SUM(est_calories), 0) as total_cal, COUNT(*) as entries FROM food_log WHERE logged_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) GROUP BY DATE(logged_at) ORDER BY day ASC");
        $stmt->execute();
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) { return []; }
}

function get_latest_weight(PDO $db): ?array {
    try {
        $stmt = $db->prepare("SELECT weight_lbs, weighed_at FROM weigh_ins ORDER BY weighed_at DESC LIMIT 1");
        $stmt->execute();
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        return $row ?: null;
    } catch (Exception $e) { return null; }
}

function category_color(string $cat): string {
    return match(true) {
        str_contains($cat, 'breakfast') => '#f59e0b',
        str_contains($cat, 'lunch')     => '#7dd3fc',
        str_contains($cat, 'dinner')    => '#facc15',
        str_contains($cat, 'snack')     => '#f87171',
        str_contains($cat, 'restaurant')=> '#fb923c',
        default                          => '#6b7280',
    };
}

function category_label(string $cat): string {
    return match(true) {
        str_contains($cat, 'breakfast') => 'Breakfast',
        str_contains($cat, 'lunch')     => 'Lunch',
        str_contains($cat, 'dinner')    => 'Dinner',
        str_contains($cat, 'snack')     => 'Snack',
        str_contains($cat, 'restaurant')=> 'Eat Out',
        default                          => $cat,
    };
}

function fmt_time(string $dt): string { return date('g:ia', strtotime($dt)); }

function balance_color(int $b): string {
    if ($b > 400) return '#22c55e';
    if ($b > 0)   return '#facc15';
    return '#f87171';
}

try {
    $db        = get_db();
    $entries   = get_today_entries($db);
    $week      = get_week_entries($db);
    $latest_wt = get_latest_weight($db);
} catch (Exception $e) {
    $entries = []; $week = []; $latest_wt = null;
}

$total_consumed = array_sum(array_column($entries, 'est_calories'));
$remaining      = $daily_target - $total_consumed;

$pie_slices = [];
foreach ($entries as $e) {
    if ($e['est_calories'] === null) continue;
    $cat = $e['category'];
    if (!isset($pie_slices[$cat])) {
        $pie_slices[$cat] = ['cal' => 0, 'color' => category_color($cat), 'label' => category_label($cat)];
    }
    $pie_slices[$cat]['cal'] += (int) $e['est_calories'];
}
if ($remaining > 0) {
    $pie_slices['__remaining__'] = ['cal' => $remaining, 'color' => '#22c55e', 'label' => 'Remaining'];
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>TOPS &mdash; Dashboard</title>
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
.stat-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 24px; }
.stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px 10px; text-align: center; }
.stat-val { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; line-height: 1; margin-bottom: 4px; }
.stat-lbl { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.pie-wrap { display: flex; align-items: center; gap: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 24px; }
.pie-wrap svg { flex-shrink: 0; overflow: visible; }
.legend { flex: 1; }
.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; }
.legend-item:last-child { margin-bottom: 0; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-name { color: var(--text); flex: 1; }
.legend-cal { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); }
.entry-list { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 24px; }
.entry-row { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--border); }
.entry-row:last-child { border-bottom: none; }
.entry-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.entry-body { flex: 1; min-width: 0; }
.entry-item { font-size: 13px; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.entry-meta { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); margin-top: 2px; }
.entry-cal { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); flex-shrink: 0; }
.week-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 24px; }
.week-bars { display: flex; align-items: flex-end; gap: 6px; height: 60px; margin-bottom: 6px; }
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; }
.bar { width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; opacity: 0.7; min-height: 2px; }
.bar.today { opacity: 1; }
.bar-lbl { font-family: 'JetBrains Mono', monospace; font-size: 8px; color: var(--muted); text-transform: uppercase; }
.weight-row { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; display: flex; align-items: baseline; gap: 10px; margin-bottom: 24px; }
.weight-val { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; }
.weight-unit { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); }
.weight-date { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); margin-left: auto; }
.log-btn {
    display: flex; align-items: center; justify-content: center;
    width: 100%; min-height: 52px; padding: 0 15px;
    background: var(--accent); border: none; border-radius: 12px; color: #fff;
    font-family: 'Syne', sans-serif; font-size: 16px; font-weight: 700;
    text-decoration: none; cursor: pointer;
}
.empty { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); padding: 20px; text-align: center; }
@media (min-width: 600px) { body { max-width: 480px; margin: 0 auto; } }
</style>
</head>
<body>
<header>
    <h1>TOPS &mdash; Today</h1>
    <div class="links"><a href="/tops_weight">&#x2696; Weigh-in</a></div>
</header>

<div class="wrap">
    <div class="stat-row">
        <div class="stat-card"><div class="stat-val"><?= $total_consumed ?></div><div class="stat-lbl">consumed</div></div>
        <div class="stat-card"><div class="stat-val" style="color:<?= balance_color($remaining) ?>"><?= $remaining ?></div><div class="stat-lbl">remaining</div></div>
        <div class="stat-card"><div class="stat-val"><?= count($entries) ?></div><div class="stat-lbl">entries</div></div>
    </div>

    <?php if (!empty($pie_slices)): ?>
    <div class="section">
        <div class="section-label">Calorie breakdown</div>
        <div class="pie-wrap">
            <svg id="pie" width="110" height="110" viewBox="-10 -10 120 120" xmlns="http://www.w3.org/2000/svg" overflow="visible">
                <defs>
                    <filter id="pie-shadow" x="-20%" y="-20%" width="150%" height="150%">
                        <feDropShadow dx="3" dy="3" stdDeviation="3" flood-color="#000000" flood-opacity="0.45"/>
                    </filter>
                </defs>
            </svg>
            <div class="legend" id="legend"></div>
        </div>
    </div>
    <?php endif ?>

    <div class="section">
        <div class="section-label">Today</div>
        <?php if (empty($entries)): ?>
        <div class="entry-list"><div class="empty">Nothing logged yet today.</div></div>
        <?php else: ?>
        <div class="entry-list">
            <?php foreach ($entries as $e): ?>
            <div class="entry-row">
                <div class="entry-dot" style="background:<?= category_color($e['category']) ?>"></div>
                <div class="entry-body">
                    <div class="entry-item"><?= htmlspecialchars($e['item']) ?></div>
                    <div class="entry-meta"><?= category_label($e['category']) ?> &middot; <?= fmt_time($e['logged_at']) ?> &middot; <?= $e['portion_pct'] ?>%</div>
                </div>
                <div class="entry-cal"><?= $e['est_calories'] !== null ? $e['est_calories'] . ' cal' : '&mdash;' ?></div>
            </div>
            <?php endforeach ?>
        </div>
        <?php endif ?>
    </div>

    <div class="section">
        <div class="section-label">This week</div>
        <div class="week-wrap">
            <?php
            $week_by_day = [];
            foreach ($week as $w) $week_by_day[$w['day']] = $w;
            $max_cal = max(array_merge([1], array_column($week, 'total_cal')));
            $days_shown = [];
            for ($i = 6; $i >= 0; $i--) {
                $d   = date('Y-m-d', strtotime("-{$i} days"));
                $lbl = strtoupper(substr(date('D', strtotime($d)), 0, 1));
                $cal = isset($week_by_day[$d]) ? (int)$week_by_day[$d]['total_cal'] : 0;
                $days_shown[] = ['d' => $d, 'lbl' => $lbl, 'cal' => $cal, 'today' => $i === 0];
            }
            $max_h = 55;
            ?>
            <div class="week-bars">
                <?php foreach ($days_shown as $ds):
                    $h = $max_cal > 0 ? round(($ds['cal'] / $max_cal) * $max_h) : 0;
                    $h = max($h, $ds['cal'] > 0 ? 4 : 2);
                ?>
                <div class="bar-col">
                    <div class="bar <?= $ds['today'] ? 'today' : '' ?>" style="height:<?= $h ?>px"></div>
                    <span class="bar-lbl"><?= $ds['lbl'] ?></span>
                </div>
                <?php endforeach ?>
            </div>
        </div>
    </div>

    <?php if ($latest_wt): ?>
    <div class="section">
        <div class="section-label">Last weigh-in</div>
        <div class="weight-row">
            <span class="weight-val"><?= number_format($latest_wt['weight_lbs'], 1) ?></span>
            <span class="weight-unit">lbs</span>
            <span class="weight-date"><?= date('M j', strtotime($latest_wt['weighed_at'])) ?></span>
        </div>
    </div>
    <?php endif ?>

    <a class="log-btn" href="/tops">+ Log a meal</a>
</div>

<script>
const slices = <?= json_encode(array_values($pie_slices)) ?>;
const total  = slices.reduce((s,sl)=>s+sl.cal,0);
if (total > 0 && slices.length > 0) {
    const svg=document.getElementById('pie');
    const legend=document.getElementById('legend');
    const cx=50,cy=50,r=45;
    let startAngle=-Math.PI/2;
    slices.forEach(sl=>{
        const pct=sl.cal/total,angle=pct*2*Math.PI,end=startAngle+angle;
        const x1=cx+r*Math.cos(startAngle),y1=cy+r*Math.sin(startAngle);
        const x2=cx+r*Math.cos(end),y2=cy+r*Math.sin(end);
        const large=angle>Math.PI?1:0;
        if(pct<1){
            const path=document.createElementNS('http://www.w3.org/2000/svg','path');
            path.setAttribute('d',`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`);
            path.setAttribute('fill',sl.color);path.setAttribute('filter','url(#pie-shadow)');
            svg.appendChild(path);
        } else {
            const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');
            circle.setAttribute('cx',cx);circle.setAttribute('cy',cy);
            circle.setAttribute('r',r);circle.setAttribute('fill',sl.color);
            circle.setAttribute('filter','url(#pie-shadow)');svg.appendChild(circle);
        }
        startAngle=end;
        const item=document.createElement('div');
        item.className='legend-item';
        item.innerHTML=`<div class="legend-dot" style="background:${sl.color}"></div><span class="legend-name">${sl.label}</span><span class="legend-cal">${sl.cal}</span>`;
        legend.appendChild(item);
    });
}
</script>
</body>
</html>
