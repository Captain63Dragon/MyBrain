"""
mail_service.py - Tag-based email parsing, triage, and auto-creation.
Called by mail_ingestor._poll() after local .eml archive write.

Pipeline:
  1. Decode MIME subject, extract [tag]
  2. Strip preamble, extract [VERA:] instructions
  3. Strip code blocks before field extraction
  4. Apply per-type schema - canonical fields, recovery mappings, raw_extras
  5. For markdown-heavy emails (no Pip preamble) - extract ## sections
  6. Gate auto-create - permissive: preamble + primary field = intent confirmed
  7. Route: auto-create → archive-instructions/ on success, vera-queue/{tag}/ on fail
            triage-only or gate fail → vera-queue/{tag}/ with extracted fields attached
            untagged → vera-queue/untagged/

Triage files always include extracted fields AND raw body.
Vera never needs to re-read the raw .eml.

Auto-create types:   todo, feature.request, feature_request
Triage-only types:   idea, note, tracker, buscard, r2h, web, and all unknown tags
"""

import email
import re
from email.header import decode_header as _decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.shared.mfi_shared import email_queue_path, email_archive_path


# ── Constants ─────────────────────────────────────────────────────────────────

AUTO_CREATE_TAGS = {'todo', 'feature.request', 'feature_request'}
PRIORITY_DEFAULT = 'medium'
STATUS_DEFAULT   = 'open'
VALID_PRIORITY   = {'high', 'medium', 'low'}
VALID_STATUS     = {'open', 'pending', 'in_progress', 'deferred', 'completed', 'closed'}
VALID_FRICTION   = {
    'phone-call', 'difficult', 'uncertain', 'boring',
    'waiting-on-other', 'hated-meeting', 'procrastination', 'interviews'
}


# ── Per-type schemas ──────────────────────────────────────────────────────────

TYPE_SCHEMAS = {
    'todo': {
        'primary':   'description',
        'canonical': {
            'description', 'status', 'priority', 'friction',
            'due', 'context', 'notes', 'owner', 'source_pin',
        },
        'recovery': {
            'summary':    'description',
            'title':      'description',
            'pain_point': 'friction',
            'blocker':    'friction',
        },
        'freeform': None,
    },
    'idea': {
        'primary':   'summary',
        'canonical': {
            'summary', 'spark', 'potential', 'connects_to',
            'status', 'priority', 'owner', 'tags', 'body',
        },
        'recovery': {
            'description': 'summary',
            'title':       'summary',
        },
        'freeform': 'body',
    },
    'note': {
        'primary':   'summary',
        'canonical': {'summary', 'context', 'url', 'body'},
        'recovery': {
            'description': 'summary',
            'title':       'summary',
        },
        'freeform': 'body',
    },
    'feature.request': {
        'primary':   'summary',
        'canonical': {
            'summary', 'status', 'priority', 'pain_point',
            'problem', 'proposed', 'owners', 'notes',
        },
        'recovery': {
            'description': 'summary',
            'title':       'summary',
        },
        'freeform': None,
    },
}
TYPE_SCHEMAS['feature_request'] = TYPE_SCHEMAS['feature.request']

_UNKNOWN_SCHEMA = {
    'primary':   None,
    'canonical': set(),
    'recovery':  {},
    'freeform':  None,
}

def _get_schema(tag: str) -> dict:
    return TYPE_SCHEMAS.get(tag, _UNKNOWN_SCHEMA)


# ── Path helpers ──────────────────────────────────────────────────────────────

def _archive_instructions_path() -> Path:
    return email_archive_path().parent / 'archive-instructions'


# ── Subject decoding ──────────────────────────────────────────────────────────

def decode_subject(raw_subject: str) -> str:
    try:
        parts = _decode_header(raw_subject)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded.append(part)
        return ''.join(decoded)
    except Exception:
        return raw_subject


# ── Tag extraction ────────────────────────────────────────────────────────────

_TAG_RE = re.compile(r'^\s*\[([^\]]+)\]', re.IGNORECASE)

def extract_tag(subject: str) -> str | None:
    match = _TAG_RE.match(subject)
    return match.group(1).strip().lower() if match else None

