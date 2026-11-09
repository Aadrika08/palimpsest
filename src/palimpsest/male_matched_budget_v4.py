"""Pure v4 matched-budget schedule derivation: the unchanged v3 rule under the v4 domain.

The row rule (Hamilton largest-remainder tails, seeded cyclic remainder segments, resets
at source/sweep/wrap, multi-fragment packing, no padding, no dropped rows) is imported
from the frozen v3 module, whose bytes and behaviour stay untouched. Only the domain
string that seeds remainder starts and labels canonical schedule bytes differs:
``M7-NAV-V4-REGEN-MATCHED-BUDGET-1``.

``derive`` turns the S0z-pinned v4 corpus manifest bytes into every per-arm array the
protocol derives after the pin (N, q/r, allocations, per-source totals, seed starts,
schedule SHA-256s). It is Torch-free, opens nothing, and is byte-identical on replay.
"""
from dataclasses import dataclass
import hashlib
import json

from palimpsest import male_matched_budget as _v3

PROTOCOL_ID = "M7-NAV-V4-REGEN-MATCHED-BUDGET-1"
SCHEDULE_VERSION = "matched-real-row-v1"
DERIVATION_SCHEMA = "m7-navigation-v4-schedule-derivation-1"
DEFAULT_PRESENTATIONS = _v3.DEFAULT_PRESENTATIONS
DEFAULT_ROWS_PER_UPDATE = _v3.DEFAULT_ROWS_PER_UPDATE
OPTIMIZER_UPDATES = DEFAULT_PRESENTATIONS // DEFAULT_ROWS_PER_UPDATE
SEEDS = (10, 11, 12)
ARMS = ("old-corpus", "augmented")
# Lost v2/v3 corpus manifest; never admissible as a v4 pin.
V3_DATA_SHA256 = "47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41"
OLD_TEACHER_SOURCES, RECOVERY_SOURCES, ADVICE_SOURCES, DEV_SOURCES = 8, 2, 12, 4
MAX_RECOVERY_ROWS, MAX_ADVICE_ROWS = 120, 600
ADVICE_ORDER = tuple((scene, learner) for scene in (3100, 3101, 3102, 3103)
                     for learner in (10, 11, 12))
MAX_MANIFEST_BYTES = 4 * 1024**2

SourceIdentity = _v3.SourceIdentity
Fragment = _v3.Fragment
UpdateUnit = _v3.UpdateUnit


@dataclass(frozen=True)
class Schedule(_v3.Schedule):
    """v3 schedule fields; canonical bytes carry the v4 domain string."""

    def canonical_bytes(self):
        payload = json.loads(super().canonical_bytes())
        if payload.get("protocol_id") != _v3.PROTOCOL_ID:
            raise ValueError("v3 canonical schedule layout changed")
        payload["protocol_id"] = PROTOCOL_ID
        return _dumps(payload)


def _dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def remainder_start(seed, source):
    """First eight SHA-256 bytes of domain NUL seed NUL identity, mod source length."""
    payload = (PROTOCOL_ID.encode() + b"\0" + str(seed).encode("ascii") + b"\0" +
               source.identity.encode())
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % source.rows


def build_schedule(sources, seed, presentations=DEFAULT_PRESENTATIONS,
                   rows_per_update=DEFAULT_ROWS_PER_UPDATE):
    """The v3 ``build_schedule`` rule with v4 remainder starts; opens no data."""
    if type(sources) is not tuple or not sources or any(
            type(source) is not SourceIdentity for source in sources):
        raise ValueError("sources must be a nonempty exact SourceIdentity tuple")
    if len({source.identity for source in sources}) != len(sources):
        raise ValueError("source identities must be unique")
    _v3._integer(seed, "seed")
    _v3._integer(presentations, "presentations", positive=True)
    _v3._integer(rows_per_update, "rows_per_update", positive=True)
    if presentations % rows_per_update:
        raise ValueError("presentations must fill exact optimizer updates")
    lengths = tuple(source.rows for source in sources)
    total = sum(lengths)
    sweeps, remainder = divmod(presentations, total)
    allocations = _v3._allocate_remainder(lengths, remainder, total)
    if any(count > length for count, length in zip(allocations, lengths, strict=True)):
        raise ValueError("remainder allocation exceeds its source")
    starts = tuple(remainder_start(seed, source) for source in sources)
    totals = tuple(sweeps * length + count
                   for length, count in zip(lengths, allocations, strict=True))
    fragments = _v3._logical_fragments(sources, sweeps, allocations, starts)
    schedule = Schedule(sources, seed, presentations, rows_per_update, sweeps, remainder,
                        allocations, starts, totals, fragments,
                        _v3._pack(fragments, rows_per_update))
    _v3._validate(schedule)
    return schedule


# --------------------------------------------------------------------------- pinned manifest

def _sources(rows, name):
    if not isinstance(rows, list):
        raise ValueError(f"{name} roster must be a list")
    result = []
    for row in rows:
        if (not isinstance(row, dict) or
                set(row) != {"run_id", "episode", "ticks", "feature_target_sha256"}):
            raise ValueError(f"{name} source identity is not exact")
        result.append(SourceIdentity(row["run_id"], row["episode"],
                                     row["feature_target_sha256"], row["ticks"]))
    return tuple(result)


