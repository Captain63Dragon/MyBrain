<?php
header('Content-Type: text/html; charset=utf-8');
require_once 'config.php';
require_once 'session_auth.php';
date_default_timezone_set('America/Edmonton');

$created_todo = null;
$error        = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $description = trim($_POST['description'] ?? '');
    if (!$description) {
        $error = 'Description is required.';
    } else {
        try {
            $db         = get_db();
            $priority   = $_POST['priority']   ?? 'medium';
            $status     = $_POST['status']     ?? 'open';
            $friction   = trim($_POST['friction'] ?? '') ?: null;
            $due        = trim($_POST['due']      ?? '') ?: null;
            $notes      = trim($_POST['notes']    ?? '') ?: null;
            $owner      = 'user';
            $now        = date('Y-m-d H:i:s');
            $todo_id    = 'todo-' . round(microtime(true) * 1000);

            $stmt = $db->prepare(
                "INSERT INTO todos
                 (todo_id, description, priority, status, friction,
                  due, notes, owner, created, updated_at, synced_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,NULL)"
            );
            $stmt->execute([
                $todo_id, $description, $priority, $status, $friction,
                $due, $notes, $owner, $now, $now
            ]);

            $fetch = $db->prepare('SELECT * FROM todos WHERE todo_id = ?');
            $fetch->execute([$todo_id]);
            $created_todo = $fetch->fetch(PDO::FETCH_ASSOC);

        } catch (Exception $e) {
            $error = $e->getMessage();
        }
    }
}

function priority_icon($p) {
    return match($p) {
        'high'   => '&#x1F534;',
        'medium' => '&#x1F7E1;',
        'low'    => '&#x26AA;',
        default  => ''
    };
}

function fmt_date($d) {
    if (!$d) return '&mdash;';
    return date('M j, Y', strtotime($d));
}

function null_or($v) {
    return ($v !== null && $v !== '') ? htmlspecialchars($v) : '&mdash;';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>New Todo &mdash; MyBrain</title>
<link rel="icon" href="https://zaudi.com/favicon.ico" type="image/x-icon">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
    --bg:        #0e0f11;
    --surface:   #16181c;
    --surface2:  #1e2026;
    --border:    #2a2d35;
    --text:      #e2e4e9;
    --muted:     #6b7280;
    --accent:    #4f8ef7;
    --danger:    #f87171;
    --success:   #22c55e;

    --pill-open:     #3b82f6;
    --pill-pending:  #8b5cf6;
    --pill-progress: #22c55e;

    --pri-high: #f97316;
    --pri-med:  #facc15;
    --pri-low:  #6b7280;
}

* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    min-height: 100vh;
    padding-bottom: 60px;
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

header a {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    text-decoration: none;
    margin-left: auto;
}

.form-wrap { padding: 20px 16px; }

.field { margin-bottom: 18px; }

label {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

label .req { color: var(--accent); margin-left: 2px; }

textarea,
input[type="text"],
input[type="date"],
select {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    padding: 12px 14px;
    outline: none;
    transition: border-color 0.15s;
    appearance: none;
    -webkit-appearance: none;
}

textarea {
    min-height: 90px;
    resize: vertical;
    line-height: 1.5;
    font-size: 15px;
}

textarea:focus, input:focus, select:focus { border-color: var(--accent); }

.priority-row { display: flex; gap: 8px; }
.priority-row input[type="radio"] { display: none; }
.priority-row label {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    text-transform: none;
    color: var(--muted);
    transition: all 0.15s;
    margin-bottom: 0;
}
.priority-row input[type="radio"]:checked + label {
    border-color: var(--accent);
    color: var(--text);
    background: var(--surface2);
}
.pri-high-lbl { color: var(--pri-high) !important; }
.pri-med-lbl  { color: var(--pri-med)  !important; }
.pri-low-lbl  { color: var(--pri-low)  !important; }

.submit-btn {
    width: 100%;
    padding: 15px;
    background: var(--accent);
    border: none;
    border-radius: 12px;
    color: #fff;
    font-family: 'Syne', sans-serif;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.15s;
    margin-top: 8px;
}
.submit-btn:active { opacity: 0.8; }

.error-bar {
    background: rgba(239,68,68,0.12);
    border: 1px solid var(--danger);
    border-radius: 10px;
    color: var(--danger);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    padding: 10px 14px;
    margin-bottom: 18px;
}

.confirm-wrap { padding: 20px 16px; }

.confirm-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--success);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.confirm-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
}
.confirm-card .card-head {
    padding: 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.confirm-card .card-desc { font-size: 16px; line-height: 1.4; flex: 1; }
.confirm-card .field-row {
    display: flex;
    gap: 8px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
}
.confirm-card .field-row:last-child { border-bottom: none; }
.confirm-card .field-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    width: 80px;
    flex-shrink: 0;
    padding-top: 1px;
}
.confirm-card .field-val { color: var(--text); line-height: 1.5; word-break: break-word; }

.pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
}
.pill-open     { background: var(--pill-open);     color: #fff; }
.pill-pending  { background: var(--pill-pending);  color: #fff; }
.pill-progress { background: var(--pill-progress); color: #fff; }

.id-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
}

.another-btn {
    display: block;
    width: 100%;
    margin-top: 16px;
    padding: 13px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--muted);
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
}

@media (min-width: 600px) {
    body { max-width: 480px; margin: 0 auto; }
}
</style>
</head>
<body>

<header>
    <h1>New Todo</h1>
    <a href="/user">&larr; Active</a>
</header>

<?php if ($created_todo): ?>

<div class="confirm-wrap">
    <div class="confirm-label">&#x2713; Added to queue</div>
    <div class="confirm-card">
        <div class="card-head">
            <span><?= priority_icon($created_todo['priority']) ?></span>
            <span class="card-desc"><?= htmlspecialchars($created_todo['description']) ?></span>
        </div>
        <?php
        $fields = [
            ['status',   '<span class="pill pill-' . $created_todo['status'] . '">' . htmlspecialchars($created_todo['status']) . '</span>'],
            ['priority', htmlspecialchars($created_todo['priority'])],
            ['friction', null_or($created_todo['friction'])],
            ['due',      fmt_date($created_todo['due'])],
            ['notes',    null_or($created_todo['notes'])],
            ['created',  htmlspecialchars($created_todo['created'])],
            ['id',       '<span class="id-val">' . htmlspecialchars($created_todo['todo_id']) . '</span>'],
        ];
        foreach ($fields as [$label, $val]):
        ?>
        <div class="field-row">
            <span class="field-label"><?= $label ?></span>
            <span class="field-val"><?= $val ?></span>
        </div>
        <?php endforeach ?>
    </div>
    <a class="another-btn" href="/new_todo">+ Add another</a>
</div>

<?php else: ?>

<div class="form-wrap">

    <?php if ($error): ?>
    <div class="error-bar">&#x26A0; <?= htmlspecialchars($error) ?></div>
    <?php endif ?>

    <form method="POST" action="">

        <div class="field">
            <label>Description <span class="req">*</span></label>
            <textarea name="description" placeholder="What needs doing?" autofocus><?= htmlspecialchars($_POST['description'] ?? '') ?></textarea>
        </div>

        <div class="field">
            <label>Priority</label>
            <div class="priority-row">
                <input type="radio" name="priority" id="pri-high" value="high"
                       <?= ($_POST['priority'] ?? '') === 'high' ? 'checked' : '' ?>>
                <label for="pri-high" class="pri-high-lbl">&#x1F534; High</label>

                <input type="radio" name="priority" id="pri-med" value="medium"
                       <?= ($_POST['priority'] ?? 'medium') === 'medium' ? 'checked' : '' ?>>
                <label for="pri-med" class="pri-med-lbl">&#x1F7E1; Med</label>

                <input type="radio" name="priority" id="pri-low" value="low"
                       <?= ($_POST['priority'] ?? '') === 'low' ? 'checked' : '' ?>>
                <label for="pri-low" class="pri-low-lbl">&#x26AA; Low</label>
            </div>
        </div>

        <div class="field">
            <label>Status</label>
            <select name="status">
                <?php foreach (['open','pending','in_progress'] as $s): ?>
                <option value="<?= $s ?>" <?= ($_POST['status'] ?? 'open') === $s ? 'selected' : '' ?>><?= $s ?></option>
                <?php endforeach ?>
            </select>
        </div>

        <div class="field">
            <label>Friction</label>
            <input type="text" name="friction"
                   placeholder="e.g. procrastination"
                   value="<?= htmlspecialchars($_POST['friction'] ?? '') ?>">
        </div>

        <div class="field">
            <label>Due date</label>
            <input type="date" name="due" value="<?= htmlspecialchars($_POST['due'] ?? '') ?>">
        </div>

        <div class="field">
            <label>Notes</label>
            <textarea name="notes" placeholder="Optional context..."><?= htmlspecialchars($_POST['notes'] ?? '') ?></textarea>
        </div>

        <button type="submit" class="submit-btn">Add Todo</button>

    </form>
</div>

<?php endif ?>

</body>
</html>
