<?php
header('Content-Type: application/vnd.collection+json');
require_once 'config.php';
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
date_default_timezone_set('America/Edmonton');
define('BASE_URL', 'https://api.zaudi.com/todos.php');

// --- Helpers ---

// Builds the item URL for a single todo. Called by todo_to_item().
function todo_href(string $todo_id): string {
    return BASE_URL . '/' . urlencode($todo_id);
}

// Converts a raw DB row into a Collection+JSON item rows from the DB.
function todo_to_item(array $row): array {
    $fields = [
        'todo_id', 'description', 'priority', 'status',
        'friction', 'created', 'due', 'updated_at',
        'owner', 'notes', 'source_pin', 'synced_at'
    ];
    $prompts = [
        'todo_id'     => 'ID',
        'description' => 'Description',
        'priority'    => 'Priority',
        'status'      => 'Status',
        'friction'    => 'Friction',
        'created'     => 'Created',
        'due'         => 'Due',
        'updated_at'  => 'Updated',
        'owner'       => 'Owner',
        'notes'       => 'Notes',
        'source_pin'  => 'Source pin',
        'synced_at'   => 'Synced',
    ];
    $data = [];
    foreach ($fields as $f) {
        $data[] = [
            'name'   => $f,
            'value'  => $row[$f] ?? null,
            'prompt' => $prompts[$f],
        ];
    }
    return [
        'href'  => todo_href($row['todo_id']),
        'data'  => $data,
        'links' => [],
    ];
}

// Returns the static template block. Called by send_collection().
function collection_template(): array {
    return [
        'data' => [
            ['name' => 'description', 'value' => '',      'prompt' => 'Description'],
            ['name' => 'priority',    'value' => 'medium','prompt' => 'Priority'],
            ['name' => 'status',      'value' => 'open',  'prompt' => 'Status'],
            ['name' => 'friction',    'value' => '',      'prompt' => 'Friction type'],
            ['name' => 'due',         'value' => '',      'prompt' => 'Due date'],
            ['name' => 'notes',       'value' => '',      'prompt' => 'Notes'],
            ['name' => 'source_pin',  'value' => '',      'prompt' => 'Source pin'],
            ['name' => 'owner',       'value' => 'user',  'prompt' => 'Owner'],
        ]
    ];
}

// Returns the static queries block. Called by send_collection().
function collection_queries(): array {
    return [[
        'rel'    => 'search',
        'href'   => BASE_URL,
        'prompt' => 'Filter todos',
        'data'   => [
            ['name' => 'status',   'value' => ''],
            ['name' => 'priority', 'value' => ''],
            ['name' => 'owner',    'value' => ''],
            ['name' => 'friction', 'value' => ''],
            ['name' => 'synced',   'value' => ''],
        ]
    ]];
}

