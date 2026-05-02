<?php
header('Content-Type: text/html; charset=utf-8');
require_once 'config.php';
require_once 'session_auth.php';
date_default_timezone_set('America/Edmonton');

$daily_target = defined('DAILY_CALORIES') ? DAILY_CALORIES : 1800;

function get_library(PDO $db): array {
    try {
        $stmt = $db->query("SELECT item_name, venue, category, calories, unit_desc, mia_rating FROM food_library ORDER BY category, venue, item_name");
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) { return []; }
}

function get_today_consumed(PDO $db): int {
    try {
        $stmt = $db->prepare("SELECT COALESCE(SUM(est_calories),0) FROM food_log WHERE DATE(logged_at) = CURDATE()");
        $stmt->execute();
        return (int) $stmt->fetchColumn();
    } catch (Exception $e) { return 0; }
}

function get_streak(PDO $db): array {
    $days = [];
    for ($i = 6; $i >= 0; $i--) {
        $d = date('Y-m-d', strtotime("-{$i} days"));
        try {
            $s = $db->prepare("SELECT COUNT(*) FROM food_log WHERE DATE(logged_at) = ?");
            $s->execute([$d]);
            $hit = (int) $s->fetchColumn() > 0;
        } catch (Exception $e) { $hit = false; }
        $days[] = ['day' => strtoupper(substr(date('D', strtotime($d)), 0, 1)), 'hit' => $hit, 'today' => $i === 0];
    }
    return $days;
}

function parse_portion_pct(string $portion): int {
    $p = trim(strtolower($portion));
    $p = preg_replace('/\s+(cups?|oz|g|ml|servings?|slices?|pieces?|tbsp|tsp|cans?|pkg|pack)\s*$/', '', $p);
    $p = trim($p);
    if ($p === '' || $p === 'standard' || $p === 'whole' || $p === 'full') return 100;
    if ($p === 'half')                           return 50;
    if ($p === 'quarter')                        return 25;
    if ($p === 'third')                          return 33;
    if ($p === 'two thirds'  || $p === '2/3')    return 67;
    if ($p === 'three quarters' || $p === '3/4') return 75;
    if (preg_match('/^(\d+(?:\.\d+)?)\s*%$/', $p, $m)) return (int) round((float)$m[1]);
    if (preg_match('/^(\d+)\s*\/\s*(\d+)$/',  $p, $m)) return (int) round(($m[1] / $m[2]) * 100);
    if (preg_match('/^(\d+(?:\.\d+)?)$/',      $p, $m)) return (int) round((float)$m[1]);
    return 100;
}

function get_categories(PDO $db): array {
    $base = ['restaurant', 'snack', 'breakfast-home', 'lunch-home', 'dinner-home', 'cheat'];
    try {
        $stmt = $db->query("SELECT DISTINCT category FROM food_library ORDER BY category");
        $db_cats = array_column($stmt->fetchAll(PDO::FETCH_ASSOC), 'category');
        return array_values(array_unique(array_merge($base, $db_cats)));
    } catch (Exception $e) { return $base; }
}

function category_label_from_slug(string $slug): string {
    $map = [
        'restaurant'     => 'Restaurant',
        'snack'          => 'Snack',
        'breakfast'      => 'Breakfast',
        'breakfast-home' => 'Breakfast - Home',
        'lunch-home'     => 'Lunch - Home',
        'dinner-home'    => 'Dinner - Home',
        'eat-out'        => 'Eat Out',
        'cheat'          => 'Cheat Day',
    ];
    return $map[$slug] ?? ucwords(str_replace('-', ' ', $slug));
}

