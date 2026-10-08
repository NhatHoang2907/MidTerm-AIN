"""Streamlit skeleton for Project 03 (Academic Rule and Prerequisite Advisor).

This page loads the knowledge base via `kb_loader.py` and lets the user
pick a sample student and a target course. It does **not** implement
prerequisite checking, entailment, or graduation reasoning -- it only
shows raw facts and then reports that the core is not implemented.
Fill `student_core.py` with your own reasoning to make this page useful.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import kb_loader
import student_core

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(page_title="Academic Rule and Prerequisite Advisor — starter", layout="wide")
st.title("Academic Rule and Prerequisite Advisor — starter")
st.markdown(
    "The **AI core is student work**. This page loads the knowledge base and "
    "lets you pick a student and a course, but it must not check "
    "prerequisites, entail graduation, or explain reasoning on its own."
)

try:
    kb = kb_loader.load_all(DATA_DIR)
except kb_loader.SchemaError as exc:
    st.error(f"Knowledge base failed to load: {exc}")
    st.stop()

students = kb["students"]
courses = kb["courses"]

with st.sidebar:
    st.header("Controls")
    student_labels = [f"{s['id']} — {s['name']}" for s in students]
    student_choice = st.selectbox("Sample student", student_labels)
    selected_student = students[student_labels.index(student_choice)]

    course_codes = [c["code"] for c in courses] + ["GRADUATION"]
    target_course = st.selectbox("Target course (or GRADUATION)", course_codes)

st.subheader("Selected student — raw facts")
st.json(selected_student)

st.subheader(f"Query: is {selected_student['id']} eligible for {target_course}?")

if st.button("Check eligibility"):
    try:
        result = student_core.check_eligibility(selected_student, target_course, kb)
        st.write(result)
    except NotImplementedError:
        st.info(
            "Core not implemented. Fill `entails`, `check_eligibility`, and "
            "`missing_requirements` in `starter/student_core.py` in your own code."
        )

st.subheader("Reasoning chain")
st.caption(
    "Once implemented, this section should show the propositions and rules "
    "used to reach the eligibility conclusion above (see the reasoning_probe "
    "field in data/test_cases.json)."
)
