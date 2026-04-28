"""
Financial Valuation Platform - Backend Application Package

A professional-grade valuation platform implementing:
- DCF (Discounted Cash Flow) with Perpetuity and Exit Multiple methods
- DuPont Analysis (3-step and 5-step)
- Trading Comparables (Comps)
- AI-powered assumptions with 3-tier fallback (Groq → Gemini → Qwen → Deterministic)

Package Structure:
├── api/           # API layer (routes, schemas)
├── core/          # Core configuration, security, exceptions
├── engines/       # Valuation calculation engines
├── services/      # Business logic and orchestration
└── models/        # Domain models and data structures
"""

__version__ = "2.0.0"
__author__ = "Valuation Engine Team"
