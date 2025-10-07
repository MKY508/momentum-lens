# Momentum Lens CLI Architecture

## Project Structure

```
momentum_cli/
├── cli.py (5009 lines)          # Main CLI entry point and coordination
│
├── commands/                     # Menu command handlers
│   ├── __init__.py
│   ├── about.py                 # About page
│   ├── backtest_menu.py         # Backtest tools menu
│   ├── history_menu.py          # Report history menu
│   ├── settings_menu.py         # Settings and tools menu
│   └── templates_menu.py        # Template management menu
│
├── business/                     # Business logic layer
│   ├── __init__.py
│   ├── alerts.py                # Alert detection logic
│   ├── analysis.py              # Analysis execution
│   ├── analysis_presets.py      # Analysis preset display
│   ├── backtest.py              # Backtest logic
│   ├── bundle.py                # Data bundle management
│   ├── config.py                # Configuration management (360 lines)
│   ├── history.py               # History management
│   ├── reports.py               # Report generation and formatting
│   └── templates.py             # Template management
│
├── utils/                        # Utility functions
│   ├── __init__.py
│   ├── colors.py                # Color and styling
│   ├── display.py               # Display utilities
│   ├── formatters.py            # Data formatting
│   └── helpers.py               # Helper functions
│
├── ui/                           # UI components
│   ├── __init__.py
│   ├── input.py                 # Input handling
│   ├── interactive.py           # Interactive menu system
│   └── menu.py                  # Menu utilities
│
├── analysis.py                   # Core analysis engine
├── analysis_presets.py           # Analysis preset definitions
├── backtest.py                   # Backtest engine
├── indicators.py                 # Technical indicators
├── presets.py                    # Code presets
└── ...                           # Other modules
```

## Layer Responsibilities

### CLI Layer (`cli.py`)
- Command-line argument parsing
- Main entry point and coordination
- Global state management
- Thin wrappers calling business layer

### Commands Layer (`commands/`)
- Menu navigation and display
- User interaction flows
- Delegates to business layer for logic

### Business Layer (`business/`)
- Core business logic
- Data processing and validation
- Analysis execution
- Report generation
- Configuration management

### Utils Layer (`utils/`)
- Formatting and display helpers
- Color and styling utilities
- Common helper functions

### UI Layer (`ui/`)
- Interactive menu system
- Input handling
- Display components

## Design Patterns

### Thin Wrapper Pattern
CLI functions act as thin wrappers that:
1. Gather current state/configuration
2. Call business layer with callbacks
3. Handle global state updates

Example:
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

### Callback Injection
Business layer receives callbacks to avoid circular dependencies:
- `colorize_func`: For styling output
- `prompt_func`: For user input
- `setter_func`: For state updates
- `format_func`: For data formatting

## Refactoring Progress

### Completed
- ✅ Phase 1: Display/Formatting Functions (-471 lines)
- ✅ Phase 3: Configuration Functions (-371 lines)
- ✅ Phase 4 (partial): Analysis Functions (-43 lines)

### Current Status
- **Original**: 5819 lines
- **Current**: 5009 lines
- **Reduced**: 810 lines (13.9%)
- **Target**: < 2000 lines

### Remaining Work
- Simplify main entry functions
- Migrate remaining analysis/backtest functions
- Migrate large helper functions
- Extract constants to config module

## Key Achievements

1. **Fixed UI Issues**: Interactive menu rendering is stable
2. **Clear Architecture**: 4-layer separation (commands/business/utils/ui)
3. **Migrated 13 Functions**: Including largest 268-line function
4. **Created 4 New Modules**: alerts, analysis_presets, config, bundle
5. **Maintained Functionality**: All migrations use thin wrappers

## Development Guidelines

### Adding New Features
1. Place business logic in `business/` layer
2. Create thin wrapper in `cli.py` if needed
3. Use callback injection for dependencies
4. Keep UI concerns in `ui/` or `commands/`

### Refactoring Existing Code
1. Identify business logic vs UI/coordination
2. Extract business logic to appropriate module
3. Create thin wrapper with callbacks
4. Test functionality preservation
5. Commit incrementally

### Module Organization
- **business/**: Pure logic, no direct UI calls
- **commands/**: Menu flows, delegates to business
- **utils/**: Stateless helpers
- **ui/**: Reusable UI components
- **cli.py**: Coordination and global state

