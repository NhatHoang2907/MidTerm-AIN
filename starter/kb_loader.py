"""Knowledge-base loaders for Project 03 (Academic Rule and Prerequisite Advisor).

This module is **infrastructure only**: it reads the JSON files under
`data/`, validates their shape, and hands back plain Python data
structures (dicts / lists). It does not perform any prerequisite
checking, entailment, or graduation reasoning -- that is the graded
core the student implements in `student_core.py`.

Every loader rejects unknown top-level keys on each record so that a
typo or an undocumented field fails loudly instead of silently being
ignored by whatever reasoning code consumes it later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    """Raised when a JSON file does not match the documented schema."""


def _read_json(path: str | Path) -> Any:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"{path}: not valid JSON ({exc})") from exc


def _check_keys(record: dict, allowed: set[str], required: set[str], where: str) -> None:
    if not isinstance(record, dict):
        raise SchemaError(f"{where}: expected an object, got {type(record).__name__}")
    unknown = set(record.keys()) - allowed
    if unknown:
        raise SchemaError(f"{where}: unknown key(s) {sorted(unknown)}; allowed={sorted(allowed)}")
    missing = required - set(record.keys())
    if missing:
        raise SchemaError(f"{where}: missing required key(s) {sorted(missing)}")


COURSE_KEYS = {"code", "title", "credits", "mandatory", "program", "year", "semester"}
COURSE_REQUIRED = {"code", "title", "credits", "mandatory", "program"}


def load_courses(path: str | Path) -> list[dict]:
    """Load and validate `courses.json`. Returns the list of course records."""
    data = _read_json(path)
    if "courses" not in data:
        raise SchemaError(f"{path}: top-level object must contain a 'courses' key")
    courses = data["courses"]
    for i, course in enumerate(courses):
        _check_keys(course, COURSE_KEYS, COURSE_REQUIRED, f"{path}#courses[{i}]")
    return courses


PREREQ_KEYS = {"id", "course", "requires_all", "comment"}
PREREQ_REQUIRED = {"id", "course", "requires_all"}


def load_prerequisites(path: str | Path) -> list[dict]:
    """Load and validate `prerequisites.json`. Returns the list of prerequisite rules."""
    data = _read_json(path)
    if "rules" not in data:
        raise SchemaError(f"{path}: top-level object must contain a 'rules' key")
    rules = data["rules"]
    for i, rule in enumerate(rules):
        _check_keys(rule, PREREQ_KEYS, PREREQ_REQUIRED, f"{path}#rules[{i}]")
    return rules


DEGREE_RULE_KEYS = {"id", "description", "type", "min_total_credits", "ref", "represented_by"}
DEGREE_RULE_REQUIRED = {"id", "description", "type"}


def load_degree_rules(path: str | Path) -> dict:
    """Load and validate `degree_rules.json`.

    Returns a dict with keys ``mandatory_courses`` (list[str]) and
    ``rules`` (list[dict]).
    """
    data = _read_json(path)
    if "mandatory_courses" not in data or "rules" not in data:
        raise SchemaError(f"{path}: top-level object must contain 'mandatory_courses' and 'rules'")
    for i, rule in enumerate(data["rules"]):
        _check_keys(rule, DEGREE_RULE_KEYS, DEGREE_RULE_REQUIRED, f"{path}#rules[{i}]")
    return {"mandatory_courses": data["mandatory_courses"], "rules": data["rules"]}


COMPLETED_COURSE_KEYS = {"code", "credits", "grade"}
COMPLETED_COURSE_REQUIRED = {"code", "credits", "grade"}
STUDENT_KEYS = {
    "id",
    "name",
    "cohort",
    "completed_courses",
    "self_reported_status",
    "declared_total_credits",
    "notes",
}
STUDENT_REQUIRED = {"id", "name", "completed_courses"}


def load_students(path: str | Path) -> list[dict]:
    """Load and validate `students.json`. Returns the list of student records."""
    data = _read_json(path)
    if "students" not in data:
        raise SchemaError(f"{path}: top-level object must contain a 'students' key")
    students = data["students"]
    for i, student in enumerate(students):
        _check_keys(student, STUDENT_KEYS, STUDENT_REQUIRED, f"{path}#students[{i}]")
        for j, course in enumerate(student.get("completed_courses", [])):
            _check_keys(
                course,
                COMPLETED_COURSE_KEYS,
                COMPLETED_COURSE_REQUIRED,
                f"{path}#students[{i}].completed_courses[{j}]",
            )
    return students


TEST_CASE_KEYS = {
    "id",
    "class",
    "student_id",
    "query_type",
    "target_course",
    "description",
    "expected_behavior",
    "reasoning_probe",
}
TEST_CASE_REQUIRED = {"id", "class", "student_id", "query_type", "target_course"}


def load_test_cases(path: str | Path) -> list[dict]:
    """Load and validate `test_cases.json`. Returns the list of demo fixtures."""
    data = _read_json(path)
    if "test_cases" not in data:
        raise SchemaError(f"{path}: top-level object must contain a 'test_cases' key")
    cases = data["test_cases"]
    for i, case in enumerate(cases):
        _check_keys(case, TEST_CASE_KEYS, TEST_CASE_REQUIRED, f"{path}#test_cases[{i}]")
    return cases


def load_all(data_dir: str | Path) -> dict[str, Any]:
    """Convenience loader: reads every KB file under `data_dir` at once."""
    data_dir = Path(data_dir)
    return {
        "courses": load_courses(data_dir / "courses.json"),
        "prerequisites": load_prerequisites(data_dir / "prerequisites.json"),
        "degree_rules": load_degree_rules(data_dir / "degree_rules.json"),
        "students": load_students(data_dir / "students.json"),
        "test_cases": load_test_cases(data_dir / "test_cases.json"),
    }
