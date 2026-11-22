"""Generador del PDF del presupuesto con ReportLab (HU08)."""
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

EMPRESA = {"nombre": "M y C Revestimientos y Pinturas SpA", "rut": "78.136.827-K", "ciudad": "Valdivia, Chile"}
LOGO = Path(__file__).parent / "assets" / "logo_mc.png"
VIGENCIA_DIAS = 30  # las planillas actuales de M y C tienen vigencia de un mes


def clp(n):
    return "$" + f"{int(n):,}".replace(",", ".")


def num(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")


def generar_pdf(cot) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"Presupuesto COD-{cot.pk:03d}", author=EMPRESA["nombre"])
    est = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=est["Title"], fontSize=18, alignment=0, spaceAfter=2)
    peq = ParagraphStyle("peq", parent=est["Normal"], fontSize=9, leading=12)
    sec = ParagraphStyle("sec", parent=est["Heading3"], spaceBefore=10, spaceAfter=4)
    azul = colors.HexColor("#0A2A50")
    dorado = colors.HexColor("#DAB14C")
    f = []

    fecha = cot.fecha_calculo or cot.fecha_solicitud
    datos_empresa = [Paragraph(EMPRESA["nombre"], h1), Paragraph(f"RUT {EMPRESA['rut']} · {EMPRESA['ciudad']}", peq)]
    if LOGO.exists():
        logo = Image(str(LOGO), width=3.2 * cm, height=3.2 * cm * 0.86)  # proporción real del logo (700x602)
        encabezado = Table([[logo, datos_empresa]], colWidths=[3.8 * cm, 13.2 * cm])
        encabezado.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        f.append(encabezado)
    else:
        f.extend(datos_empresa)
    f.append(Spacer(1, 8))
    cab = Table([[f"PRESUPUESTO N° COD-{cot.pk:03d}", f"Fecha: {fecha:%d/%m/%Y}"],
                 [f"Estado: {cot.get_estado_display()}", f"Vigencia: {(fecha + timedelta(days=VIGENCIA_DIAS)):%d/%m/%Y}"]],
                colWidths=[9.5 * cm, 7.5 * cm])
    cab.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10),
                             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF6")), ("LINEBELOW", (0, 1), (-1, 1), 1.5, dorado), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    f.append(cab)

    c = cot.cliente
    f.append(Paragraph("Datos del cliente", sec))
    f.append(Paragraph(f"<b>{c.nombre_razon_social}</b> · RUT {c.rut}<br/>{c.correo_contacto}"
                       + (f" · {c.telefono}" if c.telefono else ""), peq))
    f.append(Paragraph("Obra", sec))
    f.append(Paragraph(f"<b>{cot.nombre_obra}</b><br/>{cot.direccion_obra}, {cot.ciudad}<br/>"
                       f"Alcance: {'obra vendida, incluye materiales e insumos' if cot.origen_materiales == 'EMPRESA' else 'solo mano de obra, materiales a cargo del cliente'}", peq))

    f.append(Paragraph("Descripción de los trabajos", sec))
    filas = [["Ítem", "Descripción", "Un.", "Cantidad", "P. unitario", "Total"]]
    for i, d in enumerate(cot.detalles.all(), 1):
        desc = d.tipo_acabado.nombre + (f" — {d.descripcion}" if d.descripcion else "")
        filas.append([i, Paragraph(desc, peq), d.unidad.lower(), num(d.cantidad), clp(d.precio_unitario), clp(d.costo_mano_obra)])
    n_trab = len(filas) - 1

    t = Table(filas, colWidths=[1.1 * cm, 7 * cm, 1.3 * cm, 2.3 * cm, 2.6 * cm, 2.7 * cm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), azul), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("ALIGN", (3, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D1DB")),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    f.append(t)
    f.append(Spacer(1, 10))

    if cot.iva:
        filas_tot = [["Neto", clp(cot.neto)], ["IVA", clp(cot.iva)], ["TOTAL", clp(cot.total)]]
    else:
        filas_tot = [["TOTAL NETO", clp(cot.neto)]]
    tot = Table(filas_tot, colWidths=[3.4 * cm, 3.4 * cm], hAlign="RIGHT")
    ult = len(filas_tot) - 1
    tot.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, ult), (-1, ult), "Helvetica-Bold"),
                             ("FONTSIZE", (0, ult), (-1, ult), 12), ("LINEABOVE", (0, ult), (-1, ult), 1.5, dorado)]))
    f.append(tot)
    if cot.observaciones:
        f.append(Paragraph("Observaciones", sec))
        f.append(Paragraph(cot.observaciones.replace("\n", "<br/>"), peq))
    f.append(Spacer(1, 14))
    f.append(Paragraph("Valores en pesos chilenos" + (", netos: no incluyen IVA." if not cot.iva else ".") + " Presupuesto sujeto a verificación de medidas en terreno.", peq))
    doc.build(f)
    return buf.getvalue()