def load_manifest(raw, expected_sha256):
    """Admit the exact pinned v4 corpus manifest bytes; refuse v3 and unpinned bytes."""
    if not isinstance(raw, bytes) or len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Bounded pinned manifest bytes required")
    _v3._hex(expected_sha256, 64, "pinned manifest sha256")
    if expected_sha256 == V3_DATA_SHA256:
        raise ValueError("Lost v2/v3 corpus 47c4523c... is not a v4 corpus")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Corpus manifest bytes differ from the v4 pin")
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise ValueError("Pinned corpus manifest is not JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Pinned corpus manifest must be an object")
    return value


def admit_rosters(manifest):
    """Structural admission: 8+2 old, +12 advice, 4 shared dev, 0 held-out."""
    if (manifest.get("status") != "prepared-navigation-advice-research-only" or
            manifest.get("labels") != {"old": "unchanged executed targets",
                                       "new": "nav_advice_action"} or
            manifest.get("qualification_claims") != []):
        raise ValueError("Prepared research-only corpus status/labels required")
    arms = manifest.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"old", "augmented"}:
        raise ValueError("Exact old and augmented manifest arms required")
    for arm in arms.values():
        if not isinstance(arm, dict) or set(arm) != {"train", "dev", "held_out"}:
            raise ValueError("Exact train/dev/held_out splits required")
        if arm["held_out"] != []:
            raise ValueError("Training manifest must contain no held-out rows")
    old = _sources(arms["old"]["train"], "old")
    augmented = _sources(arms["augmented"]["train"], "augmented")
    dev = _sources(arms["old"]["dev"], "dev")
    if arms["augmented"]["dev"] != arms["old"]["dev"] or len(dev) != DEV_SOURCES:
        raise ValueError("Exact shared four-source recorded-development roster required")
    if len(old) != OLD_TEACHER_SOURCES + RECOVERY_SOURCES:
        raise ValueError("Old arm must be 8 teacher then 2 recovery sources")
    if len(augmented) != len(old) + ADVICE_SOURCES or augmented[:len(old)] != old:
        raise ValueError("Augmented arm must be the exact old prefix then 12 advice sources")
    if any(source.rows > MAX_RECOVERY_ROWS for source in old[OLD_TEACHER_SOURCES:]):
        raise ValueError("Recovery source exceeds 120 rows")
    if any(source.rows > MAX_ADVICE_ROWS for source in augmented[len(old):]):
        raise ValueError("Advice source exceeds 600 rows")
    advice = manifest.get("new_sources")
    if (not isinstance(advice, list) or len(advice) != ADVICE_SOURCES or
            any(not isinstance(row, dict) for row in advice) or
            [(row.get("scene_seed"), row.get("learner_seed")) for row in advice] !=
            list(ADVICE_ORDER) or
            [row.get("run_id") for row in advice] !=
            [source.run_id for source in augmented[len(old):]]):
        raise ValueError("Advice sources must follow scene 3100..3103 x learner 10,11,12")
    identities = [source.identity for source in augmented + dev]
    if len(set(identities)) != len(identities):
        raise ValueError("Training and development source identities must be unique")
    return {"old-corpus": old, "augmented": augmented, "dev": dev}


def derive(raw, expected_sha256, seeds=SEEDS):
    """Every post-pin array, as a canonical document; pure and replay-identical."""
    rosters = admit_rosters(load_manifest(raw, expected_sha256))
    if type(seeds) is not tuple or not seeds or any(type(seed) is not int for seed in seeds):
        raise ValueError("Exact training seed tuple required")
    arms, schedules = {}, {}
    for arm in ARMS:
        sources = rosters[arm]
        total = sum(source.rows for source in sources)
        q, r = divmod(DEFAULT_PRESENTATIONS, total)
        per_seed = {}
        for seed in seeds:
            schedule = build_schedule(sources, seed)
            schedules[seed, arm] = schedule
            per_seed[str(seed)] = {"remainder_starts": list(schedule.remainder_starts),
                                   "schedule_sha256": schedule.sha256,
                                   "fragments": len(schedule.fragments)}
        reference = schedules[seeds[0], arm]
        arms[arm] = {"N": total, "q": q, "r": r,
                     "source_rows": [source.rows for source in sources],
                     "remainder_allocations": list(reference.remainder_allocations),
                     "per_source_totals": list(reference.source_presentations),
                     "seeds": per_seed}
    for seed in seeds:
        old, augmented = schedules[seed, ARMS[0]], schedules[seed, ARMS[1]]
        if old.remainder_starts != augmented.remainder_starts[:len(old.sources)]:
            raise ValueError("Shared old-source remainder starts differ between arms")
    document = {
        "schema": DERIVATION_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "schedule_version": SCHEDULE_VERSION,
        "data_manifest_sha256": expected_sha256,
        "presentations": DEFAULT_PRESENTATIONS,
        "rows_per_update": DEFAULT_ROWS_PER_UPDATE,
        "optimizer_updates": OPTIMIZER_UPDATES,
        "dev_rows": sum(source.rows for source in rosters["dev"]),
        "arms": arms,
    }
    payload = _dumps(document)
    return {"document": document, "bytes": payload,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "rosters": rosters, "schedules": schedules}