function lookup_calories(PDO $db, string $item, string $venue): ?int {
    try {
        $stmt = $db->prepare("SELECT calories FROM food_library WHERE item_name = ? AND venue = ? LIMIT 1");
        $stmt->execute([$item, $venue]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        return $row ? (int) $row['calories'] : null;
    } catch (Exception $e) { return null; }
}

function balance_color(int $b): string {
    if ($b > 400) return '#22c55e';
    if ($b > 0)   return '#facc15';
    return '#f87171';
}

$logged_entry = null;
$error        = null;
$portion      = '100%';

try {
    $db             = get_db();
    $library        = get_library($db);
    $categories     = get_categories($db);
    $today_consumed = get_today_consumed($db);
    $today_balance  = $daily_target - $today_consumed;
    $streak         = get_streak($db);
} catch (Exception $e) {
    $base_cats  = ['restaurant', 'snack', 'breakfast-home', 'lunch-home', 'dinner-home', 'cheat'];
    $library    = []; $categories = $base_cats; $today_balance = $daily_target; $streak = [];
    $error = 'DB: ' . $e->getMessage();
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $category = trim($_POST['category'] ?? '');
    $venue    = trim($_POST['venue']    ?? '');
    $item     = trim($_POST['item']     ?? '');
    $portion  = trim($_POST['portion']  ?? '100%') ?: '100%';
    $notes    = trim($_POST['notes']    ?? '') ?: null;

    if (!$category || !$venue || !$item) {
        $error = 'Category, venue, and item are required.';
    } else {
        try {
            $portion_pct  = parse_portion_pct($portion);
            $base_cal     = lookup_calories($db, $item, $venue);
            $est_calories = $base_cal !== null ? (int) round($base_cal * ($portion_pct / 100)) : null;
            $consumed_now  = get_today_consumed($db);
            $daily_balance = $est_calories !== null ? $daily_target - $consumed_now - $est_calories : null;
            $log_id = 'log-' . round(microtime(true) * 1000);
            $now    = date('Y-m-d H:i:s');

            $db->prepare("INSERT INTO food_log (log_id, logged_at, category, venue, item, portion_pct, est_calories, daily_balance, notes) VALUES (?,?,?,?,?,?,?,?,?)")
               ->execute([$log_id, $now, $category, $venue, $item, $portion_pct, $est_calories, $daily_balance, $notes]);

            $chk = $db->prepare("SELECT item_id FROM food_library WHERE item_name = ? AND venue = ? LIMIT 1");
            $chk->execute([$item, $venue]);
            if (!$chk->fetch()) {
                $db->prepare("INSERT INTO food_library (item_id, item_name, venue, category, calories, verified) VALUES (?,?,?,?,0,0)")
                   ->execute(['lib-' . round(microtime(true) * 1000), $item, $venue, $category]);
            }

            $logged_entry = compact('log_id','category','venue','item','portion_pct','est_calories','daily_balance','notes');
            $logged_entry['logged_at']   = $now;
            $logged_entry['unverified']  = ($base_cal === null);
            $logged_entry['portion_raw'] = $portion;
            $today_consumed = get_today_consumed($db);
            $today_balance  = $daily_target - $today_consumed;
            $streak         = get_streak($db);
        } catch (Exception $e) { $error = $e->getMessage(); }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>TOPS &mdash; Food Log</title>
<link rel="icon" href="https://zaudi.com/favicon.ico" type="image/x-icon">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
    --bg:#0e0f11; --surface:#16181c; --surface2:#1e2026; --border:#2a2d35;
    --text:#e2e4e9; --muted:#6b7280; --accent:#4f8ef7;
    --danger:#f87171; --success:#22c55e; --warn:#facc15;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body { background: var(--bg); color: var(--text); font-family: 'Syne', sans-serif; font-size: 15px; min-height: 100vh; padding-bottom: 80px; }
header { position: sticky; top: 0; z-index: 10; background: var(--bg); border-bottom: 1px solid var(--border); padding: 14px 16px 10px; display: flex; align-items: baseline; gap: 10px; }
header h1 { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); }
header .balance { font-family: 'JetBrains Mono', monospace; font-size: 11px; }
header .links { margin-left: auto; display: flex; gap: 12px; }
header a { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); text-decoration: none; }
.form-wrap { padding: 20px 16px 0; }
.field { margin-bottom: 16px; }
.field.hidden { display: none; }
label { display: block; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px; }
select, input[type="text"] { width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; color: var(--text); font-family: 'JetBrains Mono', monospace; font-size: 14px; padding: 12px 14px; outline: none; transition: border-color 0.15s; appearance: none; -webkit-appearance: none; }
select:focus, input:focus { border-color: var(--accent); }
select option { background: #1e2026; }
.submit-btn {
    display: flex; align-items: center; justify-content: center;
    width: 100%; min-height: 52px; padding: 0 15px;
    background: var(--accent); border: none; border-radius: 12px; color: #fff;
    font-family: 'Syne', sans-serif; font-size: 16px; font-weight: 700;
    cursor: pointer; transition: opacity 0.15s; margin-top: 8px;
    text-decoration: none;
}
.submit-btn:active { opacity: 0.8; }
.error-bar { background: rgba(239,68,68,0.12); border: 1px solid var(--danger); border-radius: 10px; color: var(--danger); font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 10px 14px; margin-bottom: 16px; }
.confirm-wrap { padding: 20px 16px; }
.confirm-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--success); letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
.confirm-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
.card-head { padding: 16px; border-bottom: 1px solid var(--border); }
.card-item { font-size: 17px; line-height: 1.4; margin-bottom: 4px; }
.card-venue { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); }
.metrics { display: grid; grid-template-columns: 1fr 1fr; border-bottom: 1px solid var(--border); }
.metric { padding: 14px 12px; text-align: center; border-right: 1px solid var(--border); }
.metric:last-child { border-right: none; }
.metric-val { font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 600; line-height: 1; margin-bottom: 4px; }
.metric-lbl { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.field-row { display: flex; gap: 8px; padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 13px; }
.field-row:last-child { border-bottom: none; }
.field-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); width: 80px; flex-shrink: 0; padding-top: 1px; }
.field-val { color: var(--text); line-height: 1.5; word-break: break-word; }
.unverified-note { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--warn); padding: 8px 16px; background: rgba(250,204,21,0.06); border-top: 1px solid var(--border); text-align: center; }
.another-btn {
    display: flex; align-items: center; justify-content: center;
    width: 100%; min-height: 48px; padding: 0 13px; margin-top: 16px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    color: var(--muted); font-family: 'Syne', sans-serif; font-size: 14px;
    text-decoration: none; cursor: pointer;
}
.streak-bar { position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg); border-top: 1px solid var(--border); display: flex; justify-content: space-around; padding: 10px 16px 14px; z-index: 10; }
.streak-day { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.streak-icon { font-size: 14px; line-height: 1; }
.streak-lbl { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted); letter-spacing: 0.05em; }
.streak-day.today .streak-lbl { color: var(--accent); }
@media (min-width: 600px) { body { max-width: 480px; margin: 0 auto; } .streak-bar { max-width: 480px; left: 50%; transform: translateX(-50%); } }
</style>
</head>
<body>
<header>
    <h1>TOPS</h1>
    <span class="balance"><?php $bc = balance_color($today_balance); echo '<span style="color:' . $bc . '">' . $today_balance . ' cal left</span>'; ?></span>
    <div class="links">
        <a href="/tops_weight">&#x2696; Weigh-in</a>
        <a href="/tops_dash">&#x2022;&#x2022;&#x2022;</a>
    </div>
