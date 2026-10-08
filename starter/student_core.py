"""Graded AI core for Project 03 (Academic Rule and Prerequisite Advisor).

You implement this module. It must formalize the courses, prerequisite
rules, degree rules, and student facts loaded by `kb_loader.py` as a
propositional knowledge base, then answer queries by entailment /
inference over that knowledge base.

Do not hand-code the answer for a specific student or course: the
functions below must generalize to any knowledge base built from the
same `data/` schema.

Forbidden shortcuts (do not paste or adapt any of these into this file
or elsewhere in `starter/`):

- a working general-purpose resolution or model-checking engine copied
  from a library or from a previous course;
- a hard-coded lookup table keyed by student id that bypasses
  reasoning over the rules;
- calling a hosted LLM to decide eligibility instead of reasoning over
  the knowledge base yourself.
"""

from __future__ import annotations

from typing import Any


def entails(knowledge_base: dict[str, Any], query: str) -> bool | None:
    """Decide whether `knowledge_base` entails the proposition `query`.

    Parameters
    ----------
    knowledge_base:
        Whatever representation you choose to build from `courses`,
        `prerequisites`, `degree_rules`, and one student's facts
        (e.g. a set of propositional symbols plus a set of Horn
        clauses, a CNF sentence, or another representation from your
        required experiment).
    query:
        A proposition name, e.g. ``"completed(CS101)"`` or
        ``"eligible(CS220)"``. The exact symbol naming scheme is your
        design decision -- document it in your report.

    Returns
    -------
    True if the KB entails the query, False if the KB entails the
    negation of the query, or None if the KB has insufficient or
    contradictory information to decide (see `TC04` in
    `data/test_cases.json`).

    Raises
    ------
    NotImplementedError
        Always, until you implement this function.
    """
    raise NotImplementedError("Implement propositional entailment for Project 03.")


def check_eligibility(student: dict[str, Any], course: str, kb: dict[str, Any]) -> bool | None:
    """Decide whether `student` is eligible to take `course`.

    Parameters
    ----------
    student:
        One record from `students.json` (see `data/README.md`).
    course:
        A course code from `courses.json`, or the literal string
        ``"GRADUATION"`` to check the degree rules instead of a single
        course's prerequisites.
    kb:
        The loaded knowledge base (courses, prerequisites,
        degree_rules) from `kb_loader.load_all`.

    Returns
    -------
    True, False, or None (unknown/contradictory), matching the
    semantics of `entails`.

    Raises
    ------
    NotImplementedError
        Always, until you implement this function.
    """
    raise NotImplementedError("Implement eligibility checking for Project 03.")


def missing_requirements(student: dict[str, Any], course: str, kb: dict[str, Any]) -> list[str]:
    """List the propositions that are missing (or contradictory) for `student` to take `course`.

    This backs the "which proposition is missing" and "show the
    reasoning chain" presentation probes: the returned list should be
    exactly the facts an advisor would need to add (or resolve, if
    contradictory) to flip `check_eligibility` to True.

    Raises
    ------
    NotImplementedError
        Always, until you implement this function.
    """
    raise NotImplementedError("Implement missing-requirement detection for Project 03.")
