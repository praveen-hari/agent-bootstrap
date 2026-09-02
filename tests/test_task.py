#!/usr/bin/env python3
"""Unit tests for scripts/task.py

Covers the stage machine, artifact enforcement, and all guard logic.
Runs with plain: python3 tests/test_task.py
No external dependencies beyond the stdlib.
"""

import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

# Ensure scripts/ is importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scripts.task as task


# ── Test Helpers ──────────────────────────────────────────────────────


def make_env(index_data, task_files=None, gates_content=None, evidence=None):
    """Create an isolated temp environment and point task module at it."""
    tmp = tempfile.mkdtemp()
    tasks_dir = os.path.join(tmp, "tasks")
    os.makedirs(tasks_dir)

    with open(os.path.join(tasks_dir, "index.json"), "w") as f:
        json.dump(index_data, f, indent=2)

    if task_files:
        for name, content in task_files.items():
            with open(os.path.join(tasks_dir, name), "w") as f:
                f.write(content)

    if gates_content:
        with open(os.path.join(tmp, "gates.yaml"), "w") as f:
            f.write(gates_content)

    if evidence:
        # evidence = {task_id: {"verdict": "pass", ...}}
        for task_id, summary in evidence.items():
            ev_dir = os.path.join(tmp, "evidence", task_id)
            os.makedirs(ev_dir, exist_ok=True)
            with open(os.path.join(ev_dir, "gate-summary.json"), "w") as f:
                json.dump(summary, f)

    task.TASKS_DIR = tasks_dir
    task.INDEX_FILE = os.path.join(tasks_dir, "index.json")
    task.EVIDENCE_DIR = os.path.join(tmp, "evidence")
    task.LOCK_FILE = os.path.join(tmp, "harness-lock.json")
    task.GATES_FILE = os.path.join(tmp, "gates.yaml")
    importlib.reload(task)  # reset module-level state
    task.TASKS_DIR = tasks_dir
    task.INDEX_FILE = os.path.join(tasks_dir, "index.json")
    task.EVIDENCE_DIR = os.path.join(tmp, "evidence")
    task.LOCK_FILE = os.path.join(tmp, "harness-lock.json")
    task.GATES_FILE = os.path.join(tmp, "gates.yaml")
    return tmp


