# ears-trace

[日本語版 / Japanese README](./README.ja.md)

A Python CLI tool that mechanically visualizes test gaps starting from requirements written in EARS notation (`requirements.md`).

ears-trace automates the "next step" after Spec-driven development. Once you have written your requirements, it shows — as a traceability table — which requirements are covered by tests and which are **untested gaps**.

Built for the **Kiro University Challenge** as the final project, demonstrating all 7 lessons plus a bonus.

## What it does

1. **Traceability report** — visualizes requirement ID ↔ test mapping as a self-contained HTML report
2. **Coverage check** — detects requirements with no linked test (gaps); can fail CI
3. **pytest stub generation** — generates test skeletons for uncovered requirements

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Generate an HTML traceability report
ears-trace report --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ -o out/traceability.html

# Check coverage (non-zero exit if gaps exist and coverage is below the threshold — for CI)
ears-trace check --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ --min-coverage 0.8

# Generate pytest stubs for uncovered requirements
ears-trace generate --requirements .kiro/specs/ears-trace/requirements.md --tests tests/ -o tests/test_generated_stubs.py

# Optional: enrich the report with EARS pattern annotations fetched via MCP (see docs/mcp-enrich-workflow.md)
ears-trace report --requirements <req.md> --tests tests/ -o out/traceability.html --enrich out/annotations.json
```

## Linking tests to requirements

Declare a requirement ID in your pytest tests in any of three ways:

```python
import pytest


# 1. Marker
@pytest.mark.requirement("R-02")
def test_invalid_form_shows_errors() -> None: ...


# 2. Naming convention (test_r02_... -> R-02)
def test_r02_invalid_form() -> None: ...


# 3. docstring tag
def test_something() -> None:
    """req: R-02"""
    ...
```

## EARS patterns

| Pattern | Syntax |
|---|---|
| Ubiquitous | `THE SYSTEM SHALL <response>` |
| Event | `WHEN <trigger> THE SYSTEM SHALL <response>` |
| State | `WHILE <state> THE SYSTEM SHALL <response>` |
| Unwanted | `IF <condition> THEN THE SYSTEM SHALL <response>` |
| Optional | `WHERE <feature> THE SYSTEM SHALL <response>` |

## Development

```bash
pytest --cov=src/ears_trace --cov-report=term-missing   # 175 tests, 99% coverage
ruff check .
```

## Kiro University Challenge — how each lesson is incorporated

This project is built with Kiro as the primary development tool. The `.kiro/` folder contains the evidence for each lesson.

| Lesson | Feature | Where in this repo |
|---|---|---|
| **L1 Spec-driven development** | Feature specs (requirements → design → tasks) | `.kiro/specs/ears-trace/{requirements,design,tasks}.md` — the tool's own requirements written in EARS (dogfooding), authored in Kiro IDE Spec mode |
| **L2 Steering** | Persistent project knowledge | `.kiro/steering/{ears-vocabulary,report-format,python-conventions}.md` — conventions that steer code generation |
| **L3 Hooks** | Event-driven automation | `.kiro/hooks/{retrace-on-save,lint-on-save}.json` — re-trace on requirements save; Ruff on Python save |
| **L4 Property-based testing** (IDE only) | Hypothesis PBT from spec | `tests/test_properties_*.py` — properties P1–P7 (partition, monotonicity, determinism, parser robustness, …), each tagged with its requirement ID. Run in Kiro IDE |
| **L5 Powers** | Reuse an installed power | `docs/l5-powers/` — used `spec-driven-presentation-maker` power to turn the coverage result into a slide deck |
| **L6 MCP** | External MCP server at runtime | `.kiro/settings/mcp.json` (fetch) + `src/ears_trace/enrich.py` — `--enrich` embeds EARS annotations fetched via MCP; see `docs/mcp-enrich-workflow.md` |
| **L7 Custom agents** | Purpose-built, least-privilege agent | `.kiro/agents/requirements-reviewer.json` — read-only reviewer (read/glob/grep only, write excluded, shell limited to `ears-trace`) |
| **Bonus2 Package a power** | Author your own power | `powers/ears-trace-power/` — plugin.json + skill packaging ears-trace itself |
| **Bonus1 Cloud sessions** | Kiro Web / cloud config | Build run (tests + self-trace) executed in a cloud session with synced local `.kiro` configuration |

### Dogfooding

ears-trace traces **its own** requirements: `ears-trace report --requirements .kiro/specs/ears-trace/requirements.md --tests tests/` yields 50/50 (100%) self-coverage. A parser edge case found this way (inline-code `` `SHALL` `` false positives) is documented and fixed in `docs/known-issues.md` (KI-01).

## License

MIT
