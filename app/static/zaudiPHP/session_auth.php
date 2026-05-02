<?php
// session_auth.php - Session gate for browser-facing pages.
// Include at the top of any page that requires a logged-in session.
// Redirects to login.php if no valid session found.

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

if (empty($_SESSION['authed'])) {
    $return = urlencode($_SERVER['REQUEST_URI'] ?? '/');
    header('Location: /login.php?return=' . $return);
    exit;
}
