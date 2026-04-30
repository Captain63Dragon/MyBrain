<?php
header('Content-Type: application/vnd.collection+json');
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
date_default_timezone_set('America/Edmonton');
define('BASE_URL', 'https://api.zaudi.com/terms.php');

// --- Helpers ---

function term_href(string $term_id): string {
    return BASE_URL . '/' . urlencode($term_id);
}

function term_to_item(array $row): array {
    $fields = ['term_id', 'name', 'definition', 'category', 'status', 'updated_at'];
    $prompts = [
        'term_id'    => 'ID',
        'name'       => 'Name',
        'definition' => 'Definition',
        'category'   => 'Category',
        'status'     => 'Status',
        'updated_at' => 'Updated',
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
        'href'  => term_href($row['term_id']),
        'data'  => $data,
        'links' => [],
    ];
}

function collection_queries(): array {
    return [[
        'rel'    => 'search',
        'href'   => BASE_URL,
        'prompt' => 'Filter terms',
        'data'   => [
            ['name' => 'category', 'value' => ''],
            ['name' => 'term',     'value' => ''],
        ]
    ]];
}

function send_collection(array $items, ?string $error = null, ?array $error_detail = null): void {
    $collection = [
        'version' => '1.0',
        'href'    => BASE_URL,
        'queries' => collection_queries(),
        'items'   => $items,
    ];
    if ($error) {
        $err = ['title' => $error];
        if ($error_detail) $err = array_merge($err, $error_detail);
        $collection['error'] = $err;
    }
    echo json_encode(['collection' => $collection], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

function send_error(int $code, string $message, ?array $detail = null): void {
    http_response_code($code);
    send_collection([], $message, $detail);
    exit;
}

// --- Valid categories and aliases ---

const VALID_CATEGORIES = ['Core', 'Persona', 'Interaction', 'Pipeline', 'BotLibrary'];

const ALIASES = [
    'analytics'  => 'Persona',
    'workflow'   => 'Pipeline',
    'command'    => 'Interaction',
    'vocabulary' => 'Core',
    'library'    => 'BotLibrary',
    'persona'    => 'Persona',
    'core'       => 'Core',
    'interaction'=> 'Interaction',
    'pipeline'   => 'Pipeline',
    'botlibrary' => 'BotLibrary',
];

function resolve_category(string $input): string {
    if (in_array($input, VALID_CATEGORIES)) return $input;

    $suggestion = ALIASES[strtolower($input)] ?? null;
    send_error(400, "\"$input\" is not a recognised category.", [
        'message'          => $suggestion ? "Did you mean: $suggestion?" : null,
        'valid_categories' => VALID_CATEGORIES,
    ]);
}

// --- Router ---

try {
    $db     = get_db();
    $method = $_SERVER['REQUEST_METHOD'];

    if ($method !== 'GET') {
        send_error(405, 'Method not allowed');
    }

    $where  = [];
    $params = [];

    if (isset($_GET['category'])) {
        $cat     = resolve_category($_GET['category']);
        $where[] = 'category = ?';
        $params[] = $cat;
    }

    if (isset($_GET['term'])) {
        $where[]  = 'name = ?';
        $params[] = $_GET['term'];
    }

    $sql = 'SELECT * FROM terms';
    if ($where) $sql .= ' WHERE ' . implode(' AND ', $where);
    $sql .= ' ORDER BY category, name';

    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $rows  = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $items = array_map('term_to_item', $rows);

    send_collection($items);

} catch (Exception $e) {
    http_response_code(500);
    send_collection([], $e->getMessage());
}
?>