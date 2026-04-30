<?php
header('Content-Type: text/html; charset=utf-8');
require_once 'config.php';
require_once 'session_auth.php';
date_default_timezone_set('America/Edmonton');

$db = get_db();
$stmt = $db->prepare(
    "SELECT * FROM todos
     WHERE status IN ('open','pending','in_progress')
     AND owner = 'user'
     AND synced_at IS NOT NULL
     ORDER BY FIELD(priority,'high','medium','low'), due ASC, created ASC"
);
$stmt->execute();
$todos = $stmt->fetchAll(PDO::FETCH_ASSOC);

function age_class($created) {
    if (!$created) return 'age-none';
    $days = (time() - strtotime($created)) / 86400;
    if ($days <= 3)  return 'age-fresh';
    if ($days <= 7)  return 'age-aging';
    if ($days <= 14) return 'age-old';
    return 'age-ancient';
}

function due_class($due) {
    if (!$due) return '';
    $days = (strtotime($due) - time()) / 86400;
    if ($days < 0)  return 'due-past';
    if ($days <= 3) return 'due-soon';
    return 'due-ok';
}

function priority_icon($p) {
    return match($p) {
        'high'   => '<span class="pri pri-high">&#x1F534;</span>',
        'medium' => '<span class="pri pri-med">&#x1F7E1;</span>',
        'low'    => '<span class="pri pri-low">&#x26AA;</span>',
        default  => ''
    };
}

function status_pill($s) {
    return match($s) {
        'in_progress' => '<span class="pill pill-progress">in_progress</span>',
        'pending'     => '<span class="pill pill-pending">pending</span>',
        'open'        => '<span class="pill pill-open">open</span>',
        default       => "<span class='pill'>$s</span>"
    };
}

function friction_icon($f) {
    if (!$f) return '';
    return '<span class="friction">&#x26A1;' . htmlspecialchars($f) . '</span>';
}

function fmt_date($d) {
    if (!$d) return '&mdash;';
    return date('M j', strtotime($d));
}

function days_ago($created) {
    if (!$created) return '';
    $days = floor((time() - strtotime($created)) / 86400);
    if ($days === 0) return 'today';
    if ($days === 1) return '1d ago';
    return $days . 'd ago';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>MyBrain &mdash; Active</title>
<link rel="icon" href="https://zaudi.com/favicon.ico" type="image/x-icon">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
    --bg:           #0e0f11;
    --surface:      #16181c;
    --surface2:     #1e2026;
    --border:       #2a2d35;
    --text:         #e2e4e9;
    --muted:        #6b7280;
    --accent:       #4f8ef7;

    --pill-progress:#22c55e;
    --pill-pending: #8b5cf6;
    --pill-open:    #3b82f6;

    --pri-high:     #f97316;
    --pri-med:      #facc15;
    --pri-low:      #6b7280;

    --age-fresh:    transparent;
    --age-aging:    rgba(234,179,8,0.06);
    --age-old:      rgba(234,179,8,0.13);
    --age-ancient:  rgba(239,68,68,0.15);

    --due-past:     rgba(239,68,68,0.18);
    --due-soon:     rgba(234,179,8,0.15);
    --due-ok:       transparent;
}

* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    min-height: 100vh;
}

header {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 14px 16px 10px;
    display: flex;
    align-items: baseline;
    gap: 10px;
}

header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
}

header .count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
}

header a {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    text-decoration: none;
    margin-left: auto;
}

.list { padding: 8px 0 80px; }

.todo-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.15s;
    position: relative;
}

.todo-row.age-aging  { background: var(--age-aging); }
.todo-row.age-old    { background: var(--age-old); }
.todo-row.age-ancient{ background: var(--age-ancient); }
.todo-row.due-past   { background: var(--due-past); }
.todo-row.due-soon   { background: var(--due-soon); }
.todo-row:active     { background: var(--surface2); }

.pri { font-size: 11px; margin-top: 3px; flex-shrink: 0; width: 14px; text-align: center; }
.pri-high { color: var(--pri-high); }
.pri-med  { color: var(--pri-med); }
.pri-low  { color: var(--pri-low); }

.todo-body { flex: 1; min-width: 0; }

.description { font-size: 15px; line-height: 1.4; color: var(--text); word-break: break-word; }

.meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    flex-wrap: wrap;
}

.pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.03em;
}
.pill-progress { background: var(--pill-progress); color: #fff; }
.pill-pending  { background: var(--pill-pending);  color: #fff; }
.pill-open     { background: var(--pill-open);     color: #fff; }

.due-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }
.due-label.due-past { color: #f87171; }
.due-label.due-soon { color: #fbbf24; }

.age-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }

.friction { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #fb923c; }

.overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    backdrop-filter: blur(3px);
}
.overlay.open { display: flex; align-items: flex-end; }

.sheet {
    background: var(--surface);
    border-top: 1px solid var(--border);
    border-radius: 20px 20px 0 0;
    width: 100%;
    max-height: 80vh;
    overflow-y: auto;
    padding: 20px 20px 40px;
    animation: slideup 0.22s ease;
}

@keyframes slideup {
    from { transform: translateY(60px); opacity: 0; }
    to   { transform: translateY(0);    opacity: 1; }
}

.sheet-handle { width: 36px; height: 4px; background: var(--border); border-radius: 2px; margin: 0 auto 20px; }
.sheet h2 { font-size: 17px; line-height: 1.4; margin-bottom: 16px; color: var(--text); }

.field-row { display: flex; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.field-row:last-child { border-bottom: none; }
.field-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); width: 80px; flex-shrink: 0; padding-top: 1px; }
.field-val { color: var(--text); line-height: 1.5; word-break: break-word; }
.field-val.notes { color: #9ca3af; font-size: 13px; }

.close-btn {
    display: block;
    width: 100%;
    margin-top: 20px;
    padding: 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--muted);
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    cursor: pointer;
    text-align: center;
}
</style>
</head>
<body>

<header>
    <h1>MyBrain</h1>
    <span class="count"><?= count($todos) ?> active</span>
    <a href="/new_todo">+ New</a>
</header>

<div class="list">
<?php foreach ($todos as $t):
    $age  = age_class($t['created']);
    $due  = due_class($t['due']);
    $row_class = $due ?: $age;
    $id   = htmlspecialchars($t['todo_id']);
    $desc = htmlspecialchars($t['description']);
    $due_fmt = $t['due'] ? fmt_date($t['due']) : null;
    $due_cls = due_class($t['due']);
?>
<div class="todo-row <?= $row_class ?>" onclick="openSheet('<?= $id ?>')">
    <?= priority_icon($t['priority']) ?>
    <div class="todo-body">
        <div class="description"><?= $desc ?></div>
        <div class="meta">
            <?= status_pill($t['status']) ?>
            <?php if ($due_fmt): ?>
                <span class="due-label <?= $due_cls ?>"><?= $due_fmt ?></span>
            <?php endif ?>
            <span class="age-label"><?= days_ago($t['created']) ?></span>
            <?= friction_icon($t['friction']) ?>
        </div>
    </div>
</div>
<?php endforeach ?>
</div>

<div class="overlay" id="overlay" onclick="closeSheet(event)">
    <div class="sheet" id="sheet">
        <div class="sheet-handle"></div>
        <h2 id="sh-desc"></h2>
        <div id="sh-fields"></div>
        <button class="close-btn" onclick="closeSheet()">Close</button>
    </div>
</div>

<script>
const todos = <?= json_encode(array_values($todos)) ?>;
const idx   = {};
todos.forEach(t => idx[t.todo_id] = t);

function openSheet(id) {
    const t = idx[id];
    if (!t) return;
    document.getElementById('sh-desc').textContent = t.description;
    const fields = [
        ['status',   t.status],
        ['priority', t.priority],
        ['friction', t.friction || '\u2014'],
        ['due',      t.due || '\u2014'],
        ['created',  t.created ? t.created.substring(0,10) : '\u2014'],
        ['owner',    t.owner],
        ['source',   t.source_pin || '\u2014'],
        ['notes',    t.notes || '\u2014'],
        ['id',       t.todo_id],
    ];
    document.getElementById('sh-fields').innerHTML = fields.map(([k,v]) =>
        `<div class="field-row">
            <span class="field-label">${k}</span>
            <span class="field-val ${k === 'notes' ? 'notes' : ''}">${escHtml(String(v))}</span>
        </div>`
    ).join('');
    document.getElementById('overlay').classList.add('open');
}

function closeSheet(e) {
    if (e && e.target !== document.getElementById('overlay')) return;
    document.getElementById('overlay').classList.remove('open');
}

function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>
