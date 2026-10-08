# Data dictionary — Project 03

All data in this folder is **synthetic educational data** for a campus degree-audit exercise. Course codes, degree rules (credit thresholds, mandatory core, English exit), and student cohorts are fictional fixtures for this assignment. Every file is loaded and schema-checked by `starter/kb_loader.py`, which **rejects unknown top-level keys** on each record — treat that as a contract, not a suggestion, when you extend these files.

## `courses.json`

| Field | Type | Notes |
|---|---|---|
| `code` | string | Unique course code, e.g. `CS201`. |
| `title` | string | Human-readable course title. |
| `credits` | int | Credit weight of the course. |
| `mandatory` | bool | Whether the course is required for graduation (see `degree_rules.json`). |
| `program` | string | `"CS"` or `"GENED"`. |

## `prerequisites.json`

| Field | Type | Notes |
|---|---|---|
| `id` | string | Rule id, e.g. `PR08`. |
| `course` | string | The course code the rule gates. |
| `requires_all` | list[string] | Every listed course code must be completed first (conjunction). |
| `comment` | string, optional | Free-text explanation, e.g. mapping an informal name ("Python") to a course code. |

## `degree_rules.json`

| Field | Type | Notes |
|---|---|---|
| `mandatory_courses` | list[string] | Course codes that must all be completed for `DR02`. |
| `rules[].id` | string | Rule id, e.g. `DR01`. |
| `rules[].type` | string | `"credit_threshold"` or `"mandatory_courses_complete"`. |
| `rules[].min_total_credits` | int | Present on `credit_threshold` rules. |
| `rules[].ref` | string | Present on `mandatory_courses_complete` rules; points at the `mandatory_courses` list. |

Graduation is entailed only when **both** `DR01` and `DR02` hold.

## `students.json`

| Field | Type | Notes |
|---|---|---|
| `id` | string | Student id, e.g. `S001`. |
| `name` | string | Fictional name. |
| `completed_courses[].code` | string | Course code completed. |
| `completed_courses[].credits` | int | Credits earned for that course. |
| `completed_courses[].grade` | string | Letter grade, informational only. |
| `self_reported_status` | object | Maps a course code to a self-reported status string (e.g. `"in_progress"`). May directly conflict with `completed_courses` — that conflict is intentional for `S004`. |
| `declared_total_credits` | int or `null` | Total credits the student claims. `null` means the fact is unknown, not zero. |
| `notes` | string | Explains why the record is interesting for the reasoning demo. |

## `test_cases.json`

Four required demo classes, one fixture each: `enough_prereqs`, `missing_prereq`, `credits_without_mandatory`, `incomplete_conflicting_facts`. Each entry names a `student_id`, a `query_type` (`course_eligibility` or `graduation_check`), a `target_course` (a course code or the literal `"GRADUATION"`), and a `reasoning_probe` question your presentation should be able to answer live. `expected_behavior` is a qualitative description of correct reasoning, not a return value to hard-code — build your own `entails` / `check_eligibility` / `missing_requirements` logic against the rules above.

## Unknown-key policy

`kb_loader.py` raises `ValueError` if a record in any of these files contains a key not listed above (or in the matching loader's `ALLOWED_KEYS` set). If you add a field, update both this dictionary and the loader's allow-list in the same change.
