import errno
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from palimpsest.lab import LabSupervisor


def late_log_failure_owner(*args):
    """Fail the native log's final fsync after the owner reports completion."""
    from palimpsest import worker
    returned = threading.Event()
    original_fsync = os.fsync

    def complete(config, commands, replies, display, disconnected, stop, progress,
                 final_messages=None):
        os.write(1, b"final native diagnostic\n")
        message = {"version": 1, "type": "closed", "run_id": config["run_id"],
                   "status": "closed", "state": {"phase": "paused", "total_tick": 0}, "receipts": []}
        if final_messages is None:
            replies.put(message)
        else:
            final_messages.append(message)
        returned.set()

    def fsync(fd):
        if os.readlink(f"/proc/self/fd/{fd}").endswith("/stdout.log"):
            if not returned.wait(2.):
                raise RuntimeError("owner did not reach close boundary")
            # Under the old wrapper, the supervisor has already accepted closed
            # and will stop draining replies before this final flush error.
            time.sleep(.15)
            raise OSError(errno.ENOSPC, "injected final log fsync failure")
        original_fsync(fd)

    with patch.object(worker, "_own", complete), patch("palimpsest.evaluate.os.fsync", fsync):
        worker.run_worker(*args)


class WorkerLogCompletion(unittest.TestCase):
    def test_late_native_log_fsync_failure_cannot_report_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supervisor = LabSupervisor(Path(__file__).resolve().parents[1], root / "assets", root / "runs",
                                       worker_target=late_log_failure_owner)
            try:
                identifier = supervisor.start({})
                owner = supervisor.workers[identifier]
                self.assertTrue(owner.done.wait(5.))
                result = supervisor.close(identifier)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["failure"]["type"], "LogLimit")
                self.assertIn("injected final log fsync failure", result["failure"]["message"])
                self.assertEqual((supervisor.path(identifier) / "stdout.log").read_bytes(), b"final native diagnostic\n")
                self.assertFalse(owner.process.is_alive())
            finally:
                supervisor.shutdown()


if __name__ == "__main__":
    unittest.main()
