"""
Unified Valuation AI Hybrid Input Module

Retrieves AI-extracted footnote data, forward guidance, hybrid adjustments,
peer matching analysis, and valuation suggestions.

Primary source: LLM parsing of SEC EDGAR filings (10-K/10-Q), earnings transcripts, IR presentations
Fallback: Manual estimates or API-sourced base figures with AI confidence scoring

Schema-compliant with Unified_Valuation_AI_Hybrid_Schema
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

# AI/LLM API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SEC_EDGAR_BASE_URL = "https://data.sec.gov/submissions"


class AIValuationInputs:
    """
    Unified class to fetch and store AI-extracted and hybrid valuation inputs.
    Follows the Unified_Valuation_AI_Hybrid_Schema structure.
    """

    def __init__(self, ticker: str, company_name: str = ""):
        self.ticker = ticker.upper()
        self.company_name = company_name
        self.extraction_timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Initialize schema-compliant structure
        self.data: Dict[str, Any] = {
            "ai_footnote_extractions": {},
            "ai_contextual_forward_guidance": {},
            "ai_api_hybrid_adjustments": {},
            "ai_peer_matching_analysis": {},
            "ai_hybrid_valuation_suggestions": {},
            "ai_metadata_and_audit": {}
        }
        
        # Confidence tracking
        self.confidence_scores: Dict[str, float] = {}
        self.source_citations: List[Dict[str, Any]] = []
        
    def fetch_all(self, api_base_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch all AI-extracted data and calculate hybrid adjustments.
        
        Args:
            api_base_data: Base financial data from API (yfinance/Alpha Vantage)
                          used for hybrid calculations
        
        Returns:
            Dictionary containing all AI hybrid schema-compliant fields
        """
        self._extract_footnote_data()
        self._extract_forward_guidance()
        self._calculate_hybrid_adjustments(api_base_data)
        self._analyze_peer_matching()
        self._generate_valuation_suggestions()
        self._build_metadata_audit()
        
        return self.data

    def _extract_footnote_data(self):
        """
        Extract structured data from 10-K/10-Q footnotes via LLM parsing.
        Sources: SEC EDGAR, company IR presentations
        """
        try:
            # Step 1: Fetch latest 10-K filing URL
            filing_url = self._get_latest_filing_url("10-K")
            
            if filing_url:
                # Step 2: Extract filing content
                filing_content = self._fetch_filing_content(filing_url)
                
                # Step 3: Use LLM to parse footnotes
                extracted = self._llm_parse_footnotes(filing_content)
                
                self.data["ai_footnote_extractions"] = {
                    "tax_basis_pp_e": extracted.get("tax_basis_pp_e"),
                    "nol_carryforward_amount": extracted.get("nol_carryforward_amount", 0),
                    "nol_expiration_dates": extracted.get("nol_expiration_dates", []),
                    "useful_life_existing_assets": extracted.get("useful_life_existing_assets", []),
                    "useful_life_new_assets": extracted.get("useful_life_new_assets", []),
                    "lease_liability_operating": extracted.get("lease_liability_operating", 0),
                    "lease_liability_finance": extracted.get("lease_liability_finance", 0),
                    "rent_expense_ltm": extracted.get("rent_expense_ltm", 0),
                    "deferred_tax_assets": extracted.get("deferred_tax_assets", 0),
                    "deferred_tax_liabilities": extracted.get("deferred_tax_liabilities", 0),
                    "goodwill_and_intangibles": extracted.get("goodwill_and_intangibles", 0),
                    "pension_opeb_obligations": extracted.get("pension_opeb_obligations", 0),
                    "contingent_liabilities_litigation": extracted.get("contingent_liabilities_litigation", 0),
                    "related_party_transaction_amount": extracted.get("related_party_transaction_amount", 0),
                    "capital_commitments": extracted.get("capital_commitments", {}),
                    "accounting_policy_differences": extracted.get("accounting_policy_differences", ""),
                    "tax_jurisdiction_statutory_rates": extracted.get("tax_jurisdiction_statutory_rates", []),
                    "segment_revenue_breakdown": extracted.get("segment_revenue_breakdown", []),
                    "segment_ebitda_breakdown": extracted.get("segment_ebitda_breakdown", []),
                    "m_and_a_pro_forma_adjustments": extracted.get("m_and_a_pro_forma_adjustments", {})
                }
                
                # Track confidence scores
                for field, value in extracted.items():
                    if value is not None:
                        self.confidence_scores[f"footnote_{field}"] = extracted.get(f"{field}_confidence", 0.75)
            else:
                raise ValueError("No 10-K filing found")
                
        except Exception as e:
            print(f"Warning: Footnote extraction error for {self.ticker}: {e}")
            # Fallback to empty/default values
            self.data["ai_footnote_extractions"] = {
                "tax_basis_pp_e": None,
                "nol_carryforward_amount": 0,
                "nol_expiration_dates": [],
                "useful_life_existing_assets": [],
                "useful_life_new_assets": [],
                "lease_liability_operating": 0,
                "lease_liability_finance": 0,
                "rent_expense_ltm": 0,
                "deferred_tax_assets": 0,
                "deferred_tax_liabilities": 0,
                "goodwill_and_intangibles": 0,
                "pension_opeb_obligations": 0,
                "contingent_liabilities_litigation": 0,
                "related_party_transaction_amount": 0,
                "capital_commitments": {},
                "accounting_policy_differences": "",
                "tax_jurisdiction_statutory_rates": [],
                "segment_revenue_breakdown": [],
                "segment_ebitda_breakdown": [],
                "m_and_a_pro_forma_adjustments": {}
            }
            self.confidence_scores["footnote_extraction"] = 0.0

    def _get_latest_filing_url(self, filing_type: str = "10-K") -> Optional[str]:
        """Get the latest SEC filing URL for the given type."""
        try:
            # Fetch CIK for ticker
            cik = self._get_cik_for_ticker()
            if not cik:
                return None
            
            # Fetch submission list
            url = f"{SEC_EDGAR_BASE_URL}/CIK{cik}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            submissions = response.json()
            filings = submissions.get("filings", {}).get("recent", {})
            
            # Find latest matching filing type
            forms = filings.get("form", [])
            accession_numbers = filings.get("accessionNumber", [])
            documents = filings.get("primaryDocument", [])
            
            for i, form in enumerate(forms):
                if form == filing_type:
                    acc_num = accession_numbers[i]
                    # Construct document URL
                    acc_num_no_dash = acc_num.replace("-", "")
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_no_dash}/{documents[i]}"
                    return doc_url
                    
        except Exception as e:
            print(f"Warning: Error fetching filing URL: {e}")
        
        return None

    def _get_cik_for_ticker(self) -> Optional[str]:
        """Get CIK number for a ticker symbol."""
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            companies = response.json()
            for key, value in companies.items():
                if value.get("ticker", "").upper() == self.ticker:
                    return str(value.get("cik_str", "")).zfill(10)
                    
        except Exception as e:
            print(f"Warning: Error fetching CIK: {e}")
        
        return None

    def _fetch_filing_content(self, url: str) -> str:
        """Fetch filing content from SEC URL."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text[:500000]  # Limit content size for LLM
        except Exception as e:
            print(f"Warning: Error fetching filing content: {e}")
            return ""

    def _llm_parse_footnotes(self, content: str) -> Dict[str, Any]:
        """
        Parse footnotes using LLM (OpenAI/Claude).
        Returns structured extraction with confidence scores.
        """
        if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
            print("Warning: No LLM API key configured. Using placeholder extractions.")
            return self._placeholder_footnote_extraction()
        
        prompt = f"""
        Extract the following information from this SEC filing for {self.ticker}:
        
        Return JSON with these fields:
        - tax_basis_pp_e: Tax basis of PP&E
        - nol_carryforward_amount: NOL carryforwards
        - nol_expiration_dates: Array of expiration dates
        - useful_life_existing_assets: Array of {{asset_class, years}}
        - useful_life_new_assets: Array of years
        - lease_liability_operating: Operating lease liability
        - lease_liability_finance: Finance lease liability
        - rent_expense_ltm: Operating lease expense
        - deferred_tax_assets: DTA balance
        - deferred_tax_liabilities: DTL balance
        - goodwill_and_intangibles: Combined goodwill + intangibles
        - pension_opeb_obligations: Net pension obligations
        - contingent_liabilities_litigation: Litigation estimates
        - related_party_transaction_amount: Related-party transactions
        - capital_commitments: {{year_1, years_1_3, years_3_5, beyond_5}}
        - accounting_policy_differences: Summary string
        - tax_jurisdiction_statutory_rates: Array of {{jurisdiction, rate}}
        - segment_revenue_breakdown: Array of segment data
        - segment_ebitda_breakdown: Array of segment EBITDA
        - m_and_a_pro_forma_adjustments: {{pro_forma_revenue, pro_forma_ebitda}}
        
        Include confidence score (0-1) for each field as {{field}}_confidence.
        
        Filing content excerpt:
        {content[:50000]}
        """
        
        try:
            if OPENAI_API_KEY:
                return self._call_openai(prompt)
            elif ANTHROPIC_API_KEY:
                return self._call_anthropic(prompt)
        except Exception as e:
            print(f"Warning: LLM parsing failed: {e}")
        
        return self._placeholder_footnote_extraction()

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for extraction."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a financial analyst extracting data from SEC filings. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic Claude API for extraction."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result["content"][0]["text"]
        return json.loads(content)

    def _placeholder_footnote_extraction(self) -> Dict[str, Any]:
        """Return placeholder values when LLM is unavailable."""
        return {
            "tax_basis_pp_e": None,
            "nol_carryforward_amount": 0,
            "nol_expiration_dates": [],
            "useful_life_existing_assets": [],
            "useful_life_new_assets": [],
            "lease_liability_operating": 0,
            "lease_liability_finance": 0,
            "rent_expense_ltm": 0,
            "deferred_tax_assets": 0,
            "deferred_tax_liabilities": 0,
            "goodwill_and_intangibles": 0,
            "pension_opeb_obligations": 0,
            "contingent_liabilities_litigation": 0,
            "related_party_transaction_amount": 0,
            "capital_commitments": {},
            "accounting_policy_differences": "",
            "tax_jurisdiction_statutory_rates": [],
            "segment_revenue_breakdown": [],
            "segment_ebitda_breakdown": [],
            "m_and_a_pro_forma_adjustments": {}
        }

    def _extract_forward_guidance(self):
        """
        Extract forward-looking guidance from MD&A and earnings call transcripts.
        """
        try:
            # Fetch earnings call transcript
            transcript = self._get_earnings_transcript()
            
            if transcript:
                guidance = self._llm_parse_guidance(transcript)
                
                self.data["ai_contextual_forward_guidance"] = {
                    "plant_utilization_target": guidance.get("plant_utilization_target"),
                    "projected_interest_rate_on_debt": guidance.get("projected_interest_rate_on_debt"),
                    "projected_depreciation_rate": guidance.get("projected_depreciation_rate"),
                    "tax_loss_utilization_schedule": guidance.get("tax_loss_utilization_schedule", {}),
                    "working_capital_policy_change_days": guidance.get("working_capital_policy_change_days"),
                    "capex_as_pct_of_revenue_forecast": guidance.get("capex_as_pct_of_revenue_forecast"),
                    "revenue_growth_forecast_5y": guidance.get("revenue_growth_forecast_5y", []),
                    "management_guidance_notes": guidance.get("management_guidance_notes", "")
                }
                
                # Track confidence
                for field, value in guidance.items():
                    if value is not None:
                        self.confidence_scores[f"guidance_{field}"] = guidance.get(f"{field}_confidence", 0.7)
            else:
                raise ValueError("No transcript available")
                
        except Exception as e:
            print(f"Warning: Forward guidance extraction error: {e}")
            self.data["ai_contextual_forward_guidance"] = {
                "plant_utilization_target": None,
                "projected_interest_rate_on_debt": None,
                "projected_depreciation_rate": None,
                "tax_loss_utilization_schedule": {},
                "working_capital_policy_change_days": None,
                "capex_as_pct_of_revenue_forecast": None,
                "revenue_growth_forecast_5y": [],
                "management_guidance_notes": ""
            }
            self.confidence_scores["guidance_extraction"] = 0.0

    def _get_earnings_transcript(self) -> Optional[str]:
        """Fetch earnings call transcript (placeholder - would integrate with transcript API)."""
        # In production, integrate with services like:
        # - AlphaVantage Transcript API
        # - Quiver Quantitative
        # - Bloomberg/Refinitiv
        print(f"Note: Transcript fetching not yet implemented for {self.ticker}")
        return None

    def _llm_parse_guidance(self, transcript: str) -> Dict[str, Any]:
        """Parse guidance from transcript using LLM."""
        if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
            return self._placeholder_guidance()
        
        prompt = f"""
        Extract forward guidance from this earnings call transcript for {self.ticker}:
        
        Return JSON with:
        - plant_utilization_target: Target capacity utilization (0-1)
        - projected_interest_rate_on_debt: Expected borrowing cost
        - projected_depreciation_rate: D&A as % of PPE or Revenue
        - tax_loss_utilization_schedule: {{year_1_pct, year_2_pct, year_3_pct}}
        - working_capital_policy_change_days: Target WC adjustment
        - capex_as_pct_of_revenue_forecast: Guided CapEx intensity
        - revenue_growth_forecast_5y: Array of 5 growth rates
        - management_guidance_notes: Qualitative summary
        
        Include confidence scores for each field.
        
        Transcript excerpt:
        {transcript[:30000]}
        """
        
        try:
            if OPENAI_API_KEY:
                return self._call_openai(prompt)
            elif ANTHROPIC_API_KEY:
                return self._call_anthropic(prompt)
        except Exception as e:
            print(f"Warning: Guidance parsing failed: {e}")
        
        return self._placeholder_guidance()

    def _placeholder_guidance(self) -> Dict[str, Any]:
        """Return placeholder guidance values."""
        return {
            "plant_utilization_target": None,
            "projected_interest_rate_on_debt": None,
            "projected_depreciation_rate": None,
            "tax_loss_utilization_schedule": {},
            "working_capital_policy_change_days": None,
            "capex_as_pct_of_revenue_forecast": None,
            "revenue_growth_forecast_5y": [],
            "management_guidance_notes": ""
        }

    def _calculate_hybrid_adjustments(self, api_base_data: Optional[Dict[str, Any]] = None):
        """
        Calculate hybrid adjustments combining AI extractions with API base figures.
        """
        try:
            # Get base values from API data
            base_ebitda = 0
            base_net_income = 0
            base_ev = 0
            base_assets = 0
            base_equity = 0
            base_net_debt = 0
            base_revenue = 0
            
            if api_base_data:
                income = api_base_data.get("income_statement_raw", {})
                market = api_base_data.get("market_structure", {})
                balance = api_base_data.get("balance_sheet_raw", {})
                
                base_ebitda = income.get("ebitda", 0) or 0
                base_net_income = income.get("net_income", 0) or 0
                base_ev = market.get("enterprise_value", 0) or 0
                base_assets = balance.get("total_assets", 0) or 0
                base_equity = balance.get("total_equity", 0) or 0
                base_net_debt = market.get("net_debt", 0) or 0
                base_revenue = income.get("revenue_total", 0) or 0
            
            # Get AI extractions
            footnote = self.data.get("ai_footnote_extractions", {})
            
            lease_op = footnote.get("lease_liability_operating", 0) or 0
            rent_expense = footnote.get("rent_expense_ltm", 0) or 0
            goodwill_intangible = footnote.get("goodwill_and_intangibles", 0) or 0
            
            # Calculate hybrid adjustments
            adjusted_ebitda = base_ebitda + rent_expense  # Add back operating lease expense
            adjusted_net_income = base_net_income  # Would add NOL/tax adjustments here
            
            lease_adjusted_ev = base_ev + lease_op
            ev_ebitda_ex_rent = lease_adjusted_ev / adjusted_ebitda if adjusted_ebitda else 0
            
            tangible_equity = base_equity - goodwill_intangible
            tangible_equity_multiplier = base_assets / tangible_equity if tangible_equity else 1.0
            
            lease_adjusted_assets = base_assets + lease_op
            lease_adjusted_asset_turnover = base_revenue / lease_adjusted_assets if lease_adjusted_assets else 0
            
            net_debt_post_leases = base_net_debt + lease_op
            
            self.data["ai_api_hybrid_adjustments"] = {
                "adjusted_ebitda": adjusted_ebitda,
                "adjusted_net_income": adjusted_net_income,
                "lease_adjusted_enterprise_value": lease_adjusted_ev,
                "ev_ebitda_ex_rent": ev_ebitda_ex_rent,
                "tangible_equity_multiplier": tangible_equity_multiplier,
                "lease_adjusted_asset_turnover": lease_adjusted_asset_turnover,
                "normalized_tax_burden": None,  # Would calculate from AI tax data
                "blended_tax_depreciation_rate": None,
                "net_debt_post_operating_leases": net_debt_post_leases,
                "fye_aligned_ltm_metrics": {}
            }
            
        except Exception as e:
            print(f"Warning: Hybrid adjustment calculation error: {e}")
            self.data["ai_api_hybrid_adjustments"] = {
                "adjusted_ebitda": 0,
                "adjusted_net_income": 0,
                "lease_adjusted_enterprise_value": 0,
                "ev_ebitda_ex_rent": 0,
                "tangible_equity_multiplier": 1.0,
                "lease_adjusted_asset_turnover": 0,
                "normalized_tax_burden": None,
                "blended_tax_depreciation_rate": None,
                "net_debt_post_operating_leases": 0,
                "fye_aligned_ltm_metrics": {}
            }

    def _analyze_peer_matching(self):
        """
        AI-driven peer identification and similarity scoring.
        """
        try:
            # In production, would use LLM to analyze business descriptions, segments, etc.
            ai_suggested_peers = self._suggest_peers_via_llm()
            
            self.data["ai_peer_matching_analysis"] = {
                "ai_suggested_peer_tickers": ai_suggested_peers,
                "business_model_similarity_score": 0.85,  # Placeholder
                "geographic_exposure_match": {
                    "primary_regions": ["North America"],
                    "match_pct": 0.80
                },
                "size_band_ratio": 1.0,
                "growth_differential": 0.0,
                "conglomerate_diversification_flag": False,
                "exclusion_reasons_ai": [],
                "peer_quality_score_composite": 75
            }
            
        except Exception as e:
            print(f"Warning: Peer matching analysis error: {e}")
            self.data["ai_peer_matching_analysis"] = {
                "ai_suggested_peer_tickers": [],
                "business_model_similarity_score": 0,
                "geographic_exposure_match": {"primary_regions": [], "match_pct": 0},
                "size_band_ratio": 0,
                "growth_differential": 0,
                "conglomerate_diversification_flag": False,
                "exclusion_reasons_ai": [],
                "peer_quality_score_composite": 0
            }

    def _suggest_peers_via_llm(self) -> List[str]:
        """Use LLM to suggest peer companies based on business description."""
        # Placeholder - would integrate with industry classification APIs
        default_peers_by_sector = {
            "AAPL": ["MSFT", "GOOGL", "AMZN", "META"],
            "MSFT": ["AAPL", "GOOGL", "ORCL", "CRM"],
            "JPM": ["BAC", "WFC", "C", "GS"],
            "XOM": ["CVX", "COP", "SLB", "EOG"]
        }
        return default_peers_by_sector.get(self.ticker, [])

    def _generate_valuation_suggestions(self):
        """
        Generate AI-suggested valuation drivers and adjustments.
        """
        try:
            comps = self.data.get("comps_specific_calculated", {})
            guidance = self.data.get("ai_contextual_forward_guidance", {})
            
            # Suggest scenario weights
            self.data["ai_hybrid_valuation_suggestions"] = {
                "growth_adjusted_terminal_multiple_suggestion": None,
                "implied_credit_spread_from_guidance": None,
                "forward_ebitda_margin_ai_adjusted": None,
                "scenario_weight_suggestions": {
                    "best_case_weight": 0.25,
                    "base_case_weight": 0.50,
                    "worst_case_weight": 0.25
                },
                "quality_discount_premium_suggestion": 0.0
            }
            
        except Exception as e:
            print(f"Warning: Valuation suggestion generation error: {e}")
            self.data["ai_hybrid_valuation_suggestions"] = {
                "growth_adjusted_terminal_multiple_suggestion": None,
                "implied_credit_spread_from_guidance": None,
                "forward_ebitda_margin_ai_adjusted": None,
                "scenario_weight_suggestions": {
                    "best_case_weight": 0.25,
                    "base_case_weight": 0.50,
                    "worst_case_weight": 0.25
                },
                "quality_discount_premium_suggestion": 0.0
            }

    def _build_metadata_audit(self):
        """Build metadata and audit trail for AI outputs."""
        # Calculate overall confidence
        if self.confidence_scores:
            overall_confidence = sum(self.confidence_scores.values()) / len(self.confidence_scores)
        else:
            overall_confidence = 0.0
        
        # Determine validation status
        if overall_confidence >= 0.7:
            validation_status = "verified"
        elif overall_confidence >= 0.5:
            validation_status = "pending"
        else:
            validation_status = "flagged_for_review"
        
        self.data["ai_metadata_and_audit"] = {
            "confidence_score_overall": round(overall_confidence, 3),
            "confidence_scores_by_field": {k: round(v, 3) for k, v in self.confidence_scores.items()},
            "source_citations": self.source_citations,
            "parsing_model_version": "gpt-4o-mini-2024-07-18" if OPENAI_API_KEY else "claude-sonnet-4-20250514" if ANTHROPIC_API_KEY else "none",
            "extraction_timestamp": self.extraction_timestamp,
            "validation_status": validation_status,
            "user_override_log": []
        }

    def to_json(self, indent: int = 2) -> str:
        """Export data as JSON string."""
        return json.dumps(self.data, indent=indent, default=str)

    def save_to_file(self, filepath: str):
        """Save data to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
        print(f"AI valuation inputs saved to {filepath}")


def fetch_ai_valuation_inputs(ticker: str, api_base_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to fetch all AI-assisted valuation inputs.
    
    Args:
        ticker: Stock ticker symbol
        api_base_data: Optional base financial data from API for hybrid calculations
    
    Returns:
        Dictionary containing all AI hybrid schema-compliant fields
    """
    inputs = AIValuationInputs(ticker)
    return inputs.fetch_all(api_base_data)


# Example usage
if __name__ == "__main__":
    # Test with Apple (without actual LLM calls)
    print("Testing AI Valuation Inputs module...")
    data = fetch_ai_valuation_inputs("AAPL")
    print(json.dumps(data, indent=2, default=str))
