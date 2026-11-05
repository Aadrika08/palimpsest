"""Benchmark-only sink: drops records; never a replay or reproducibility source."""
from pathlib import Path


class NullWriter:
    def __init__(self, path, manifest, max_bytes=None, *, storage_budget=None):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        # Engine.application_state hashes this empty stream outside timed ticks.
        (self.path / 'events.jsonl').touch(exist_ok=False)
        self.manifest = {**manifest, 'status': 'running', 'benchmark_null_writer': True}
        self.storage_budget = None
        self._closed = self._finished = False

    def _active(self):
        if self._closed or self._finished:
            raise ValueError('null writer is closed or finished')

    def event(self, kind, **data):
        self._active()

    def tick(self, episode, tick, **arrays):
        self._active()

    def flush(self):
        self._active()

    def background_stats(self):
        return None

    def finish(self, summary, status='completed'):
        self._active()
        self.manifest.update(summary=summary, status=status)
        self._finished = True

    def close(self):
        self._closed = True
