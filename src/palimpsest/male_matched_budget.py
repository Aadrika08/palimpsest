"""Pure deterministic row scheduler for the frozen navigation-v3 budget."""
from dataclasses import dataclass
import hashlib
import json
import sys


PROTOCOL_ID = "M7-NAV-V3-MATCHED-BUDGET-1"
DEFAULT_PRESENTATIONS = 46_080
DEFAULT_ROWS_PER_UPDATE = 32
_HEX = frozenset("0123456789abcdef")


def _integer(value, name, *, positive=False):
    minimum = 1 if positive else 0
    if type(value) is not int or value < minimum or value > sys.maxsize:
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be a {qualifier} bounded integer")


def _hex(value, length, name):
    if not isinstance(value, str) or len(value) != length or not set(value) <= _HEX:
        raise ValueError(f"{name} must be {length} lowercase hexadecimal characters")


@dataclass(frozen=True)
class SourceIdentity:
    run_id: str
    episode: int
    feature_target_sha256: str
    rows: int

    def __post_init__(self):
        _hex(self.run_id, 32, "run_id")
        _integer(self.episode, "episode")
        _hex(self.feature_target_sha256, 64, "feature_target_sha256")
        _integer(self.rows, "rows", positive=True)

    @property
    def identity(self):
        return f"{self.run_id}:{self.episode}:{self.feature_target_sha256}"


@dataclass(frozen=True)
class Fragment:
    source_index: int
    start: int
    stop: int
    reset_before: bool

    def __post_init__(self):
        _integer(self.source_index, "source_index")
        _integer(self.start, "fragment start")
        _integer(self.stop, "fragment stop", positive=True)
        if self.stop <= self.start or type(self.reset_before) is not bool:
            raise ValueError("fragment must be a nonempty interval with an exact reset marker")

    @property
    def rows(self):
        return self.stop - self.start


@dataclass(frozen=True)
class UpdateUnit:
    fragments: tuple[Fragment, ...]

    def __post_init__(self):
        if type(self.fragments) is not tuple or not self.fragments or any(
                type(fragment) is not Fragment for fragment in self.fragments):
            raise ValueError("update fragments must be a nonempty exact tuple")

    @property
    def rows(self):
        return sum(fragment.rows for fragment in self.fragments)


