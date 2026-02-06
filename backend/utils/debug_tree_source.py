# Injected into debuggee to build variable tree. No other imports; used by debug.py and tests.

BUILD_VAR_TREE_SOURCE = r"""
def _safe_repr(obj, max_len=256):
    try:
        s = repr(obj)
        return s[:max_len] + ("..." if len(s) > max_len else "")
    except Exception as e:
        return "<repr error: %s>" % (e,)

def _make_node(name, val, depth, max_depth, max_children, seen):
    try:
        oid = id(val)
    except Exception:
        oid = None
    if oid is not None and oid in seen:
        return {"name": name, "value": "<cycle>", "kind": "primitive"}
    if depth > max_depth:
        return {"name": name, "value": _safe_repr(val), "kind": "primitive"}
    try:
        if val is None or type(val) in (bool, int, float, str, bytes):
            return {"name": name, "value": _safe_repr(val), "kind": "primitive"}
    except Exception:
        pass
    if type(val) is list:
        if oid is not None:
            seen.add(oid)
        children = []
        for i, item in enumerate(val[:max_children]):
            children.append(_make_node(str(i), item, depth + 1, max_depth, max_children, seen))
        if len(val) > max_children:
            children.append({"name": "...", "value": "%d more" % (len(val) - max_children), "kind": "primitive"})
        if oid is not None:
            seen.discard(oid)
        return {"name": name, "value": _safe_repr(val, 80), "kind": "list", "children": children}
    if type(val) is tuple:
        if oid is not None:
            seen.add(oid)
        children = []
        for i, item in enumerate(val[:max_children]):
            children.append(_make_node(str(i), item, depth + 1, max_depth, max_children, seen))
        if len(val) > max_children:
            children.append({"name": "...", "value": "%d more" % (len(val) - max_children), "kind": "primitive"})
        if oid is not None:
            seen.discard(oid)
        return {"name": name, "value": _safe_repr(val, 80), "kind": "tuple", "children": children}
    if type(val) is dict:
        if oid is not None:
            seen.add(oid)
        children = []
        for i, (k, v) in enumerate(list(val.items())[:max_children]):
            try:
                kstr = str(k)
            except Exception:
                kstr = "<key error>"
            children.append(_make_node(kstr, v, depth + 1, max_depth, max_children, seen))
        if len(val) > max_children:
            children.append({"name": "...", "value": "%d more" % (len(val) - max_children), "kind": "primitive"})
        if oid is not None:
            seen.discard(oid)
        return {"name": name, "value": _safe_repr(val, 80), "kind": "dict", "children": children}
    if type(val) is set:
        if oid is not None:
            seen.add(oid)
        children = []
        for i, item in enumerate(list(val)[:max_children]):
            children.append(_make_node(str(i), item, depth + 1, max_depth, max_children, seen))
        if len(val) > max_children:
            children.append({"name": "...", "value": "%d more" % (len(val) - max_children), "kind": "primitive"})
        if oid is not None:
            seen.discard(oid)
        return {"name": name, "value": _safe_repr(val, 80), "kind": "set", "children": children}
    # Class instance or other object: expose attributes
    try:
        if hasattr(val, "__dict__"):
            if oid is not None:
                seen.add(oid)
            attrs = vars(val)
            children = []
            for i, (k, v) in enumerate(list(attrs.items())[:max_children]):
                if k.startswith("__") and k.endswith("__"):
                    continue
                children.append(_make_node(k, v, depth + 1, max_depth, max_children, seen))
            if len(attrs) > max_children:
                children.append({"name": "...", "value": "%d more" % (len(attrs) - max_children), "kind": "primitive"})
            if oid is not None:
                seen.discard(oid)
            return {"name": name, "value": _safe_repr(val, 80), "kind": "instance", "children": children}
        if hasattr(val, "__slots__"):
            if oid is not None:
                seen.add(oid)
            children = []
            slot_list = list(val.__slots__)[:max_children]
            for k in slot_list:
                try:
                    v = getattr(val, k)
                except Exception as e:
                    v = "<error: %s>" % (e,)
                children.append(_make_node(k, v, depth + 1, max_depth, max_children, seen))
            if len(val.__slots__) > max_children:
                children.append({"name": "...", "value": "%d more" % (len(val.__slots__) - max_children), "kind": "primitive"})
            if oid is not None:
                seen.discard(oid)
            return {"name": name, "value": _safe_repr(val, 80), "kind": "instance", "children": children}
    except Exception as e:
        return {"name": name, "value": "<error: %s>" % (e,), "kind": "primitive"}
    return {"name": name, "value": _safe_repr(val), "kind": "other"}

def build_var_tree(locals_dict, max_depth=4, max_children=64):
    out = {}
    seen = set()
    for k, v in locals_dict.items():
        if k.startswith("__"):
            continue
        node = _make_node(k, v, 0, max_depth, max_children, seen)        
        out[k] = {"id": id(v), "repr_tree": node}
    return out
"""
