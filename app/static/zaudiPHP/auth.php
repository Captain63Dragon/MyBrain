<?php
// auth.php — API key gate
// Include at the top of any endpoint that requires authentication.
// Set the key in config.php as: define('API_KEY', 'your-secret-key');
// or hardcode it here if config.php is not available.

$provided = $_SERVER['HTTP_X_API_KEY'] ?? '';

if (!defined('API_KEY') || $provided !== API_KEY) {
    http_response_code(401);
    header('Content-Type: application/vnd.collection+json');
    echo json_encode([
        'collection' => [
            'version' => '1.0',
            'href'    => $_SERVER['REQUEST_URI'] ?? '/',
            'error'   => ['title' => 'Unauthorized']
        ]
    ]);
    exit;
}
?>