def capture(fn):
    """Run fn(), capturing stdout. Returns output string."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


def active_task(index_data=None):
    """Return a minimal active task record."""
    return {"id": "T-001", "title": "Test task", "status": "active",
            "stage": "SPEC", "needs": []}


# ── check_artifact ────────────────────────────────────────────────────


class TestCheckArtifact(unittest.TestCase):

    def setUp(self):
        make_env([active_task()])

    def _write(self, content):
        path = os.path.join(task.TASKS_DIR, "T-001.md")
        with open(path, "w") as f:
            f.write(content)

    # Missing file
    def test_missing_file_rejected(self):
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertFalse(ok)
        self.assertIn("does not exist", msg)

    # Header present but no body
    def test_empty_section_rejected(self):
        self._write("# T\n\n## What\n\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertFalse(ok)
        self.assertIn("empty", msg)

    # Whitespace-only body
    def test_whitespace_only_body_rejected(self):
        self._write("# T\n\n## What\n\n   \n\t\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertFalse(ok)

    # Windows CRLF
    def test_crlf_line_endings_accepted(self):
        self._write("# T\r\n\r\n## What\r\n\r\nacceptance criteria here\r\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertTrue(ok, msg)

    # Real content passes
    def test_real_content_accepted(self):
        self._write("# T\n\n## What\n\nThe system returns 400 on bad input.\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertTrue(ok, msg)

    # Pattern not required (None)
    def test_none_pattern_always_passes(self):
        ok, _ = task.check_artifact("T-001", None)
        self.assertTrue(ok)

    # Empty checkbox stubs rejected
    def test_empty_checkbox_stubs_rejected(self):
        self._write("# T\n\n## Plan\n\n- [ ] \n- [ ] \n")
        ok, msg = task.check_artifact("T-001", r"## Plan")
        self.assertFalse(ok)
        self.assertIn("checkbox", msg)

    # Checkboxes with titles accepted
    def test_checkboxes_with_titles_accepted(self):
        self._write("# T\n\n## Plan\n\n- [ ] Write the login endpoint\n- [ ] Add tests\n")
        ok, msg = task.check_artifact("T-001", r"## Plan")
        self.assertTrue(ok, msg)

    # Duplicate header — first one is empty, second has content.
    # The regex matches the FIRST occurrence; its body runs until the next ##
    # heading (which is the second ## What), so it is correctly seen as empty.
    # This is the right behaviour: an empty ## What is always rejected.
    def test_duplicate_header_first_empty_is_rejected(self):
        self._write("# T\n\n## What\n\n## What\n\ncriteria here\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertFalse(ok, "first ## What is empty — should be rejected")

    # Section body stops at next ## heading
    def test_body_bounded_by_next_heading(self):
        # ## What has no content before ## Plan starts
        self._write("# T\n\n## What\n\n## Plan\n\nsome plan\n")
        ok, msg = task.check_artifact("T-001", r"## What")
        self.assertFalse(ok)

    # ## Review with content
    def test_review_section_with_content(self):
        self._write("# T\n\n## Review\n\nNo issues found.\n")
        ok, msg = task.check_artifact("T-001", r"## Review")
        self.assertTrue(ok, msg)

    # ## Log with content
    def test_log_section_with_content(self):
        self._write("# T\n\n## Log\n\nDecided to use POST not PUT because...\n")
        ok, msg = task.check_artifact("T-001", r"## Log")
        self.assertTrue(ok, msg)


# ── cmd_stage (read) ──────────────────────────────────────────────────


class TestCmdStageRead(unittest.TestCase):

    def test_spec_stage_shows_skill(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "SPEC", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("spec.md", out)
        self.assertIn("SPEC", out)
        self.assertIn("1/6", out)

    def test_plan_stage_shows_plan_skill(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "PLAN", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("plan.md", out)
        self.assertIn("2/6", out)

    def test_build_stage_shows_tdd_skill(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "BUILD", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("tdd.md", out)

    def test_verify_stage_shows_debugging_skill(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "VERIFY", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("debugging.md", out)

    def test_review_stage_shows_review_skill(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "REVIEW", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("review.md", out)

    def test_learn_stage_has_no_skill_file(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "LEARN", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("LEARN", out)
        self.assertNotIn("SKILL:", out)

    def test_missing_stage_field_defaults_to_spec(self):
        # Legacy task with no stage field
        make_env([{"id": "T-001", "title": "T", "status": "active", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("SPEC", out)

    def test_corrupt_stage_name_prints_unknown(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "TYPO_STAGE", "needs": []}])
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertTrue("unknown" in out.lower() or "check task index" in out.lower())

    def test_no_active_task_exits_1(self):
        make_env([{"id": "T-001", "title": "T", "status": "todo",
                   "stage": "SPEC", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_stage(task.load_index(), advance=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_artifact_present_shows_checkmark(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\ncriteria here\n"}
        )
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("✅", out)

    def test_artifact_missing_shows_cross(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\n"}
        )
        out = capture(lambda: task.cmd_stage(task.load_index(), advance=False))
        self.assertIn("❌", out)


# ── cmd_stage (advance) ───────────────────────────────────────────────


class TestCmdStageAdvance(unittest.TestCase):

    def test_advance_spec_to_plan_with_artifact(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\nreal criteria\n"}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["stage"], "PLAN")

    def test_advance_blocked_without_artifact(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "SPEC", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_stage(task.load_index(), advance=True)
        self.assertEqual(ctx.exception.code, 1)

    def test_advance_blocked_with_empty_section(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\n"}
        )
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_stage(task.load_index(), advance=True)
        self.assertEqual(ctx.exception.code, 1)

    def test_advance_plan_to_build_with_artifact(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "PLAN", "needs": []}],
            {"T-001.md": "# T\n\n## Plan\n\n- [ ] Write login endpoint\n"}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["stage"], "BUILD")

    def test_advance_build_to_verify_no_artifact_required(self):
        # BUILD has no artifact check — advance always succeeds
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "BUILD", "needs": []}])
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["stage"], "VERIFY")

    def test_advance_verify_blocked_without_evidence(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "VERIFY", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_stage(task.load_index(), advance=True)
        self.assertEqual(ctx.exception.code, 1)

    def test_advance_verify_to_review_with_passing_evidence(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "VERIFY", "needs": []}],
            evidence={"T-001": {"verdict": "pass", "gates": [], "commit": None}}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["stage"], "REVIEW")

    def test_advance_review_to_learn_with_artifact(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "REVIEW", "needs": []}],
            {"T-001.md": "# T\n\n## Review\n\nNo issues found.\n"}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["stage"], "LEARN")

    def test_advance_from_learn_prints_done_message(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "LEARN", "needs": []}],
            {"T-001.md": "# T\n\n## Log\n\nDecisions and rationale.\n"}
        )
        tasks = task.load_index()
        out = capture(lambda: task.cmd_stage(tasks, advance=True))
        self.assertIn("final stage", out.lower())
        self.assertIn("done", out.lower())

    def test_double_advance_without_artifact_blocked(self):
        # First advance: SPEC → PLAN (with artifact)
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\nreal criteria\n"}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        # Second advance: PLAN → BUILD — no ## Plan written yet
        tasks = task.load_index()
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_stage(tasks, advance=True)
        self.assertEqual(ctx.exception.code, 1)

    def test_advance_persists_stage_to_disk(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\nreal criteria\n"}
        )
        tasks = task.load_index()
        capture(lambda: task.cmd_stage(tasks, advance=True))
        # Read raw JSON to confirm it's on disk, not just in memory
        with open(task.INDEX_FILE) as f:
            raw = json.load(f)
        self.assertEqual(raw[0]["stage"], "PLAN")


# ── cmd_done stage guard ──────────────────────────────────────────────


class TestCmdDoneStageGuard(unittest.TestCase):

    def test_done_blocked_at_spec_no_gates(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "SPEC", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_done(task.load_index(), skip_gates=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_done_blocked_at_plan_no_gates(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "PLAN", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_done(task.load_index(), skip_gates=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_done_blocked_at_build_no_gates(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "BUILD", "needs": []}])
        with self.assertRaises(SystemExit) as ctx:
            task.cmd_done(task.load_index(), skip_gates=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_done_allowed_at_learn_no_gates(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "LEARN", "needs": []}])
        capture(lambda: task.cmd_done(task.load_index(), skip_gates=False))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["status"], "done")

    def test_done_skip_gates_bypasses_stage_guard(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "BUILD", "needs": []}])
        capture(lambda: task.cmd_done(task.load_index(), skip_gates=True))
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001")["status"], "done")

    def test_done_error_message_names_current_stage(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "REVIEW", "needs": []}])
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                task.cmd_done(task.load_index(), skip_gates=False)
        except SystemExit:
            pass
        self.assertIn("REVIEW", buf.getvalue())


# ── cmd_next stage persistence ────────────────────────────────────────


class TestCmdNextStage(unittest.TestCase):

    def test_next_prints_stage_instruction_on_first_pick(self):
        make_env([{"id": "T-001", "title": "T", "status": "todo",
                   "stage": "SPEC", "needs": []}])
        out = capture(lambda: task.cmd_next(task.load_index()))
        self.assertIn("STAGE:", out)
        self.assertIn("spec.md", out)

    def test_next_reprints_stage_on_resume(self):
        # Already active — task next should reprint stage, not just "ACTIVE:"
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "PLAN", "needs": []}],
            {"T-001.md": "# T\n\n## What\n\ncriteria\n"}
        )
        out = capture(lambda: task.cmd_next(task.load_index()))
        self.assertIn("STAGE:", out)
        self.assertIn("PLAN", out)
        self.assertIn("plan.md", out)

    def test_next_sets_stage_spec_on_new_task_without_stage_field(self):
        # Legacy task — no stage field at all
        make_env([{"id": "T-001", "title": "T", "status": "todo", "needs": []}])
        capture(lambda: task.cmd_next(task.load_index()))
        reloaded = task.load_index()
        t = task.get_by_id(reloaded, "T-001")
        self.assertEqual(t.get("stage"), "SPEC")

    def test_next_persists_stage_spec_to_disk_for_new_task(self):
        make_env([{"id": "T-001", "title": "T", "status": "todo",
                   "stage": "SPEC", "needs": []}])
        capture(lambda: task.cmd_next(task.load_index()))
        with open(task.INDEX_FILE) as f:
            raw = json.load(f)
        self.assertEqual(raw[0].get("stage"), "SPEC")

    def test_next_dependent_task_gets_spec_stage_when_dependency_has_no_stage(self):
        # T-001 done with no stage field (legacy), T-002 should start at SPEC
        make_env([
            {"id": "T-001", "title": "Done", "status": "done", "needs": []},
            {"id": "T-002", "title": "Next", "status": "todo",
             "stage": "SPEC", "needs": ["T-001"]}
        ])
        capture(lambda: task.cmd_next(task.load_index()))
        reloaded = task.load_index()
        t2 = task.get_by_id(reloaded, "T-002")
        self.assertEqual(t2.get("stage"), "SPEC")
        self.assertEqual(t2["status"], "active")

    def test_next_second_task_starts_at_spec_after_first_done(self):
        make_env([
            {"id": "T-001", "title": "Done", "status": "done",
             "stage": "LEARN", "needs": []},
            {"id": "T-002", "title": "Next", "status": "todo",
             "stage": "SPEC", "needs": []}
        ])
        out = capture(lambda: task.cmd_next(task.load_index()))
        reloaded = task.load_index()
        t2 = task.get_by_id(reloaded, "T-002")
        self.assertEqual(t2["status"], "active")
        self.assertEqual(t2.get("stage"), "SPEC")


# ── block/unblock stage preservation ─────────────────────────────────


class TestBlockUnblockStage(unittest.TestCase):

    def test_stage_preserved_after_block(self):
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "PLAN", "needs": []}])
        tasks = task.load_index()
        capture(lambda: task.cmd_block(tasks, "need more info"))
        reloaded = task.load_index()
        t = task.get_by_id(reloaded, "T-001")
        self.assertEqual(t["status"], "blocked")
        self.assertEqual(t.get("stage"), "PLAN")

    def test_stage_preserved_after_unblock(self):
        make_env([{"id": "T-001", "title": "T", "status": "blocked",
                   "stage": "PLAN", "needs": []}])
        tasks = task.load_index()
        capture(lambda: task.cmd_unblock(tasks, "T-001"))
        reloaded = task.load_index()
        t = task.get_by_id(reloaded, "T-001")
        self.assertEqual(t["status"], "todo")
        self.assertEqual(t.get("stage"), "PLAN")

    def test_stage_preserved_after_rollback_simulation(self):
        # Simulate rollback resetting status to todo but keeping stage
        make_env([{"id": "T-001", "title": "T", "status": "active",
                   "stage": "BUILD", "needs": [], "baseSha": "abc123"}])
        tasks = task.load_index()
        t = task.get_by_id(tasks, "T-001")
        t["status"] = "todo"
        task.save_index(tasks)
        reloaded = task.load_index()
        self.assertEqual(task.get_by_id(reloaded, "T-001").get("stage"), "BUILD")


# ── cmd_add stage initialisation ─────────────────────────────────────


class TestCmdAdd(unittest.TestCase):

    def test_add_task_gets_stage_spec(self):
        make_env([])
        tasks = task.load_index()
        capture(lambda: task.cmd_add(tasks, "New feature"))
        reloaded = task.load_index()
        self.assertEqual(reloaded[0].get("stage"), "SPEC")

    def test_add_backlog_task_gets_stage_spec(self):
        make_env([])
        tasks = task.load_index()
        capture(lambda: task.cmd_add(tasks, "Future idea", backlog=True))
        reloaded = task.load_index()
        self.assertEqual(reloaded[0].get("stage"), "SPEC")


# ── Full stage sequence integration ──────────────────────────────────


class TestFullStageSequence(unittest.TestCase):
    """Walk SPEC → PLAN → BUILD → REVIEW → LEARN with correct artifacts."""

    def test_full_sequence_spec_to_learn(self):
        make_env(
            [{"id": "T-001", "title": "T", "status": "active",
              "stage": "SPEC", "needs": []}],
            {"T-001.md": "# T\n\n"}
        )

        task_file = os.path.join(task.TASKS_DIR, "T-001.md")

        def write(content):
            with open(task_file, "w") as f:
                f.write(content)

        # SPEC: write ## What, advance to PLAN
        write("# T\n\n## What\n\nThe system returns 400 on bad input.\n")
        capture(lambda: task.cmd_stage(task.load_index(), advance=True))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["stage"], "PLAN")

        # PLAN: write ## Plan, advance to BUILD
        write("# T\n\n## What\n\ncriteria\n\n## Plan\n\n- [ ] Write test\n- [ ] Implement\n")
        capture(lambda: task.cmd_stage(task.load_index(), advance=True))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["stage"], "BUILD")

        # BUILD: no artifact needed, advance to VERIFY
        capture(lambda: task.cmd_stage(task.load_index(), advance=True))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["stage"], "VERIFY")

        # VERIFY: needs passing evidence — inject it
        ev_dir = os.path.join(task.EVIDENCE_DIR, "T-001")
        os.makedirs(ev_dir, exist_ok=True)
        with open(os.path.join(ev_dir, "gate-summary.json"), "w") as f:
            json.dump({"verdict": "pass", "gates": [], "commit": None}, f)
        capture(lambda: task.cmd_stage(task.load_index(), advance=True))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["stage"], "REVIEW")

        # REVIEW: write ## Review, advance to LEARN
        write("# T\n\n## What\n\ncriteria\n\n## Plan\n\n- [ ] step\n\n## Review\n\nNo issues.\n")
        capture(lambda: task.cmd_stage(task.load_index(), advance=True))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["stage"], "LEARN")

        # LEARN: write ## Log, then done
        write("# T\n\n## What\n\nc\n\n## Plan\n\n- [ ] s\n\n## Review\n\nok\n\n## Log\n\nDecisions made.\n")
        capture(lambda: task.cmd_done(task.load_index(), skip_gates=False))
        self.assertEqual(task.get_by_id(task.load_index(), "T-001")["status"], "done")


if __name__ == "__main__":
    unittest.main(verbosity=2)
