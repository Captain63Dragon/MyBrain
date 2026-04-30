<?php
/**
 * todo_sync.php
 * Two-action sync endpoint between Zaudi MySQL and Neo4j (via Flask).
 *
 * Actions:
 *   get_unprocessed — begin lock, claim fresh rows, return fresh + stranded
 *   commit          — bulk upsert todos_new, drop processing, rename to live
 *
 * Auth: X-API-Key header (via auth.php)
 * Content-Type: application/vnd.collection+json
 * Updated: 2026-04-27 — orphan recovery fix + empty payload guard
 */

header('Content-Type: application/vnd.collection+json');
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';

date_default_timezone_set('America/Edmonton');

define('BASE_URL', 'https://api.zaudi.com/todo_sync.php');

// -- Collection+JSON helpers ---------------------------------------------------

function make_todo_item(array $row): array {
    return [
        'href' => BASE_URL,
        'data' => [
            ['name' => 'todo_id',     'value' => $row['todo_id']     ?? null, 'prompt' => 'ID'],
            ['name' => 'description', 'value' => $row['description'] ?? null, 'prompt' => 'Description'],
            ['name' => 'priority',    'value' => $row['priority']    ?? null, 'prompt' => 'Priority'],
            ['name' => 'status',      'value' => $row['status']      ?? null, 'prompt' => 'Status'],
            ['name' => 'friction',    'value' => $row['friction']    ?? null, 'prompt' => 'Friction'],
            ['name' => 'created',     'value' => $row['created']     ?? null, 'prompt' => 'Created'],
            ['name' => 'due',         'value' => $row['due']         ?? null, 'prompt' => 'Due'],
            ['name' => 'owner',       'value' => $row['owner']       ?? null, 'prompt' => 'Owner'],
            ['name' => 'source_pin',  'value' => $row['source_pin']  ?? null, 'prompt' => 'Source pin'],
            ['name' => 'notes',       'value' => $row['notes']       ?? null, 'prompt' => 'Notes'],
            ['name' => 'synced_at',   'value' => $row['synced_at']   ?? null, 'prompt' => 'Synced'],
            ['name' => 'processing',  'value' => $row['processing']  ?? null, 'prompt' => 'Processing'],
        ],
        'links' => [],
    ];
}

function respond(array $data, int $code = 200): void {
    http_response_code($code);
    echo json_encode([
        'collection' => array_merge([
            'version' => '1.0',
            'href'    => BASE_URL,
        ], $data)
    ]);
    exit;
}

function respond_error(string $message, int $code = 400): void {
    respond([
        'error' => [
            'title'   => 'Error',
            'message' => $message,
        ]
    ], $code);
}

// -- Request validation --------------------------------------------------------

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond_error('POST required', 405);
}

$body   = json_decode(file_get_contents('php://input'), true);
$action = $body['action'] ?? '';

if (!$action) {
    respond_error('action required');
}

// -- Helpers -------------------------------------------------------------------

function table_exists(PDO $db, string $table): bool {
    $stmt = $db->prepare(
        "SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema = DATABASE() AND table_name = ?"
    );
    $stmt->execute([$table]);
    return (bool) $stmt->fetchColumn();
}

function create_todos_new(PDO $db): void {
    $db->exec("CREATE TABLE todos_new LIKE todos_processing");
}

