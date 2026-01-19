# museum_api.py - Fixed version handling BOTH @graph and flat JSON-LD formats
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import time
import httpx

SEARCH_URL = "https://data.rijksmuseum.nl/search/collection"

@dataclass
class RijksCache:
    value: Optional[dict] = None
    expires_at: float = 0.0

    def get(self) -> Optional[dict]:
        if self.value is not None and time.time() < self.expires_at:
            return self.value
        return None

    def set(self, v: dict, ttl_seconds: int) -> None:
        self.value = v
        self.expires_at = time.time() + ttl_seconds


# ============================================================================
# HELPER FUNCTIONS FOR JSON-LD NAVIGATION
# ============================================================================

def _as_list(x):
    """Normalize to list."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _node_id(node: Dict[str, Any]) -> Optional[str]:
    """Extract node ID from @id, id, or _id field."""
    if not isinstance(node, dict):
        return None
    return node.get("@id") or node.get("id") or node.get("_id")


def _types(node: Dict[str, Any]) -> List[str]:
    """Extract all type values from a node, handling both 'type' and '@type' keys."""
    if not isinstance(node, dict):
        return []
    t = node.get("type") or node.get("@type")
    if isinstance(t, list):
        return [str(x) for x in t]
    if isinstance(t, str):
        return [t]
    return []


def _has_type(node: Dict[str, Any], short: str) -> bool:
    """Check if node has given type, handling URI forms and exact matches."""
    for t in _types(node):
        if t == short:
            return True
        # handle URI forms like ".../HumanMadeObject" or "...#HumanMadeObject"
        if t.endswith("/" + short) or t.endswith("#" + short) or t.endswith(":" + short):
            return True
    return False


def _label(node: Dict[str, Any]) -> Optional[str]:
    """Extract a human-readable label from a node."""
    if not isinstance(node, dict):
        return None
    for k in ("content", "_label", "label", "name"):
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _build_id_map(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a mapping from @id/id to full node for reference resolution."""
    m = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = _node_id(n)
        if nid:
            m[nid] = n
    return m


def _resolve_ref(x: Any, id_map: Dict[str, Dict[str, Any]]) -> Any:
    """If x is a reference like {"@id": "..."} or {"id": "..."}, resolve it to the full node."""
    if isinstance(x, dict):
        rid = _node_id(x)
        if rid and rid in id_map:
            return id_map[rid]
    return x


def _get_label_any(x, id_map):
    """Get label from x after resolving references."""
    x = _resolve_ref(x, id_map)
    if isinstance(x, dict):
        return _label(x)
    return None


def _collect_labels_from_list(xs, id_map):
    """Collect unique labels from a list, preserving order."""
    out = []
    for x in _as_list(xs):
        lab = _get_label_any(x, id_map)
        if lab:
            out.append(lab)
    # unique preserve order
    seen = set()
    res = []
    for v in out:
        if v not in seen:
            seen.add(v)
            res.append(v)
    return res


