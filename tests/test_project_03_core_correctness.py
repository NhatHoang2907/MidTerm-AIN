from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STARTER_DIR = PROJECT_ROOT / "starter"


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


kb_loader = _load_module("project03_kb_loader_correctness", STARTER_DIR / "kb_loader.py")
student_core = _load_module("project03_student_core_correctness", STARTER_DIR / "student_core.py")
benchmark = _load_module("project03_benchmark_correctness", PROJECT_ROOT / "benchmark_student_core.py")

KB = kb_loader.load_all(DATA_DIR)
STUDENTS = {student["id"]: student for student in KB["students"]}


def test_tc01_eligibility_true_and_no_missing_requirements():
    student = STUDENTS["S001"]
    assert student_core.check_eligibility(student, "AIN301", KB) is True
    assert student_core.missing_requirements(student, "AIN301", KB) == []
    assert student_core.entails({**KB, "student": student}, "eligible(AIN301)") is True


def test_tc02_missing_prerequisites_are_traced_recursively():
    student = STUDENTS["S002"]
    result = student_core.check_eligibility(student, "AIN301", KB)
    assert result is False
    missing = student_core.missing_requirements(student, "AIN301", KB)
    assert "completed(DSA201)" in missing
    assert "completed(STA201)" in missing
    assert all("AIN301" not in item for item in missing)


def test_tc03_graduation_flags_credit_and_mandatory_gaps():
    student = STUDENTS["S003"]
    assert student_core.check_eligibility(student, "GRADUATION", KB) is False
    missing = student_core.missing_requirements(student, "GRADUATION", KB)
    assert "credits_at_least(135)" in missing
    assert any("AIN301" in item for item in missing)
    assert any("ENG301" in item for item in missing)


def test_tc04_contradiction_returns_none_for_eligibility_and_graduation():
    student = STUDENTS["S004"]
    assert student_core.check_eligibility(student, "AIN301", KB) is None
    assert student_core.check_eligibility(student, "GRADUATION", KB) is None
    missing = student_core.missing_requirements(student, "AIN301", KB)
    assert any("CPR101" in item for item in missing)
    assert any(item.startswith("resolve(") for item in missing)


def test_completed_queries_and_unknown_course_semantics():
    student = STUDENTS["S001"]
    kb_with_student = {**KB, "student": student}
    assert student_core.entails(kb_with_student, "completed(CPR101)") is True
    assert student_core.entails(kb_with_student, "completed(DBS201)") is False
    assert student_core.check_eligibility(student, "NOPE999", KB) is None
    assert student_core.missing_requirements(student, "NOPE999", KB) == []


def test_benchmark_writes_csv(tmp_path):
    output_csv = tmp_path / "benchmark.csv"
    rc = benchmark.main(["--repeats", "1", "--csv", str(output_csv)])
    assert rc == 0
    assert output_csv.exists()
    with output_csv.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "benchmark CSV should contain rows"
    assert {"student_id", "query", "fc_state", "tt_state", "agreement"}.issubset(rows[0].keys())



