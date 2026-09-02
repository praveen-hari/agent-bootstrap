#!/usr/bin/env python3
"""Task manager for agent harness loop.

Manages task state in index.json so the agent never edits JSON directly.
Agent creates task content in markdown files. This script manages status transitions.

Usage:
    python3 .codestudio/task.py next
    python3 .codestudio/task.py verify
    python3 .codestudio/task.py done [--skip-gates]
    python3 .codestudio/task.py block "reason"
    python3 .codestudio/task.py unblock T-003
    python3 .codestudio/task.py review
    python3 .codestudio/task.py approve
    python3 .codestudio/task.py reject
    python3 .codestudio/task.py add "title" [--needs T-001] [--backlog]
    python3 .codestudio/task.py defer T-003 "reason"
    python3 .codestudio/task.py rollback T-003 [--force]
    python3 .codestudio/task.py stage
    python3 .codestudio/task.py stage advance
    python3 .codestudio/task.py status
    python3 .codestudio/task.py list [--status]
    python3 .codestudio/task.py info T-XXX
    python3 .codestudio/task.py archive
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

try:
    import yaml
except ImportError:
    yaml = None

# Default gate timeout in seconds (overridable per-gate in gates.yaml)
DEFAULT_GATE_TIMEOUT = 300
# Coverage report file patterns to scan when stdout parsing fails
COVERAGE_FILE_PATTERNS = [
    "**/coverage-summary.json",
    "**/coverage-final.json",
    "**/coverage.cobertura.xml",
    "**/cobertura-coverage.xml",
    "**/lcov.info",
    "**/coverage.json",
    "**/cover.out",
]

CODESTUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(CODESTUDIO_DIR, "tasks")
INDEX_FILE = os.path.join(TASKS_DIR, "index.json")
ARCHIVE_DIR = os.path.join(CODESTUDIO_DIR, "archive")
EVIDENCE_DIR = os.path.join(CODESTUDIO_DIR, "evidence")
LOCK_FILE = os.path.join(CODESTUDIO_DIR, "harness-lock.json")
GATES_FILE = os.path.join(CODESTUDIO_DIR, "gates.yaml")
CONTEXT_FILE = os.path.join(CODESTUDIO_DIR, "project-context.md")


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE, "r") as f:
        return json.load(f)


def save_index(tasks):
    os.makedirs(TASKS_DIR, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(tasks, f, indent=2)
        f.write("\n")


def next_id(tasks):
    if not tasks:
        return "T-001"
    max_num = 0
    for t in tasks:
        try:
            num = int(t["id"].split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    return f"T-{max_num + 1:03d}"


def get_active(tasks):
    for t in tasks:
        if t["status"] == "active":
            return t
    return None


def get_by_id(tasks, task_id):
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


# ── Evidence Gates ────────────────────────────────────────────────────


def git_head():
    """Get current git HEAD commit hash, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def parse_gates():
    """Parse gates from gates.yaml (preferred) or fall back to project-context.md markdown."""
    # Preferred: structured YAML file
    if os.path.exists(GATES_FILE):
        return _parse_gates_yaml()
    # Legacy fallback: regex on project-context.md ## Gates section
    return _parse_gates_markdown()