// -----------------------------------------------------------------------------
try {
    $db = get_db();

    // -- ACTION: get_unprocessed -----------------------------------------------
    if ($action === 'get_unprocessed') {

        $orphan = table_exists($db, 'todos_processing');

        if ($orphan) {
            // Orphan recovery: todos_processing is the source of truth from the
            // failed prior cycle. If a live `todos` table also exists (from a
            // partial recovery or stale state), drop it so the final RENAME
            // can succeed at commit time.
            if (table_exists($db, 'todos')) {
                $db->exec("DROP TABLE todos");
            }
        } else {
            $db->exec("RENAME TABLE todos TO todos_processing");
        }

        // todos_new from a previous failed cycle must not be reused
        if (table_exists($db, 'todos_new')) {
            $db->exec("DROP TABLE todos_new");
        }
        create_todos_new($db);

        // Crash victims — already claimed, never completed
        $stranded_stmt = $db->query(
            "SELECT * FROM todos_processing
             WHERE processing IS NOT NULL AND synced_at IS NULL"
        );
        $stranded_rows = $stranded_stmt->fetchAll(PDO::FETCH_ASSOC);

        // Fresh — not yet claimed
        $fresh_stmt = $db->query(
            "SELECT * FROM todos_processing
             WHERE processing IS NULL AND synced_at IS NULL"
        );
        $fresh_rows = $fresh_stmt->fetchAll(PDO::FETCH_ASSOC);

        // Claim fresh rows
        if (!empty($fresh_rows)) {
            $ids = array_map(fn($r) => $db->quote($r['todo_id']), $fresh_rows);
            $in  = implode(',', $ids);
            $db->exec(
                "UPDATE todos_processing
                 SET processing = NOW()
                 WHERE todo_id IN ($in)"
            );
        }

        $items = [];
        foreach ($fresh_rows as $row) {
            $item = make_todo_item($row);
            $item['links'][] = ['rel' => 'fresh', 'href' => BASE_URL];
            $items[] = $item;
        }
        foreach ($stranded_rows as $row) {
            $item = make_todo_item($row);
            $item['links'][] = ['rel' => 'stranded', 'href' => BASE_URL];
            $items[] = $item;
        }

        respond([
            'items' => $items,
            'meta'  => [
                ['name' => 'orphan',         'value' => $orphan],
                ['name' => 'fresh_count',    'value' => count($fresh_rows)],
                ['name' => 'stranded_count', 'value' => count($stranded_rows)],
            ],
        ]);
    }

    // -- ACTION: commit --------------------------------------------------------
    if ($action === 'commit') {

        $todos = $body['todos'] ?? [];

        if (!is_array($todos)) {
            respond_error('todos must be an array');
        }

        if (!table_exists($db, 'todos_processing')) {
            respond_error('No active sync session — todos_processing not found', 409);
        }

        $upserted = 0;
        if (!empty($todos)) {
            $sql = "INSERT INTO todos_new
                        (todo_id, description, priority, status, friction,
                         created, due, owner, source_pin, notes, synced_at)
                    VALUES
                        (:todo_id, :description, :priority, :status, :friction,
                         :created, :due, :owner, :source_pin, :notes, :synced_at)
                    ON DUPLICATE KEY UPDATE
                        description = VALUES(description),
                        priority    = VALUES(priority),
                        status      = VALUES(status),
                        friction    = VALUES(friction),
                        due         = VALUES(due),
                        owner       = VALUES(owner),
                        source_pin  = VALUES(source_pin),
                        notes       = VALUES(notes),
                        synced_at   = VALUES(synced_at)";

            $stmt = $db->prepare($sql);

            foreach ($todos as $todo) {
                $stmt->execute([
                    ':todo_id'     => $todo['todo_id']     ?? null,
                    ':description' => $todo['description'] ?? null,
                    ':priority'    => $todo['priority']    ?? 'medium',
                    ':status'      => $todo['status']      ?? 'open',
                    ':friction'    => $todo['friction']    ?? null,
                    ':created'     => $todo['created']     ?? null,
                    ':due'         => $todo['due']         ?? null,
                    ':owner'       => $todo['owner']       ?? 'user',
                    ':source_pin'  => $todo['source_pin']  ?? null,
                    ':notes'       => $todo['notes']       ?? null,
                    ':synced_at'   => $todo['synced_at']   ?? null,
                ]);
                $upserted++;
            }
        }

        // Empty payload — no new todos from Neo4j but still must complete the rename.
        // Dropping todos_new and renaming todos_processing back preserves the live table.
        // Do NOT abort here — the lock must always be released.
        $count = (int) $db->query("SELECT COUNT(*) FROM todos_new")->fetchColumn();
        if ($count === 0) {
            $db->exec("DROP TABLE todos_new");
            $db->exec("RENAME TABLE todos_processing TO todos");
            respond([
                'meta' => [
                    ['name' => 'status',   'value' => 'ok'],
                    ['name' => 'upserted', 'value' => 0],
                    ['name' => 'note',     'value' => 'empty payload — lock released, table restored'],
                    ['name' => 'time',     'value' => date('c')],
                ],
            ]);
        }

        $db->exec("DROP TABLE todos_processing");
        $db->exec("RENAME TABLE todos_new TO todos");

        respond([
            'meta' => [
                ['name' => 'status',   'value' => 'ok'],
                ['name' => 'upserted', 'value' => $upserted],
                ['name' => 'time',     'value' => date('c')],
            ],
        ]);
    }

    // -- Unknown action --------------------------------------------------------
    respond_error("Unknown action: $action");

} catch (Exception $e) {
    respond_error($e->getMessage(), 500);
}
?>
