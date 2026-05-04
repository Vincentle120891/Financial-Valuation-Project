"""Step 9: DuPont Analysis Processor"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DuPontComponent(BaseModel):
    name: str
    value: float
    formula: str
    interpretation: str

class DuPontTrendYear(BaseModel):
    year: str
    net_profit_margin: float
    asset_turnover: float
    equity_multiplier: float
    roe: float

class Step9Response(BaseModel):
    ticker: str
    components: List[DuPontComponent]
    trend_analysis: List[DuPontTrendYear]
    roe_breakdown: Dict
    insights: List[str]

class Step9DuPontProcessor:
    
    def _calculate_dupont_components(self, net_income: float, revenue: float, 
                                     total_assets: float, equity: float) -> tuple:
        """Calculate DuPont components with validation."""
        if not revenue or revenue == 0:
            net_margin = 0.0
        else:
            net_margin = net_income / revenue
            
        if not total_assets or total_assets == 0:
            asset_turnover = 0.0
        else:
            asset_turnover = revenue / total_assets
            
        if not equity or equity == 0:
            equity_multiplier = 1.0
        else:
            equity_multiplier = total_assets / equity
            
        roe = net_margin * asset_turnover * equity_multiplier
        
        return net_margin, asset_turnover, equity_multiplier, roe
    
    def _extract_historical_data(self, financial_data: Dict) -> List[Dict]:
        """Extract historical financial data arrays for trend analysis."""
        years = financial_data.get('years', [])
        net_incomes = financial_data.get('net_income', [])
        revenues = financial_data.get('revenue', [])
        total_assets = financial_data.get('total_assets', [])
        equities = financial_data.get('equity', [])
        
        # If no historical arrays, try to extract from latest fields with year suffixes
        if not years and 'year_1' in financial_data:
            years = []
            net_incomes = []
            revenues = []
            total_assets = []
            equities = []
            
            for i in range(1, 4):  # Look for up to 3 years of data
                year_key = f'year_{i}'
                if year_key in financial_data:
                    years.append(str(financial_data[year_key]))
                    net_incomes.append(financial_data.get(f'net_income_{i}', 0))
                    revenues.append(financial_data.get(f'revenue_{i}', 0))
                    total_assets.append(financial_data.get(f'total_assets_{i}', 0))
                    equities.append(financial_data.get(f'equity_{i}', 0))
        
        # Build historical records
        historical_records = []
        min_len = min(len(years), len(net_incomes), len(revenues), 
                     len(total_assets), len(equities))
        
        for i in range(min_len):
            if years[i] and revenues[i]:  # Only include valid years with revenue
                historical_records.append({
                    'year': str(years[i]),
                    'net_income': net_incomes[i],
                    'revenue': revenues[i],
                    'total_assets': total_assets[i],
                    'equity': equities[i]
                })
        
        return historical_records
    
    def _generate_insights(self, trend_analysis: List[DuPontTrendYear], 
                          current_roe: float, net_margin: float, 
                          asset_turnover: float, equity_multiplier: float) -> List[str]:
        """Generate sophisticated insights based on actual trend analysis."""
        insights = []
        
        # Current ROE assessment
        if current_roe > 0.15:
            insights.append(f"Strong ROE of {current_roe:.1%} indicates excellent shareholder returns.")
        elif current_roe > 0.10:
            insights.append(f"Healthy ROE of {current_roe:.1%} demonstrates good profitability.")
        elif current_roe > 0:
            insights.append(f"Moderate ROE of {current_roe:.1%} suggests room for improvement.")
        else:
            insights.append(f"Negative ROE of {current_roe:.1%} indicates losses or financial distress.")
        
        # Primary driver analysis
        drivers = {
            'profitability': net_margin,
            'efficiency': asset_turnover,
            'leverage': equity_multiplier
        }
        
        # Determine primary driver based on relative strength
        if net_margin > 0.15:
            insights.append(f"High profit margins ({net_margin:.1%}) are the primary driver of ROE.")
        elif asset_turnover > 1.0:
            insights.append(f"Strong asset turnover ({asset_turnover:.2f}x) drives returns through operational efficiency.")
        elif equity_multiplier > 2.5:
            insights.append(f"High financial leverage ({equity_multiplier:.2f}x) significantly boosts ROE but increases risk.")
        
        # Trend analysis
        if len(trend_analysis) >= 2:
            recent_roe = trend_analysis[-1].roe
            prior_roe = trend_analysis[-2].roe
            roe_change = recent_roe - prior_roe
            
            if abs(roe_change) > 0.02:  # More than 2% change
                direction = "improved" if roe_change > 0 else "declined"
                insights.append(f"ROE has {direction} by {abs(roe_change):.1%} points compared to the prior period.")
                
                # Analyze what drove the change
                margin_change = trend_analysis[-1].net_profit_margin - trend_analysis[-2].net_profit_margin
                turnover_change = trend_analysis[-1].asset_turnover - trend_analysis[-2].asset_turnover
                leverage_change = trend_analysis[-1].equity_multiplier - trend_analysis[-2].equity_multiplier
                
                changes = {
                    'profitability': margin_change,
                    'efficiency': turnover_change,
                    'leverage': leverage_change
                }
                primary_change_driver = max(changes, key=lambda k: abs(changes[k]))
                
                if primary_change_driver == 'profitability':
                    driver_label = "profitability margins"
                elif primary_change_driver == 'efficiency':
                    driver_label = "asset utilization"
                else:
                    driver_label = "financial leverage"
                    
                insights.append(f"The change was primarily driven by shifts in {driver_label}.")
        
        # Leverage risk assessment
        if equity_multiplier > 3.0:
            insights.append(f"Caution: Equity multiplier of {equity_multiplier:.2f}x indicates very high leverage and increased financial risk.")
        elif equity_multiplier > 2.0:
            insights.append(f"Equity multiplier of {equity_multiplier:.2f}x shows moderate leverage usage.")
        else:
            insights.append(f"Conservative capital structure with equity multiplier of {equity_multiplier:.2f}x.")
        
        return insights
    
    def process_dupont_analysis(self, ticker: str, financial_data: Dict) -> Step9Response:
        """Process DuPont analysis using historical data from financial_data."""
        
        # Validate required inputs
        required_fields = ['net_income_latest', 'revenue_latest', 'total_assets_latest', 'equity_latest']
        missing_fields = [field for field in required_fields if field not in financial_data]
        
        if missing_fields:
            logger.warning(f"Missing required fields for DuPont analysis: {missing_fields}")
            # Use defaults only if critical fields are missing
            for field in missing_fields:
                financial_data[field] = 0
        
        # Extract latest values
        net_income_latest = financial_data.get('net_income_latest', 0)
        revenue_latest = financial_data.get('revenue_latest', 0)
        total_assets_latest = financial_data.get('total_assets_latest', 0)
        equity_latest = financial_data.get('equity_latest', 0)
        
        # Calculate current DuPont components
        net_margin, asset_turnover, equity_multiplier, roe = self._calculate_dupont_components(
            net_income_latest, revenue_latest, total_assets_latest, equity_latest
        )
        
        # Build components list
        components = [
            DuPontComponent(
                name="Net Profit Margin",
                value=net_margin,
                formula="Net Income / Revenue",
                interpretation="Measures profitability per dollar of sales"
            ),
            DuPontComponent(
                name="Asset Turnover",
                value=asset_turnover,
                formula="Revenue / Total Assets",
                interpretation="Measures how efficiently assets generate revenue"
            ),
            DuPontComponent(
                name="Equity Multiplier",
                value=equity_multiplier,
                formula="Total Assets / Equity",
                interpretation="Measures financial leverage and capital structure"
            )
        ]
        
        # Extract and calculate historical trends
        historical_records = self._extract_historical_data(financial_data)
        
        trend_analysis = []
        
        # Process historical records
        for record in historical_records:
            hist_net_margin, hist_asset_turn, hist_eq_mult, hist_roe = self._calculate_dupont_components(
                record['net_income'],
                record['revenue'],
                record['total_assets'],
                record['equity']
            )
            
            trend_analysis.append(DuPontTrendYear(
                year=record['year'],
                net_profit_margin=hist_net_margin,
                asset_turnover=hist_asset_turn,
                equity_multiplier=hist_eq_mult,
                roe=hist_roe
            ))
        
        # Add current period if not already included
        current_year = financial_data.get('latest_year', 'Current')
        if not trend_analysis or trend_analysis[-1].year != str(current_year):
            trend_analysis.append(DuPontTrendYear(
                year=str(current_year),
                net_profit_margin=net_margin,
                asset_turnover=asset_turnover,
                equity_multiplier=equity_multiplier,
                roe=roe
            ))
        
        # Generate insights based on actual data
        insights = self._generate_insights(
            trend_analysis, roe, net_margin, asset_turnover, equity_multiplier
        )
        
        return Step9Response(
            ticker=ticker,
            components=components,
            trend_analysis=trend_analysis,
            roe_breakdown={
                "roe": roe,
                "net_margin": net_margin,
                "asset_turnover": asset_turnover,
                "equity_multiplier": equity_multiplier
            },
            insights=insights
        )