@dataclass(frozen=True)
class Schedule:
    sources: tuple[SourceIdentity, ...]
    seed: int
    presentations: int
    rows_per_update: int
    full_sweeps: int
    remainder_rows: int
    remainder_allocations: tuple[int, ...]
    remainder_starts: tuple[int, ...]
    source_presentations: tuple[int, ...]
    fragments: tuple[Fragment, ...]
    updates: tuple[UpdateUnit, ...]

    def canonical_bytes(self):
        def fragment(value):
            return [value.source_index, value.start, value.stop, value.reset_before]
        payload = {
            "version": 1,
            "protocol_id": PROTOCOL_ID,
            "seed": self.seed,
            "presentations": self.presentations,
            "rows_per_update": self.rows_per_update,
            "full_sweeps": self.full_sweeps,
            "remainder_rows": self.remainder_rows,
            "remainder_allocations": list(self.remainder_allocations),
            "remainder_starts": list(self.remainder_starts),
            "source_presentations": list(self.source_presentations),
            "sources": [{"run_id": source.run_id, "episode": source.episode,
                         "feature_target_sha256": source.feature_target_sha256,
                         "rows": source.rows} for source in self.sources],
            "fragments": [fragment(value) for value in self.fragments],
            "updates": [[fragment(value) for value in unit.fragments]
                        for unit in self.updates],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode()

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _allocate_remainder(lengths, remainder, total):
    allocations = [remainder * length // total for length in lengths]
    missing = remainder - sum(allocations)
    order = sorted(range(len(lengths)),
                   key=lambda index: (-((remainder * lengths[index]) % total), index))
    for index in order[:missing]:
        allocations[index] += 1
    return tuple(allocations)


def _start(seed, source):
    payload = (PROTOCOL_ID.encode() + b"\0" + str(seed).encode("ascii") + b"\0" +
               source.identity.encode())
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % source.rows


def _logical_fragments(sources, sweeps, allocations, starts):
    fragments = []
    for _ in range(sweeps):
        fragments.extend(Fragment(index, 0, source.rows, True)
                         for index, source in enumerate(sources))
    for index, (source, count, start) in enumerate(zip(sources, allocations, starts, strict=True)):
        if not count:
            continue
        stop = start + count
        if stop <= source.rows:
            fragments.append(Fragment(index, start, stop, True))
        else:
            fragments.append(Fragment(index, start, source.rows, True))
            fragments.append(Fragment(index, 0, stop - source.rows, True))
    return tuple(fragments)


def _pack(fragments, rows_per_update):
    updates, current, remaining = [], [], rows_per_update
    for fragment in fragments:
        cursor, first = fragment.start, True
        while cursor < fragment.stop:
            count = min(fragment.stop - cursor, remaining)
            current.append(Fragment(fragment.source_index, cursor, cursor + count,
                                    fragment.reset_before if first else False))
            cursor += count
            remaining -= count
            first = False
            if not remaining:
                updates.append(UpdateUnit(tuple(current)))
                current, remaining = [], rows_per_update
    if current or remaining != rows_per_update:
        raise ValueError("presentations do not fill exact optimizer updates")
    return tuple(updates)


def _validate(schedule):
    if sum(fragment.rows for fragment in schedule.fragments) != schedule.presentations:
        raise ValueError("logical fragments do not cover the presentation budget")
    logical = [0] * len(schedule.sources)
    for fragment in schedule.fragments:
        if fragment.stop > schedule.sources[fragment.source_index].rows:
            raise ValueError("logical fragment exceeds its declared source")
        logical[fragment.source_index] += fragment.rows
    if tuple(logical) != schedule.source_presentations:
        raise ValueError("logical fragments differ from source presentation totals")
    packed = [0] * len(schedule.sources)
    if len(schedule.updates) != schedule.presentations // schedule.rows_per_update:
        raise ValueError("optimizer update count differs from the presentation budget")
    for update in schedule.updates:
        if update.rows != schedule.rows_per_update:
            raise ValueError("optimizer update does not contain exact real rows")
        for fragment in update.fragments:
            if fragment.stop > schedule.sources[fragment.source_index].rows:
                raise ValueError("packed fragment exceeds its declared source")
            packed[fragment.source_index] += fragment.rows
    if packed != logical:
        raise ValueError("packed fragments differ from logical fragments")


def build_schedule(sources: tuple[SourceIdentity, ...], seed: int,
                   presentations: int = DEFAULT_PRESENTATIONS,
                   rows_per_update: int = DEFAULT_ROWS_PER_UPDATE) -> Schedule:
    """Build the frozen deterministic real-row schedule without opening data."""
    if type(sources) is not tuple or not sources or any(
            type(source) is not SourceIdentity for source in sources):
        raise ValueError("sources must be a nonempty exact SourceIdentity tuple")
    if len({source.identity for source in sources}) != len(sources):
        raise ValueError("source identities must be unique")
    _integer(seed, "seed")
    _integer(presentations, "presentations", positive=True)
    _integer(rows_per_update, "rows_per_update", positive=True)
    if presentations % rows_per_update:
        raise ValueError("presentations must fill exact optimizer updates")
    lengths = tuple(source.rows for source in sources)
    total = sum(lengths)
    if total > sys.maxsize:
        raise ValueError("corpus row count exceeds the bounded integer range")
    sweeps, remainder = divmod(presentations, total)
    allocations = _allocate_remainder(lengths, remainder, total)
    if any(count > length for count, length in zip(allocations, lengths, strict=True)):
        raise ValueError("remainder allocation exceeds its source")
    starts = tuple(_start(seed, source) for source in sources)
    source_presentations = tuple(sweeps * length + count
                                 for length, count in zip(lengths, allocations, strict=True))
    fragments = _logical_fragments(sources, sweeps, allocations, starts)
    schedule = Schedule(sources, seed, presentations, rows_per_update, sweeps, remainder,
                        allocations, starts, source_presentations, fragments,
                        _pack(fragments, rows_per_update))
    _validate(schedule)
    return schedule
