<?php
header('Content-Type: application/json');
require_once 'config.php';

try {
    $db = get_db();
    $db_status = 'ok';
} catch (Exception $e) {
    $db_status = 'error';
}

echo json_encode([
    'status' => 'ok',
    'db'     => $db_status,
    'time'   => date('c')
]);
?>