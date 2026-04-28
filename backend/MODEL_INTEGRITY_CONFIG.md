# Model Integrity Configuration

## Overview

This project enforces strict model integrity requirements to ensure that all valuation models (DCF, Trading Comps, DuPont Analysis) maintain their completeness and accuracy. This is mandated by the [MODEL_INTEGRITY_MANIFESTO.md](../MODEL_INTEGRITY_MANIFESTO.md).

## Reference Documentation

All model specifications are stored in the `excel models/` directory:

- **DCF_Model_Documentation.txt** - Complete DCF model specification
- **Comps_Model_Documentation.txt** - Trading comparables model specification  
- **dupont.txt** - DuPont analysis model specification

These files serve as the **single source of truth** for all model implementations.

## Automatic Validation

### Pre-commit Hook

A pre-commit hook automatically validates all changes to engines and inputs before allowing commits. The hook:

1. ✅ Scans staged files for engine/input modifications
2. ✅ Verifies reference documentation exists
3. ✅ Blocks prohibited removals of components
4. ✅ Validates against the manifesto requirements

The hook is located at `.git/hooks/pre-commit` and runs automatically on every commit.

### Manual Validation

You can manually validate model integrity using the CLI:

```bash
# Check all model documents
cd backend
python -m app.core.model_integrity check

# Scan and display document hashes
python -m app.core.model_integrity scan

# Validate a specific target before editing
python -m app.core.model_integrity validate dcf_engine modify
```

### Programmatic Usage

In your Python code:

```python
from app.core.model_integrity import ModelIntegrityValidator, ModelIntegrityError

validator = ModelIntegrityValidator()

# Option 1: Check validation result
result = validator.validate_before_edit('dcf_engine', 'modify')
if not result.passed:
    print("Validation failed:", result.discrepancies)

# Option 2: Assert validity (raises exception on failure)
try:
    validator.assert_valid('comps_engine', 'add')
except ModelIntegrityError as e:
    print("Cannot proceed:", e)

# Option 3: Use decorator for automatic validation
from app.core.model_integrity import validate_before_modification

@validate_before_modification('dcf_engine', 'add')
def add_new_feature():
    # This will only execute if validation passes
    ...
```

## Protected Components

The following cannot be removed or simplified without explicit exemption from the Model Governance Committee:

### DCF Model
- Revenue drivers (volume + price separation)
- Cost structure (COGS, SG&A, Other OpEx)
- Capital expenditure (scenario-based)
- Working capital (AR/Inventory/AP days)
- WACC calculation (peer analysis required)
- Tax calculations (levered AND unlevered schedules)
- Depreciation (book and tax schedules)
- Free cash flow (two methods with reconciliation)
- Terminal value (perpetuity AND exit multiple)
- Discounting (partial period adjustment)
- Enterprise value bridge
- Equity value per share
- Sensitivity analysis

### Trading Comps Model
- Peer selection (minimum 5 companies)
- Enterprise value bridge for each peer
- Multiple calculations (EV/Revenue, EV/EBITDA, EV/EBIT, P/E, P/B)
- Statistical analysis (average, median, min, max)
- Implied valuation

### DuPont Analysis
- Net profit margin
- Asset turnover
- Equity multiplier
- ROE decomposition

## Prohibited Actions

❌ **REMOVAL** of any inputs, calculations, or outputs
❌ **SIMPLIFICATION** that hides complexity or assumptions
❌ **HARDCODING** previously user-adjustable assumptions
❌ **BYPASSING** calculations with shortcuts
❌ **REDUCING** scenario analysis capability
❌ **ELIMINATING** reconciliation checks

## Change Management Process

### Minor Changes (bug fixes, performance optimization)
1. Developer testing
2. Code review
3. Update changelog

### Major Changes (new features, methodology updates)
1. Design document
2. Impact analysis
3. Peer review (minimum 2 reviewers)
4. Regression testing
5. Documentation update
6. User communication

### Prohibited Changes (require explicit written exemption)
- Removing any input fields
- Hardcoding assumptions previously user-input
- Bypassing calculations with shortcuts
- Reducing scenario analysis capability
- Eliminating reconciliation checks

## Cache System

The validator maintains a cache file (`.model_integrity_cache.json`) that tracks:
- Document hashes for change detection
- Last validation timestamp
- Last validated target and edit type

This cache is automatically updated after each validation run.

## Troubleshooting

### "Reference documentation missing" error
Ensure the `excel models/` directory exists and contains the required `.txt` files.

### "MODEL_INTEGRITY_MANIFESTO.md not found" error
Run validation from within the project directory structure. The validator auto-detects the root by searching for the manifesto file.

### Pre-commit hook not running
Verify the hook is executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Import errors in pre-commit hook
Ensure you're running from the correct directory and the backend package is in the Python path.

## References

- [MODEL_INTEGRITY_MANIFESTO.md](../MODEL_INTEGRITY_MANIFESTO.md) - Core principles and requirements
- [COMPLETE_MODEL_REFERENCE.md](backend/COMPLETE_MODEL_REFERENCE.md) - Detailed model specifications
- [FLOW_IMPLEMENTATION.md](backend/FLOW_IMPLEMENTATION.md) - Implementation details

---

**Remember:** When in doubt, preserve completeness. There is no such thing as "too detailed" in valuation modeling.
