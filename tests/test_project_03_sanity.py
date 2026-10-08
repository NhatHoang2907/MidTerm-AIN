"""Sanity tests for Project 03 (Academic Rule and Prerequisite Advisor).

These tests check that the provided data loads, that the required demo
fixtures exist, and that the starter core is still unimplemented. They
do **not** grade any student's reasoning implementation.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STARTER_DIR = PROJECT_ROOT / "starter"


def _load_module(module_name: str, file_path: Path):
    """Load a starter module under a project-unique name.

    `student_core.py` is a filename shared by every knowledge project in
    this kit, so importing it as a plain top-level `student_core` module
    would collide across projects when their tests run in the same
    pytest session. Loading by file path under a unique name avoids
    that collision regardless of test run order.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


kb_loader = _load_module("project03_kb_loader", STARTER_DIR / "kb_loader.py")
student_core = _load_module("project03_student_core", STARTER_DIR / "student_core.py")

REQUIRED_DEMO_CLASSES = {
    "enough_prereqs",
    "missing_prereq",
    "credits_without_mandatory",
    "incomplete_conflicting_facts",
}


def test_courses_load():
    courses = kb_loader.load_courses(DATA_DIR / "courses.json")
    assert len(courses) > 0
    codes = [c["code"] for c in courses]
    assert len(codes) == len(set(codes)), "course codes must be unique"


def test_prerequisites_load_and_reference_known_courses():
    courses = {c["code"] for c in kb_loader.load_courses(DATA_DIR / "courses.json")}
    rules = kb_loader.load_prerequisites(DATA_DIR / "prerequisites.json")
    assert len(rules) > 0
    for rule in rules:
        assert rule["course"] in courses
        for req in rule["requires_all"]:
            assert req in courses


def test_degree_rules_load():
    degree = kb_loader.load_degree_rules(DATA_DIR / "degree_rules.json")
    assert len(degree["mandatory_courses"]) > 0
    rule_types = {rule["type"] for rule in degree["rules"]}
    assert "credit_threshold" in rule_types
    assert "mandatory_courses_complete" in rule_types


def test_students_load_and_have_contradictory_record():
    students = kb_loader.load_students(DATA_DIR / "students.json")
    assert len(students) >= 4
    contradictory = [
        s
        for s in students
        if s.get("self_reported_status")
        and any(
            course["code"] in s["self_reported_status"]
            for course in s.get("completed_courses", [])
        )
    ]
    assert contradictory, "expected at least one student with a self_reported_status/completed_courses conflict"


def test_test_cases_cover_four_required_demo_classes():
    cases = kb_loader.load_test_cases(DATA_DIR / "test_cases.json")
    classes = {case["class"] for case in cases}
    assert REQUIRED_DEMO_CLASSES.issubset(classes)
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "test case ids must be unique"


def test_kb_loader_rejects_unknown_keys(tmp_path):
    bad_file = tmp_path / "courses.json"
    bad_file.write_text(
        json.dumps(
            {
                "courses": [
                    {
                        "code": "CS999",
                        "title": "Bad Course",
                        "credits": 3,
                        "mandatory": False,
                        "program": "CS",
                        "unexpected_field": "should trigger rejection",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(kb_loader.SchemaError):
        kb_loader.load_courses(bad_file)


def test_load_all_smoke():
    kb = kb_loader.load_all(DATA_DIR)
    assert set(kb.keys()) == {"courses", "prerequisites", "degree_rules", "students", "test_cases"}


@pytest.mark.parametrize(
    "call",
    [
        lambda: student_core.entails({}, "eligible(CS201)"),
        lambda: student_core.check_eligibility({}, "CS201", {}),
        lambda: student_core.missing_requirements({}, "CS201", {}),
    ],
)
def test_student_core_is_not_implemented(call):
    with pytest.raises(NotImplementedError):
        call()
