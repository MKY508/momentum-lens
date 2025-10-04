# Repository Guidelines

## Project Structure & Module Organization
- `momentum_cli/`: Core Python package with CLI logic, analysis presets, and data loading utilities.
- `scripts/`: Maintenance helpers (`setup.sh`, `link_cli.sh`) for environment creation and PATH linking.
- `results/`: Generated reports and Plotly HTML charts (ignored by Git).
- `strategies/`: Auto-exported RQAlpha strategies; cleaned via settings menu.
- Root files include `momentum_lens.sh` (entrypoint), `requirements.txt`, and documentation (`README.md`, `AGENTS.md`).

## Build, Test, and Development Commands
- `./scripts/setup.sh`: Create `.venv` and install dependencies.
- `source .venv/bin/activate`: Activate virtual environment for development.
- `momentum-lens` or `./momentum_lens.sh`: Launch CLI in interactive mode.
- `momentum-lens analyze --preset core --no-plot`: Run a non-interactive analysis using preset parameters.

## Coding Style & Naming Conventions
- Python source uses 4-space indentation and type hints where practical.
- Modules follow snake_case (`data_loader.py`, `analysis_presets.py`); classes use PascalCase (e.g., `AnalysisPreset`).
- Keep user-facing text bilingual-friendly (Chinese primary, concise English alternatives).
- Persistent settings are JSON-formatted and stored next to modules.

## Testing Guidelines
- No automated test suite yet; rely on manual CLI runs (`momentum` quick analysis, chart generation) after modifications.
- When adding tests, place under `tests/` (create directory) and adopt `pytest` naming (`test_*.py`).
- Validate Plotly outputs by opening the latest `results/momentum_*_interactive.html` and verifying legend toggles.

## Commit & Pull Request Guidelines
- Use descriptive commits (e.g., `Add rank-drop alert detection`), grouping related changes.
- Ensure `git status` is clean (no generated artefacts) before committing.
- Pull requests should include: summary of changes, manual verification steps, and screenshots for UI/plot tweaks when applicable.
- Link related issues in the PR description and flag any new dependencies or setup steps.
