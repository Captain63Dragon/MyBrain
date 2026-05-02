<?php
// login.php - Session login for browser-facing MyBrain pages.
// Validates password against MYBRAIN_PASSWORD_HASH in config.php.
// On success: sets $_SESSION['authed'] = true, redirects to return URL or /user.

require_once __DIR__ . '/config.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Already logged in
if (!empty($_SESSION['authed'])) {
    header('Location: /user');
    exit;
}

$error  = null;
$return = $_GET['return'] ?? '/user';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $password = $_POST['password'] ?? '';
    $return   = $_POST['return']   ?? '/user';

    if (!defined('MYBRAIN_PASSWORD_HASH')) {
        $error = 'Server configuration error.';
    } elseif (password_verify($password, MYBRAIN_PASSWORD_HASH)) {
        $_SESSION['authed']    = true;
        $_SESSION['authed_at'] = time();
        header('Location: ' . $return);
        exit;
    } else {
        $error = 'Nice try.';
        // Small delay to slow brute force
        sleep(1);
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Login &mdash; MyBrain</title>
<link rel="icon" href="https://zaudi.com/favicon.ico" type="image/x-icon">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
    --bg:      #0e0f11;
    --surface: #16181c;
    --border:  #2a2d35;
    --text:    #e2e4e9;
    --muted:   #6b7280;
    --accent:  #4f8ef7;
    --danger:  #f87171;
}

* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px 16px;
}

.login-wrap {
    width: 100%;
    max-width: 360px;
}

header {
    margin-bottom: 32px;
    text-align: center;
}

header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
}

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

input[type="password"],
input[type="text"] {
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
    -webkit-appearance: none;
}

input:focus { border-color: var(--accent); }

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
    letter-spacing: 0.03em;
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

.pass-wrap { position: relative; }
.pass-wrap input { padding-right: 50px; }
.eye-btn {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    cursor: pointer;
    font-size: 14px;
    color: var(--muted);
}
</style>
</head>
<body>
<div class="login-wrap">
    <header>
        <h1>MyBrain</h1>
    </header>

    <?php if ($error): ?>
    <div class="error-bar">&#x26A0; <?= htmlspecialchars($error) ?></div>
    <?php endif ?>

    <form method="POST" action="">
        <input type="hidden" name="return" value="<?= htmlspecialchars($return) ?>">

        <div class="field">
            <label>Password</label>
            <div class="pass-wrap">
                <input type="password" name="password" id="password"
                       placeholder="Who goes there?"
                       autofocus autocomplete="current-password">
                <span class="eye-btn" onclick="togglePass()">&#x1F441;</span>
            </div>
        </div>

        <button type="submit" class="submit-btn">Enter</button>
    </form>
</div>

<script>
function togglePass() {
    const f = document.getElementById('password');
    f.type = f.type === 'password' ? 'text' : 'password';
}
</script>
</body>
</html>