</header>

<?php if ($logged_entry): ?>
<div class="confirm-wrap">
    <div class="confirm-label">&#x2713; Logged</div>
    <div class="confirm-card">
        <div class="card-head">
            <div class="card-item"><?= htmlspecialchars($logged_entry['item']) ?></div>
            <div class="card-venue"><?= htmlspecialchars($logged_entry['venue']) ?> &middot; <?= htmlspecialchars($logged_entry['category']) ?></div>
        </div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-val"><?= $logged_entry['est_calories'] !== null ? $logged_entry['est_calories'] : '&mdash;' ?></div>
                <div class="metric-lbl">cal</div>
            </div>
            <div class="metric">
                <div class="metric-val" style="color:<?= $logged_entry['daily_balance'] !== null ? balance_color($logged_entry['daily_balance']) : 'var(--muted)' ?>">
                    <?= $logged_entry['daily_balance'] !== null ? $logged_entry['daily_balance'] : '&mdash;' ?>
                </div>
                <div class="metric-lbl">remaining</div>
            </div>
        </div>
        <div class="field-row"><span class="field-label">portion</span><span class="field-val"><?= $logged_entry['portion_pct'] ?>%</span></div>
        <div class="field-row"><span class="field-label">entered as</span><span class="field-val"><?= htmlspecialchars($logged_entry['portion_raw']) ?></span></div>
        <?php if ($logged_entry['notes']): ?>
        <div class="field-row"><span class="field-label">notes</span><span class="field-val"><?= htmlspecialchars($logged_entry['notes']) ?></span></div>
        <?php endif ?>
        <?php if ($logged_entry['unverified']): ?>
        <div class="unverified-note">&#x26A0; New item &mdash; pending Mia review</div>
        <?php endif ?>
    </div>
    <a class="another-btn" href="/tops">+ Log another</a>
</div>

