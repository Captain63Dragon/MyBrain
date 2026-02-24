import re
import json
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

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
        nodes.append(data)
    return nodes

def map_properties(mfn, node):
    # Keep all discovered properties; MFN gives suggested core/optional fields
    props = {}
    for k, v in node.items():
        # normalize some common key variants
        key = k.strip()
        # unify context_notes/context_note
        if key == "context_notes":
            key = "context_note"
        if isinstance(v, (dict, tuple, list)):
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