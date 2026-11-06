"""
Servicio de Generación de Reportes Financieros en PDF y Excel
Genera documentos ejecutivos para comités de crédito, auditoría y cobranzas de la CMAC.
"""

import io
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generar_excel_reporte(tipo_reporte: str, datos: list) -> io.BytesIO:
    """
    Genera un archivo Excel (.xlsx) profesional con formato bancario.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = tipo_reporte[:31]

    # Paleta de colores fintech
    header_fill = PatternFill(start_color="0B132B", end_color="0B132B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=16, bold=True, color="0B132B")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="475569")
    bold_font = Font(name="Calibri", size=10, bold=True)
    regular_font = Font(name="Calibri", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # Encabezado Institucional
    ws.merge_cells("A1:G1")
    ws["A1"] = "CAJA INTELIGENTE - SISTEMA DE EVALUACIÓN DE RIESGO CREDITICIO"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A2:G2")
    ws["A2"] = f"Reporte: {tipo_reporte.upper()} | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Sede: CMAC Perú"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[1].height = 25
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 24

    if not datos:
        ws["A4"] = "No hay registros disponibles para este reporte."
        ws["A4"].font = Font(name="Calibri", size=11, italic=True)
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    # Obtener encabezados desde las claves del primer registro
    headers = list(datos[0].keys())
    # Formatear nombres de columnas
    header_labels = [h.replace("_", " ").title() for h in headers]

    start_row = 4
    for col_idx, label in enumerate(header_labels, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=label)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Llenar datos
    for row_idx, item in enumerate(datos, start=start_row + 1):
        ws.row_dimensions[row_idx].height = 20
        # Alternancia de color en filas
        row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") if row_idx % 2 == 0 else PatternFill(fill_type=None)

        for col_idx, key in enumerate(headers, 1):
            val = item.get(key, "")
            if isinstance(val, str) and val.startswith(("=", "+", "-", "@")):
                val = "'" + val
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            if row_fill.fill_type:
                cell.fill = row_fill

            # Alineación según tipo de dato
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Autoajustar ancho de columnas de forma segura
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header_labels[col_idx - 1])
        for row_idx in range(start_row + 1, start_row + 1 + len(datos)):
            val_str = str(ws.cell(row=row_idx, column=col_idx).value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generar_pdf_reporte(tipo_reporte: str, datos: list, kpis: dict = None) -> io.BytesIO:
    """
    Genera un informe ejecutivo en formato PDF con membrete de Caja Inteligente.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos tipográficos
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0B132B'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )

    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    story = []

    # 1. Cabecera institucional
    story.append(Paragraph("<b>CAJA INTELIGENTE</b> | Sistema de Riesgo Crediticio con IA", title_style))
    story.append(Paragraph(
        f"<b>REPORTE EJECUTIVO:</b> {escape(str(tipo_reporte).upper())} &nbsp;|&nbsp; "
        f"<b>Fecha de Emisión:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} &nbsp;|&nbsp; "
        f"<b>CMAC Perú - Sede Central</b>",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0B132B'), spaceAfter=15))

    # 2. Resumen de KPIs si se proporciona
    if kpis:
        kpi_data = [
            [Paragraph(f"<b>{escape(str(k))}</b>", ParagraphStyle('KPIK', fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#0B132B'))),
             Paragraph(escape(str(v)), ParagraphStyle('KPIV', fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#0284C7')))]
            for k, v in kpis.items()
        ]
        # Agrupar en tabla de 2 columnas o 4
        kpi_table = Table(kpi_data, colWidths=[200, 200])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 15))

    # 3. Tabla principal de datos
    if not datos:
        story.append(Paragraph("No se encontraron registros para los criterios seleccionados.", subtitle_style))
    else:
        # Seleccionar hasta 7 columnas principales para que encaje elegantemente en horizontal
        raw_keys = list(datos[0].keys())
        keys_to_show = raw_keys[:7]

        header_row = [Paragraph(f"<b>{escape(k.replace('_', ' ').title())}</b>", header_cell_style) for k in keys_to_show]
        table_rows = [header_row]

        for item in datos:
            row_data = []
            for k in keys_to_show:
                val = str(item.get(k, ''))
                # Formatear números si aplica
                if isinstance(item.get(k), float):
                    val = f"{item.get(k):,.2f}"
                row_data.append(Paragraph(escape(val), cell_style))
            table_rows.append(row_data)

        # Determinar anchos
        col_width = (doc.width) / len(keys_to_show)
        pdf_table = Table(table_rows, colWidths=[col_width] * len(keys_to_show))
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B132B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(pdf_table)

    # 4. Pie de página y aviso normativo SBS
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=8))
    story.append(Paragraph(
        "<b>Nota Regulatoria SBS:</b> Documento de control interno confidencial. "
        "Las evaluaciones cuantitativas y dictámenes generados por Inteligencia Artificial actúan como soporte analítico y no sustituyen "
        "el dictamen vinculante del Comité de Créditos.",
        ParagraphStyle('Footer', fontSize=7, fontName='Helvetica', textColor=colors.HexColor('#64748B'))
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
