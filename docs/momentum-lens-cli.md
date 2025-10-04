# momentum_lens.sh Guide

This document describes how to work with the `momentum_lens.sh` launcher script after the structural refactor. It explains the available commands, the runtime checks performed before delegating to `momentum_cli`, and the environment variables you can use to customize the workflow.

## Overview

- Provides a stable entry point to the `momentum_cli` Python package from any directory.
- Resolves the script directory even when invoked through symlinks, so relative resources remain accessible.
- Locates an appropriate Python interpreter (virtual environment, user override, or system fallback).
- Verifies that the interpreter is Python 3.8+ and that the `momentum_cli` package can be imported, surfacing friendly errors when the environment is incomplete.
- Supports an explicit `help` command that skips Python checks, allowing you to inspect documentation even before the environment is ready.

## Command Summary

```
./momentum_lens.sh help                     # show command reference (no Python required)
./momentum_lens.sh                          # interactive menu (default action)
./momentum_lens.sh analyze [args...]        # non-interactive execution, args passed to momentum_cli
./momentum_lens.sh presets                  # list portfolio presets and exit
./momentum_lens.sh analysis-presets         # list analysis presets and exit
./momentum_lens.sh bundle-update            # update RQAlpha bundle (alias: update-bundle)
```

All unknown commands are forwarded directly to `python -m momentum_cli`, so any new sub-commands added by the Python package remain accessible without editing the shell script.

## Environment Detection

1. Determine the script directory, following symlinks to guarantee predictable relative paths.
2. Resolve the Python binary in the following order:
   - `MOMENTUM_PYTHON` (if set by the user).
   - `~/rqalpha_env/bin/python` (bundled virtual environment).
   - `python3`, then `python` on the current PATH.
3. Ensure the interpreter is executable and reports Python 3.8 or newer.
4. Unless explicitly skipped, import `momentum_cli` to fail fast when dependencies are missing.
5. Change to the project directory and dispatch the selected command, replacing the shell process with the Python module via `exec`.

## Environment Variables

- `MOMENTUM_PYTHON`: Absolute path to the Python interpreter that should run `momentum_cli`. Use this when the default virtual environment is missing or you prefer a different environment.
- `MOMENTUM_SKIP_IMPORT_CHECK`: Set to `1` to bypass the module import probe. This is useful in advanced automation when the Python environment is guaranteed to be correct and you want to avoid the extra process startup.

## Terminal Themes

The settings menu now ships with eight curated palettes inspired by international designers and artists. Each preset fine-tunes menu highlights, prompts, and alert colors:
- `aurora` – Bright cyan aurora hues for dark terminals.
- `ember` – Warm ember tones that pop on light backgrounds.
- `evergreen` – Muted greens for a calm, low-saturation look.
- `monet` – Pastel blue/pink gradients reminiscent of Monet’s water lilies.
- `bauhaus` – Crisp Bauhaus primaries with strong geometric contrast.
- `hokusai` – Indigo and sea-foam blues echoing Hokusai woodblock prints.
- `noir` – Film-noir monochrome with a cinematic orange accent.
- `rothko` – Layered crimson and ochre blocks inspired by Mark Rothko.

Select any theme via “终端主题与色彩”, and the choice persists in `cli_settings.json`.

## Usage Examples

- Run the interactive dashboard with the bundled virtual environment:
  `./momentum_lens.sh`
- Trigger a backtest preset without entering the menu:
  `./momentum_lens.sh analyze --preset core --run-backtest`
- Export the default strategy template:
  `./momentum_lens.sh analyze --preset core --export-strategy strategies/momentum_strategy.py`
- Inspect available presets prior to configuring automation:
  `./momentum_lens.sh presets`
- Download updated market data before running analyses:
  `./momentum_lens.sh bundle-update`

## Troubleshooting

- **"Python interpreter not found"**: Install Python 3.8+ or point `MOMENTUM_PYTHON` to an existing interpreter.
- **"momentum_cli module cannot be imported"**: Activate the virtual environment or reinstall dependencies (`pip install -r requirements.txt`). Override with `MOMENTUM_SKIP_IMPORT_CHECK=1` only when you are certain the module is installed.
- **Different project checkout path**: The script derives the project root by resolving its own location, so you can symlink or copy `momentum_lens.sh` anywhere. No additional configuration is required.
