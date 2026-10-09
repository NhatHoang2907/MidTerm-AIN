"""Benchmark Project 03 inference on Forward Chaining vs Truth-Table model checking.

The benchmark compares two independently implemented reasoning styles on the same
student profiles and query targets:

1. Forward Chaining via `starter.student_core.check_eligibility`
2. An independent Truth-Table checker implemented in this file

It prints a CSV-like table to stdout and also writes a real CSV file.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
STARTER_DIR = PROJECT_ROOT / "starter"
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))

import kb_loader  # type: ignore  # noqa: E402
import student_core  # type: ignore  # noqa: E402

NEGATIVE_STATUSES = {"in_progress", "planned", "registered", "enrolled"}


@dataclass(frozen=True)
class BenchmarkRow:
    student_id: str
    student_name: str
    query: str
    case_ids: str
    case_classes: str
    fc_state: bool | None
    tt_state: bool | None
    agreement: bool
    fc_ms: float
    tt_ms: float
    fc_peak_kb: float
    tt_peak_kb: float
    dependency_depth: int


class _TruthTableChecker:
    def __init__(self, kb: dict[str, Any], student: dict[str, Any], query: str):
        self.kb = kb if isinstance(kb, dict) else {}
        self.student = student if isinstance(student, dict) else {}
        self.query = query
        self.course_order = self._course_order()
        self.catalog = set(self.course_order)
        self.prereq_map = self._prereq_map()
        self.credit_threshold = self._credit_threshold()
        self.english_exit = self._english_exit_course()
        self.mandatory_courses = self._mandatory_courses()
        self.query_kind, self.query_course = self._parse_query(query)
        self.relevant_courses = self._relevant_courses()
        self.fixed_course_values, self.no_models = self._fixed_course_values()

    def _course_order(self) -> list[str]:
        courses = self.kb.get("courses", [])
        return [c["code"] for c in courses if isinstance(c, dict) and isinstance(c.get("code"), str)]

    def _prereq_map(self) -> dict[str, tuple[str, ...]]:
        mapping: dict[str, tuple[str, ...]] = {}
        for rule in self.kb.get("prerequisites", []):
            if not isinstance(rule, dict):
                continue
            course = rule.get("course")
            reqs = rule.get("requires_all", [])
            if not isinstance(course, str):
                continue
            ordered: list[str] = []
            for req in reqs:
                if isinstance(req, str) and req not in ordered:
                    ordered.append(req)
            mapping[course] = tuple(ordered)
        return mapping

    def _credit_threshold(self) -> int:
        degree_rules = self.kb.get("degree_rules", {})
        if not isinstance(degree_rules, dict):
            return 135
        for rule in degree_rules.get("rules", []):
            if isinstance(rule, dict) and rule.get("type") == "credit_threshold" and isinstance(rule.get("min_total_credits"), int):
                return rule["min_total_credits"]
        return 135

    def _english_exit_course(self) -> str | None:
        degree_rules = self.kb.get("degree_rules", {})
        if not isinstance(degree_rules, dict):
            return None
        for rule in degree_rules.get("rules", []):
            if isinstance(rule, dict) and rule.get("type") == "english_exit_clearance":
                represented_by = rule.get("represented_by")
                if isinstance(represented_by, str):
                    return represented_by
        return None

    def _mandatory_courses(self) -> list[str]:
        degree_rules = self.kb.get("degree_rules", {})
        if not isinstance(degree_rules, dict):
            return []
        return [c for c in degree_rules.get("mandatory_courses", []) if isinstance(c, str)]

    def _parse_query(self, query: str) -> tuple[str, str | None]:
        query = query.strip()
        if query in {"GRADUATION", "graduated"}:
            return ("graduation", None)
        if query.startswith("eligible(") and query.endswith(")"):
            inner = query[len("eligible(") : -1]
            if inner == "GRADUATION":
                return ("graduation", None)
            return ("eligible", inner)
        if query in self.catalog:
            return ("eligible", query)
        return ("unknown", None)

    def _student_completed_courses(self) -> set[str]:
        completed: set[str] = set()
        for record in self.student.get("completed_courses", []) or []:
            if isinstance(record, dict) and isinstance(record.get("code"), str):
                completed.add(record["code"])
        return completed

    def _student_statuses(self) -> dict[str, str]:
        raw = self.student.get("self_reported_status", {})
        if not isinstance(raw, dict):
            return {}
        return {code: status for code, status in raw.items() if isinstance(code, str) and isinstance(status, str)}

    def _completion_state(self, course: str) -> bool | None:
        completed = self._student_completed_courses()
        statuses = self._student_statuses()
        positive = course in completed or statuses.get(course) == "completed"
        negative = statuses.get(course) in NEGATIVE_STATUSES
        if positive and negative:
            return None
        if positive:
            return True
        if negative:
            return False
        if course in self.catalog:
            return False
        return None

    def _credit_state(self) -> bool | None:
        declared = self.student.get("declared_total_credits", None)
        if declared is None or not isinstance(declared, int):
            return None
        return declared >= self.credit_threshold

    def _relevant_courses(self) -> list[str]:
        if self.query_kind == "eligible" and self.query_course in self.catalog:
            roots = [self.query_course]
        elif self.query_kind == "graduation":
            roots = list(self.mandatory_courses)
            if self.english_exit:
                roots.append(self.english_exit)
        else:
            roots = []

        seen: set[str] = set()
        relevant: list[str] = []

        def visit(course: str) -> None:
            if course in seen or course not in self.catalog:
                return
            seen.add(course)
            relevant.append(course)
            for req in self.prereq_map.get(course, ()):
                visit(req)

        for root in roots:
            visit(root)
        return relevant

    def _fixed_course_values(self) -> tuple[dict[str, bool], bool]:
        fixed: dict[str, bool] = {}
        for course in self.relevant_courses:
            state = self._completion_state(course)
            if state is None:
                return {}, True
            fixed[course] = state
        return fixed, False

    def _eligible_rules_ok(self, assignment: dict[str, bool]) -> bool:
        if self.query_kind != "eligible" or not self.query_course:
            return False
        prereqs = self.prereq_map.get(self.query_course, ())
        prereq_truth = all(assignment.get(f"completed({req})", False) for req in prereqs)
        return assignment[f"eligible({self.query_course})"] == prereq_truth

    def _graduation_rules_ok(self, assignment: dict[str, bool]) -> bool:
        if self.query_kind != "graduation":
            return False
        req_vars = [f"completed({course})" for course in self.mandatory_courses]
        if self.english_exit:
            req_vars.append(f"completed({self.english_exit})")
        prereq_truth = assignment.get("credits_ok", False) and all(assignment.get(var, False) for var in req_vars)
        return assignment["graduated"] == prereq_truth

    def _rules_ok(self, assignment: dict[str, bool]) -> bool:
        if self.query_kind == "eligible":
            return self._eligible_rules_ok(assignment)
        if self.query_kind == "graduation":
            return self._graduation_rules_ok(assignment)
        return False

    def _candidate_assignments(self) -> list[dict[str, bool]]:
        base: dict[str, bool] = {f"completed({course})": value for course, value in self.fixed_course_values.items()}
        credits_state = self._credit_state()
        if credits_state is True:
            base["credits_ok"] = True
        elif credits_state is False:
            base["credits_ok"] = False

        free_names: list[str] = []
        query_var = self._query_variable()
        if "credits_ok" not in base and credits_state is None:
            free_names.append("credits_ok")
        free_names.append(query_var)

        candidates: list[dict[str, bool]] = []
        for values in itertools.product([False, True], repeat=len(free_names)):
            extra = dict(zip(free_names, values))
            candidate = dict(base)
            candidate.update(extra)
            candidates.append(candidate)
        return candidates

    def _query_variable(self) -> str:
        if self.query_kind == "graduation":
            return "graduated"
        if self.query_kind == "eligible" and self.query_course:
            return f"eligible({self.query_course})"
        return "unknown"

    def _model_summary(self) -> tuple[int, bool, bool]:
        query_var = self._query_variable()
        models_seen = 0
        true_seen = False
        false_seen = False
        for assignment in self._candidate_assignments():
            if query_var not in assignment:
                assignment[query_var] = False
            if not self._rules_ok(assignment):
                continue
            models_seen += 1
            if assignment[query_var]:
                true_seen = True
            else:
                false_seen = True
        return models_seen, true_seen, false_seen

    def entailment(self) -> bool | None:
        if self.query_kind not in {"eligible", "graduation"} or self.no_models:
            return None

        models_seen, true_seen, false_seen = self._model_summary()

        if models_seen == 0:
            return None
        if true_seen and not false_seen:
            return True
        if false_seen and not true_seen:
            return False
        return None


def _student_by_id(students: list[dict[str, Any]], student_id: str) -> dict[str, Any]:
    for student in students:
        if student.get("id") == student_id:
            return student
    raise KeyError(student_id)


def _dependency_map(kb: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    mapping: dict[str, tuple[str, ...]] = {}
    for rule in kb.get("prerequisites", []):
        if not isinstance(rule, dict):
            continue
        course = rule.get("course")
        reqs = rule.get("requires_all", [])
        if not isinstance(course, str):
            continue
        ordered: list[str] = []
        for req in reqs:
            if isinstance(req, str) and req not in ordered:
                ordered.append(req)
        mapping[course] = tuple(ordered)
    return mapping


def _query_targets(test_cases: list[dict[str, Any]]) -> list[str]:
    targets: list[str] = []
    for case in test_cases:
        target = case.get("target_course")
        if isinstance(target, str) and target not in targets:
            targets.append(target)
    return targets


def _query_roots(target: str, kb: dict[str, Any]) -> list[str]:
    if target != "GRADUATION":
        return [target]

    degree = kb.get("degree_rules", {})
    if not isinstance(degree, dict):
        return []
    roots = [c for c in degree.get("mandatory_courses", []) if isinstance(c, str)]
    for rule in degree.get("rules", []):
        if isinstance(rule, dict) and rule.get("type") == "english_exit_clearance" and isinstance(rule.get("represented_by"), str):
            roots.append(rule["represented_by"])
            break
    return roots


def _dependency_depth_from_root(course: str, prereq_map: dict[str, tuple[str, ...]], memo: dict[str, int]) -> int:
    if course in memo:
        return memo[course]
    prereqs = prereq_map.get(course, ())
    if not prereqs:
        memo[course] = 1
        return 1
    value = 1 + max(_dependency_depth_from_root(req, prereq_map, memo) for req in prereqs)
    memo[course] = value
    return value


def _dependency_depth_for_query(target: str, kb: dict[str, Any]) -> int:
    prereq_map = _dependency_map(kb)
    roots = _query_roots(target, kb)
    if not roots:
        return 1
    memo: dict[str, int] = {}
    return max(_dependency_depth_from_root(root, prereq_map, memo) for root in roots)


def _normalize_case_index(test_cases: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    index: dict[tuple[str, str], list[dict[str, str]]] = {}
    for case in test_cases:
        student_id = case.get("student_id")
        target = case.get("target_course")
        if not isinstance(student_id, str) or not isinstance(target, str):
            continue
        bucket = index.setdefault((student_id, target), [])
        bucket.append({"id": str(case.get("id", "")), "class": str(case.get("class", ""))})
    return index


def _time_and_memory(func, *args, repeats: int = 1) -> tuple[Any, float, float]:
    results: list[Any] = []
    elapsed: list[float] = []
    peaks: list[float] = []
    for _ in range(repeats):
        tracemalloc.start()
        start = time.perf_counter()
        result = func(*args)
        duration = (time.perf_counter() - start) * 1000.0
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results.append(result)
        elapsed.append(duration)
        peaks.append(peak / 1024.0)
    return results[-1], statistics.mean(elapsed), max(peaks)


def _benchmark_one(student: dict[str, Any], target: str, kb: dict[str, Any], repeats: int) -> tuple[bool | None, bool | None, float, float, float, float]:
    fc_state, fc_ms, fc_peak = _time_and_memory(student_core.check_eligibility, student, target, kb, repeats=repeats)
    tt_state, tt_ms, tt_peak = _time_and_memory(lambda s, t, k: _TruthTableChecker(k, s, t).entailment(), student, target, kb, repeats=repeats)
    return fc_state, tt_state, fc_ms, tt_ms, fc_peak, tt_peak


def _print_table(rows: list[BenchmarkRow]) -> None:
    print("student_id,student_name,query,case_ids,case_classes,fc_state,tt_state,agreement,fc_ms,tt_ms,fc_peak_kb,tt_peak_kb,dependency_depth")
    for row in rows:
        print(
            f"{row.student_id},{row.student_name},{row.query},{row.case_ids},{row.case_classes},"
            f"{row.fc_state},{row.tt_state},{row.agreement},"
            f"{row.fc_ms:.4f},{row.tt_ms:.4f},{row.fc_peak_kb:.2f},{row.tt_peak_kb:.2f},{row.dependency_depth}"
        )


def _write_csv(path: Path, rows: list[BenchmarkRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "student_id",
                "student_name",
                "query",
                "case_ids",
                "case_classes",
                "fc_state",
                "tt_state",
                "agreement",
                "fc_ms",
                "tt_ms",
                "fc_peak_kb",
                "tt_peak_kb",
                "dependency_depth",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Project 03 inference methods.")
    parser.add_argument("--repeats", type=int, default=20, help="Number of timing repeats per row.")
    parser.add_argument("--csv", type=Path, default=PROJECT_ROOT / "benchmark_student_core.csv", help="Output CSV path.")
    args = parser.parse_args(argv)

    kb = kb_loader.load_all(PROJECT_ROOT / "data")
    students = kb["students"]
    cases = kb["test_cases"]
    targets = _query_targets(cases)
    case_index = _normalize_case_index(cases)

    rows: list[BenchmarkRow] = []
    for student in students:
        for target in targets:
            fc_state, tt_state, fc_ms, tt_ms, fc_peak, tt_peak = _benchmark_one(student, target, kb, max(1, args.repeats))
            matches = case_index.get((student["id"], target), [])
            case_ids = ";".join(item["id"] for item in matches) if matches else ""
            case_classes = ";".join(item["class"] for item in matches) if matches else ""
            rows.append(
                BenchmarkRow(
                    student_id=student["id"],
                    student_name=student["name"],
                    query=target,
                    case_ids=case_ids,
                    case_classes=case_classes,
                    fc_state=fc_state,
                    tt_state=tt_state,
                    agreement=fc_state == tt_state,
                    fc_ms=fc_ms,
                    tt_ms=tt_ms,
                    fc_peak_kb=fc_peak,
                    tt_peak_kb=tt_peak,
                    dependency_depth=_dependency_depth_for_query(target, kb),
                )
            )

    _print_table(rows)
    print()
    print("# Summary")
    print(f"avg_fc_ms={statistics.mean(row.fc_ms for row in rows):.4f}")
    print(f"avg_tt_ms={statistics.mean(row.tt_ms for row in rows):.4f}")
    print(f"avg_fc_peak_kb={statistics.mean(row.fc_peak_kb for row in rows):.2f}")
    print(f"avg_tt_peak_kb={statistics.mean(row.tt_peak_kb for row in rows):.2f}")
    print(f"avg_dependency_depth={statistics.mean(row.dependency_depth for row in rows):.2f}")
    disagreements = [row for row in rows if not row.agreement]
    print(f"disagreements={len(disagreements)}")

    print()
    print("# TC04 / S004 analysis")
    s004 = _student_by_id(students, "S004")
    print(f"S004.completed_courses includes: {[c['code'] for c in s004.get('completed_courses', []) if isinstance(c, dict) and c.get('code') == 'CPR101']}")
    print(f"S004.self_reported_status['CPR101'] = {s004.get('self_reported_status', {}).get('CPR101')}")
    print(f"S004.declared_total_credits = {s004.get('declared_total_credits')}")
    print("The CPR101 conflict affects AIN301 eligibility because CPR101 is in the prerequisite closure; the null credits affect graduation.")

    _write_csv(Path(args.csv), rows)
    print(f"CSV written to: {Path(args.csv).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

