import re
import json
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

SYSTEM_FIELDS = ['FILE-NODE-id', 'filepath']
CORE_FIELDS = [
    'description', 'category', 'contact_name', 'phone', 'context_note'
]
OPTIONAL_FIELDS = [
    'phone-1-800', 'cell', 'fax', 'email', 'company',
    'location', 'instagram', 'url', 'recommendation'
]
REVIEW_FIELDS = ['reviewed', 'review_priority', 'pattern_matched']

def load_mfn(mfn_path):
    with open(mfn_path, "r", encoding="utf-8") as fh:
        node = yaml.safe_load(fh)
        if isinstance(node, dict) and node.get('META-FILE-NODE') is not None:
            #add a filenode id for this meta file node
            node['MFN-id'] = node.get('META-FILE-NODE')
        return node

def parse_gfn(gfn_path):
    text = open(gfn_path, "r", encoding="utf-8").read()
    # Split into blocks by FILE-NODE: marker (keep entries after the marker)
    parts = re.split(r'(?m)^FILE-NODE:\s*', text)
    nodes = []
    for part in parts[1:]:
        # first line is the id/key, remainder are properties
        m = re.match(r"([^\n]+)\r?\n(.*)$", part, re.S)
        if not m:
            continue
        node_id = m.group(1).strip()
        body = m.group(2)
        # build a YAML-like block with an explicit id field
        yaml_block = f"FILE-NODE-id: \"{node_id}\"\n" + body
        try:
            data = yaml.safe_load(yaml_block)
            print(f"[parse_gfn] {data.get('FILE-NODE-id')} — keys: {list(data.keys())}")
            if not isinstance(data, dict):
                data = {"FILE-NODE-id": node_id}
        except Exception:
            # fallback to simple line-by-line parse
            data = {"FILE-NODE-id": node_id}
            for line in body.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                if v.startswith("'") and v.endswith("'"):
                    v = v[1:-1]
                # handle empty lists '[]' and simple lists
                if v.startswith("[") and v.endswith("]"):
                    # remove brackets and split by comma
                    items = [it.strip().strip('"').strip("'") for it in v[1:-1].split(",") if it.strip()]
                    data[k] = items
                else:
                    data[k] = v
        related = data.pop('related', None)
        if related and isinstance(related, list):
            data['_related'] = []
            for entry in related:
                if not isinstance(entry, dict):
                    continue
                rel_type = entry.get('relationship')
                stub = entry.get('node')
                if rel_type and isinstance(stub, dict):
                    data['_related'].append({
                        'relationship': rel_type,
                        'node': stub
                    })
        nodes.append(data)
    return nodes

def get_src_folders(mapped: list[dict]) -> list[str]:
    """
    Extract unique parent folders from mapped node filepaths.
    Pure parsing — no Neo4j, no filesystem. Safe to call outside a session.
    Uses PureWindowsPath because paths are Windows strings, container is Linux.
    """
    from pathlib import PureWindowsPath
    seen, folders = set(), []
    for node in mapped:
        fp = node.get('filepath', '')
        if fp:
            folder = str(PureWindowsPath(fp).parent)
            if folder not in seen:
                seen.add(folder)
                folders.append(folder)
    return folders

def serialize_gfn(rows: list, mfn: dict) -> str:
    """
    Serialize export rows to GFN YAML string.
    Field order: system → core → optional → review → related stubs.
    Nulls and empty lists skipped.
    """
    lines = []
    field_order = SYSTEM_FIELDS + CORE_FIELDS + OPTIONAL_FIELDS + REVIEW_FIELDS

    for row in rows:
        node = row['node']
        related = row.get('related', [])

        node_id = node.get('FILE-NODE-id', '')
        lines.append(f"FILE-NODE: {node_id}")

        # write fields in order, skip nulls and empty lists
        for field in field_order:
            if field == 'FILE-NODE-id':
                continue  # already written as FILE-NODE header
            val = node.get(field)
            if val is None or val == '' or val == []:
                continue
            lines.append(_format_field(field, val))

        # write any remaining fields not in ordered list
        known = set(field_order)
        for k, v in node.items():
            if k in known or k == 'FILE-NODE-id':
                continue
            if v is None or v == '' or v == []:
                continue
            lines.append(_format_field(k, v))

        # write related stubs
        if related:
            lines.append("related:")
            for entry in related:
                rel_type = entry['rel']
                stub = entry['stub']
                stub_id = entry['stub_id']
                lines.append(f"  - relationship: {rel_type}")
                lines.append(f"    node:")
                lines.append(f"      FILE-NODE-id: {stub_id}")
                for sf in ['filepath', 'reviewed', 'review_priority']:
                    sv = stub.get(sf)
                    if sv is None:
                        continue
                    lines.append(f"      {sf}: {_scalar(sv)}")
                # relationship field on stub for import fidelity
                rel_field = 'insitu_copy_of' if rel_type == 'INSITU_COPY_OF' else 'copy_of'
                lines.append(f"      {rel_field}: {node_id}")

        lines.append("")  # blank line between records

    return "\n".join(lines)


def _format_field(key: str, val) -> str:
    return f"{key}: {_scalar(val)}"

def _scalar(val) -> str:
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        return str(val)
    val = str(val)
    if '\\' in val:
        return f"'{val}'"
    if any(c in val for c in [':', '#', '"', "'"]):
        val = val.replace('"', '\\"')
        return f'"{val}"'
    return val

def map_properties(mfn, node):
    # Keep all discovered properties; MFN gives suggested core/optional fields
    props = {}
    for k, v in node.items():
        # normalize some common key variants
        key = k.strip()
        # unify context_notes/context_note
        if key == "context_notes":
            key = "context_note"
        if k == '_related':
            props[k] = v
        elif isinstance(v, (dict, tuple, list)):
            props[k] = json.dumps(v)
        else:
            props[key] = v

    return props

def parse_user_search_input(raw_input):
    """Convert user input 'key:value, key2:value2' into dict"""
    properties = {}
    if not raw_input:
        return properties
    
    pairs = raw_input.split(',')
    for pair in pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)  # split on first : only
            properties[key.strip()] = value.strip()
    
    return properties