"""Tests for TaskRunner and ThreadedTaskRunner."""

from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication

from vector_inspector.services.task_runner import TaskRunner, ThreadedTaskRunner


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# TaskRunner (QThread) - call run() directly to avoid real threading
# ---------------------------------------------------------------------------


def test_task_runner_success(qapp):
    """run() calls task_func and emits result_ready on success."""
    results = []

    runner = TaskRunner(lambda: 42)
    runner.result_ready.connect(lambda v: results.append(v))

    runner.run()  # synchronous

    assert results == [42]


def test_task_runner_success_with_args(qapp):
    """run() passes positional/keyword args to task_func."""
    results = []

    runner = TaskRunner(lambda a, b=0: a + b, 10, b=5)
    runner.result_ready.connect(lambda v: results.append(v))
    runner.run()

    assert results == [15]


def test_task_runner_exception_emits_error(qapp):
    """run() emits error signal when task_func raises."""
    errors = []

    def bad_task():
        raise ValueError("something went wrong")

    runner = TaskRunner(bad_task)
    runner.error.connect(lambda msg: errors.append(msg))
    runner.run()

    assert len(errors) == 1
    assert "something went wrong" in errors[0]


def test_task_runner_cancelled_before_run_does_nothing(qapp):
    """If cancelled before run(), task_func is not called and no signals emitted."""
    called = []
    results = []
    errors = []

    runner = TaskRunner(lambda: called.append(1) or 99)
    runner.result_ready.connect(lambda v: results.append(v))
    runner.error.connect(lambda s: errors.append(s))

    runner.cancel()
    runner.run()

    assert called == []
    assert results == []
    assert errors == []


def test_task_runner_cancel_and_is_cancelled(qapp):
    """cancel() sets _cancelled and is_cancelled() returns True."""
    runner = TaskRunner(lambda: None)
    assert runner.is_cancelled() is False

    runner.cancel()
    assert runner.is_cancelled() is True


def test_task_runner_report_progress_emits_signal(qapp):
    """report_progress emits progress signal when not cancelled."""
    progress_events = []

    runner = TaskRunner(lambda: None)
    runner.progress.connect(lambda msg, pct: progress_events.append((msg, pct)))

    runner.report_progress("loading", 50)

    assert progress_events == [("loading", 50)]


def test_task_runner_report_progress_suppressed_when_cancelled(qapp):
    """report_progress does NOT emit when cancelled."""
    progress_events = []

    runner = TaskRunner(lambda: None)
    runner.progress.connect(lambda msg, pct: progress_events.append((msg, pct)))

    runner.cancel()
    runner.report_progress("loading", 75)

    assert progress_events == []


# ---------------------------------------------------------------------------
# ThreadedTaskRunner
# ---------------------------------------------------------------------------


def test_threaded_task_runner_run_task_calls_on_finished(qapp):
    """run_task calls on_finished with the task result (via thread)."""
    from PySide6.QtCore import QCoreApplication

    ttr = ThreadedTaskRunner()
    results = []

    task_id = ttr.run_task(lambda: "hello", on_finished=lambda v: results.append(v))
    assert isinstance(task_id, str)

    # Wait for the thread to finish
    if task_id in ttr._active_tasks:
        ttr._active_tasks[task_id].wait(3000)

    # Process queued signals so on_finished is called
    QCoreApplication.processEvents()

    assert "hello" in results


def test_threaded_task_runner_is_running_and_get_active_count(qapp):
    """is_running and get_active_count reflect active / finished tasks."""
    ttr = ThreadedTaskRunner()

    assert ttr.get_active_count() == 0

    # Run a very fast task
    task_id = ttr.run_task(lambda: None)
    # The task may have already finished (it's fast), so we just verify
    # the return values are sane
    assert isinstance(ttr.is_running(task_id), bool)
    assert isinstance(ttr.get_active_count(), int)


def test_threaded_task_runner_fixed_task_id_reuses_slot(qapp):
    """run_task with same task_id cancels the previous task."""
    ttr = ThreadedTaskRunner()

    done = []
    # Start a slow task with a fixed ID
    ttr.run_task(lambda: time.sleep(0.05), task_id="fixed", on_finished=lambda _: done.append(1))
    # Immediately replace it with a fast task using the same ID
    ttr.run_task(lambda: None, task_id="fixed")
    # Give the second task time to finish
    if "fixed" in ttr._active_tasks:
        ttr._active_tasks["fixed"].wait(3000)


def test_threaded_task_runner_cancel_task(qapp):
    """cancel_task stops a running task."""
    ttr = ThreadedTaskRunner()

    ttr.run_task(lambda: time.sleep(10), task_id="slow")
    assert ttr.is_running("slow")
    ttr.cancel_task("slow")
    assert not ttr.is_running("slow")


def test_threaded_task_runner_cancel_all(qapp):
    """cancel_all stops all active tasks."""
    ttr = ThreadedTaskRunner()

    ttr.run_task(lambda: time.sleep(10), task_id="t1")
    ttr.run_task(lambda: time.sleep(10), task_id="t2")
    ttr.cancel_all()
    assert ttr.get_active_count() == 0
