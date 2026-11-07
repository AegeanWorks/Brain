"""Generation manifest fingerprints for the model seam.

ModelDuck-style provenance, Brain-sized: every backend proposal can be
traced to the exact bytes the model saw. A manifest is a canonical
dict plus its SHA-256 over canonical JSON (sorted keys, compact
separators), covering model identity, checkpoint label, prompt text,
observation, and sampling params. Same inputs always yield the same
manifest; any prompt-set change yields a different one, so
before/after batteries prove they ran the same prompts.

Weights never enter the repo: checkpoint is a label supplied by the
caller (e.g. a GGUF basename or pinned hash recorded outside the
repo), never file bytes.
"""

import hashlib
import json


def canonical(obj):
    """Render canonical JSON: sorted keys, compact separators, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def manifest_for(prompt, observation, model_id="stub", checkpoint="stub",
                 sampling=None):
    """Build the generation manifest for one backend call.

    Returns {"manifest": {...canonical fields...}, "sha256": hex}.
    Deterministic: identical inputs give identical sha256.
    """
    sampling = dict(sampling) if sampling is not None else {}
    manifest = {
        "model_id": str(model_id),
        "checkpoint": str(checkpoint),
        "prompt": str(prompt),
        "observation": _jsonable(observation),
        "sampling": {str(k): sampling[k] for k in sorted(sampling)},
    }
    digest = hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()
    return {"manifest": manifest, "sha256": digest}


def prompt_set_manifest(entries):
    """Hash a battery's manifest list into one prompt-set digest.

    Entries are per-call sha256 strings (or {"sha256": ...} dicts);
    order-independent: sorted before hashing, so reruns compare equal
    regardless of execution order.
    """
    digests = []
    for entry in entries:
        if isinstance(entry, dict):
            digests.append(str(entry.get("sha256", "")))
        else:
            digests.append(str(entry))
    body = canonical({"prompts": sorted(digests)})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _jsonable(value):
    """Convert an observation mapping into canonical JSON-safe data."""
    if isinstance(value, dict):
        return {str(k): _jsonable(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