// Assembles and echoes the full Collection+JSON envelope. Every exit path calls this.
function send_collection(array $items, ?string $error = null): void {
    $collection = [
        'version'  => '1.0',
        'href'     => BASE_URL,
        'links'    => [['rel' => 'vera', 'href' => 'https://api.zaudi.com/vera']],
        'queries'  => collection_queries(),
        'template' => collection_template(),
        'items'    => $items,
    ];
    if ($error) {
        $collection['error'] = ['title' => $error];
    }
    echo json_encode(['collection' => $collection], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

// Calls send_collection() with an error title and the right HTTP code, then exits.
function send_error(int $code, string $message): void {
    http_response_code($code);
    send_collection([], $message);
    exit;
}

// Extracts todo-123 from the URL path if present. Called once at the top of the router.
function parse_todo_id_from_uri(): ?string {
    $path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    if (preg_match('#/todos\.php/(.+)$#', $path, $m)) {
        return urldecode($m[1]);
    }
    return null;
}

// Flattens the incoming POST body into a simple key-value array regardless of whether it arrived as a Collection+JSON 
// template or plain JSON.
function template_to_fields(array $body): array {
    if (isset($body['template']['data'])) {
        $fields = [];
        foreach ($body['template']['data'] as $item) {
            if (isset($item['name'])) {
                $fields[$item['name']] = $item['value'] ?? null;
            }
        }
        return $fields;
    }
    return $body;
}

// Runs the UPDATE query and returns the updated item. Called by the POST router when _method: PUT is detected.
function handle_update(PDO $db, string $todoId, array $fields): void {
    $allowed = ['description','priority','status','friction','due','notes','source_pin','owner','synced_at'];
    $set     = [];
    $params  = [];

    foreach ($allowed as $col) {
        if (array_key_exists($col, $fields)) {
            $set[]    = "$col = ?";
            $params[] = $fields[$col];
        }
    }

    if (!$set) send_error(400, 'No updatable fields provided');

    $set[]    = 'updated_at = ?';
    $params[] = date('Y-m-d H:i:s');
    $params[] = $todoId;

    $stmt = $db->prepare('UPDATE todos SET ' . implode(', ', $set) . ' WHERE todo_id = ?');
    $stmt->execute($params);

    if ($stmt->rowCount() === 0) send_error(404, 'Todo not found');

    $upd = $db->prepare('SELECT * FROM todos WHERE todo_id = ?');
    $upd->execute([$todoId]);
    $row = $upd->fetch(PDO::FETCH_ASSOC);

    send_collection([todo_to_item($row)]);
}

// --- Router ---

try {
    $db     = get_db();
    $method = $_SERVER['REQUEST_METHOD'];
    $todoId = parse_todo_id_from_uri();
    $isVera = strpos($_SERVER['REQUEST_URI'], '/vera') !== false;

    // --- GET ---
    if ($method === 'GET') {

        $status   = $_GET['status']   ?? null;
        $priority = $_GET['priority'] ?? null;
        $owner    = $_GET['owner']    ?? null;
        $friction = $_GET['friction'] ?? null;
        $synced   = $_GET['synced']   ?? null;

        if ($isVera) {
            $stmt = $db->prepare(
                "SELECT * FROM todos
                 WHERE status IN ('open','pending','in_progress')
                 AND owner = 'user'
                 AND synced_at IS NOT NULL
                 ORDER BY FIELD(priority,'high','medium','low'),
                          due ASC, created ASC
                 LIMIT 20"
            );
            $stmt->execute();

        } else {
            $where  = [];
            $params = [];

            if ($synced === 'false') {
                $where[] = '(synced_at IS NULL OR synced_at < updated_at)';
            }
            if ($status) {
                if ($status === 'active') {
                    $where[] = "status IN ('open','pending','in_progress')";
                } else {
                    $where[] = 'status = ?';
                    $params[] = $status;
                }
            }
            if ($priority) { $where[] = 'priority = ?'; $params[] = $priority; }
            if ($owner)    { $where[] = 'owner = ?';    $params[] = $owner; }
            if ($friction) { $where[] = 'friction = ?'; $params[] = $friction; }

            $sql = 'SELECT * FROM todos';
            if ($where) $sql .= ' WHERE ' . implode(' AND ', $where);
            $sql .= " ORDER BY FIELD(priority,'high','medium','low'), created ASC";

            $stmt = $db->prepare($sql);
            $stmt->execute($params);
        }

        $rows  = $stmt->fetchAll(PDO::FETCH_ASSOC);
        $items = array_map('todo_to_item', $rows);
        send_collection($items);

    // --- POST (create or _method override) ---
    } elseif ($method === 'POST') {

        $body   = json_decode(file_get_contents('php://input'), true) ?? [];
        $fields = template_to_fields($body);

        // _method override — treat as PUT
        $override = strtoupper($fields['_method'] ?? '');
        if ($override === 'PUT') {
            $resolvedId = $todoId ?? ($fields['todo_id'] ?? null);
            if (!$resolvedId) send_error(400, 'todo_id required for update');
            unset($fields['_method'], $fields['todo_id']);
            handle_update($db, $resolvedId, $fields);
            exit;
        }

        // Normal POST — create
        $description = trim($fields['description'] ?? '');
        if (!$description) send_error(400, 'description is required');

        $priority   = $fields['priority']   ?? 'medium';
        $status     = $fields['status']     ?? 'open';
        $friction   = $fields['friction']   ?? null;
        $due        = $fields['due']        ?? null;
        $notes      = $fields['notes']      ?? null;
        $source_pin = $fields['source_pin'] ?? null;
        $owner      = $fields['owner']      ?? 'user';
        $now        = date('Y-m-d H:i:s');
        $todo_id    = 'todo-' . round(microtime(true) * 1000);

        $stmt = $db->prepare(
            "INSERT INTO todos
             (todo_id, description, priority, status, friction,
              due, notes, source_pin, owner, created, updated_at)
             VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        );
        $stmt->execute([
            $todo_id, $description, $priority, $status, $friction,
            $due ?: null, $notes, $source_pin, $owner, $now, $now
        ]);

        $new = $db->prepare('SELECT * FROM todos WHERE todo_id = ?');
        $new->execute([$todo_id]);
        $row = $new->fetch(PDO::FETCH_ASSOC);

        http_response_code(201);
        send_collection([todo_to_item($row)]);

    } else {
        send_error(405, 'Method not allowed');
    }

} catch (Exception $e) {
    http_response_code(500);
    send_collection([], $e->getMessage());
}
?>
