# rijksmuseum_service.py
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

def _types(node: Dict[str, Any]) -> List[str]:
    t = node.get("type") or node.get("@type")
    if isinstance(t, list):
        return [str(x) for x in t]
    if isinstance(t, str):
        return [t]
    return []

def _has_type(node: Dict[str, Any], short: str) -> bool:
    for t in _types(node):
        if t == short:
            return True
        # handle URI forms like ".../HumanMadeObject" or "...#HumanMadeObject"
        if t.endswith("/" + short) or t.endswith("#" + short) or t.endswith(":" + short):
            return True
    return False

def _find_hmo(graph: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for n in graph:
        if _has_type(n, "HumanMadeObject"):
            return n
    return None


def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def _get_label_any(x, id_map):
    x = _resolve_ref(x, id_map)
    if isinstance(x, dict):
        lab = _label(x)
        return lab
    return None

def _collect_labels_from_list(xs, id_map):
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

def _node_id(node: Dict[str, Any]) -> Optional[str]:
    return node.get("@id") or node.get("id")

def _label(node: Dict[str, Any]) -> Optional[str]:
    for k in ("content", "_label", "label", "name"):
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _build_id_map(graph: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    m = {}
    for n in graph:
        nid = _node_id(n)
        if nid:
            m[nid] = n
    return m

def _resolve_ref(x: Any, id_map: Dict[str, Dict[str, Any]]) -> Any:
    # If it's a reference like {"@id": "..."} try resolve it to the full node
    if isinstance(x, dict):
        rid = _node_id(x)
        if rid and rid in id_map:
            return id_map[rid]
    return x

def _collect_labels(obj: Any, out: Set[str]) -> None:
    """Heuristic label collector for JSON-LD/LinkedArt-ish structures."""
    if isinstance(obj, dict):
        # common label fields
        for k in ("_label", "label", "name"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                out.add(v.strip())

        # recurse through values
        for v in obj.values():
            _collect_labels(v, out)

    elif isinstance(obj, list):
        for item in obj:
            _collect_labels(item, out)


def _find_human_made_object(graph: List[dict]) -> Optional[dict]:
    # Linked Art usually includes a HumanMadeObject node
    for node in graph:
        t = node.get("type") or node.get("@type")
        if t in ("HumanMadeObject", "VisualItem", "LinguisticObject"):
            # Prefer HumanMadeObject if present
            if t == "HumanMadeObject":
                return node
    return graph[0] if graph else None


def _extract_techniques_from_graph(graph: List[dict]) -> List[str]:
    """
    Linked Art typically encodes technique as classifications (Type nodes) somewhere
    in/near the HumanMadeObject via 'classified_as' / 'used_specific_object' etc.
    We'll do a heuristic:
      - look for keys likely to contain technique classification
      - collect labels from those subtrees
    """
    hmo = _find_human_made_object(graph)
    if not hmo:
        return []

    candidates: List[Any] = []
    for key in ("technique", "classified_as", "carried_out", "used_specific_object", "made_of", "referred_to_by"):
        if key in hmo:
            candidates.append(hmo[key])

    labels: Set[str] = set()
    for c in candidates:
        _collect_labels(c, labels)

    # This will likely include extra labels. You can tighten later once you inspect a sample response.
    # For now: return a sorted unique list.
    return sorted(labels)


async def search_pid_by_object_number(object_number: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(SEARCH_URL, params={"objectNumber": object_number})
        r.raise_for_status()
        data = r.json()

    items = data.get("orderedItems") or []
    if not items:
        raise ValueError(f"No results for objectNumber={object_number}")

    # first hit; could also validate exact match later
    return items[0]["id"]  # e.g. https://id.rijksmuseum.nl/20024929


async def resolve_pid_jsonld(pid_url: str, profile: str = "la", mediatype: str = "application/ld+json") -> dict:
    # use query-string content negotiation
    params = {"_profile": profile, "_mediatype": mediatype}

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(pid_url, params=params)
        r.raise_for_status()
        return r.json()


def extract_classified_as_labels(jsonld: Dict[str, Any]) -> List[str]:
    graph = jsonld.get("@graph")
    if not isinstance(graph, list):
        return []

    id_map = _build_id_map(graph)

    # find main artwork node (Linked Art often uses type HumanMadeObject)
    hmo = next((n for n in graph if n.get("type") == "HumanMadeObject"), None)
    if not hmo:
        return []

    ca = hmo.get("classified_as")
    if ca is None:
        return []

    items = ca if isinstance(ca, list) else [ca]
    labels = []
    for item in items:
        node = _resolve_ref(item, id_map)
        if isinstance(node, dict):
            lab = _label(node)
            if lab:
                labels.append(lab)

    # unique, keep order
    seen = set()
    out = []
    for lab in labels:
        if lab not in seen:
            seen.add(lab)
            out.append(lab)
    return out

def extract_core_fields(jsonld: Dict[str, Any]) -> Dict[str, Any]:
    graph = jsonld.get("@graph")
    if not isinstance(graph, list):
        return {}

    id_map = _build_id_map(graph)
    hmo = _find_hmo(graph)
    if not hmo:
        return {}

    # TITLE / IDENTIFIED_BY (Linked Art uses identified_by Name objects)
    titles = []
    for ident in _as_list(hmo.get("identified_by")):
        node = _resolve_ref(ident, id_map)
        if isinstance(node, dict):
            # Often has 'type': 'Name' and either 'content' or label/name
            content = node.get("content")
            if isinstance(content, str) and content.strip():
                titles.append(content.strip())
            else:
                lab = _label(node)
                if lab:
                    titles.append(lab)
    title = titles[0] if titles else None

    # CLASSIFICATION
    classified_as = _collect_labels_from_list(hmo.get("classified_as"), id_map)

    # MATERIALS (often made_of -> Type/Material nodes)
    materials = _collect_labels_from_list(hmo.get("made_of"), id_map)

    # DESCRIPTIONS / NOTES (often referred_to_by -> LinguisticObject with content)
    descriptions = []
    for note in _as_list(hmo.get("referred_to_by")):
        node = _resolve_ref(note, id_map)
        if isinstance(node, dict):
            content = node.get("content")
            if isinstance(content, str) and content.strip():
                descriptions.append(content.strip())
            else:
                lab = _label(node)
                if lab:
                    descriptions.append(lab)
    # keep it sane
    descriptions = descriptions[:10]

    # DIMENSIONS (Linked Art often uses dimension objects)
    dimensions = []
    for dim in _as_list(hmo.get("dimension")):
        node = _resolve_ref(dim, id_map)
        if isinstance(node, dict):
            value = node.get("value")
            unit = _get_label_any(node.get("unit"), id_map)
            dtype = _get_label_any(node.get("classified_as"), id_map)  # sometimes type of dimension
            if value is not None:
                s = f"{dtype + ': ' if dtype else ''}{value}{(' ' + unit) if unit else ''}"
                dimensions.append(s)
            else:
                lab = _label(node)
                if lab:
                    dimensions.append(lab)

    # PRODUCTION / CREATOR (often produced_by -> carried_out_by -> Actor)
    artist = None
    produced_by = _resolve_ref(hmo.get("produced_by"), id_map)
    if isinstance(produced_by, dict):
        carried = produced_by.get("carried_out_by")
        if carried:
            # could be list
            names = _collect_labels_from_list(carried, id_map)
            if names:
                artist = names[0]

    # DATE / TIMESPAN (often produced_by -> timespan)
    date = None
    if isinstance(produced_by, dict):
        ts = _resolve_ref(produced_by.get("timespan"), id_map)
        if isinstance(ts, dict):
            # common keys: begin_of_the_begin/end_of_the_end or identified_by/content
            for k in ("identified_by", "content", "begin_of_the_begin", "end_of_the_end"):
                v = ts.get(k)
                if isinstance(v, str) and v.strip():
                    date = v.strip()
                    break

    return {
        "title": title,
        "artist": artist,
        "date": date,
        "materials": materials,
        "dimensions": dimensions,
        "descriptions": descriptions,
        "classified_as": classified_as,
    }


async def fetch_artwork_metadata(object_number: str, profile: str = "la", mediatype: str = "application/ld+json") -> Dict[str, Any]:
    pid = await search_pid_by_object_number(object_number)
    jsonld = await resolve_pid_jsonld(pid, profile=profile, mediatype=mediatype)

    graph = jsonld.get("@graph") or []
    technique = _extract_techniques_from_graph(graph) if isinstance(graph, list) else []
    classified_as = extract_classified_as_labels(jsonld)
    parsed = extract_core_fields(jsonld)

    return {
        "objectNumber": object_number,
        "pid": pid,
        #"profile": profile,
        #"mediatype": mediatype,
        #"technique": technique,
        #"classified_as": classified_as,
        "parsed": parsed,
        "raw": jsonld,  # keep for debugging; you can drop later
    }