<?php else: ?>
<div class="form-wrap">
    <?php if ($error): ?><div class="error-bar">&#x26A0; <?= htmlspecialchars($error) ?></div><?php endif ?>
    <form method="POST" action="" id="tops-form" autocomplete="off">
        <input type="hidden" name="venue" id="f-venue">
        <input type="hidden" name="item"  id="f-item">
        <div class="field" id="w-category">
            <label>Category</label>
            <select id="sel-category" name="category" onchange="onCategory(this.value)">
                <option value="">Select&hellip;</option>
                <?php foreach ($categories as $cat): ?>
                <option value="<?= htmlspecialchars($cat) ?>"><?= htmlspecialchars(category_label_from_slug($cat)) ?></option>
                <?php endforeach ?>
            </select>
        </div>
        <div class="field hidden" id="w-venue">
            <label>Venue / Source</label>
            <select id="sel-venue" onchange="onVenue(this.value)"><option value="">Select&hellip;</option></select>
        </div>
        <div class="field hidden" id="w-venue-new">
            <label>Venue name</label>
            <input type="text" id="inp-venue-new" placeholder="e.g. Johnnie's Eatery" oninput="onVenueNew(this.value)">
        </div>
        <div class="field hidden" id="w-item">
            <label>Item</label>
            <select id="sel-item" onchange="onItem(this.value)"><option value="">Select&hellip;</option></select>
        </div>
        <div class="field hidden" id="w-item-new">
            <label>Item name</label>
            <input type="text" id="inp-item-new" placeholder="Describe the item" oninput="onItemNew(this.value)">
        </div>
        <div class="field hidden" id="w-portion">
            <label>Portion</label>
            <input type="text" name="portion" id="inp-portion" placeholder="e.g. 90%, half, 5/8, 1/2 cup, standard" oninput="onPortion(this.value)">
        </div>
        <div class="field hidden" id="w-notes">
            <label>Notes <span style="color:var(--muted);font-size:10px">(optional)</span></label>
            <input type="text" name="notes" placeholder="Context, label data&hellip;">
        </div>
        <div class="field hidden" id="w-submit">
            <button type="submit" class="submit-btn">Log it</button>
        </div>
    </form>
</div>
<?php endif ?>

<div class="streak-bar">
    <?php foreach ($streak as $s): ?>
    <div class="streak-day <?= $s['today'] ? 'today' : '' ?>">
        <span class="streak-icon"><?= $s['hit'] ? '&#x2B50;' : '&#x2715;' ?></span>
        <span class="streak-lbl"><?= $s['day'] ?></span>
    </div>
    <?php endforeach ?>
</div>

<script>
const lib = <?= json_encode($library, JSON_UNESCAPED_UNICODE) ?>;
const lookup = {};
lib.forEach(row => {
    const cat = row.category, venue = row.venue || '__none__';
    if (!lookup[cat]) lookup[cat] = {};
    if (!lookup[cat][venue]) lookup[cat][venue] = [];
    lookup[cat][venue].push(row.item_name);
});
const staticVenues = <?= json_encode([
    'restaurant'     => [],
    'snack'          => ['many', 'single', 'combo', 'travel'],
    'breakfast-home' => ['favorite'],
    'lunch-home'     => ['prepared-food'],
    'dinner-home'    => ['home'],
    'cheat'          => [],
], JSON_UNESCAPED_UNICODE) ?>;
function show(id){document.getElementById(id).classList.remove('hidden');}
function hide(id){document.getElementById(id).classList.add('hidden');}
function resetFrom(){
    ['venue','venue-new','item','item-new','portion','notes','submit'].forEach(s=>hide('w-'+s));
    document.getElementById('f-venue').value='';
    document.getElementById('f-item').value='';
}
function fillSelect(selId,options){
    const sel=document.getElementById(selId);
    sel.innerHTML='<option value="">Select\u2026</option>';
    options.forEach(opt=>{const o=document.createElement('option');o.value=opt;o.textContent=opt;sel.appendChild(o);});
    const n=document.createElement('option');n.value='__new__';n.textContent='+ New';sel.appendChild(n);
}
function onCategory(val){
    resetFrom();if(!val)return;
    const catVenues=Object.keys(lookup[val]||{}).filter(v=>v!=='__none__');
    const merged=[...new Set([...(staticVenues[val]||[]),...catVenues])];
    fillSelect('sel-venue',merged);show('w-venue');
    if(merged.length===1){document.getElementById('sel-venue').value=merged[0];onVenue(merged[0]);}
}
function onVenue(val){
    resetFrom();hide('w-venue-new');if(!val)return;
    if(val==='__new__'){show('w-venue-new');document.getElementById('inp-venue-new').value='';return;}
    document.getElementById('f-venue').value=val;
    const items=(lookup[document.getElementById('sel-category').value]||{})[val]||[];
    fillSelect('sel-item',items);show('w-item');
    if(items.length===1){document.getElementById('sel-item').value=items[0];onItem(items[0]);}
}
function onVenueNew(val){
    document.getElementById('f-venue').value=val;
    if(val.trim().length>1){hide('w-item');show('w-item-new');document.getElementById('inp-item-new').value='';}
}
function onItem(val){
    hide('w-item-new');if(!val)return;
    if(val==='__new__'){show('w-item-new');document.getElementById('inp-item-new').value='';return;}
    document.getElementById('f-item').value=val;show('w-portion');show('w-notes');
}
function onItemNew(val){
    document.getElementById('f-item').value=val;
    if(val.trim().length>1){show('w-portion');show('w-notes');}
}
function onPortion(val){val.trim().length>0?show('w-submit'):hide('w-submit');}
</script>
</body>
</html>
