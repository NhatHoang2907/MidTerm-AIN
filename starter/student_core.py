"""Graded AI core for Project 03 (Academic Rule and Prerequisite Advisor).

The project requires exactly three public module-level functions:
`entails`, `check_eligibility`, and `missing_requirements`.
All other reasoning logic lives inside the internal `_Reasoner` class.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_COMPLETED_RE = re.compile(r"^completed\((?P<code>[^()]+)\)$")
_ELIGIBLE_RE = re.compile(r"^eligible\((?P<code>[^()]+)\)$")
_CREDITS_RE = re.compile(r"^(?:credits_at_least|declared_total_credits_at_least)\((?P<n>\d+)\)$")
_NEGATIVE_STATUSES = {"in_progress", "planned", "registered", "enrolled"}


class _Reasoner:
    def __init__(self, knowledge_base: dict[str, Any], student: dict[str, Any] | None = None):
        self.kb = knowledge_base if isinstance(knowledge_base, dict) else {}
        raw_student = student if isinstance(student, dict) else self.kb.get("student", {})
        self.student = raw_student if isinstance(raw_student, dict) else {}

        self.course_order = self._course_order_from_kb()
        self.catalog = set(self.course_order)
        self.prereq_map = self._prereq_map_from_kb()
        self.degree_rules = self._degree_rules_from_kb()
        self.mandatory_courses = self._mandatory_courses_from_degree_rules()
        self.credit_threshold = self._extract_credit_threshold()
        self.english_exit_course = self._extract_english_exit_course()

        self.completed_courses = self._student_completed_courses()
        self.status_map = self._student_statuses()
        self.derived_facts = self._forward_chain_facts()
        self.prereq_closure = self._compute_prereq_closure()

    def _extract_credit_threshold(self) -> int:
        for rule in self.degree_rules.get("rules", []):
            if isinstance(rule, dict) and rule.get("type") == "credit_threshold" and isinstance(rule.get("min_total_credits"), int):
                return rule["min_total_credits"]
        return 135

    def _course_order_from_kb(self) -> list[str]:
        courses = self.kb.get("courses", [])
        return [course["code"] for course in courses if isinstance(course, dict) and isinstance(course.get("code"), str)]

    def _prereq_map_from_kb(self) -> dict[str, tuple[str, ...]]:
        prereq_map: dict[str, tuple[str, ...]] = {}
        for rule in self.kb.get("prerequisites", []):
            if not isinstance(rule, dict):
                continue
            course = rule.get("course")
            requires_all = rule.get("requires_all", [])
            if not isinstance(course, str):
                continue
            seen: list[str] = []
            for req in requires_all:
                if isinstance(req, str) and req not in seen:
                    seen.append(req)
            prereq_map[course] = tuple(seen)
        return prereq_map

    def _degree_rules_from_kb(self) -> dict[str, Any]:
        degree_rules = self.kb.get("degree_rules", {})
        if isinstance(degree_rules, dict):
            return degree_rules
        return {}

    def _mandatory_courses_from_degree_rules(self) -> list[str]:
        return [c for c in self.degree_rules.get("mandatory_courses", []) if isinstance(c, str)]

    def _extract_english_exit_course(self) -> str | None:
        for rule in self.degree_rules.get("rules", []):
            if isinstance(rule, dict) and rule.get("type") == "english_exit_clearance":
                represented_by = rule.get("represented_by")
                if isinstance(represented_by, str):
                    return represented_by
        return None

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
        return {
            code: status
            for code, status in raw.items()
            if isinstance(code, str) and isinstance(status, str)
        }

    def _completion_state(self, course: str) -> bool | None:
        positive = course in self.completed_courses or self.status_map.get(course) == "completed"
        negative = self.status_map.get(course) in _NEGATIVE_STATUSES

        if positive and negative:
            return None
        if positive:
            return True
        if negative:
            return False
        if course in self.catalog:
            return False
        if course in self.completed_courses or course in self.status_map:
            return False
        return None

    def _credit_state(self, minimum: int) -> bool | None:
        declared = self.student.get("declared_total_credits", None)
        if declared is None:
            return None
        if not isinstance(declared, int):
            return None
        return declared >= minimum

    def _parse_query(self, query: str) -> tuple[str, str | None]:
        query = query.strip()
        if query in {"GRADUATION", "graduated"}:
            return ("graduation", None)
        completed = _COMPLETED_RE.match(query)
        if completed:
            return ("completed", completed.group("code"))
        eligible = _ELIGIBLE_RE.match(query)
        if eligible:
            target = eligible.group("code")
            if target == "GRADUATION":
                return ("graduation", None)
            return ("eligible", target)
        credits_match = _CREDITS_RE.match(query)
        if credits_match:
            return ("credits", credits_match.group("n"))
        return ("unknown", None)

    def _base_facts(self) -> set[str]:
        facts: set[str] = set()
        for course in self.course_order:
            if course in self.completed_courses or self.status_map.get(course) == "completed":
                facts.add(f"completed({course})")
        if self._credit_state(self.credit_threshold) is True:
            facts.add(f"credits_ok({self.credit_threshold})")
        return facts

    def _build_rules(self) -> list[tuple[str, tuple[str, ...]]]:
        rules: list[tuple[str, tuple[str, ...]]] = []
        for course in self.course_order:
            prereqs = self.prereq_map.get(course, ())
            rules.append((f"eligible({course})", tuple(f"completed({req})" for req in prereqs)))

        graduation_antecedents = [f"credits_ok({self.credit_threshold})"]
        graduation_antecedents.extend(f"completed({course})" for course in self.mandatory_courses)
        if self.english_exit_course:
            graduation_antecedents.append(f"completed({self.english_exit_course})")
        rules.append(("graduated", tuple(graduation_antecedents)))
        return rules

    def _apply_forward_chain(self, facts: set[str], rules: list[tuple[str, tuple[str, ...]]]) -> set[str]:
        agenda = list(facts)
        remaining = [len(antecedents) for _head, antecedents in rules]
        watchers, derived = self._index_rules(rules, agenda, remaining, facts)

        while agenda:
            self._advance_forward_chain(agenda.pop(), watchers, remaining, rules, derived, agenda)

        return derived

    def _index_rules(
        self,
        rules: list[tuple[str, tuple[str, ...]]],
        agenda: list[str],
        remaining: list[int],
        facts: set[str],
    ) -> tuple[dict[str, list[int]], set[str]]:
        watchers: dict[str, list[int]] = defaultdict(list)
        derived = set(facts)
        for idx, (_head, antecedents) in enumerate(rules):
            if not antecedents:
                head = rules[idx][0]
                if head not in derived:
                    derived.add(head)
                    agenda.append(head)
                remaining[idx] = 0
                continue
            for antecedent in antecedents:
                watchers[antecedent].append(idx)
        return watchers, derived

    def _advance_forward_chain(
        self,
        fact: str,
        watchers: dict[str, list[int]],
        remaining: list[int],
        rules: list[tuple[str, tuple[str, ...]]],
        derived: set[str],
        agenda: list[str],
    ) -> None:
        for rule_index in watchers.get(fact, []):
            if remaining[rule_index] <= 0:
                continue
            remaining[rule_index] -= 1
            head, _ = rules[rule_index]
            if remaining[rule_index] == 0 and head not in derived:
                derived.add(head)
                agenda.append(head)

    def _forward_chain_facts(self) -> set[str]:
        return self._apply_forward_chain(self._base_facts(), self._build_rules())

    def _compute_prereq_closure(self) -> dict[str, tuple[str, ...]]:
        closure: dict[str, set[str]] = {course: set(reqs) for course, reqs in self.prereq_map.items()}
        changed = True
        while changed:
            changed = False
            for course in self.course_order:
                current = closure.setdefault(course, set())
                before = set(current)
                for req in before:
                    current.update(closure.get(req, set()))
                if course in current:
                    current.discard(course)
                if current != before:
                    changed = True
        return {course: tuple(reqs) for course, reqs in closure.items()}

    def _direct_state(self, course: str) -> bool | None:
        return self._completion_state(course)

    def _missing_chain(self, course: str, seen: set[str], output: list[str]) -> None:
        if course in seen:
            return
        seen.add(course)
        for req in self.prereq_map.get(course, ()):
            state = self._direct_state(req)
            if state is True:
                continue
            if state is None:
                item = f"resolve(completed({req}))"
            else:
                item = f"completed({req})"
            if item not in output:
                output.append(item)
            self._missing_chain(req, seen, output)

    def _graduation_requirements(self) -> list[str]:
        requirements = list(self.mandatory_courses)
        if self.english_exit_course and self.english_exit_course not in requirements:
            requirements.append(self.english_exit_course)
        return requirements

    def _missing_requirements_for_course(self, course: str) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for req in self.prereq_map.get(course, ()):
            state = self._direct_state(req)
            if state is True:
                continue
            token = f"resolve(completed({req}))" if state is None else f"completed({req})"
            if token not in output:
                output.append(token)
            self._missing_chain(req, seen, output)
        return output

    def _missing_requirements_for_graduation(self) -> list[str]:
        output: list[str] = []
        credit_state = self._credit_state(self.credit_threshold)
        if credit_state is None:
            output.append("resolve(declared_total_credits)")
        elif credit_state is False:
            output.append(f"credits_at_least({self.credit_threshold})")

        seen: set[str] = set()
        for requirement in self._graduation_requirements():
            state = self._direct_state(requirement)
            if state is True:
                continue
            token = f"resolve(completed({requirement}))" if state is None else f"completed({requirement})"
            if token not in output:
                output.append(token)
            self._missing_chain(requirement, seen, output)
        return output

    def _evaluate_eligibility(self, course: str) -> bool | None:
        if course not in self.catalog:
            return None
        prereqs = self.prereq_map.get(course, ())
        if not prereqs:
            return True

        saw_missing = False
        for req in prereqs:
            state = self._direct_state(req)
            if state is None:
                return None
            if state is False:
                saw_missing = True
        if saw_missing:
            return False
        return f"eligible({course})" in self.derived_facts

    def _evaluate_graduation(self) -> bool | None:
        credit_state = self._credit_state(self.credit_threshold)
        if credit_state is None:
            return None
        if credit_state is False:
            return False

        for requirement in self._graduation_requirements():
            state = self._direct_state(requirement)
            if state is None:
                return None
            if state is False:
                return False
        return "graduated" in self.derived_facts

    def entails(self, query: str) -> bool | None:
        kind, arg = self._parse_query(query)
        if kind == "completed" and arg is not None:
            return self._direct_state(arg)
        if kind == "eligible" and arg is not None:
            return self._evaluate_eligibility(arg)
        if kind == "graduation":
            return self._evaluate_graduation()
        if kind == "credits" and arg is not None:
            try:
                threshold = int(arg)
            except ValueError:
                return None
            return self._credit_state(threshold)
        return None

    def missing_requirements(self, course: str) -> list[str]:
        if course not in self.catalog and course != "GRADUATION":
            return []
        if course == "GRADUATION":
            return self._missing_requirements_for_graduation()
        return self._missing_requirements_for_course(course)


def entails(knowledge_base: dict[str, Any], query: str) -> bool | None:
    """Decide whether `knowledge_base` entails the proposition `query`."""
    reasoner = _Reasoner(knowledge_base)
    return reasoner.entails(query)


def check_eligibility(student: dict[str, Any], course: str, kb: dict[str, Any]) -> bool | None:
    """Decide whether `student` is eligible to take `course`."""
    reasoner = _Reasoner({**(kb if isinstance(kb, dict) else {}), "student": student if isinstance(student, dict) else {}} , student)
    if course == "GRADUATION":
        return reasoner.entails("GRADUATION")
    return reasoner.entails(f"eligible({course})")


def missing_requirements(student: dict[str, Any], course: str, kb: dict[str, Any]) -> list[str]:
    """List the propositions that are missing (or contradictory) for `student` to take `course`."""
    reasoner = _Reasoner({**(kb if isinstance(kb, dict) else {}), "student": student if isinstance(student, dict) else {}} , student)
    return reasoner.missing_requirements(course)
