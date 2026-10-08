# Project 03 — Academic Rule and Prerequisite Advisor

## 1. Problem Description

Knowledge Representation and Reasoning (KRR) is a foundational discipline of Artificial Intelligence focused on encoding domain knowledge into formal logic to enable autonomous deduction of implicit facts. In higher-education administration, verifying curriculum progression and graduation readiness requires logical entailment over complex course dependency graphs, credit accumulation thresholds, and institutional graduation rules.

This project builds an automated, logic-based academic advisory system. Students formalise synthetic degree rules using Propositional Logic, construct a formal Knowledge Base (KB), and implement inference engines from first principles to evaluate course eligibility and graduation readiness with complete, traceable proof chains. The synthetic curriculum targets approximately 135 academic credits across foundational computing, data structures, algorithms, and capstone work (course IDs appear as data keys in `data/courses.json`).

---

## 2. Provided Materials & Starter Resources

The project provides synthetic curriculum datasets, loader utilities, and a skeleton Streamlit interface.

### File Structure
```text
project-03-academic-advisor/
├── data/
│   ├── README.md                 # Data dictionary and schema definitions
│   ├── courses.json              # Course catalog with IDs, names, and credit values
│   ├── prerequisites.json        # Prerequisite dependency rules (PR01–PR11)
│   ├── degree_rules.json         # Graduation policies (135 credits, mandatory core, English C1)
│   ├── students.json             # Synthetic academic transcripts across cohorts K21–K24
│   └── test_cases.json           # Benchmark fixtures (TC01–TC04)
├── starter/
│   ├── kb_loader.py              # Schema-validated JSON loaders (provided; do not modify)
│   ├── student_core.py           # Algorithmic stubs — implement here
│   └── app.py                   # Streamlit web application skeleton (provided)
├── tests/
│   └── test_project_03_sanity.py
└── requirements.txt
```

### Starter Infrastructure vs. Student Implementation
`starter/kb_loader.py` handles input deserialization and schema validation. `starter/app.py` renders the dashboard. Students implement all AI logic in `starter/student_core.py`.

### Installation and Execution
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run starter/app.py
```

---

## 3. Requirements & Deliverables

### 3.1 Midterm Milestone — AI Core
- **Implement**: `entails`, `check_eligibility`, and `missing_requirements` in `starter/student_core.py` from first principles (Forward Chaining, TT-Entails, DPLL, or Resolution). Third-party theorem provers and LLM APIs are prohibited. The engine must return ternary truth states (`True`, `False`, or `None` for ambiguous/conflicting data) and produce traceable proof chains.
- **Experiment**: Empirically compare at least two distinct inference paradigms (e.g., Horn-clause Forward Chaining vs. CNF Model Checking). Measure wall-clock latency, memory use, and proof-tree depth across all student profiles. Explicitly analyse performance on the contradictory-record edge case (`TC04`).
- **Deliverables**: Completed `student_core.py`, benchmarking notebook or script, `presentation.pdf`.
- **Grading Criteria**: Problem formalisation and inference soundness (15 pts); experimental comparison and edge-case handling (10 pts); oral defence and live proof demo (15 pts). **Total: 40 pts.**

### 3.2 Final Milestone — AI Product
- **Interactive Application**: Streamlit advisor that lets users select student transcripts from `data/students.json`, inspect credit progression toward the 135-credit threshold, audit course eligibility or graduation readiness, and view step-by-step reasoning chains.
- **Stress Scenarios**: Reliably diagnose all four benchmark cases in `data/test_cases.json`: fully qualified students (`TC01`), missing prerequisite chains (`TC02`), credit deficits with missing mandatory courses (`TC03`), and incomplete or conflicting records (`TC04`).
- **Deliverables**: Fully operational Streamlit application, GitHub repository, `report.pdf` (IEEE format).
- **Grading Criteria**: Product UI, explanation transparency, and software ergonomics (25 pts); technical report, formal logic formulation, and empirical analysis (15 pts); oral defence against complex curriculum queries (10 pts). **Total: 50 pts.**

---

## 4. References

- [1] S. Russell and P. Norvig, *Artificial Intelligence: A Modern Approach*, 4th ed. Hoboken, NJ, USA: Pearson, 2020, pp. 208–251.
- [2] M. Davis, G. Logemann, and D. Loveland, "A machine program for theorem-proving," *Communications of the ACM*, vol. 5, no. 7, pp. 394–397, 1962, doi: 10.1145/368273.368557.
- [3] J. A. Robinson, "A machine-oriented logic based on the resolution principle," *Journal of the ACM*, vol. 12, no. 1, pp. 23–41, 1965, doi: 10.1145/321250.321253.
