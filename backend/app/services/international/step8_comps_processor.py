"""Step 8: Comparable Companies Processor"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PeerCompany(BaseModel):
    ticker: str
    name: str
    ev_ebitda_ltm: Optional[float] = None
    pe_ratio_ltm: Optional[float] = None
    ev_revenue_ltm: Optional[float] = None
    pb_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    is_outlier: bool = False

class CompsMetrics(BaseModel):
    median_ev_ebitda: Optional[float] = None
    mean_ev_ebitda: Optional[float] = None
    median_pe: Optional[float] = None
    mean_pe: Optional[float] = None

class Step8Response(BaseModel):
    target_ticker: str
    peer_companies: List[PeerCompany]
    comps_metrics: CompsMetrics
    outliers_removed: int = 0
    warnings: List[str] = []

class Step8CompsProcessor:
    def process_comps_analysis(self, target_ticker: str, peer_list: List[str], apply_outlier_filter: bool = True) -> Step8Response:
        peers = [PeerCompany(ticker=p, name=f"{p} Inc.", ev_ebitda_ltm=12.5, pe_ratio_ltm=18.0, ev_revenue_ltm=3.2, pb_ratio=2.5, market_cap=50e9, sector="Technology") for p in peer_list[:10]]
        outliers_removed = 0
        if apply_outlier_filter and len(peers) >= 4:
            evs = [p.ev_ebitda_ltm for p in peers if p.ev_ebitda_ltm]
            if len(evs) >= 4:
                q1, q3 = sorted(evs)[len(evs)//4], sorted(evs)[3*len(evs)//4]
                iqr = q3 - q1
                for p in peers:
                    if p.ev_ebitda_ltm and (p.ev_ebitda_ltm < q1-1.5*iqr or p.ev_ebitda_ltm > q3+1.5*iqr):
                        p.is_outlier = True; outliers_removed += 1
        
        evs_clean = [p.ev_ebitda_ltm for p in peers if p.ev_ebitda_ltm and not p.is_outlier]
        pes_clean = [p.pe_ratio_ltm for p in peers if p.pe_ratio_ltm and not p.is_outlier]
        metrics = CompsMetrics(median_ev_ebitda=sorted(evs_clean)[len(evs_clean)//2] if evs_clean else None, mean_ev_ebitda=sum(evs_clean)/len(evs_clean) if evs_clean else None, median_pe=sorted(pes_clean)[len(pes_clean)//2] if pes_clean else None, mean_pe=sum(pes_clean)/len(pes_clean) if pes_clean else None)
        return Step8Response(target_ticker=target_ticker, peer_companies=peers, comps_metrics=metrics, outliers_removed=outliers_removed)
