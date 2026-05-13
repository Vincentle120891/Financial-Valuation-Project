"""
Step 3: Selected Models Processor
Handles model selection (DCF, DuPont, Comps) for valuation workflow.
This is the CORRECT Step 3 implementation.
"""

from typing import List, Dict, Any


class Step3SelectedModelsProcessor:
    """Processes selected valuation models from user input."""
    
    def __init__(self, market: str):
        self.market = market
        self.valid_models = ['DCF', 'DuPont', 'Comps']
    
    def process_model_selection(self, selected_models: List[str]) -> Dict[str, Any]:
        """
        Process and validate selected valuation models.
        
        Args:
            selected_models: List of model names selected by user
            
        Returns:
            Dictionary with validated models and metadata
        """
        # Validate selected models
        validated_models = []
        invalid_models = []
        
        for model in selected_models:
            if model in self.valid_models:
                validated_models.append(model)
            else:
                invalid_models.append(model)
        
        # Build response
        result = {
            'selected_models': validated_models,
            'invalid_models': invalid_models,
            'market': self.market,
            'model_count': len(validated_models),
            'is_valid': len(validated_models) > 0 and len(invalid_models) == 0
        }
        
        return result
    
    def get_required_inputs_by_model(self, selected_models: List[str]) -> Dict[str, List[str]]:
        """
        Get list of required inputs for each selected model.
        
        Args:
            selected_models: List of validated model names
            
        Returns:
            Dictionary mapping model names to their required input lists
        """
        inputs_mapping = {
            'DCF': [
                'revenue_growth_rates',
                'ebitda_margins',
                'capex_percentages',
                'nwc_percentages',
                'depreciation_amortization',
                'terminal_growth_rate',
                'wacc',
                'shares_outstanding',
                'net_debt'
            ],
            'DuPont': [
                'net_income',
                'revenue',
                'total_assets',
                'shareholders_equity',
                'tax_rate',
                'interest_expense',
                'ebit'
            ],
            'Comps': [
                'peer_ev_ebitda',
                'peer_pe_ratios',
                'peer_pb_ratios',
                'peer_revenue_multiples',
                'target_company_metrics'
            ]
        }
        
        required_inputs = {}
        for model in selected_models:
            if model in inputs_mapping:
                required_inputs[model] = inputs_mapping[model]
        
        return required_inputs
