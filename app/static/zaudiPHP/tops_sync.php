<?php
/**
 * tops_sync.php
 * Internal sync endpoint for TOPS food_library and food_log tables.
 * Used by garden personas (Mia, Walter) to read unverified items
 * and push back verified data, ratings, and corrections.
 *
 * Actions:
 *   get_unverified  - return unverified/unrated rows from specified table
 *   update          - upsert rows into specified table
 *   delete          - remove rows from food_library by item_id
 *
 * Auth:    X-API-Key header (via auth.php)
 * Request: application/json  { "action": "...", "table": "...", ... }
 * Response: application/json
 *
 * Tables supported: food_library, food_log
 * Generated: 2026-04-29 by Iris
 */

header('Content-Type: application/json');
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';

date_default_timezone_set('America/Edmonton');

// -- Helpers ------------------------------------------------------------------

function respond(array $data, int $code = 200): void {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

function respond_error(string $message, int $code = 400): void {
    respond(['status' => 'error', 'message' => $message], $code);
}

// -- Field maps - defines what each table exposes via sync --------------------

function library_fields(): array {
    return [
        'item_id', 'item_name', 'venue', 'category',
        'calories', 'unit_desc', 'verified',
        'mia_rating', 'mia_notes', 'mia_reviewed_at',
        'synced_at', 'created_at', 'updated_at',
    ];
}

function log_fields(): array {
    return [
        'log_id', 'logged_at', 'category', 'venue', 'item',
        'portion_pct', 'est_calories', 'mia_rating',
        'daily_balance', 'notes', 'synced_at',
    ];
}

function filter_row(array $row, array $fields): array {
    return array_intersect_key($row, array_flip($fields));
}

// -- Request ------------------------------------------------------------------

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond_error('POST required', 405);
}

$body   = json_decode(file_get_contents('php://input'), true);
$action = $body['action'] ?? '';
$table  = $body['table']  ?? '';

if (!$action) respond_error('action required');
if (!$table)  respond_error('table required');

$allowed_tables = ['food_library', 'food_log'];
if (!in_array($table, $allowed_tables, true)) {
    respond_error("Unknown table: $table. Allowed: " . implode(', ', $allowed_tables));
}

// -- DB -----------------------------------------------------------------------

try {
    $db = get_db();

    // -------------------------------------------------------------------------
    // ACTION: get_unverified
    // Returns rows that need persona attention:
    //   food_library - verified=0 OR mia_rating IS NULL
    //   food_log     - mia_rating IS NULL
    // -------------------------------------------------------------------------
    if ($action === 'get_unverified') {

        if ($table === 'food_library') {
            $stmt = $db->query(
                "SELECT * FROM food_library
                 WHERE verified = 0 OR mia_rating IS NULL
                 ORDER BY created_at ASC"
            );
            $fields = library_fields();
        } else {
            // food_log - entries awaiting Mia rating
            $stmt = $db->query(
                "SELECT * FROM food_log
                 WHERE mia_rating IS NULL
                 ORDER BY logged_at ASC"
            );
            $fields = log_fields();
        }

        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        $items = array_map(fn($r) => filter_row($r, $fields), $rows);

        respond([
            'status' => 'ok',
            'table'  => $table,
            'count'  => count($items),
            'items'  => $items,
        ]);
    }

    // -------------------------------------------------------------------------
    // ACTION: update
    // Upserts rows into the specified table.
    // Only fields defined in the field map are accepted - unknown fields ignored.
    // synced_at is always set to NOW() on update.
    // -------------------------------------------------------------------------
    if ($action === 'update') {

        $items = $body['items'] ?? [];
        if (!is_array($items) || empty($items)) {
            respond_error('items array required and must not be empty');
        }

        $upserted = 0;

        if ($table === 'food_library') {
            $sql = "INSERT INTO food_library
                        (item_id, item_name, venue, category, calories, unit_desc,
                         verified, mia_rating, mia_notes, mia_reviewed_at, synced_at)
                    VALUES
                        (:item_id, :item_name, :venue, :category, :calories, :unit_desc,
                         :verified, :mia_rating, :mia_notes, :mia_reviewed_at, NOW())
                    ON DUPLICATE KEY UPDATE
                        item_name        = VALUES(item_name),
                        venue            = VALUES(venue),
                        category         = VALUES(category),
                        calories         = VALUES(calories),
                        unit_desc        = VALUES(unit_desc),
                        verified         = VALUES(verified),
                        mia_rating       = VALUES(mia_rating),
                        mia_notes        = VALUES(mia_notes),
                        mia_reviewed_at  = VALUES(mia_reviewed_at),
                        synced_at        = NOW()";

            $stmt = $db->prepare($sql);
            foreach ($items as $item) {
                $stmt->execute([
                    ':item_id'          => $item['item_id']          ?? null,
                    ':item_name'        => $item['item_name']        ?? null,
                    ':venue'            => $item['venue']            ?? null,
                    ':category'         => $item['category']         ?? null,
                    ':calories'         => $item['calories']         ?? 0,
                    ':unit_desc'        => $item['unit_desc']        ?? null,
                    ':verified'         => $item['verified']         ?? 0,
                    ':mia_rating'       => $item['mia_rating']       ?? null,
                    ':mia_notes'        => $item['mia_notes']        ?? null,
                    ':mia_reviewed_at'  => $item['mia_reviewed_at']  ?? null,
                ]);
                $upserted++;
            }

        } else {
            // food_log - garden can update est_calories, mia_rating, daily_balance
            $sql = "UPDATE food_log SET
                        est_calories  = :est_calories,
                        mia_rating    = :mia_rating,
                        daily_balance = :daily_balance,
                        synced_at     = NOW()
                    WHERE log_id = :log_id";

            $stmt = $db->prepare($sql);
            foreach ($items as $item) {
                if (empty($item['log_id'])) continue;
                $stmt->execute([
                    ':log_id'       => $item['log_id'],
                    ':est_calories' => $item['est_calories']  ?? null,
                    ':mia_rating'   => $item['mia_rating']    ?? null,
                    ':daily_balance'=> $item['daily_balance'] ?? null,
                ]);
                $upserted++;
            }
        }

        respond([
            'status'   => 'ok',
            'table'    => $table,
            'upserted' => $upserted,
            'time'     => date('c'),
        ]);
    }

    // -------------------------------------------------------------------------
    // ACTION: delete
    // Removes rows from food_library by item_id.
    // food_log deletions are not permitted - log is append-only.
    // -------------------------------------------------------------------------
    if ($action === 'delete') {

        if ($table !== 'food_library') {
            respond_error('delete is only permitted on food_library - food_log is append-only');
        }

        $item_ids = $body['item_ids'] ?? [];
        if (!is_array($item_ids) || empty($item_ids)) {
            respond_error('item_ids array required and must not be empty');
        }

        $placeholders = implode(',', array_fill(0, count($item_ids), '?'));
        $stmt = $db->prepare("DELETE FROM food_library WHERE item_id IN ($placeholders)");
        $stmt->execute($item_ids);
        $deleted = $stmt->rowCount();

        respond([
            'status'  => 'ok',
            'table'   => 'food_library',
            'deleted' => $deleted,
            'time'    => date('c'),
        ]);
    }

    // -- Unknown action -------------------------------------------------------
    respond_error("Unknown action: $action. Allowed: get_unverified, update, delete");

} catch (Exception $e) {
    respond_error($e->getMessage(), 500);
}
?>
