import errno
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import time
import struct
import unittest
from unittest.mock import patch

from palimpsest.lab import LabSupervisor


class SlowModuleFinalizer:
    def __init__(self):
        self.sleep = time.sleep

    def __del__(self):
        self.sleep(30.)


def module_finalization_owner(*args):
    from palimpsest import worker
    def complete(config, commands, replies, display, disconnected, stop, progress,
                 final_messages=None):
        # Retained until interpreter module cleanup, after all worker work.
        global late_finalizer
        late_finalizer = SlowModuleFinalizer()
        os.write(1, b"durable last diagnostic\n")
        display.put({"type": "sample", "pixels": b"x" * (2 * 1024**2),
                     "state": {"revision": 0, "total_tick": 0}})
        final_messages.append({"version": 1, "type": "closed", "run_id": config["run_id"],
                               "status": "closed", "state": {"revision": 0, "total_tick": 0}})
    with patch.object(worker, '_own', complete):
        worker.run_worker(*args)


def delayed_final_display_owner(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    replies.put({"version": 1, "type": "closed", "run_id": config["run_id"], "status": "closed"})
    # Model a display feeder arriving after the independent reply feeder.
    # The parent observes completion before requesting close and releasing us.
    if not stop.wait(5.):
        raise RuntimeError("close was not requested")
    display.put({"type": "sample", "pixels": b"x" * (2 * 1024**2)})


def truncated_display_owner(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    # The same length-prefix framing used by multiprocessing.Connection.
    os.write(display._writer.fileno(), struct.pack("!i", 2 * 1024**2) + b"x" * 1024)
    os._exit(19)


def check_truncated_display(root, result):
    supervisor = LabSupervisor(Path(__file__).resolve().parents[1], root / "assets", root / "runs",
                               worker_target=truncated_display_owner)
    try:
        identifier = supervisor.start({})
        if not supervisor.workers[identifier].done.wait(3.):
            raise RuntimeError("truncated frame blocked the monitor")
        closed = supervisor.close(identifier)
        result.put((closed["status"], closed["failure"]["type"]))
    finally:
        supervisor.shutdown()


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
    def test_completed_worker_flushes_queues_without_module_finalization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supervisor = LabSupervisor(Path(__file__).resolve().parents[1], root / 'assets', root / 'runs',
                                       worker_target=module_finalization_owner)
            try:
                identifier = supervisor.start({})
                owner = supervisor.workers[identifier]
                result = supervisor.close(identifier)
                self.assertEqual(result['status'], 'closed', result.get('failure'))
                self.assertEqual(owner.process.exitcode, 0)
                self.assertFalse(owner.process.is_alive())
                self.assertTrue(supervisor.thread.is_alive())
                self.assertEqual((supervisor.path(identifier) / 'stdout.log').read_bytes(), b'durable last diagnostic\n')
            finally:
                supervisor.shutdown()

    def test_truncated_display_cannot_hold_monitor_after_producer_exit(self):
        context = multiprocessing.get_context("spawn")
        result = context.Queue()
        with tempfile.TemporaryDirectory() as temporary:
            process = context.Process(target=check_truncated_display, args=(Path(temporary), result))
            try:
                process.start()
                process.join(6.)
                self.assertFalse(process.is_alive(), "dead producer left monitor blocked inside recv_bytes")
                self.assertEqual(process.exitcode, 0)
                self.assertEqual(result.get(timeout=1.), ("failed", "OwnerIPCError"))
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(2.)
                process.close()
                result.close()

    def test_delayed_final_display_is_drained_after_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supervisor = LabSupervisor(Path(__file__).resolve().parents[1], root / "assets", root / "runs",
                                       worker_target=delayed_final_display_owner)
            try:
                identifier = supervisor.start({})
                owner = supervisor.workers[identifier]
                self.assertTrue(owner.done.wait(5.))
                with supervisor.lock:
                    pass  # Finish the monitor's original completion iteration.
                self.assertEqual(supervisor.close(identifier)["status"], "closed")
                self.assertFalse(owner.process.is_alive())
                self.assertEqual(owner.process.exitcode, 0)
                self.assertTrue(supervisor.thread.is_alive())
            finally:
                supervisor.shutdown()

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
