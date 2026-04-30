"""Create a sample VNM PDF for testing"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Try to register a Vietnamese font (optional)
try:
    pdfmetrics.registerFont(TTFont('Arial', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
except:
    pass

def create_sample_vnm_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = styles['Heading1']
    elements.append(Paragraph("CONG TY CO PHAN SUA VIET NAM (VNM)", title_style))
    elements.append(Paragraph("BAO CAO TAI CHINH HOP NHAT NAM 2023", styles['Heading2']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Balance Sheet Data (in billions VND - ty dong)
    balance_data = [
        ['CHI TIÊU', '2023 (ty VND)', '2022 (ty VND)'],
        ['TONG TAI SAN', '50,500', '48,200'],
        ['Tai san ngan han', '25,300', '24,100'],
        ['  Tien va tuong duong tien', '8,500', '7,200'],
        ['  Phai thu khach hang', '3,200', '2,900'],
        ['  Hang ton kho', '6,800', '6,500'],
        ['Tai san dai han', '25,200', '24,100'],
        ['  Tai san co dinh', '20,100', '19,500'],
        ['TONG NO PHAI TRA', '18,200', '17,500'],
        ['No ngan han', '10,500', '9,800'],
        ['No dai han', '7,700', '7,700'],
        ['VON CHU SO HUU', '32,300', '30,700'],
    ]
    
    elements.append(Paragraph("BANG CAN DOI KE TOAN", styles['Heading3']))
    table = Table(balance_data, colWidths=[3*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Income Statement Data
    income_data = [
        ['CHI TIÊU', '2023 (ty VND)', '2022 (ty VND)'],
        ['DOANH THU THUAN', '85,500', '82,300'],
        ['Gia von hang ban', '52,300', '50,100'],
        ['LOI NHUAN GOP', '33,200', '32,200'],
        ['Chi phi ban hang', '15,200', '14,800'],
        ['Chi phi quan ly doanh nghiep', '3,500', '3,200'],
        ['LOI NHUAN TU HDKD', '14,500', '14,200'],
        ['EBITDA', '16,800', '16,200'],
        ['LOI NHUAN TRUOC THUE', '14,200', '13,900'],
        ['Thue TNDN', '2,840', '2,780'],
        ['LOI NHUAN SAU THUE', '11,360', '11,120'],
    ]
    
    elements.append(Paragraph("BAO CAO KET QUA HOAT DONG KINH DOANH", styles['Heading3']))
    table2 = Table(income_data, colWidths=[3*inch, 1.2*inch, 1.2*inch])
    table2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table2)
    
    doc.build(elements)
    print(f"Created sample VNM PDF: {filename}")

if __name__ == "__main__":
    try:
        create_sample_vnm_pdf("/workspace/test_pdfs/VNM_Bao_Cao_Tai_Chinh_2023.pdf")
    except ImportError:
        print("reportlab not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab"])
        create_sample_vnm_pdf("/workspace/test_pdfs/VNM_Bao_Cao_Tai_Chinh_2023.pdf")