def _parse_gates_yaml():
    """Parse gates from .codestudio/gates.yaml."""
    if yaml is None:
        print("ERROR: gates.yaml exists but PyYAML is not installed.")
        print("Install with: pip install pyyaml")
        print()
        print("Without PyYAML, gate verification cannot run and tasks cannot be")
        print("marked done. This is intentional — silent degradation is not allowed.")
        sys.exit(1)
    try:
        with open(GATES_FILE, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse {GATES_FILE}: {e}")
        sys.exit(1)
    if not data or "gates" not in data:
        return []
    gates = []
    errors = []
    for i, entry in enumerate(data["gates"]):
        if not isinstance(entry, dict):
            errors.append(f"  Entry {i+1}: not a dict — {entry}")
            continue
        # Validate required fields
        missing = [k for k in ("id", "command", "type", "threshold") if k not in entry]
        if missing:
            errors.append(f"  Entry {i+1}: missing {missing} — {entry.get('id', '?')}")
            continue
        # Validate type
        valid_types = ("exit-code", "coverage", "audit")
        gate_type = str(entry["type"])
        if gate_type not in valid_types:
            errors.append(f"  Gate '{entry['id']}': unknown type '{gate_type}' (expected: {', '.join(valid_types)})")
            continue
        # Parse threshold robustly
        try:
            threshold_val = float(entry["threshold"])
        except (ValueError, TypeError):
            errors.append(f"  Gate '{entry['id']}': threshold must be numeric, got '{entry['threshold']}'")
            continue
        gate = {
            "id": str(entry["id"]),
            "command": str(entry["command"]),
            "type": gate_type,
            "threshold_desc": str(entry["threshold"]),
            "threshold_value": threshold_val,
            "ratchet": bool(entry.get("ratchet", False)),
            "timeout": int(entry.get("timeout", DEFAULT_GATE_TIMEOUT)),
        }
        gates.append(gate)
    if errors:
        print(f"WARNING: {len(errors)} gate entries had issues and were skipped:")
        for e in errors:
            print(e)
    if not gates and data.get("gates"):
        print("ERROR: All gate entries are invalid. Fix gates.yaml before proceeding.")
        sys.exit(1)
    return gates


def _parse_gates_markdown():
    """Legacy: parse gates from project-context.md's ## Gates section."""
    if not os.path.exists(CONTEXT_FILE):
        return []
    with open(CONTEXT_FILE, "r") as f:
        content = f.read()
    match = re.search(r'^## Gates\s*\n(.*?)(?=^## |\Z)', content, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    gates_text = match.group(1)
    gates = []
    for m in re.finditer(
        r'^\d+\.\s+\*\*(\S+)\*\*.*?`([^`]+)`.*?(?:type:\s*(\S+),\s*)?threshold:\s*(.+?)(?:\s*\(ratchet\))?\s*$',
        gates_text, re.MULTILINE
    ):
        gate = {
            "id": m.group(1),
            "command": m.group(2),
            "type": m.group(3) if m.group(3) else "exit-code",
            "threshold_desc": m.group(4).strip(),
            "ratchet": "(ratchet)" in m.group(0)
        }
        try:
            gate["threshold_value"] = float(re.search(r'[\d.]+', gate["threshold_desc"]).group())
        except (AttributeError, ValueError):
            gate["threshold_value"] = 0
        gates.append(gate)
    if gates:
        print("NOTE: Using legacy markdown gates from project-context.md.")
        print("      Consider migrating to .codestudio/gates.yaml for reliability.")
    return gates


def load_lock():
    """Load harness-lock.json."""
    if not os.path.exists(LOCK_FILE):
        return {"ratchetFloors": {}}
    with open(LOCK_FILE, "r") as f:
        return json.load(f)


def save_lock(lock):
    """Save harness-lock.json."""
    with open(LOCK_FILE, "w") as f:
        json.dump(lock, f, indent=2)
        f.write("\n")


def parse_coverage(output):
    """Extract coverage percentage from stdout/stderr output."""
    # Try JSON summary format (jest --coverageReporters=json-summary, c8)
    try:
        json_match = re.search(r'\{[\s\S]*"total"[\s\S]*\}', output)
        if json_match:
            data = json.loads(json_match.group())
            if "total" in data and "lines" in data["total"]:
                return data["total"]["lines"].get("pct", 0)
    except (json.JSONDecodeError, KeyError):
        pass
    # Try text format: "Lines   : 85.5%" or "TOTAL ... 85%"
    m = re.search(r'(?:lines|line rate|total).*?([\d.]+)\s*%', output, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Try Cobertura XML inline: line-rate="0.85"
    m = re.search(r'line-rate="([\d.]+)"', output)
    if m:
        return float(m.group(1)) * 100
    # Try Go cover format: "coverage: 85.5% of statements"
    m = re.search(r'coverage:\s*([\d.]+)%', output)
    if m:
        return float(m.group(1))
    return None


def parse_coverage_from_files():
    """Scan for coverage report files on disk when stdout parsing fails.

    Many tools (coverlet, c8, jest) write reports to files rather than stdout.
    This function finds the most recent coverage report and extracts the value.
    """
    for pattern in COVERAGE_FILE_PATTERNS:
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            continue
        # Use the most recently modified file
        latest = max(matches, key=os.path.getmtime)
        try:
            with open(latest, "r") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            continue
        # JSON-based reports (coverage-summary.json, coverage-final.json)
        if latest.endswith(".json"):
            try:
                data = json.loads(content)
                # jest/c8 coverage-summary.json format
                if "total" in data and "lines" in data["total"]:
                    return data["total"]["lines"].get("pct", 0)
                # coverage-final.json (aggregate ourselves)
                if all(isinstance(v, dict) for v in data.values()):
                    total_stmts = total_covered = 0
                    for file_cov in data.values():
                        s = file_cov.get("s", {})
                        total_stmts += len(s)
                        total_covered += sum(1 for v in s.values() if v > 0)
                    if total_stmts > 0:
                        return round(total_covered / total_stmts * 100, 2)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        # Cobertura XML (coverlet, many CI tools)
        elif latest.endswith(".xml"):
            m = re.search(r'line-rate="([\d.]+)"', content)
            if m:
                return float(m.group(1)) * 100
        # LCOV format
        elif latest.endswith(".info"):
            lf = lh = 0
            for line in content.split("\n"):
                if line.startswith("LF:"):
                    lf += int(line[3:])
                elif line.startswith("LH:"):
                    lh += int(line[3:])
            if lf > 0:
                return round(lh / lf * 100, 2)
        # Go cover.out format
        elif latest.endswith(".out"):
            total = covered = 0
            for line in content.split("\n"):
                m_go = re.match(r'.+:[\d.]+,[\d.]+ (\d+) (\d+)', line)
                if m_go:
                    stmts = int(m_go.group(1))
                    count = int(m_go.group(2))
                    total += stmts
                    if count > 0:
                        covered += stmts
            if total > 0:
                return round(covered / total * 100, 2)
    return None


def get_diff_changed_lines(base_sha):
    """Get set of (file, line) tuples for lines changed since base_sha.
    
    This enables diff-scoped coverage: only measure coverage of lines
    this task changed, not the entire codebase. Makes coverage gates
    enforceable on brownfield repos from day one.
    """
    if not base_sha:
        return None
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", f"{base_sha}..HEAD"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    changed = set()
    current_file = None
    for line in result.stdout.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@ ") and current_file:
            # Parse hunk header: @@ -old,count +new,count @@
            m = re.search(r'\+(\d+)(?:,(\d+))?', line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) else 1
                for i in range(start, start + count):
                    changed.add((current_file, i))
    return changed if changed else None


def parse_diff_coverage(output, base_sha):
    """Calculate coverage only for lines changed since base_sha.
    
    Returns diffLineRate (0.0-1.0) or None if unable to compute.
    This is the single most important feature for brownfield repos:
    global coverage at 4% is unenforceable. Diff coverage at 80% is
    enforceable from day one because it only concerns code just written.
    """
    changed_lines = get_diff_changed_lines(base_sha)
    if not changed_lines:
        return None

    # Try to parse coverage from files on disk
    covered_lines = set()
    for pattern in COVERAGE_FILE_PATTERNS:
        matches = glob.glob(pattern, recursive=True)
        for filepath in matches:
            try:
                with open(filepath, "r") as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue
            # JSON format (jest/c8 coverage-final.json)
            if filepath.endswith(".json"):
                try:
                    data = json.loads(content)
                    for src_file, file_cov in data.items():
                        if isinstance(file_cov, dict) and "statementMap" in file_cov and "s" in file_cov:
                            for stmt_id, count in file_cov["s"].items():
                                if count > 0 and stmt_id in file_cov["statementMap"]:
                                    loc = file_cov["statementMap"][stmt_id]
                                    start_line = loc.get("start", {}).get("line", 0)
                                    end_line = loc.get("end", {}).get("line", start_line)
                                    for ln in range(start_line, end_line + 1):
                                        covered_lines.add((src_file, ln))
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
            # LCOV format
            elif filepath.endswith(".info"):
                current_sf = None
                for line in content.split("\n"):
                    if line.startswith("SF:"):
                        current_sf = line[3:]
                    elif line.startswith("DA:") and current_sf:
                        parts = line[3:].split(",")
                        if len(parts) >= 2 and int(parts[1]) > 0:
                            covered_lines.add((current_sf, int(parts[0])))

    if not covered_lines:
        return None

    # Intersect: of the lines this task changed, how many are covered?
    changed_count = len(changed_lines)
    covered_count = 0
    uncovered = []
    for file_line in changed_lines:
        if file_line in covered_lines:
            covered_count += 1
        else:
            uncovered.append(file_line)

    if changed_count == 0:
        return 1.0  # No changed lines = trivially covered

    rate = covered_count / changed_count

    # Report uncovered changed lines (actionable remediation)
    if uncovered and rate < 1.0:
        print(f"  [harness] Diff coverage: {covered_count}/{changed_count} changed lines covered")
        # Show first 10 uncovered lines
        for f, ln in sorted(uncovered)[:10]:
            print(f"       {f}:{ln}")
        if len(uncovered) > 10:
            print(f"       ... and {len(uncovered) - 10} more")

    return round(rate * 100, 2)


def parse_audit(output):
    """Extract high/critical vulnerability count from audit tool outputs."""
    # npm audit --json format
    try:
        data = json.loads(output)
        if "metadata" in data and "vulnerabilities" in data["metadata"]:
            vuln = data["metadata"]["vulnerabilities"]
            return vuln.get("high", 0) + vuln.get("critical", 0)
        # Alternate npm audit format
        if "vulnerabilities" in data:
            count = 0
            for v in data["vulnerabilities"].values():
                if v.get("severity") in ("high", "critical"):
                    count += 1
            return count
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    # Text format: "N high" or "N critical"
    high = 0
    for m in re.finditer(r'(\d+)\s+(?:high|critical)', output, re.IGNORECASE):
        high += int(m.group(1))
    return high


def check_ratchet(gate, measured_value):
    """Check if a ratchet gate meets its recorded floor. Returns (ok, message)."""
    if not gate.get("ratchet") or measured_value is None:
        return True, ""
    lock = load_lock()
    floors = lock.get("ratchetFloors", {})
    floor_entry = floors.get(gate["id"])
    if not floor_entry or "value" not in floor_entry:
        return True, ""  # No floor recorded yet
    floor_value = floor_entry["value"]
    gate_type = gate.get("type", "exit-code")
    if gate_type in ("coverage", "coverage-diff"):
        # Coverage must be >= floor
        if measured_value < floor_value:
            return False, (
                f"RATCHET VIOLATION: {gate['id']} coverage {measured_value}% "
                f"is below recorded floor {floor_value}% "
                f"(set on {floor_entry.get('recordedAt', '?')}). "
                f"Coverage can only go up."
            )
    elif gate_type == "audit":
        # Audit vulns must be <= floor (floor should be 0 ideally)
        if measured_value > floor_value:
            return False, (
                f"RATCHET VIOLATION: {gate['id']} has {measured_value} high/critical vulns, "
                f"floor is {floor_value} "
                f"(set on {floor_entry.get('recordedAt', '?')})."
            )
    return True, ""


def run_gate(gate, task_id):
    """Run a single gate and return (pass, output, ratchet_msg, measured_value)."""
    evidence_task_dir = os.path.join(EVIDENCE_DIR, task_id)
    os.makedirs(evidence_task_dir, exist_ok=True)
    gate_type = gate.get("type", "exit-code")
    gate_timeout = gate.get("timeout", DEFAULT_GATE_TIMEOUT)
    measured_value = None
    ratchet_msg = ""

    try:
        result = subprocess.run(
            gate["command"], shell=True,
            capture_output=True, text=True, timeout=gate_timeout
        )
        output = result.stdout + result.stderr

        # Evaluate based on gate type
        if gate_type == "coverage-diff":
            # Diff-scoped coverage: only measure lines this task changed
            # Find baseSha from the active task
            tasks_data = load_index()
            active_task = get_by_id(tasks_data, task_id)
            base_sha = active_task.get("baseSha") if active_task else None
            if base_sha:
                # First run the command to generate coverage data
                measured_value = parse_diff_coverage(output, base_sha)
                if measured_value is not None:
                    passed = measured_value >= gate.get("threshold_value", 80)
                    output += f"\n[harness] Diff coverage (since {base_sha[:8]}): {measured_value}%"
                else:
                    # Fallback to global coverage if diff parsing fails
                    measured_value = parse_coverage(output)
                    if measured_value is None:
                        measured_value = parse_coverage_from_files()
                    if measured_value is not None:
                        passed = measured_value >= gate.get("threshold_value", 80)
                        output += f"\n[harness] Diff coverage unavailable, using global: {measured_value}%"
                    else:
                        passed = False
                        output += "\n[harness] Could not parse coverage"
            else:
                # No baseSha = new task system, fall back to global
                measured_value = parse_coverage(output)
                if measured_value is None:
                    measured_value = parse_coverage_from_files()
                if measured_value is not None:
                    passed = measured_value >= gate.get("threshold_value", 80)
                else:
                    passed = False
                    output += "\n[harness] No baseSha and could not parse coverage"
        elif gate_type == "coverage":
            measured_value = parse_coverage(output)
            # Fallback: scan for coverage report files on disk
            if measured_value is None:
                measured_value = parse_coverage_from_files()
                if measured_value is not None:
                    output += f"\n[harness] Coverage parsed from file: {measured_value}%"
            if measured_value is not None:
                passed = measured_value >= gate.get("threshold_value", 80)
            else:
                passed = False
                output += "\n[harness] Could not parse coverage from output or files"
        elif gate_type == "audit":
            measured_value = parse_audit(output)
            passed = measured_value <= gate.get("threshold_value", 0)
        else:  # exit-code (default)
            passed = result.returncode == 0
            measured_value = result.returncode

        # Enforce ratchet floor (quality can never regress)
        if passed and gate.get("ratchet"):
            ratchet_ok, ratchet_msg = check_ratchet(gate, measured_value)
            if not ratchet_ok:
                passed = False
                output += f"\n[harness] {ratchet_msg}"

        # Save evidence
        evidence_file = os.path.join(evidence_task_dir, f"{gate['id']}.txt")
        with open(evidence_file, "w") as f:
            f.write(f"Gate: {gate['id']}\n")
            f.write(f"Type: {gate_type}\n")
            f.write(f"Command: {gate['command']}\n")
            f.write(f"Exit code: {result.returncode}\n")
            if measured_value is not None:
                f.write(f"Measured: {measured_value}\n")
                f.write(f"Threshold: {gate.get('threshold_desc', 'N/A')}\n")
            if ratchet_msg:
                f.write(f"Ratchet: {ratchet_msg}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"---\n{output}")

        return passed, output.strip(), ratchet_msg, measured_value
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT: gate exceeded {gate_timeout}s limit", "", None
    except FileNotFoundError:
        return False, f"TOOL NOT FOUND: {gate['command'].split()[0]}", "", None


def cmd_verify(tasks):
    """Run all gates for the active task, produce gate-summary.json.

    Gates run in parallel by default for performance. Each gate writes its own
    evidence file, and the summary is written after all complete.
    """
    active = get_active(tasks)
    if not active:
        print("ERROR: No active task. Run 'task next' first.")
        sys.exit(1)

    gates = parse_gates()
    if not gates:
        print("NO GATES DEFINED.")
        if os.path.exists(GATES_FILE):
            print("gates.yaml exists but contains no valid gate entries.")
        else:
            print("Create .codestudio/gates.yaml or run 'task done --skip-gates'.")
        return

    task_id = active["id"]
    evidence_task_dir = os.path.join(EVIDENCE_DIR, task_id)
    os.makedirs(evidence_task_dir, exist_ok=True)

    print(f"VERIFY: {task_id} — running {len(gates)} gates\n")

    # Run gates in parallel for performance
    gate_results = {}  # gate_id -> (passed, output, ratchet_msg, measured_value)
    max_workers = min(len(gates), 4)  # Cap parallelism at 4
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_gate, gate, task_id): gate
            for gate in gates
        }
        for future in as_completed(futures):
            gate = futures[future]
            try:
                gate_results[gate["id"]] = future.result()
            except Exception as e:
                gate_results[gate["id"]] = (False, f"EXCEPTION: {e}", "", None)

    # Report results in original gate order
    results = []
    all_pass = True
    for gate in gates:
        passed, output, ratchet_msg, measured_value = gate_results[gate["id"]]
        icon = "✅" if passed else "❌"
        extra = ""
        if measured_value is not None and gate["type"] == "coverage":
            extra = f" ({measured_value}%)"
        elif measured_value is not None and gate["type"] == "audit":
            extra = f" ({measured_value} high/critical)"
        print(f"  {icon} {gate['id']}: {'PASS' if passed else 'FAIL'}{extra}")
        if ratchet_msg:
            print(f"       ⚠️  {ratchet_msg}")
        if not passed and not ratchet_msg:
            all_pass = False
            for line in output.split("\n")[:3]:
                print(f"       {line}")
            print()
        elif not passed:
            all_pass = False
        results.append({
            "gate": gate["id"],
            "command": gate["command"],
            "passed": passed,
            "measured": measured_value,
            "ratchet": gate.get("ratchet", False)
        })

    # Write gate-summary.json
    summary = {
        "task": task_id,
        "commit": git_head(),
        "timestamp": datetime.now().isoformat(),
        "verdict": "pass" if all_pass else "fail",
        "gates": results
    }
    summary_path = os.path.join(evidence_task_dir, "gate-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    passed_count = sum(1 for r in results if r["passed"])
    print(f"\nVERDICT: {'PASS' if all_pass else 'FAIL'} ({passed_count}/{len(results)} gates)")
    if all_pass:
        print(f"Evidence: .codestudio/evidence/{task_id}/gate-summary.json")
        print("Ready for: task done")

        # Update ratchet floors — record the actual measured value as the new floor
        lock = load_lock()
        for gate, r in zip(gates, results):
            if r["ratchet"] and r["passed"] and r["measured"] is not None:
                current_floor = lock["ratchetFloors"].get(gate["id"], {}).get("value")
                new_value = r["measured"]
                # For coverage: floor goes UP (higher is better)
                # For audit: floor goes DOWN (lower is better, 0 is ideal)
                should_update = False
                if current_floor is None:
                    should_update = True
                elif gate["type"] == "coverage" and new_value > current_floor:
                    should_update = True
                elif gate["type"] == "audit" and new_value < current_floor:
                    should_update = True
                if should_update:
                    lock["ratchetFloors"][gate["id"]] = {
                        "value": new_value,
                        "recordedAt": date.today().isoformat(),
                        "task": task_id,
                    }
        save_lock(lock)
    else:
        print("Fix failures and re-run: task verify")


def git_is_dirty():
    """Check if the working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_evidence(task_id):
    """Check if passing evidence exists for the task. Returns (ok, message).

    Evidence is valid if:
    1. gate-summary.json exists and verdict is 'pass'
    2. Either:
       a. Evidence commit matches HEAD (verify ran, nothing changed since), OR
       b. Evidence commit is HEAD~1 and HEAD is the task's own commit (verify → commit → done), OR
       c. Not a git repo (no commit tracking)
    """
    summary_path = os.path.join(EVIDENCE_DIR, task_id, "gate-summary.json")
    if not os.path.exists(summary_path):
        return False, "No evidence found. Run 'task verify' first."
    with open(summary_path, "r") as f:
        summary = json.load(f)
    if summary.get("verdict") != "pass":
        return False, f"Gates did not pass (verdict: {summary['verdict']}). Fix and re-run 'task verify'."
    # Commit staleness check
    head = git_head()
    evidence_commit = summary.get("commit")
    if not head or not evidence_commit:
        return True, "Evidence valid (no git)."
    if evidence_commit == head:
        return True, "Evidence valid (matches HEAD)."
    # Allow: verify at commit A → commit creates B → done at B
    # Evidence is for A, HEAD is B. Check if A is HEAD~1 and no code changed since.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            capture_output=True, text=True, timeout=5
        )
        parent = result.stdout.strip() if result.returncode == 0 else None
        if parent and evidence_commit == parent and not git_is_dirty():
            return True, "Evidence valid (verified before last commit)."
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, (
        f"Evidence is stale (evidence commit: {evidence_commit[:8]}, "
        f"HEAD: {head[:8]}). Re-run 'task verify'."
    )


# ── Stage Machine ────────────────────────────────────────────────────

# Ordered SDLC stages for the loop. Each entry defines:
#   name       - stage identifier written into task index
#   skill      - skill file the agent must read (.codestudio/skills/<skill>.md)
#   artifact   - what must exist in the task file before advancing (regex on ## sections)
#   instruction - one-line directive printed to the agent
STAGES = [
    {
        "name": "SPEC",
        "skill": "spec.md",
        "artifact": r"## What",
        "instruction": "Read .codestudio/skills/spec.md. Follow every step. Write ## What in the task file. Present to user and wait for confirmation.",
    },
    {
        "name": "PLAN",
        "skill": "plan.md",
        "artifact": r"## Plan",
        "instruction": "Read .codestudio/skills/plan.md. Follow every step. Write ## Plan in the task file. Present to user and wait for confirmation.",
    },
    {
        "name": "BUILD",
        "skill": "tdd.md",
        "artifact": None,  # Enforced by VERIFY — BUILD output is code, not a doc section
        "instruction": "Read .codestudio/skills/tdd.md. Follow every step for EACH subtask: RED → GREEN → REFACTOR → GATES → COMMIT. Report DONE or BLOCKED.",
    },
    {
        "name": "VERIFY",
        "skill": "debugging.md",
        "artifact": None,  # Enforced by gate-summary.json existing with verdict=pass
        "instruction": "Run: python3 .codestudio/task.py verify. If gates fail, read .codestudio/skills/debugging.md and follow the triage checklist.",
    },
    {
        "name": "REVIEW",
        "skill": "review.md",
        "artifact": r"## Review",
        "instruction": "Read .codestudio/skills/review.md. Follow every step. Write ## Review in the task file.",
    },
    {
        "name": "LEARN",
        "skill": None,
        "artifact": r"## Log",
        "instruction": "Write ## Log in the task file. Append one-line summary to .codestudio/progress.md. Update project-context.md if architecture changed. Run: python3 .codestudio/task.py done.",
    },
]

STAGE_NAMES = [s["name"] for s in STAGES]


def get_stage_def(name):
    for s in STAGES:
        if s["name"] == name:
            return s
    return None


def check_artifact(task_id, artifact_pattern):
    """Check if a required artifact (## section) exists in the task file with real content.

    Rejects:
    - Missing task file
    - Section header present but body is empty or whitespace-only
    - Section body contains only empty checkbox stubs '- [ ] ' with no title text
    """
    if not artifact_pattern:
        return True, ""
    task_file = os.path.join(TASKS_DIR, f"{task_id}.md")
    if not os.path.exists(task_file):
        return False, f"Task file .codestudio/tasks/{task_id}.md does not exist."
    with open(task_file, "r") as f:
        content = f.read()
    if not re.search(artifact_pattern, content, re.MULTILINE):
        return False, f"Required section '{artifact_pattern}' not found in task file. Complete this stage before advancing."
    # Extract body: everything after the matched header up to the next ## heading or EOF
    body_match = re.search(
        artifact_pattern + r"\s*\n+(.*?)(?=^##\s|\Z)",
        content, re.MULTILINE | re.DOTALL
    )
    if not body_match:
        return False, f"Section '{artifact_pattern}' exists but appears empty. Complete it before advancing."
    body = body_match.group(1)
    # Reject whitespace-only body
    if not body.strip():
        return False, f"Section '{artifact_pattern}' exists but appears empty. Complete it before advancing."
    # Reject body made up only of empty checkbox stubs '- [ ]' with no title text
    non_empty_lines = [ln.strip() for ln in body.strip().splitlines() if ln.strip()]
    if non_empty_lines and all(re.fullmatch(r'-\s*\[[ xX]?\]\s*', ln) for ln in non_empty_lines):
        return False, f"Section '{artifact_pattern}' contains only empty checkboxes. Add task titles before advancing."
    return True, ""


def cmd_stage(tasks, advance=False):
    """Show current SDLC stage or advance to next (with artifact check)."""
    active = get_active(tasks)
    if not active:
        print("ERROR: No active task. Run 'task next' first.")
        sys.exit(1)

    task_id = active["id"]
    current_stage = active.get("stage", "SPEC")  # Default to SPEC for new tasks

    if not advance:
        # Just report current stage and what the agent must do
        stage_def = get_stage_def(current_stage)
        if not stage_def:
            print(f"STAGE: {current_stage} (unknown — check task index)")
            return

        idx = STAGE_NAMES.index(current_stage)
        print(f"TASK:    {task_id} — {active['title']}")
        print(f"STAGE:   {current_stage} ({idx + 1}/{len(STAGES)})")
        if stage_def["skill"]:
            print(f"SKILL:   .codestudio/skills/{stage_def['skill']}")
        print(f"")
        print(f"INSTRUCTION:")
        print(f"  {stage_def['instruction']}")
        if stage_def["artifact"]:
            print(f"")
            print(f"REQUIRED ARTIFACT BEFORE ADVANCING:")
            ok, msg = check_artifact(task_id, stage_def["artifact"])
            if ok:
                print(f"  ✅ {stage_def['artifact']} — present")
            else:
                print(f"  ❌ {stage_def['artifact']} — MISSING")
                print(f"     {msg}")
        return

    # Advance: check artifact, then move to next stage
    stage_def = get_stage_def(current_stage)
    if not stage_def:
        print(f"ERROR: Unknown stage '{current_stage}'. Check task index.")
        sys.exit(1)

    # Special check for VERIFY stage: require passing gate evidence
    if current_stage == "VERIFY":
        ok, msg = check_evidence(task_id)
        if not ok:
            print(f"BLOCKED: Cannot advance from VERIFY without passing gate evidence.")
            print(f"  {msg}")
            print(f"  Run: python3 .codestudio/task.py verify")
            sys.exit(1)

    # Check artifact for all other stages
    if stage_def["artifact"]:
        ok, msg = check_artifact(task_id, stage_def["artifact"])
        if not ok:
            print(f"BLOCKED: Cannot advance from {current_stage}.")
            print(f"  {msg}")
            print(f"  Complete the stage output, then re-run: task stage advance")
            sys.exit(1)

    # Find next stage
    idx = STAGE_NAMES.index(current_stage)
    if idx + 1 >= len(STAGES):
        print(f"STAGE:   {current_stage} is the final stage.")
        print(f"  Run: python3 .codestudio/task.py done")
        return

    next_stage = STAGE_NAMES[idx + 1]
    next_def = get_stage_def(next_stage)

    active["stage"] = next_stage
    save_index(tasks)

    print(f"ADVANCED: {current_stage} → {next_stage}")
    print(f"TASK:     {task_id} — {active['title']}")
    print(f"")
    print(f"NEXT INSTRUCTION:")
    print(f"  {next_def['instruction']}")
    if next_def["skill"]:
        print(f"")
        print(f"READ NOW: .codestudio/skills/{next_def['skill']}")


# ── Commands ──────────────────────────────────────────────────────────


def cmd_next(tasks):
    """Pick next eligible todo → set active. Only 1 active at a time."""
    active = get_active(tasks)
    if active:
        task_file = os.path.join(TASKS_DIR, f"{active['id']}.md")
        print(f"ACTIVE: {active['id']} — {active['title']}")
        if os.path.exists(task_file):
            print(f"FILE:   .codestudio/tasks/{active['id']}.md")
        # Always reprint stage instruction on resume so agent has full context
        current_stage = active.get("stage", "SPEC")
        stage_def = get_stage_def(current_stage)
        if stage_def:
            print(f"STAGE:  {current_stage} — {stage_def['instruction']}")
            if stage_def["skill"]:
                print(f"READ:   .codestudio/skills/{stage_def['skill']}")
        return

    done_ids = {t["id"] for t in tasks if t["status"] == "done"}

    for t in tasks:
        if t["status"] != "todo":
            continue
        needs = t.get("needs", [])
        if all(n in done_ids for n in needs):
            t["status"] = "active"
            # Record baseSha — the commit where this task starts
            # Used for diff-scoped coverage and rollback
            base = git_head()
            if base:
                t["baseSha"] = base
            save_index(tasks)

            task_file = os.path.join(TASKS_DIR, f"{t['id']}.md")
            # Ensure stage is set — covers tasks created before stage tracking
            # and tasks whose dependencies had no stage field (legacy index.json)
            if not t.get("stage"):
                t["stage"] = "SPEC"
            save_index(tasks)  # persist stage field before proceeding

            if not os.path.exists(task_file):
                with open(task_file, "w") as f:
                    f.write(f"# {t['title']}\n\n## What\n\n")
                print(f"PICKED: {t['id']} — {t['title']}")
                print(f"FILE:   .codestudio/tasks/{t['id']}.md (created)")
            else:
                print(f"PICKED: {t['id']} — {t['title']}")
                print(f"FILE:   .codestudio/tasks/{t['id']}.md")
            if base:
                print(f"BASE:   {base[:8]} (for diff-scoped gates and rollback)")

            # Print stage instruction immediately so agent knows what to do next
            stage_def = get_stage_def(t.get("stage", "SPEC"))
            if stage_def:
                print(f"STAGE:  {t['stage']} — {stage_def['instruction']}")
                if stage_def["skill"]:
                    print(f"READ:   .codestudio/skills/{stage_def['skill']}")
            return

    # Check if any tasks are blocked or have unmet dependencies
    blocked = [t for t in tasks if t["status"] == "blocked"]
    waiting = [t for t in tasks if t["status"] == "todo" and not all(
        n in done_ids for n in t.get("needs", [])
    )]

    if blocked:
        print(f"NO ELIGIBLE TASKS. {len(blocked)} blocked:")
        for t in blocked:
            print(f"  {t['id']} — {t['title']}")
    elif waiting:
        print(f"NO ELIGIBLE TASKS. {len(waiting)} waiting on dependencies:")
        for t in waiting:
            unmet = [n for n in t.get("needs", []) if n not in done_ids]
            print(f"  {t['id']} — needs: {', '.join(unmet)}")
    else:
        backlog = [t for t in tasks if t["status"] == "backlog"]
        if backlog:
            print(f"ALL TASKS DONE. {len(backlog)} items in backlog.")
            print("Promote backlog items with: task add \"title\" (from backlog ideas)")
        else:
            print("ALL TASKS DONE. No backlog items.")


def cmd_done(tasks, skip_gates=False):
    """Active → done. Requires LEARN stage + passing evidence unless --skip-gates."""
    active = get_active(tasks)
    if not active:
        print("ERROR: No active task. Run 'task next' first.")
        sys.exit(1)

    # Require LEARN stage before marking done (unless skipping gates)
    if not skip_gates:
        current_stage = active.get("stage", "SPEC")
        if current_stage != "LEARN":
            print(f"REFUSED: cannot mark {active['id']} done — still at stage {current_stage}.")
            print(f"  Complete all stages first: SPEC → PLAN → BUILD → VERIFY → REVIEW → LEARN")
            print(f"  Current stage: {current_stage}")
            print(f"  Run 'task stage' to see what is needed, then 'task stage advance' when done.")
            sys.exit(1)

    gates = parse_gates()
    if gates and not skip_gates:
        ok, msg = check_evidence(active["id"])
        if not ok:
            print(f"REFUSED: cannot mark {active['id']} done without passing gate evidence.")
            print(f"  {msg}")
            print()
            print("This is the harness working as designed: a task is done when")
            print("tools say so, not when an agent says so.")
            print()
            print("Run 'task verify' to execute gates, or 'task done --skip-gates' to bypass.")
            sys.exit(1)

    active["status"] = "done"
    save_index(tasks)
    if gates and not skip_gates:
        print(f"DONE (verified): {active['id']} — {active['title']}")
    elif skip_gates:
        print(f"DONE (gates skipped): {active['id']} — {active['title']}")
    else:
        print(f"DONE: {active['id']} — {active['title']}")


def cmd_block(tasks, reason):
    """Active → blocked."""
    active = get_active(tasks)
    if not active:
        print("ERROR: No active task.")
        sys.exit(1)
    active["status"] = "blocked"
    save_index(tasks)
    print(f"BLOCKED: {active['id']} — {active['title']}")
    print(f"REASON: {reason}")
    print(f"Add details to .codestudio/tasks/{active['id']}.md under ## Log")


def cmd_unblock(tasks, task_id):
    """Blocked → todo."""
    task = get_by_id(tasks, task_id)
    if not task:
        print(f"ERROR: Task {task_id} not found.")
        sys.exit(1)
    if task["status"] != "blocked":
        print(f"ERROR: {task_id} is not blocked (status: {task['status']})")
        sys.exit(1)
    task["status"] = "todo"
    save_index(tasks)
    print(f"UNBLOCKED: {task_id} — {task['title']}")


def cmd_review(tasks):
    """Active → review."""
    active = get_active(tasks)
    if not active:
        print("ERROR: No active task.")
        sys.exit(1)
    active["status"] = "review"
    save_index(tasks)
    print(f"IN REVIEW: {active['id']} — {active['title']}")
    print(f"Write ## Review in .codestudio/tasks/{active['id']}.md")


def cmd_approve(tasks, skip_gates=False):
    """Review → done. Requires passing evidence unless --skip-gates."""
    review_task = None
    for t in tasks:
        if t["status"] == "review":
            review_task = t
            break
    if not review_task:
        print("ERROR: No task in review.")
        sys.exit(1)

    gates = parse_gates()
    if gates and not skip_gates:
        ok, msg = check_evidence(review_task["id"])
        if not ok:
            print(f"REFUSED: cannot approve {review_task['id']} without passing gate evidence.")
            print(f"  {msg}")
            print("Run 'task verify' or 'task approve --skip-gates' to bypass.")
            sys.exit(1)

    review_task["status"] = "done"
    save_index(tasks)
    print(f"APPROVED: {review_task['id']} — {review_task['title']}")


def cmd_reject(tasks):
    """Review → active (rework)."""
    review_task = None
    for t in tasks:
        if t["status"] == "review":
            review_task = t
            break
    if not review_task:
        print("ERROR: No task in review.")
        sys.exit(1)
    review_task["status"] = "active"
    save_index(tasks)
    print(f"REWORK: {review_task['id']} — {review_task['title']}")
    print(f"Fix issues in ## Review, then 'task review' again.")


def cmd_add(tasks, title, needs=None, backlog=False):
    """Add a new task."""
    tid = next_id(tasks)
    task = {
        "id": tid,
        "title": title,
        "status": "backlog" if backlog else "todo",
        "needs": needs or [],
        "stage": "SPEC"
    }
    tasks.append(task)
    save_index(tasks)
    status_label = "BACKLOG" if backlog else "TODO"
    print(f"ADDED [{status_label}]: {tid} — {title}")
    if needs:
        print(f"DEPENDS ON: {', '.join(needs)}")


def cmd_defer(tasks, task_id, reason):
    """Backlog → deferred. Requires a reason — unevaluated backlog is not completion."""
    task = get_by_id(tasks, task_id)
    if not task:
        print(f"ERROR: Task {task_id} not found.")
        sys.exit(1)
    if task["status"] != "backlog":
        print(f"ERROR: {task_id} is not in backlog (status: {task['status']}). Only backlog items can be deferred.")
        sys.exit(1)
    task["status"] = "deferred"
    task["deferReason"] = reason
    save_index(tasks)
    print(f"DEFERRED: {task_id} — {task['title']}")
    print(f"REASON: {reason}")


def cmd_rollback(tasks, task_id, force=False):
    """Rollback a task's changes using its baseSha. Requires --force to execute."""
    task = get_by_id(tasks, task_id)
    if not task:
        print(f"ERROR: Task {task_id} not found.")
        sys.exit(1)
    base_sha = task.get("baseSha")
    if not base_sha:
        print(f"ERROR: {task_id} has no baseSha recorded. Cannot rollback.")
        print("baseSha is recorded when a task is picked with 'task next'.")
        sys.exit(1)
    head = git_head()
    if not head:
        print("ERROR: Not a git repository. Cannot rollback.")
        sys.exit(1)
    if base_sha == head:
        print(f"Nothing to rollback — HEAD is already at baseSha ({base_sha[:8]}).")
        return
    # Show what would be lost
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{base_sha}..HEAD"],
            capture_output=True, text=True, timeout=10
        )
        commits = result.stdout.strip()
        if commits:
            print(f"ROLLBACK {task_id} to {base_sha[:8]}")
            print(f"The following commits will be LOST:")
            for line in commits.split("\n"):
                print(f"  {line}")
        else:
            print(f"No commits between baseSha and HEAD.")
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("ERROR: Could not read git log.")
        sys.exit(1)
    if not force:
        print(f"\nDry run. To execute: task rollback {task_id} --force")
        return
    # Execute rollback
    try:
        result = subprocess.run(
            ["git", "reset", "--hard", base_sha],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            task["status"] = "todo"
            task.pop("baseSha", None)
            save_index(tasks)
            print(f"ROLLED BACK: {task_id} to {base_sha[:8]}")
            print(f"Task status reset to 'todo'.")
        else:
            print(f"ERROR: git reset failed: {result.stderr}")
            sys.exit(1)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def cmd_status(tasks):
    """Print summary counts."""
    counts = {}
    for t in tasks:
        s = t["status"]
        counts[s] = counts.get(s, 0) + 1
    total = len(tasks)

    print("PROJECT STATUS")
    print(f"  done:        {counts.get('done', 0)}")
    print(f"  active:      {counts.get('active', 0)}")
    print(f"  review:      {counts.get('review', 0)}")
    print(f"  todo:        {counts.get('todo', 0)}")
    print(f"  blocked:     {counts.get('blocked', 0)}")
    print(f"  backlog:     {counts.get('backlog', 0)}")
    print(f"  ─────────────────")
    print(f"  total:       {total}")

    if total > 0:
        done_count = counts.get('done', 0)
        active_count = total - counts.get('backlog', 0)
        if active_count > 0:
            pct = int((done_count / active_count) * 100)
            print(f"  progress:    {pct}% (excluding backlog)")


def cmd_list(tasks, filter_status=None):
    """Print task list."""
    for t in tasks:
        if filter_status and t["status"] != filter_status:
            continue
        status_icon = {
            "done": "✅", "active": "🔄", "review": "👀",
            "todo": "⏳", "blocked": "🚫", "backlog": "📋"
        }.get(t["status"], "?")
        needs_str = f" (needs: {', '.join(t['needs'])})" if t.get("needs") else ""
        print(f"  {status_icon} {t['id']} — {t['title']}{needs_str}")


def cmd_archive(tasks):
    """Move done tasks to archive."""
    done_tasks = [t for t in tasks if t["status"] == "done"]
    if not done_tasks:
        print("Nothing to archive.")
        return

    # Use date + counter to avoid overwriting previous archives on same day
    archive_base = date.today().isoformat()
    archive_path = os.path.join(ARCHIVE_DIR, archive_base)
    counter = 1
    while os.path.exists(archive_path):
        archive_path = os.path.join(ARCHIVE_DIR, f"{archive_base}-{counter}")
        counter += 1
    archive_tasks_path = os.path.join(archive_path, "tasks")
    os.makedirs(archive_tasks_path, exist_ok=True)

    # Save archived index — merge with any existing archive from today
    archive_index = os.path.join(archive_path, "index.json")
    with open(archive_index, "w") as f:
        json.dump(done_tasks, f, indent=2)
        f.write("\n")

    # Move task files
    moved = 0
    for t in done_tasks:
        src = os.path.join(TASKS_DIR, f"{t['id']}.md")
        dst = os.path.join(archive_tasks_path, f"{t['id']}.md")
        if os.path.exists(src):
            shutil.move(src, dst)
            moved += 1

    # Remove done from active index
    remaining = [t for t in tasks if t["status"] != "done"]
    save_index(remaining)

    print(f"ARCHIVED: {len(done_tasks)} tasks → {os.path.relpath(archive_path)}/")
    print(f"  Files moved: {moved}")
    print(f"  Remaining:   {len(remaining)} tasks")


def cmd_info(tasks, task_id):
    """Print details of a specific task."""
    task = get_by_id(tasks, task_id)
    if not task:
        print(f"ERROR: Task {task_id} not found.")
        sys.exit(1)

    print(f"TASK:    {task['id']} — {task['title']}")
    print(f"STATUS:  {task['status']}")
    if task.get("needs"):
        print(f"NEEDS:   {', '.join(task['needs'])}")
    task_file = os.path.join(TASKS_DIR, f"{task['id']}.md")
    if os.path.exists(task_file):
        print(f"FILE:    .codestudio/tasks/{task['id']}.md")
    else:
        print(f"FILE:    (not yet created)")


# ── CLI ───────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("Usage: task <command> [args]")
        print("Commands: next, done, block, unblock, review, approve, reject, add, status, list, archive, info")
        sys.exit(1)

    tasks = load_index()
    cmd = sys.argv[1]

    if cmd == "next":
        cmd_next(tasks)
    elif cmd == "stage":
        advance = len(sys.argv) > 2 and sys.argv[2] == "advance"
        cmd_stage(tasks, advance=advance)
    elif cmd == "verify":
        cmd_verify(tasks)
    elif cmd == "done":
        skip_gates = "--skip-gates" in sys.argv
        cmd_done(tasks, skip_gates=skip_gates)
    elif cmd == "block":
        reason = sys.argv[2] if len(sys.argv) > 2 else "no reason given"
        cmd_block(tasks, reason)
    elif cmd == "unblock":
        if len(sys.argv) < 3:
            print("Usage: task unblock T-XXX")
            sys.exit(1)
        cmd_unblock(tasks, sys.argv[2])
    elif cmd == "review":
        cmd_review(tasks)
    elif cmd == "approve":
        skip_gates = "--skip-gates" in sys.argv
        cmd_approve(tasks, skip_gates=skip_gates)
    elif cmd == "reject":
        cmd_reject(tasks)
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: task add \"title\" [--needs T-001] [--backlog]")
            sys.exit(1)
        title = sys.argv[2]
        needs = []
        backlog = False
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--needs" and i + 1 < len(sys.argv):
                needs.append(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--backlog":
                backlog = True
                i += 1
            else:
                i += 1
        cmd_add(tasks, title, needs, backlog)
    elif cmd == "status":
        cmd_status(tasks)
    elif cmd == "list":
        filter_status = None
        if len(sys.argv) > 2:
            filter_status = sys.argv[2].lstrip("-")
        cmd_list(tasks, filter_status)
    elif cmd == "archive":
        cmd_archive(tasks)
    elif cmd == "info":
        if len(sys.argv) < 3:
            print("Usage: task info T-XXX")
            sys.exit(1)
        cmd_info(tasks, sys.argv[2])
    elif cmd == "defer":
        if len(sys.argv) < 4:
            print('Usage: task defer T-XXX "reason why this is deferred"')
            sys.exit(1)
        cmd_defer(tasks, sys.argv[2], sys.argv[3])
    elif cmd == "rollback":
        if len(sys.argv) < 3:
            print("Usage: task rollback T-XXX [--force]")
            sys.exit(1)
        force = "--force" in sys.argv
        cmd_rollback(tasks, sys.argv[2], force=force)
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: next, stage, verify, done, block, unblock, review, approve, reject, add, defer, rollback, status, list, archive, info")
        sys.exit(1)


if __name__ == "__main__":
    main()