def _find_hmo_in_graph(graph: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the main HumanMadeObject node in a graph array."""
    for n in graph:
        if _has_type(n, "HumanMadeObject"):
            return n
    # Fallback: return first node if no HumanMadeObject found
    return graph[0] if graph else None


def _normalize_to_graph(jsonld: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert JSON-LD to a graph array, handling both formats:
    1. Graph format: {"@graph": [...]}
    2. Flat format: {"id": "...", "type": "...", ...}
    """
    # Check if it's already a graph format
    if "@graph" in jsonld and isinstance(jsonld["@graph"], list):
        return jsonld["@graph"]
    
    # It's a flat format - convert to graph
    # The main object is the HumanMadeObject, we need to extract referenced objects
    graph = [jsonld]  # Start with the main object
    
    # Recursively find all nested objects that have IDs (these are separate nodes)
    def extract_nodes(obj, collected):
        if isinstance(obj, dict):
            # If this object has an id/type, it's a separate node
            if (_node_id(obj) or obj.get("type") or obj.get("@type")) and obj not in collected:
                collected.append(obj)
            # Recurse into nested structures
            for value in obj.values():
                extract_nodes(value, collected)
        elif isinstance(obj, list):
            for item in obj:
                extract_nodes(item, collected)
    
    all_nodes = []
    extract_nodes(jsonld, all_nodes)
    
    return all_nodes


# ============================================================================
# CORE EXTRACTION FUNCTIONS
# ============================================================================

def extract_core_fields(jsonld: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fields from Rijksmuseum Linked Art JSON-LD.
    
    Handles BOTH formats:
    - Graph format: {"@graph": [...]}
    - Flat format: {"id": "...", "type": "...", ...}
    """
    # Normalize to graph array
    graph = _normalize_to_graph(jsonld)
    
    if not graph:
        return {}

    id_map = _build_id_map(graph)
    hmo = _find_hmo_in_graph(graph)
    
    if not hmo:
        return {}

    # -------- TITLE --------
    titles = []
    for ident in _as_list(hmo.get("identified_by")):
        node = _resolve_ref(ident, id_map)
        if isinstance(node, dict):
            if _has_type(node, "Name"):
                content = node.get("content")
                if isinstance(content, str) and content.strip():
                    titles.append(content.strip())
                else:
                    lab = _label(node)
                    if lab:
                        titles.append(lab)
    title = titles[0] if titles else None

    # -------- ARTIST / CREATOR --------
    artist = None
    date = None
    
    produced_by = _resolve_ref(hmo.get("produced_by"), id_map)
    if isinstance(produced_by, dict):
        # Get artist from carried_out_by
        carried = produced_by.get("carried_out_by")
        if carried:
            names = _collect_labels_from_list(carried, id_map)
            if names:
                artist = names[0]
        
        # Get date from timespan
        ts = _resolve_ref(produced_by.get("timespan"), id_map)
        if isinstance(ts, dict):
            # Try identified_by first (human-readable date strings)
            for ident in _as_list(ts.get("identified_by")):
                node = _resolve_ref(ident, id_map)
                content = _label(node)
                if content:
                    date = content
                    break
            
            # Fallback to machine timestamps
            if not date:
                begin = ts.get("begin_of_the_begin")
                end = ts.get("end_of_the_end")
                if begin:
                    date = begin[:4] if len(begin) >= 4 else begin
                elif end:
                    date = end[:4] if len(end) >= 4 else end

    # -------- CLASSIFIED_AS (categories/types) --------
    classified_as = _collect_labels_from_list(hmo.get("classified_as"), id_map)

    # -------- MATERIALS --------
    materials = _collect_labels_from_list(hmo.get("made_of"), id_map)

    # -------- DIMENSIONS --------
    dimensions = []
    for dim in _as_list(hmo.get("dimension")):
        node = _resolve_ref(dim, id_map)
        if isinstance(node, dict):
            value = node.get("value")
            unit = _get_label_any(node.get("unit"), id_map)
            dtype_list = _collect_labels_from_list(node.get("classified_as"), id_map)
            dtype = dtype_list[0] if dtype_list else None
            
            if value is not None:
                s = f"{dtype + ': ' if dtype else ''}{value}{(' ' + unit) if unit else ''}"
                dimensions.append(s)
            else:
                lab = _label(node)
                if lab:
                    dimensions.append(lab)

    # -------- DESCRIPTIONS / NOTES --------
    descriptions = []
    
    # Method 1: From referred_to_by (LinguisticObject)
    for note in _as_list(hmo.get("referred_to_by")):
        node = _resolve_ref(note, id_map)
        if isinstance(node, dict):
            if _has_type(node, "LinguisticObject"):
                content = node.get("content")
                if isinstance(content, str) and content.strip():
                    descriptions.append(content.strip())
                else:
                    lab = _label(node)
                    if lab:
                        descriptions.append(lab)
    
    # Method 2: From subject_of (web page descriptions)
    # This contains the museum website descriptions like "Nadat hij van..."
    for subj in _as_list(hmo.get("subject_of")):
        subj_node = _resolve_ref(subj, id_map)
        if isinstance(subj_node, dict):
            # Check if this level has content directly
            if _has_type(subj_node, "LinguisticObject"):
                content = subj_node.get("content")
                if isinstance(content, str) and content.strip():
                    descriptions.append(content.strip())
            
            # Navigate through parts (one level)
            for part1 in _as_list(subj_node.get("part")):
                part1_node = _resolve_ref(part1, id_map)
                if isinstance(part1_node, dict):
                    # Check if this part has content directly
                    if _has_type(part1_node, "LinguisticObject"):
                        content = part1_node.get("content")
                        if isinstance(content, str) and content.strip():
                            descriptions.append(content.strip())
                    
                    # Check nested parts (two levels deep)
                    for part2 in _as_list(part1_node.get("part")):
                        part2_node = _resolve_ref(part2, id_map)
                        if isinstance(part2_node, dict):
                            # Check content at this level
                            if _has_type(part2_node, "LinguisticObject"):
                                content = part2_node.get("content")
                                if isinstance(content, str) and content.strip():
                                    descriptions.append(content.strip())
                            
                            # Check even deeper nested parts (three levels)
                            for part3 in _as_list(part2_node.get("part")):
                                part3_node = _resolve_ref(part3, id_map)
                                if isinstance(part3_node, dict):
                                    if _has_type(part3_node, "LinguisticObject"):
                                        content = part3_node.get("content")
                                        if isinstance(content, str) and content.strip():
                                            descriptions.append(content.strip())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_descriptions = []
    for desc in descriptions:
        if desc not in seen:
            seen.add(desc)
            unique_descriptions.append(desc)
    
    # Don't limit too much - keep more descriptions
    descriptions = unique_descriptions[:20]

    return {
        "title": title,
        "artist": artist,
        "date": date,
        "classified_as": classified_as,
        "materials": materials,
        "dimensions": dimensions,
        "descriptions": descriptions,
    }


# ============================================================================
# API FUNCTIONS
# ============================================================================

async def search_pid_by_object_number(object_number: str) -> str:
    """Search for a PID URL given an object number."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(SEARCH_URL, params={"objectNumber": object_number})
        r.raise_for_status()
        data = r.json()

    items = data.get("orderedItems") or []
    if not items:
        raise ValueError(f"No results for objectNumber={object_number}")

    return items[0]["id"]


async def resolve_pid_jsonld(pid_url: str, profile: str = "la", mediatype: str = "application/ld+json") -> dict:
    """Resolve a PID to JSON-LD using content negotiation."""
    params = {"_profile": profile, "_mediatype": mediatype}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(pid_url, params=params)
        r.raise_for_status()
        return r.json()


async def fetch_artwork_metadata(object_number: str, profile: str = "la", mediatype: str = "application/ld+json") -> Dict[str, Any]:
    """
    Main entry point: fetch complete artwork metadata.
    
    Returns dict with:
        - objectNumber: the input object number
        - pid: the resolved PID URL
        - parsed: extracted structured fields (title, artist, date, materials, etc.)
        - raw: the full JSON-LD response (for debugging)
    """
    pid = await search_pid_by_object_number(object_number)
    jsonld = await resolve_pid_jsonld(pid, profile=profile, mediatype=mediatype)

    parsed = extract_core_fields(jsonld)

    return {
        "objectNumber": object_number,
        "pid": pid,
        "parsed": parsed,
        "raw": jsonld,
    }