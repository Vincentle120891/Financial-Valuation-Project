# DCF Input Source Tracking System

## Overview

The DCF model now supports **three input sources** with full auditability:

1. **API** - Financial data from external APIs (yFinance, Alpha Vantage, etc.)
2. **AI** - Forecast assumptions from LLM engines (Groq, Gemini, Qwen)
3. **Manual** - User-provided overrides

## Architecture

### Core Components

#### 1. `InputSource` Enum
```python
class InputSource:
    API = "api"           # From external APIs
    AI = "ai"             # From AI engines
    MANUAL = "manual"     # User overrides
    DEFAULT = "default"   # System defaults
```

#### 2. `InputWithMetadata` Dataclass
Wraps any input value with source tracking:
```python
@dataclass
class InputWithMetadata:
    value: Any                    # The actual numeric/date value
    source: str                   # One of InputSource
    rationale: str                # Why this value was chosen
    sources: str                  # Specific data source reference
    timestamp: str                # When the value was set
```

#### 3. `DCFInputManager` Class
Unified interface for building DCF inputs from multiple sources:
```python
manager = DCFInputManager()
manager.load_api_data(api_response)
manager.load_ai_assumptions(ai_output)
manager.apply_manual_override("terminal_growth_rate", 0.025)
inputs = manager.build_inputs()
```

### Priority System

Inputs are resolved in this order (highest to lowest priority):
1. **Manual Override** - User explicitly sets a value
2. **AI Assumptions** - LLM-generated forecasts
3. **API Data** - Historical financials from yFinance
4. **Default** - Built-in fallback values

## Usage Examples

### Example 1: Basic Usage with All Sources

```python
from dcf_input_manager import create_dcf_inputs

# API data from yFinance
api_data = {
    "profile": {
        "symbol": "AAPL",
        "currentPrice": 175.50,
        "sharesOutstanding": 15900000000,
        "totalDebt": 111000000000,
        "cash": 61500000000
    },
    "financials": {
        "revenue": {"2023": 383285, "2022": 394328, "2021": 365817},
        "cost_of_revenue": {"2023": 214137, "2022": 223546, "2021": 212981}
    }
}

# AI assumptions from your LLM engine
ai_assumptions = {
    "wacc_percent": {"value": 9.2, "rationale": "CAPM calculation", "sources": "Market data"},
    "terminal_growth_rate_percent": {"value": 2.5, "rationale": "Long-term inflation", "sources": "Fed target"},
    "revenue_growth_forecast": [
        {"value": 5.0, "rationale": "Product cycle", "sources": "AI analysis"},
        {"value": 4.5, "rationale": "Maturing market", "sources": "AI analysis"},
        {"value": 4.0, "rationale": "Saturation", "sources": "AI analysis"},
        {"value": 3.5, "rationale": "Maturity", "sources": "AI analysis"},
        {"value": 3.0, "rationale": "Steady state", "sources": "AI analysis"}
    ],
    "tax_rate_percent": {"value": 21.0, "rationale": "US statutory", "sources": "Tax code"}
}

# Create inputs with automatic source tracking
inputs = create_dcf_inputs(
    api_data=api_data,
    ai_assumptions=ai_assumptions,
    manual_overrides={"terminal_growth_rate": 0.02}  # Override AI
)

# Access values (automatically unwrapped)
print(f"Tax rate: {inputs.statutory_tax_rate}")  # 0.21

# Access metadata
if hasattr(inputs.statutory_tax_rate, 'source'):
    print(f"Source: {inputs.statutory_tax_rate.source}")      # "ai"
    print(f"Rationale: {inputs.statutory_tax_rate.rationale}") # "US statutory"
```

### Example 2: Manual Overrides Only

```python
from dcf_engine_full import DCFInputs, InputWithMetadata, InputSource

# Create inputs with explicit manual values
inputs = DCFInputs(
    statutory_tax_rate=InputWithMetadata(
        value=0.25,
        source=InputSource.MANUAL,
        rationale="Company-specific effective rate",
        sources="Management guidance"
    ),
    risk_free_rate=InputWithMetadata(
        value=0.045,
        source=InputSource.API,
        rationale="10Y Treasury yield",
        sources="Federal Reserve"
    )
)
```

### Example 3: Audit Trail Generation

```python
manager = DCFInputManager()
manager.load_api_data(api_data)
manager.load_ai_assumptions(ai_output)
manager.apply_manual_override("wacc", 0.09)

inputs = manager.build_inputs()

# Generate full audit trail
audit = manager.get_input_audit_trail()
print(audit)
# {
#     "api_data_keys": ["profile", "financials"],
#     "ai_assumption_keys": ["wacc_percent", "terminal_growth_rate_percent", ...],
#     "manual_overrides": {"wacc": {...}},
#     "source_summary": {
#         "total_api_inputs": 15,
#         "total_ai_inputs": 10,
#         "total_manual_overrides": 1
#     }
# }
```

## Integration with Existing Code

### Backward Compatibility

All existing code continues to work because `DCFInputs.get_value()` automatically unwraps `InputWithMetadata`:

```python
# Old code still works
engine = DCFEngine(inputs)
wacc, _, _, _ = engine.calculate_wacc()

# New capability: access source info
if isinstance(inputs.risk_free_rate, InputWithMetadata):
    print(f"WACC source: {inputs.risk_free_rate.source}")
```

### Updated Type Hints

Fields now accept both raw values and wrapped values:
```python
# Both are valid
historical_revenue: List[Union[float, InputWithMetadata]]
statutory_tax_rate: Union[float, InputWithMetadata]
```

## Benefits

1. **Full Auditability**: Know exactly where every assumption came from
2. **Transparency**: Rationale and sources documented for each input
3. **Flexibility**: Mix and match sources seamlessly
4. **Compliance**: Complete audit trail for regulatory requirements
5. **Debugging**: Easy to trace valuation discrepancies to specific inputs

## API Response Format

When returning results via API, include source metadata:

```json
{
  "valuation": {
    "enterprise_value": 150000000,
    "equity_value_per_share": 4.50
  },
  "input_sources": {
    "wacc": {
      "value": 0.095,
      "source": "ai",
      "rationale": "CAPM calculation",
      "sources": "Market data + Beta from Yahoo Finance"
    },
    "terminal_growth_rate": {
      "value": 0.025,
      "source": "manual",
      "rationale": "User override",
      "sources": "User Input"
    },
    "historical_revenue": {
      "value": [1000000, 900000, 800000],
      "source": "api",
      "rationale": "From financial API",
      "sources": "API: yFinance"
    }
  }
}
```

## Files Modified/Created

- `dcf_engine_full.py`: Added `InputSource`, `InputWithMetadata`, updated type hints
- `dcf_input_manager.py`: New file - input orchestration layer
- `main.py`: (To be updated) - integrate with API endpoints

## Next Steps

1. Update `main.py` to use `DCFInputManager` for all valuation requests
2. Add source metadata to API response schemas
3. Create frontend UI for viewing/editing input sources
4. Implement source-based filtering in sensitivity analysis
