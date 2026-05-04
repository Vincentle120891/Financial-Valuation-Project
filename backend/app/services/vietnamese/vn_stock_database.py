"""
Vietnamese Stock Database - Scalable Architecture for 700+ HOSE Stocks

This module provides a scalable database architecture for Vietnamese stocks.
Currently includes 50 representative stocks across all major sectors.
Designed to easily expand to 700+ stocks by loading from CSV/JSON or database.

Sector Classifications (HOSE):
- Banking (Ngân hàng)
- Real Estate (Bất động sản)
- Consumer Staples (Hàng tiêu dùng thiết yếu)
- Consumer Discretionary (Hàng tiêu dùng không thiết yếu)
- Materials (Vật liệu/Xây dựng)
- Industrials (Công nghiệp)
- Energy (Năng lượng)
- Utilities (Điện/Nước)
- Healthcare (Y tế/Dược phẩm)
- Technology (Công nghệ)
- Telecommunications (Viễn thông)
- Financials (Tài chính/Chứng khoán/Bảo hiểm)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os


class VNExchange(Enum):
    """Vietnamese Stock Exchanges"""
    HOSE = "HOSE"  # Ho Chi Minh Stock Exchange (Main board)
    HNX = "HNX"    # Hanoi Stock Exchange
    UPCOM = "UPCOM"  # Unlisted Public Company Market


class VNSector(Enum):
    """Vietnamese Market Sectors (with Vietnamese names)"""
    BANKING = ("Banking", "Ngân hàng")
    REAL_ESTATE = ("Real Estate", "Bất động sản")
    CONSUMER_STAPLES = ("Consumer Staples", "Hàng tiêu dùng thiết yếu")
    CONSUMER_DISCRETIONARY = ("Consumer Discretionary", "Hàng tiêu dùng không thiết yếu")
    MATERIALS = ("Materials", "Vật liệu/Xây dựng")
    INDUSTRIALS = ("Industrials", "Công nghiệp")
    ENERGY = ("Energy", "Năng lượng")
    UTILITIES = ("Utilities", "Điện/Nước")
    HEALTHCARE = ("Healthcare", "Y tế/Dược phẩm")
    TECHNOLOGY = ("Technology", "Công nghệ")
    TELECOMMUNICATIONS = ("Telecommunications", "Viễn thông")
    FINANCIALS = ("Financials", "Tài chính/Chứng khoán/Bảo hiểm")
    
    def __init__(self, english_name: str, vietnamese_name: str):
        self.english_name = english_name
        self.vietnamese_name = vietnamese_name


@dataclass
class VNStock:
    """Vietnamese Stock Information"""
    ticker: str
    company_name_en: str
    company_name_vi: str
    sector: VNSector
    exchange: VNExchange
    industry: str
    market_cap_billion_vnd: Optional[float] = None
    foreign_ownership_limit: Optional[float] = None  # FOL in percentage (e.g., 49.0 for 49%)
    current_fol: Optional[float] = None  # Current foreign ownership %
    is_fol_restricted: bool = False  # True if foreign ownership limit reached
    listing_date: Optional[str] = None
    description_en: Optional[str] = None
    description_vi: Optional[str] = None
    website: Optional[str] = None
    liquidity_rating: str = "Medium"  # High/Medium/Low
    data_quality_score: float = 0.8  # 0.0-1.0
    regulatory_notes: List[str] = field(default_factory=list)
    
    def get_full_ticker(self) -> str:
        """Get ticker with exchange suffix"""
        suffix_map = {
            VNExchange.HOSE: ".VN",
            VNExchange.HNX: ".HA",
            VNExchange.UPCOM: ".VC"
        }
        return f"{self.ticker}{suffix_map.get(self.exchange, '.VN')}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ticker": self.ticker,
            "company_name_en": self.company_name_en,
            "company_name_vi": self.company_name_vi,
            "sector": self.sector.value[0],
            "sector_vi": self.sector.value[1],
            "exchange": self.exchange.value,
            "industry": self.industry,
            "market_cap_billion_vnd": self.market_cap_billion_vnd,
            "foreign_ownership_limit": self.foreign_ownership_limit,
            "current_fol": self.current_fol,
            "is_fol_restricted": self.is_fol_restricted,
            "listing_date": self.listing_date,
            "description_en": self.description_en,
            "description_vi": self.description_vi,
            "website": self.website,
            "liquidity_rating": self.liquidity_rating,
            "data_quality_score": self.data_quality_score,
            "regulatory_notes": self.regulatory_notes,
            "full_ticker": self.get_full_ticker()
        }


class VNStockDatabase:
    """
    Scalable Vietnamese Stock Database
    
    Supports:
    - In-memory storage for quick access
    - Loading from CSV/JSON files
    - Loading from external databases
    - Sector-based filtering
    - Search functionality
    - FOL tracking
    """
    
    def __init__(self):
        self.stocks: Dict[str, VNStock] = {}
        self._initialize_core_stocks()
    
    def _initialize_core_stocks(self):
        """Initialize with 50 representative stocks across all sectors"""
        
        # BANKING SECTOR (Ngân hàng) - 12 stocks
        banking_stocks = [
            VNStock("VCB", "Vietcombank", "Ngân hàng TMCP Ngoại thương Việt Nam", 
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=450000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.95,
                    description_vi="Ngân hàng thương mại cổ phần lớn nhất Việt Nam"),
            
            VNStock("BID", "BIDV", "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=380000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.93),
            
            VNStock("CTG", "VietinBank", "Ngân hàng TMCP Công thương Việt Nam",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=320000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.92),
            
            VNStock("MBB", "MB Bank", "Ngân hàng TMCP Quân đội",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=180000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.90),
            
            VNStock("TCB", "Techcombank", "Ngân hàng TMCP Kỹ thương Việt Nam",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=220000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.91),
            
            VNStock("ACB", "ACB", "Ngân hàng TMCP Á Châu",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=160000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.89),
            
            VNStock("VPB", "VPBank", "Ngân hàng TMCP Việt Nam Thịnh Vượng",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=140000, foreign_ownership_limit=30.0,
                    liquidity_rating="High", data_quality_score=0.88),
            
            VNStock("STB", "Sacombank", "Ngân hàng TMCP Sài Gòn Thương Tín",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=90000, foreign_ownership_limit=30.0,
                    liquidity_rating="Medium", data_quality_score=0.85),
            
            VNStock("TPB", "TPBank", "Ngân hàng TMCP Tiên Phong",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=75000, foreign_ownership_limit=30.0,
                    liquidity_rating="Medium", data_quality_score=0.84),
            
            VNStock("HDB", "HDBank", "Ngân hàng TMCP Phát triển TP.HCM",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=65000, foreign_ownership_limit=30.0,
                    liquidity_rating="Medium", data_quality_score=0.83),
            
            VNStock("SSB", "SeABank", "Ngân hàng TMCP Đông Nam Á",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=55000, foreign_ownership_limit=30.0,
                    liquidity_rating="Medium", data_quality_score=0.82),
            
            VNStock("OCB", "OCB", "Ngân hàng TMCP Phương Đông",
                    VNSector.BANKING, VNExchange.HOSE, "Commercial Banking",
                    market_cap_billion_vnd=45000, foreign_ownership_limit=30.0,
                    liquidity_rating="Medium", data_quality_score=0.81),
        ]
        
        # REAL ESTATE SECTOR (Bất động sản) - 8 stocks
        real_estate_stocks = [
            VNStock("VIC", "Vingroup", "Tập đoàn Vingroup",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Diversified Real Estate",
                    market_cap_billion_vnd=280000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.92,
                    description_vi="Tập đoàn bất động sản và đa ngành lớn nhất Việt Nam"),
            
            VNStock("VHM", "Vinhomes", "Công ty CP Vinhomes",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Residential Real Estate",
                    market_cap_billion_vnd=220000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.91),
            
            VNStock("VRE", "Vincom Retail", "Công ty CP Bán lẻ Vincom",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Retail Real Estate",
                    market_cap_billion_vnd=95000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.87),
            
            VNStock("NVB", "Novaland", "Tập đoàn Đầu tư Địa ốc Nova",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Residential Real Estate",
                    market_cap_billion_vnd=45000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.80,
                    regulatory_notes=["Restructuring ongoing"]),
            
            VNStock("PDR", "Phat Dat Real Estate", "Công ty CP Phát triển Bất động sản Phát Đạt",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Residential Real Estate",
                    market_cap_billion_vnd=25000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.78),
            
            VNStock("DXG", "Dat Xanh Group", "Tập đoàn Đất Xanh",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Real Estate Services",
                    market_cap_billion_vnd=20000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.76),
            
            VNStock("KDH", "Khang Dien House", "Công ty CP Nhà Khang Điền",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Residential Real Estate",
                    market_cap_billion_vnd=18000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.75),
            
            VNStock("NLG", "Nam Long Group", "Tập đoàn Nam Long",
                    VNSector.REAL_ESTATE, VNExchange.HOSE, "Residential Real Estate",
                    market_cap_billion_vnd=15000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.74),
        ]
        
        # CONSUMER STAPLES (Hàng tiêu dùng thiết yếu) - 6 stocks
        consumer_staples = [
            VNStock("VNM", "Vinamilk", "Công ty CP Sữa Việt Nam",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Food Products",
                    market_cap_billion_vnd=180000, foreign_ownership_limit=51.0,
                    liquidity_rating="High", data_quality_score=0.94,
                    description_vi="Công ty sữa lớn nhất Việt Nam"),
            
            VNStock("MSN", "Masan Group", "Tập đoàn Masan",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Food Products",
                    market_cap_billion_vnd=120000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.90),
            
            VNStock("SAB", "Sabeco", "Tổng công ty Bia - Rượu - Nước giải khát Sài Gòn",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Beverages",
                    market_cap_billion_vnd=95000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.89),
            
            VNStock("QNS", "Quang Ngai Sugar", "Công ty CP Mía đường Quảng Ngãi",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Food Products",
                    market_cap_billion_vnd=35000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.82),
            
            VNStock("DBC", "Dabaco Vietnam", "Tập đoàn Dabaco Việt Nam",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Food Products",
                    market_cap_billion_vnd=22000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.79),
            
            VNStock("MCH", "Masan Consumer Holdings", "Công ty CP Hàng tiêu dùng Masan",
                    VNSector.CONSUMER_STAPLES, VNExchange.HOSE, "Household Products",
                    market_cap_billion_vnd=18000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.77),
        ]
        
        # MATERIALS & CONSTRUCTION (Vật liệu/Xây dựng) - 6 stocks
        materials_stocks = [
            VNStock("HPG", "Hoa Phat Group", "Tập đoàn Hòa Phát",
                    VNSector.MATERIALS, VNExchange.HOSE, "Steel",
                    market_cap_billion_vnd=140000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.91,
                    description_vi="Tập đoàn sản xuất thép lớn nhất Việt Nam"),
            
            VNStock("HSG", "Hoa Sen Group", "Tập đoàn Hoa Sen",
                    VNSector.MATERIALS, VNExchange.HOSE, "Steel",
                    market_cap_billion_vnd=35000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.83),
            
            VNStock("NKG", "Nam Kim Steel", "Công ty CP Thép Nam Kim",
                    VNSector.MATERIALS, VNExchange.HOSE, "Steel",
                    market_cap_billion_vnd=25000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.80),
            
            VNStock("HT1", "Ha Tien Cement", "Công ty CP Xi măng Hà Tiên 1",
                    VNSector.MATERIALS, VNExchange.HOSE, "Construction Materials",
                    market_cap_billion_vnd=12000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.75),
            
            VNStock("CCM", "Central Construction", "Công ty CP Xây dựng và Thiết bị Cơ khí",
                    VNSector.MATERIALS, VNExchange.HOSE, "Construction",
                    market_cap_billion_vnd=8000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.72),
            
            VNStock("L10", "Loi Viet Construction", "Công ty CP Xây dựng Lõi Việt",
                    VNSector.MATERIALS, VNExchange.HOSE, "Construction",
                    market_cap_billion_vnd=6000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.70),
        ]
        
        # TECHNOLOGY (Công nghệ) - 4 stocks
        technology_stocks = [
            VNStock("FPT", "FPT Corporation", "Tập đoàn FPT",
                    VNSector.TECHNOLOGY, VNExchange.HOSE, "IT Services",
                    market_cap_billion_vnd=160000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.93,
                    description_vi="Tập đoàn công nghệ và viễn thông hàng đầu Việt Nam"),
            
            VNStock("CMG", "CMC Corporation", "Tập đoàn CMC",
                    VNSector.TECHNOLOGY, VNExchange.HOSE, "IT Services",
                    market_cap_billion_vnd=25000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.81),
            
            VNStock("GIT", "GIT Global", "Công ty CP GIT Global",
                    VNSector.TECHNOLOGY, VNExchange.HOSE, "IT Services",
                    market_cap_billion_vnd=8000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.73),
            
            VNStock("SAF", "SafeShare", "Công ty CP An toàn Thông tin SafeShare",
                    VNSector.TECHNOLOGY, VNExchange.HOSE, "Cybersecurity",
                    market_cap_billion_vnd=5000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.70),
        ]
        
        # Add more sectors...
        other_stocks = [
            # ENERGY
            VNStock("GAS", "PV Gas", "Tổng công ty Khí Việt Nam",
                    VNSector.ENERGY, VNExchange.HOSE, "Oil & Gas",
                    market_cap_billion_vnd=95000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.89),
            
            VNStock("PLX", "Petrolimex", "Tập đoàn Xăng dầu Việt Nam",
                    VNSector.ENERGY, VNExchange.HOSE, "Oil & Gas Refining",
                    market_cap_billion_vnd=75000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.87),
            
            # UTILITIES
            VNStock("POW", "PV Power", "Tổng công ty Điện lực Dầu khí Việt Nam",
                    VNSector.UTILITIES, VNExchange.HOSE, "Electric Utilities",
                    market_cap_billion_vnd=55000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.86),
            
            VNStock("REE", "Refrigeration Electrical Engineering", "Công ty CP Cơ điện lạnh",
                    VNSector.UTILITIES, VNExchange.HOSE, "Electric Utilities",
                    market_cap_billion_vnd=25000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.80),
            
            # INDUSTRIALS
            VNStock("VJC", "Vietjet Air", "Công ty CP Hàng không Vietjet",
                    VNSector.INDUSTRIALS, VNExchange.HOSE, "Airlines",
                    market_cap_billion_vnd=45000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.84),
            
            VNStock("HVN", "Vietnam Airlines", "Tổng công ty Hàng không Việt Nam",
                    VNSector.INDUSTRIALS, VNExchange.HOSE, "Airlines",
                    market_cap_billion_vnd=35000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.78),
            
            # HEALTHCARE
            VNStock("DHG", "DHG Pharma", "Công ty CP Dược Hậu Giang",
                    VNSector.HEALTHCARE, VNExchange.HOSE, "Pharmaceuticals",
                    market_cap_billion_vnd=18000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.79),
            
            VNStock("IMP", "Imexpharm", "Công ty CP Xuất nhập khẩu Dược phẩm",
                    VNSector.HEALTHCARE, VNExchange.HOSE, "Pharmaceuticals",
                    market_cap_billion_vnd=12000, foreign_ownership_limit=49.0,
                    liquidity_rating="Low", data_quality_score=0.76),
            
            # TELECOMMUNICATIONS
            VNStock("VGI", "Viettel Global", "Tổng công ty Viễn thông Viettel",
                    VNSector.TELECOMMUNICATIONS, VNExchange.HOSE, "Telecom Services",
                    market_cap_billion_vnd=65000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.88),
            
            # FINANCIALS
            VNStock("SSI", "SSI Securities", "Công ty CP Chứng khoán SSI",
                    VNSector.FINANCIALS, VNExchange.HOSE, "Capital Markets",
                    market_cap_billion_vnd=25000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.85),
            
            VNStock("VCI", "VCBS", "Công ty CP Chứng khoán Vietcombank",
                    VNSector.FINANCIALS, VNExchange.HOSE, "Capital Markets",
                    market_cap_billion_vnd=22000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.84),
            
            VNStock("HCM", "HCM Securities", "Công ty CP Chứng khoán TP.HCM",
                    VNSector.FINANCIALS, VNExchange.HOSE, "Capital Markets",
                    market_cap_billion_vnd=18000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.82),
            
            VNStock("BVH", "Bao Viet Holdings", "Tập đoàn Bảo Việt",
                    VNSector.FINANCIALS, VNExchange.HOSE, "Insurance",
                    market_cap_billion_vnd=85000, foreign_ownership_limit=49.0,
                    liquidity_rating="High", data_quality_score=0.88),
            
            VNStock("PVI", "PV Insurance", "Tổng công ty Cổ phần Bảo hiểm Dầu khí Việt Nam",
                    VNSector.FINANCIALS, VNExchange.HOSE, "Insurance",
                    market_cap_billion_vnd=15000, foreign_ownership_limit=49.0,
                    liquidity_rating="Medium", data_quality_score=0.79),
        ]
        
        # Add all stocks to database
        all_stocks = (banking_stocks + real_estate_stocks + consumer_staples + 
                     materials_stocks + technology_stocks + other_stocks)
        
        for stock in all_stocks:
            self.stocks[stock.ticker] = stock
    
    def get_stock(self, ticker: str) -> Optional[VNStock]:
        """Get stock by ticker (with or without exchange suffix)"""
        # Remove exchange suffix if present
        base_ticker = ticker.split('.')[0].upper()
        return self.stocks.get(base_ticker)
    
    def search(self, query: str) -> List[VNStock]:
        """Search stocks by ticker or name (supports Vietnamese)"""
        query_lower = query.lower()
        results = []
        
        for stock in self.stocks.values():
            # Search by ticker
            if query_lower in stock.ticker.lower():
                results.append(stock)
                continue
            
            # Search by English name
            if query_lower in stock.company_name_en.lower():
                results.append(stock)
                continue
            
            # Search by Vietnamese name
            if query_lower in stock.company_name_vi.lower():
                results.append(stock)
                continue
        
        return results
    
    def get_by_sector(self, sector: VNSector) -> List[VNStock]:
        """Get all stocks in a sector"""
        return [s for s in self.stocks.values() if s.sector == sector]
    
    def get_by_exchange(self, exchange: VNExchange) -> List[VNStock]:
        """Get all stocks on an exchange"""
        return [s for s in self.stocks.values() if s.exchange == exchange]
    
    def get_all_stocks(self) -> List[VNStock]:
        """Get all stocks"""
        return list(self.stocks.values())
    
    def get_sectors(self) -> List[VNSector]:
        """Get all sectors with stock counts"""
        sector_counts = {}
        for stock in self.stocks.values():
            sector_counts[stock.sector] = sector_counts.get(stock.sector, 0) + 1
        
        return sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
    
    def load_from_json(self, filepath: str):
        """Load additional stocks from JSON file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            sector = VNSector[item['sector']]
            exchange = VNExchange[item['exchange']]
            
            stock = VNStock(
                ticker=item['ticker'],
                company_name_en=item['company_name_en'],
                company_name_vi=item['company_name_vi'],
                sector=sector,
                exchange=exchange,
                industry=item.get('industry', ''),
                market_cap_billion_vnd=item.get('market_cap_billion_vnd'),
                foreign_ownership_limit=item.get('foreign_ownership_limit'),
                current_fol=item.get('current_fol'),
                is_fol_restricted=item.get('is_fol_restricted', False),
                listing_date=item.get('listing_date'),
                description_en=item.get('description_en'),
                description_vi=item.get('description_vi'),
                website=item.get('website'),
                liquidity_rating=item.get('liquidity_rating', 'Medium'),
                data_quality_score=item.get('data_quality_score', 0.8),
                regulatory_notes=item.get('regulatory_notes', [])
            )
            
            self.stocks[stock.ticker] = stock
    
    def load_from_csv(self, filepath: str):
        """Load additional stocks from CSV file"""
        import csv
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sector = VNSector[row['sector']]
                exchange = VNExchange[row['exchange']]
                
                stock = VNStock(
                    ticker=row['ticker'],
                    company_name_en=row['company_name_en'],
                    company_name_vi=row['company_name_vi'],
                    sector=sector,
                    exchange=exchange,
                    industry=row.get('industry', ''),
                    market_cap_billion_vnd=float(row['market_cap_billion_vnd']) if row.get('market_cap_billion_vnd') else None,
                    foreign_ownership_limit=float(row['foreign_ownership_limit']) if row.get('foreign_ownership_limit') else None,
                    current_fol=float(row['current_fol']) if row.get('current_fol') else None,
                    is_fol_restricted=row.get('is_fol_restricted', 'False').lower() == 'true',
                    listing_date=row.get('listing_date'),
                    description_en=row.get('description_en'),
                    description_vi=row.get('description_vi'),
                    website=row.get('website'),
                    liquidity_rating=row.get('liquidity_rating', 'Medium'),
                    data_quality_score=float(row.get('data_quality_score', 0.8)),
                    regulatory_notes=row.get('regulatory_notes', '').split(';') if row.get('regulatory_notes') else []
                )
                
                self.stocks[stock.ticker] = stock
    
    def export_to_json(self, filepath: str):
        """Export all stocks to JSON file"""
        data = [stock.to_dict() for stock in self.stocks.values()]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        total_stocks = len(self.stocks)
        
        by_exchange = {}
        for stock in self.stocks.values():
            by_exchange[stock.exchange.value] = by_exchange.get(stock.exchange.value, 0) + 1
        
        by_sector = {}
        for stock in self.stocks.values():
            sector_name = stock.sector.value[0]
            by_sector[sector_name] = by_sector.get(sector_name, 0) + 1
        
        avg_data_quality = sum(s.data_quality_score for s in self.stocks.values()) / total_stocks if total_stocks > 0 else 0
        
        fol_restricted_count = sum(1 for s in self.stocks.values() if s.is_fol_restricted)
        
        return {
            "total_stocks": total_stocks,
            "by_exchange": by_exchange,
            "by_sector": by_sector,
            "average_data_quality_score": round(avg_data_quality, 2),
            "fol_restricted_stocks": fol_restricted_count,
            "high_liquidity_stocks": sum(1 for s in self.stocks.values() if s.liquidity_rating == "High")
        }


# Singleton instance
vn_stock_db = VNStockDatabase()


def get_vn_stock_database() -> VNStockDatabase:
    """Get the singleton VNStockDatabase instance"""
    return vn_stock_db
