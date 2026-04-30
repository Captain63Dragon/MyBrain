<?php
require_once 'config.php';
echo password_hash(API_KEY, PASSWORD_DEFAULT);
echo "\n";
?>