def _tag_to_folder(tag: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', tag).strip('_')

def _clean_subject(subject: str) -> str:
    return re.sub(r'^\s*\[[^\]]+\]\s*', '', subject).strip()


# ── Body decoding ─────────────────────────────────────────────────────────────

_PUNCT_MAP = [
    # Dashes
    ('\u2014', '--'),   # em dash
    ('\u2013', '-'),    # en dash
    ('\u2012', '-'),    # figure dash
    ('\u2015', '--'),   # horizontal bar
    ('\u2212', '-'),    # minus sign
    # Quotes
    ('\u2018', "'"),    # left single quote
    ('\u2019', "'"),    # right single quote / apostrophe
    ('\u201a', "'"),    # single low-9 quotation mark
    ('\u201b', "'"),    # single high-reversed-9 quotation mark
    ('\u201c', '"'),    # left double quote
    ('\u201d', '"'),    # right double quote
    ('\u201e', '"'),    # double low-9 quotation mark
    ('\u02bc', "'"),    # modifier letter apostrophe
    # Ellipsis
    ('\u2026', '...'),  # ellipsis
    # Spaces
    ('\u00a0', ' '),    # non-breaking space
    ('\u202f', ' '),    # narrow no-break space
    ('\u2009', ' '),    # thin space
    # Bullets / list markers
    ('\u2022', '-'),    # bullet
    ('\u2023', '-'),    # triangular bullet
    ('\u25e6', '-'),    # white bullet
    # Miscellaneous
    ('\u00b7', '.'),    # middle dot
    ('\u2027', '.'),    # hyphenation point
]

def _decode_body(raw: str) -> str:
    """
    Fix quoted-printable artifacts and normalise exotic punctuation.
    1. Re-join soft-wrapped lines (trailing = means no real line break)
    2. Decode remaining =XX hex sequences
    3. Replace exotic Unicode punctuation with ASCII equivalents
    """
    import quopri
    try:
        rejoined = raw.replace('=\n', '').replace('=\r\n', '')
        decoded  = quopri.decodestring(rejoined.encode('utf-8', errors='replace'))
        text     = decoded.decode('utf-8', errors='replace')
        for char, replacement in _PUNCT_MAP:
            text = text.replace(char, replacement)
        return text
    except Exception:
        return raw


# ── Message parsing ───────────────────────────────────────────────────────────

def _parse_message(msg) -> dict:
    raw_subject = msg.get('Subject', '')
    date_raw    = msg.get('Date', '')
    try:
        timestamp = parsedate_to_datetime(date_raw).isoformat() if date_raw else ''
    except Exception:
        timestamp = date_raw

    body        = ''
    attachments = []
    for part in msg.walk():
        ct          = part.get_content_type()
        disposition = str(part.get('Content-Disposition', ''))
        if ct == 'text/plain' and 'attachment' not in disposition:
            raw  = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            body = _decode_body(raw).strip()
        elif part.get_filename():
            attachments.append(f"  {part.get_filename()} ({ct})")

    return {
        'sender':      msg.get('From', ''),
        'timestamp':   timestamp,
        'subject':     decode_subject(raw_subject),
        'body':        body,
        'attachments': attachments,
    }


# ── Preamble + VERA instruction stripping ─────────────────────────────────────

_PIP_VER_RE = re.compile(r'^Pip ver\s*:.*$', re.IGNORECASE | re.MULTILINE)
_VERA_RE    = re.compile(r'^\[VERA:\]\s*(.+)$', re.IGNORECASE | re.MULTILINE)
_SUBJECT_RE = re.compile(r'^Subject\s+\[.*?\].*$', re.IGNORECASE | re.MULTILINE)

def _strip_preamble(body: str) -> tuple[str, bool, str | None]:
    has_preamble     = bool(_PIP_VER_RE.search(body))
    vera_match       = _VERA_RE.search(body)
    vera_instruction = vera_match.group(1).strip() if vera_match else None
    cleaned = _PIP_VER_RE.sub('', body)
    cleaned = _VERA_RE.sub('', cleaned)
    cleaned = _SUBJECT_RE.sub('', cleaned)
    return cleaned.strip(), has_preamble, vera_instruction


# ── Code block stripping ──────────────────────────────────────────────────────

_CODE_FENCE_RE = re.compile(r'```.*?```', re.DOTALL)

def _strip_code_blocks(body: str) -> tuple[str, list[str]]:
    """Remove code fences before field extraction. Returns (cleaned, blocks)."""
    blocks = []
    def _replace(m):
        blocks.append(m.group(0))
        return f'__CODE_BLOCK_{len(blocks) - 1}__'
    return _CODE_FENCE_RE.sub(_replace, body), blocks


# ── Markdown section extraction ───────────────────────────────────────────────

_MD_HEADER_RE = re.compile(r'^#{1,3} +(.+)$', re.MULTILINE)

def _extract_md_sections(body: str, schema: dict) -> dict[str, str]:
    """
    For markdown-structured emails (no Pip preamble), extract ## Header blocks
    as named sections. Applies schema recovery mappings to header names.
    Returns dict of {canonical_or_raw_name: content}.
    """
    recovery = schema.get('recovery', {})
    sections = {}
    headers  = list(_MD_HEADER_RE.finditer(body))
    if not headers:
        return sections
    for i, match in enumerate(headers):
        header_text = match.group(1).strip()
        start       = match.end()
        end         = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        content     = body[start:end].strip()
        content     = re.sub(r'^-{3,}\s*', '', content, flags=re.MULTILINE).strip()
        if not content:
            continue
        key = header_text.lower().replace(' ', '_')
        if key in recovery:
            key = recovery[key]
        sections[key] = content
    return sections


# ── Freeform block extraction ─────────────────────────────────────────────────

def _extract_freeform_block(body: str, freeform_field: str) -> tuple[str, str]:
    """Split body at freeform field. Returns (body_before, freeform_content)."""
    pattern = re.compile(
        rf'^{re.escape(freeform_field)}\s*:\s*\n?(.*)',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    match = pattern.search(body)
    if not match:
        return body, ''
    return body[:match.start()].strip(), match.group(1).strip()


# ── Key:value field extraction ────────────────────────────────────────────────

_FIELD_RE = re.compile(
    r'^([a-zA-Z][a-zA-Z0-9_ ]*?)\s*:\s*(.*?)(?=\n[a-zA-Z][a-zA-Z0-9_ ]*?\s*:|\Z)',
    re.MULTILINE | re.DOTALL
)

def _extract_raw_fields(body: str) -> dict[str, str | None]:
    """
    Extract all key: value pairs. Multi-line continuations are joined with a
    space so wrapped sentences read as continuous text.
    """
    extracted = {}
    for match in _FIELD_RE.finditer(body):
        key     = match.group(1).strip().lower().replace(' ', '_')
        raw_val = match.group(2)
        lines   = raw_val.splitlines()
        joined  = ' '.join(line.strip() for line in lines if line.strip())
        extracted[key] = joined.strip() or None
    return extracted


# ── Validators ────────────────────────────────────────────────────────────────

def _normalize_single(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().split()[0].lower().rstrip('|,;') or None

def _validate_friction(value: str | None, flags: list) -> str | None:
    if value is None:
        return None
    if value == 'none':
        return None
    if value not in VALID_FRICTION:
        flags.append(f"friction '{value}' not recognised -- nulled")
        return None
    return value

def _validate_due(value: str | None, flags: list) -> str | None:
    if not value:
        return None
    n = _normalize_single(value)
    if n and re.match(r'\d{4}-\d{2}-\d{2}', n):
        return n
    if n:
        flags.append(f"due '{value}' is not YYYY-MM-DD -- nulled")
    return None

def _validate_priority(value: str | None, flags: list) -> str:
    n = _normalize_single(value) or PRIORITY_DEFAULT
    if n not in VALID_PRIORITY:
        flags.append(f"priority '{value}' not recognised -- defaulting to '{PRIORITY_DEFAULT}'")
        return PRIORITY_DEFAULT
    return n

def _validate_status(value: str | None, flags: list) -> str:
    n = _normalize_single(value) or STATUS_DEFAULT
    if n not in VALID_STATUS:
        flags.append(f"status '{value}' not recognised -- defaulting to '{STATUS_DEFAULT}'")
        return STATUS_DEFAULT
    return n


# ── Main field processor ──────────────────────────────────────────────────────

def _all_field_names(schema: dict) -> list[str]:
    names = set(schema['canonical']) | set(schema['recovery'].keys())
    if schema.get('freeform'):
        names.add(schema['freeform'])
    return sorted(names)

def extract_fields(parsed: dict, tag: str) -> dict:
    """
    Extract and validate fields from email body for a given tag type.

    Pass 1: key:value field extraction (Pip-template emails)
    Pass 2: markdown ## section extraction (freeform/pre-template emails)
    Unknown fields → raw_extras for Vera.
    """
    body    = parsed['body']
    subject = parsed['subject']
    schema  = _get_schema(tag)
    flags         = []
    recovery_used = []

    # Strip preamble
    body, has_preamble, vera_instruction = _strip_preamble(body)

    # Strip code blocks before any extraction
    body, code_blocks = _strip_code_blocks(body)

    # Split freeform block first (idea/note body: field)
    freeform_content = ''
    freeform_field   = schema.get('freeform')
    if freeform_field:
        body, freeform_content = _extract_freeform_block(body, freeform_field)

    # Pass 1 - key:value extraction
    raw = _extract_raw_fields(body)

    # Pass 2 - markdown sections (supplement Pass 1, don't overwrite)
    md_sections = _extract_md_sections(body, schema)
    for k, v in md_sections.items():
        if k not in raw:
            raw[k] = v

    # Apply recovery mappings
    canonical_set = schema['canonical']
    for incoming, canonical in schema['recovery'].items():
        if incoming in raw and canonical not in raw:
            raw[canonical] = raw.pop(incoming)
            recovery_used.append({'from': incoming, 'to': canonical})
        elif incoming in raw and canonical in raw:
            flags.append(f"'{incoming}' and '{canonical}' both present -- kept '{canonical}'")
            raw.pop(incoming)

    # Separate extras
    extras = {k: v for k, v in raw.items() if k not in canonical_set}
    for k in list(extras):
        raw.pop(k)

    # Primary field
    primary           = schema.get('primary')
    primary_value     = raw.get(primary) if primary else None
    primary_from_body = primary_value is not None
    if not primary_from_body:
        primary_value = _clean_subject(subject) or None
        if primary_value and primary:
            flags.append(f"'{primary}' fell back to subject -- template may not be filled in")

    fields: dict = {
        '_has_preamble':      has_preamble,
        '_primary_from_body': primary_from_body,
        '_vera_instruction':  vera_instruction,
        'subject_hint':       _clean_subject(subject),
        'raw_extras':         extras if extras else None,
        'flags':              flags,
        'recovery_used':      recovery_used,
    }

    if primary and primary_value:
        fields[primary] = primary_value

    if 'status'   in canonical_set:
        fields['status']   = _validate_status(raw.get('status'), flags)
    if 'priority' in canonical_set:
        fields['priority'] = _validate_priority(raw.get('priority'), flags)
    if 'friction' in canonical_set:
        fields['friction'] = _validate_friction(_normalize_single(raw.get('friction')), flags)
    if 'due'      in canonical_set:
        fields['due']      = _validate_due(raw.get('due'), flags)

    passthrough = canonical_set - {primary, 'status', 'priority', 'friction', 'due', freeform_field} - {None}
    for f in passthrough:
        if f in raw:
            fields[f] = raw[f]

    if freeform_field:
        fields[freeform_field] = freeform_content or None

    return fields


# ── Auto-create gate ──────────────────────────────────────────────────────────

def passes_auto_create(fields: dict, tag: str) -> tuple[bool, str]:
    """
    Permissive gate:
      1. Pip ver: preamble present
      2. Primary field found in body (not subject fallback)
    """
    schema  = _get_schema(tag)
    primary = schema.get('primary')
    if not primary:
        return False, f"no primary field defined for tag '{tag}'"
    if not fields.get('_has_preamble'):
        return False, 'no Pip ver: preamble -- likely not a template email'
    if not fields.get('_primary_from_body'):
        return False, f"'{primary}' not found in body -- template not filled in"
    if not fields.get(primary):
        return False, f"'{primary}' is empty"
    return True, 'ok'


# ── File builders ─────────────────────────────────────────────────────────────

def _make_filename(parsed: dict, subfolder: str, uid_hash: str) -> str:
    ts = parsed.get('timestamp', '')[:10] or '0000-00-00'
    parts = ts.split('-')
    try:
        date_str = f"{parts[0]}_{parts[1]}{parts[2]}"
    except IndexError:
        date_str = '0000_0000'
    subject = _clean_subject(parsed.get('subject', '')) or 'no_subject'
    slug    = re.sub(r'[^a-z0-9]+', '_', subject.lower()).strip('_')[:40] or 'no_subject'
    return f"{date_str}-{subfolder}-{slug}.txt"

def _format_fields_block(fields: dict) -> list[str]:
    lines = []
    skip  = {'flags', 'recovery_used', '_has_preamble', '_primary_from_body',
              '_vera_instruction', 'subject_hint', 'raw_extras'}
    for k, v in fields.items():
        if k in skip or v is None:
            continue
        lines.append(f"{k.upper()}: {v}")
    if fields.get('raw_extras'):
        lines.append('--- EXTRAS (unrecognised fields):')
        for k, v in fields['raw_extras'].items():
            lines.append(f"  {k}: {v}")
    if fields.get('recovery_used'):
        lines.append('--- RECOVERY MAPPINGS APPLIED:')
        for r in fields['recovery_used']:
            lines.append(f"  {r['from']} -> {r['to']}")
    if fields.get('flags'):
        lines.append('--- FLAGS:')
        for f in fields['flags']:
            lines.append(f"  ! {f}")
    return lines

def _build_triage_content(parsed: dict, tag: str, uid_hash: str,
                           fields: dict | None = None,
                           reason: str | None = None) -> str:
    lines = [
        f"FROM:    {parsed['sender']}",
        f"DATE:    {parsed['timestamp']}",
        f"SUBJECT: {parsed['subject']}",
        f"TAG:     [{tag}]",
        f"SOURCE:  {uid_hash}.eml",
    ]
    if fields and fields.get('_vera_instruction'):
        lines.append(f"VERA:    {fields['_vera_instruction']}")
    if reason:
        lines.append(f"TRIAGE:  {reason}")
    if fields:
        lines.append('--- EXTRACTED FIELDS:')
        lines.extend(_format_fields_block(fields))
    lines += ['--- RAW BODY:', parsed['body'] or '(no body)']
    if parsed['attachments']:
        lines += ['--- ATTACHMENTS:'] + parsed['attachments']
    return '\n'.join(lines) + '\n'

def _build_archive_content(parsed: dict, fields: dict,
                            uid_hash: str, node_id: str) -> str:
    lines = [
        f"FROM:    {parsed['sender']}",
        f"DATE:    {parsed['timestamp']}",
        f"SUBJECT: {parsed['subject']}",
        f"SOURCE:  {uid_hash}.eml",
        f"NODE-ID: {node_id}",
        f"AUTO-CREATED: yes",
        '--- FIELDS:',
    ]
    lines.extend(_format_fields_block(fields))
    if parsed['attachments']:
        lines += ['--- ATTACHMENTS:'] + parsed['attachments']
    return '\n'.join(lines) + '\n'

def _write_triage(parsed: dict, tag: str, uid_hash: str,
                  fields: dict | None = None,
                  reason: str | None = None) -> str:
    subfolder = _tag_to_folder(tag)
    dest      = email_queue_path() / subfolder
    dest.mkdir(parents=True, exist_ok=True)
    filename  = _make_filename(parsed, subfolder, uid_hash)
    out       = dest / filename
    out.write_text(_build_triage_content(parsed, tag, uid_hash, fields, reason), encoding='utf-8')
    suffix = f" ({reason})" if reason else ""
    print(f"[mail_service] [{tag}] -> vera-queue/{subfolder}/{filename}{suffix}")
    return str(out)


# ── Attachment extraction ─────────────────────────────────────────────────────

EXTRACTABLE_MIME_PREFIXES = ('image/', 'application/pdf', 'text/plain')

def _attachments_path() -> Path:
    return email_archive_path().parent / 'attachments'

def extract_attachments(raw_bytes: bytes, uid_hash: str) -> list[dict]:
    """Extract attachments from .eml. Called directly by email_routes.py."""
    import datetime
    msg      = email.message_from_bytes(raw_bytes)
    saved    = []
    dest_dir = _attachments_path()
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        dt          = parsedate_to_datetime(msg.get('Date', ''))
        date_prefix = f"{dt.year}_{dt.month:02d}{dt.day:02d}"
    except Exception:
        dt          = datetime.datetime.now()
        date_prefix = f"{dt.year}_{dt.month:02d}{dt.day:02d}"

    part_index = 0
    for part in msg.walk():
        ct          = part.get_content_type()
        disposition = str(part.get('Content-Disposition', ''))
        content_id  = part.get('Content-ID', '').strip('<>')
        if part.get_content_maintype() == 'multipart':
            continue
        if ct == 'text/plain' and 'attachment' not in disposition:
            continue
        if ct == 'text/html':
            continue
        if not any(ct.startswith(p) for p in EXTRACTABLE_MIME_PREFIXES):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        ext        = ct.split('/')[-1].split(';')[0].strip()
        part_index += 1
        descriptor = re.sub(r'[^a-zA-Z0-9_-]', '_', content_id) if content_id else 'part'
        filename   = f"{date_prefix}-{descriptor}-{uid_hash}_{part_index:03d}.{ext}"
        out_path   = dest_dir / filename
        out_path.write_bytes(payload)
        saved.append({
            'name': filename, 'type': ct,
            'size': len(payload), 'path': str(out_path),
            'content_id': content_id or None,
        })
        print(f"[mail_service] extracted: {filename} ({ct}, {len(payload)} bytes)")
    return saved


# ── Router ────────────────────────────────────────────────────────────────────

def route(raw_bytes: bytes, uid_hash: str) -> dict:
    """
    Main entry point from mail_ingestor.

    1. Decode subject, extract tag
    2. No tag -> vera-queue/untagged/
    3. Extract fields for tag type
    4. Triage-only -> vera-queue/{tag}/ with extracted fields
    5. Auto-create gate:
       Fail -> vera-queue/{tag}/ with extracted fields + reason
       Pass -> attempt node creation:
           Success -> archive-instructions/
           Failure -> vera-queue/{tag}/ with extracted fields + error
    """
    msg    = email.message_from_bytes(raw_bytes)
    parsed = _parse_message(msg)
    tag    = extract_tag(parsed['subject'])

    result = {'tag': tag, 'path': None, 'auto_created': False, 'node_id': None}

    if not tag:
        result['path'] = _write_triage(parsed, 'untagged', uid_hash)
        return result

    fields = extract_fields(parsed, tag)

    if tag not in AUTO_CREATE_TAGS:
        result['path'] = _write_triage(parsed, tag, uid_hash, fields=fields)
        return result

    ok, reason = passes_auto_create(fields, tag)
    if not ok:
        print(f"[mail_service] [{tag}] gate fail: {reason}")
        result['path'] = _write_triage(parsed, tag, uid_hash, fields=fields, reason=reason)
        return result

    try:
        from app.bots.db.vera import create_todo
        todo = create_todo(
            description = fields.get('description'),
            priority    = fields.get('priority', PRIORITY_DEFAULT),
            status      = fields.get('status', STATUS_DEFAULT),
            friction    = fields.get('friction'),
            due         = fields.get('due'),
            notes       = fields.get('notes'),
            context     = fields.get('context'),
            source_pin  = f"{uid_hash}.eml",
            owner       = fields.get('owner', 'user'),
            made_by     = 'Claude',
            reason      = f'mail_ingestor auto-create from {uid_hash}.eml',
        )
        if 'error' in todo:
            raise RuntimeError(todo['error'])

        node_id = todo.get('todo-id')
        result.update({'node_id': node_id, 'auto_created': True})

        dest     = _archive_instructions_path()
        dest.mkdir(parents=True, exist_ok=True)
        filename = _make_filename(parsed, _tag_to_folder(tag), uid_hash)
        out      = dest / filename
        out.write_text(_build_archive_content(parsed, fields, uid_hash, node_id), encoding='utf-8')
        result['path'] = str(out)
        print(f"[mail_service] [{tag}] auto-created {node_id} -> archive-instructions/{filename}")

    except Exception as e:
        reason = f"node creation failed: {e}"
        print(f"[mail_service] [{tag}] {reason}")
        result['path'] = _write_triage(parsed, tag, uid_hash, fields=fields, reason=reason)

    return result
