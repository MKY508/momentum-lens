# Momentum Lens Project Structure

## Overview

Momentum Lens is a CLI tool for ETF momentum analysis with a clean 4-layer architecture.

## Directory Structure

```
momentum-lens-github/
├── momentum_cli/                 # Main package
│   ├── cli.py                   # CLI entry point (5009 lines)
│   │
│   ├── commands/                # Menu command handlers
│   │   ├── __init__.py
│   │   ├── about.py            # About page display
│   │   ├── backtest_menu.py    # Backtest tools menu
│   │   ├── history_menu.py     # Report history browser
│   │   ├── settings_menu.py    # Settings and tools
│   │   └── templates_menu.py   # Template management
│   │
│   ├── business/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── alerts.py           # Alert detection (correlation, rank drops)
│   │   ├── analysis.py         # Analysis execution and orchestration
│   │   ├── analysis_presets.py # Analysis preset display functions
│   │   ├── backtest.py         # Backtest logic
│   │   ├── bundle.py           # Data bundle management
│   │   ├── config.py           # Configuration management (498 lines)
│   │   ├── history.py          # History management
│   │   ├── reports.py          # Report generation and formatting
│   │   └── templates.py        # Template CRUD operations
│   │
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   ├── colors.py           # Color and styling utilities
│   │   ├── display.py          # Display formatting
│   │   ├── formatters.py       # Data formatters (summary tables, etc.)
│   │   └── helpers.py          # Helper functions (dedup, label formatting)
│   │
│   ├── ui/                     # UI components
│   │   ├── __init__.py
│   │   ├── input.py            # Input handling and key reading
│   │   ├── interactive.py      # Interactive menu system
│   │   └── menu.py             # Menu utilities
│   │
│   ├── analysis.py             # Core analysis engine
│   ├── analysis_presets.py     # Analysis preset definitions
│   ├── backtest.py             # Backtest engine
│   ├── indicators.py           # Technical indicators
│   ├── presets.py              # Code presets (core, satellite, etc.)
│   └── ...                     # Other core modules
│
├── tests/                      # Test suite
├── docs/                       # Documentation
├── ARCHITECTURE.md             # Architecture documentation
├── PROJECT_STRUCTURE.md        # This file
└── README.md                   # Project README
```

## Module Responsibilities

### Core Modules

#### `cli.py` (5009 lines)
- Main entry point (`main()`)
- Command-line argument parsing (`build_parser()`)
- Global state management
- Thin wrappers for business logic
- Interactive mode coordination

**Key Statistics:**
- 165 functions
- 82 constants
- 92 import statements
- 4211 effective code lines

#### `analysis.py`
- Core momentum analysis engine
- ETF data processing
- Indicator calculations

#### `backtest.py`
- Backtesting framework
- Strategy simulation
- Performance metrics

#### `indicators.py`
- Technical indicators (ADX, Chop, etc.)
- Momentum calculations
- Stability metrics

### Commands Layer

Menu handlers that:
- Display menu options
- Handle user navigation
- Delegate to business layer
- Manage menu state

### Business Layer

Pure business logic:
- **alerts.py**: Detect high correlation, rank drops
- **analysis.py**: Orchestrate analysis execution
- **analysis_presets.py**: Display preset information
- **backtest.py**: Backtest execution logic
- **bundle.py**: Data bundle download/update
- **config.py**: Settings management (360+ lines)
- **history.py**: Report history management
- **reports.py**: Report generation, formatting, payload building
- **templates.py**: Template CRUD, validation

### Utils Layer

Stateless helpers:
- **colors.py**: ANSI color codes, theme management
- **display.py**: Display utilities
- **formatters.py**: Data formatting (tables, summaries)
- **helpers.py**: Common helpers (dedup, label formatting)

### UI Layer

Interactive components:
- **input.py**: Keyboard input, key reading
- **interactive.py**: Menu rendering, navigation
- **menu.py**: Menu utilities

## Design Patterns

### 1. Thin Wrapper Pattern

CLI functions act as thin wrappers:
```python
def _configure_plot_style() -> None:
    global _PLOT_TEMPLATE, _PLOT_LINE_WIDTH
    
    def set_template(template: str) -> None:
        global _PLOT_TEMPLATE
        _PLOT_TEMPLATE = template
        _update_setting(_SETTINGS, "plot_template", _PLOT_TEMPLATE)
    
    _biz_config_plot_style(
        current_template=_PLOT_TEMPLATE,
        set_template_func=set_template,
        prompt_menu_choice_func=_prompt_menu_choice,
        colorize_func=colorize,
    )
```

### 2. Callback Injection

Business layer receives callbacks:
- `colorize_func`: Styling
- `prompt_func`: User input
- `setter_func`: State updates
- `format_func`: Data formatting

### 3. Separation of Concerns

- **CLI**: Coordination, state, thin wrappers
- **Commands**: Menu flows, navigation
- **Business**: Pure logic, no UI
- **Utils**: Stateless helpers
- **UI**: Reusable components

## Refactoring History

### Completed Phases

**Phase 1: Display/Formatting Functions** (-471 lines)
- Migrated 8 functions to business layer
- Largest: `build_strategy_gate_entries` (268 lines)

**Phase 3: Configuration Functions** (-371 lines)
- Migrated 6 configuration functions
- Created `business/config.py` (498 lines)
- Created `business/bundle.py`

**Phase 4: Analysis Functions** (-43 lines)
- Migrated `run_quick_analysis`

### Progress

| Metric | Value |
|--------|-------|
| Original | 5819 lines |
| Current | 5009 lines |
| Reduced | 810 lines (13.9%) |
| Target | < 2000 lines |
| Remaining | ~3009 lines to reduce |

### Key Achievements

1. ✅ Fixed interactive menu UI issues
2. ✅ Established 4-layer architecture
3. ✅ Migrated 15 major functions
4. ✅ Created 4 new business modules
5. ✅ Maintained 100% functionality

## Development Guidelines

### Adding Features

1. Place logic in appropriate layer
2. Use callback injection for dependencies
3. Create thin wrapper in CLI if needed
4. Keep UI concerns separate

### Refactoring

1. Identify business logic vs coordination
2. Extract to appropriate module
3. Create thin wrapper with callbacks
4. Test functionality
5. Commit incrementally

### Testing

- Unit tests for business logic
- Integration tests for workflows
- Manual testing for UI/UX

## Future Improvements

### Short Term
- Migrate remaining large functions
- Extract constants to config module
- Simplify main entry functions

### Long Term
- Add comprehensive test coverage
- Improve error handling
- Add plugin system
- Support more data sources

