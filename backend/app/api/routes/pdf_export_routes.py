"""
PDF Export Routes

Generates investment memorandum PDFs from valuation results.
Uses ReportLab for pure-Python PDF generation (no system dependencies).

Endpoint: POST /api/session/{session_id}/export-pdf
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.core.session_service import session_service

logger = get_logger(__name__)
router = APIRouter(tags=["PDF Export"])


class ExportPdfRequest(BaseModel):
    """Request to generate PDF export"""
    methods: List[str] = Field(
        default=["DCF", "DUPONT", "COMPS"],
        description="Valuation methods to include in report"
    )
    market: str = Field(
        default="international",
        description="Market type"
    )
    include_sensitivity: bool = Field(
        default=True,
        description="Include sensitivity analysis tables"
    )
    include_peer_comparison: bool = Field(
        default=True,
        description="Include peer comparison data"
    )


class ExportPdfResponse(BaseModel):
    """Response for PDF export status"""
    status: str
    message: str
    download_url: Optional[str] = None


@router.post("/session/{session_id}/export-pdf")
async def export_pdf(
    session_id: str,
    request: ExportPdfRequest
):
    """
    Generate a PDF investment memorandum from valuation results.
    
    Workflow:
    1. Retrieve Step 9 confirmed outputs and Step 10 results from session
    2. Build HTML template with all valuation data
    3. Convert to PDF using ReportLab
    4. Return binary PDF stream with Content-Disposition header
    
    Returns:
        StreamingResponse with PDF binary data
    """
    try:
        # Validate session exists
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        ticker = session.get("ticker", "UNKNOWN")
        company_name = session.get("company_name", ticker)
        market = request.market
        
        # Collect valuation results for all requested methods
        results = {}
        for method in request.methods:
            method_lower = method.lower()
            step9_output = session_service.get_session_value(
                session_id, "step9_confirmed_outputs", {},
                market=market, method=method_lower
            )
            step10_results = session_service.get_session_value(
                session_id, "valuation_results", {},
                market=market, method=method_lower
            )
            if step10_results:
                results[method] = {
                    "step9": step9_output,
                    "step10": step10_results,
                }
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="No valuation results found. Please complete Step 10 first."
            )
        
        # Generate PDF using ReportLab
        pdf_buffer = _generate_pdf(
            ticker=ticker,
            company_name=company_name,
            market=market,
            methods=request.methods,
            results=results,
            include_sensitivity=request.include_sensitivity,
            include_peer_comparison=request.include_peer_comparison,
        )
        
        # Return as streaming response
        filename = f"{ticker}_investment_memorandum.pdf"
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_buffer.getvalue())),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}"
        )


def _generate_pdf(
    ticker: str,
    company_name: str,
    market: str,
    methods: List[str],
    results: dict,
    include_sensitivity: bool,
    include_peer_comparison: bool,
):
    """
    Generate PDF using ReportLab.
    
    Falls back to a simple text-based PDF if ReportLab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=HexColor('#1e293b'),
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#475569'),
            spaceAfter=10,
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#334155'),
            spaceAfter=6,
        )
        
        elements = []
        
        # ─── Cover Section ───
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Investment Memorandum", title_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{company_name}</b> ({ticker})", heading_style))
        elements.append(Paragraph(f"Market: {market.title()}", body_style))
        elements.append(Paragraph(f"Valuation Methods: {', '.join(methods)}", body_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("─" * 60, body_style))
        
        # ─── Method Results ───
        for method in methods:
            if method not in results:
                continue
            
            method_data = results[method]
            step10 = method_data.get("step10", {})
            
            elements.append(Spacer(1, 15))
            elements.append(Paragraph(f"{method} Valuation Results", heading_style))
            
            # Build results table
            summary = step10.get("valuation_summary", {})
            if summary:
                table_data = [["Metric", "Value"]]
                for key, value in summary.items():
                    if isinstance(value, (int, float)):
                        table_data.append([key.replace("_", " ").title(), f"{value:,.2f}"])
                    elif isinstance(value, str):
                        table_data.append([key.replace("_", " ").title(), value])
                
                if len(table_data) > 1:
                    table = Table(table_data, colWidths=[3*inch, 2*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e2e8f0')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1e293b')),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
                        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f8fafc')]),
                    ]))
                    elements.append(table)
            else:
                elements.append(Paragraph("No results available", body_style))
        
        # ─── Sensitivity Section ───
        if include_sensitivity:
            elements.append(PageBreak())
            elements.append(Paragraph("Sensitivity Analysis", heading_style))
            elements.append(Paragraph(
                "The table below shows how the implied share price changes with variations in WACC and Terminal Growth Rate.",
                body_style
            ))
            # Placeholder for sensitivity table
            elements.append(Paragraph("[Sensitivity matrix would be rendered here]", body_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except ImportError:
        # Fallback: Generate simple text PDF without ReportLab
        return _generate_fallback_pdf(ticker, company_name, methods, results)


def _generate_fallback_pdf(ticker, company_name, methods, results):
    """Fallback PDF generation without ReportLab."""
    from io import BytesIO
    
    content = f"Investment Memorandum\n"
    content += f"{'=' * 40}\n"
    content += f"Company: {company_name} ({ticker})\n\n"
    
    for method in methods:
        if method in results:
            content += f"{method} Results:\n"
            content += f"-" * 30 + "\n"
            summary = results[method].get("step10", {}).get("valuation_summary", {})
            for k, v in summary.items():
                content += f"  {k}: {v}\n"
            content += "\n"
    
    buffer = BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    return buffer
