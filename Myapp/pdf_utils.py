from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import code128

def build_loyalty_card_pdf(customer, profile=None):
    """
    Génère un PDF carte fidélité format carte bancaire.
    profile: instance de UserProfile pour infos entreprise
    """
    buffer = BytesIO()
    width = 85.6 * mm
    height = 54 * mm
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # 🎨 Fond sombre premium
    c.setFillColorRGB(0.05, 0.1, 0.3)
    c.rect(0, 0, width, height, fill=1)

    # 🟡 Cercles style MasterCard
    circle_radius = 18 * mm
    c.setFillColorRGB(1, 0.3, 0)
    c.circle(width - 35 * mm, height - 20 * mm, circle_radius, fill=1)
    c.setFillColorRGB(1, 0.8, 0)
    c.circle(width - 25 * mm, height - 20 * mm, circle_radius, fill=1)

    # 🏷 Titre
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(10 * mm, height - 10 * mm, "CARTE DE FIDELITE")

    # 👤 Nom client
    c.setFont("Helvetica", 9)
    full_name = f"{customer.name} {customer.last_name}"
    c.drawString(10 * mm, height - 18 * mm, full_name.upper())

    # 🏢 Nom entreprise si profile fourni
    if profile and profile.entrep_name:
        c.setFont("Helvetica", 8)
        c.drawString(10 * mm, height - 26 * mm, profile.entrep_name.upper())

    # 💳 Numéro carte formaté
    card_number = customer.loyalty_card_number
    formatted_number = f"{card_number[:3]}-{card_number[3:]}"
    c.setFont("Helvetica-Bold", 14)
    c.drawString(10 * mm, height - 34 * mm, formatted_number)

    # 📊 Code barre
    barcode = code128.Code128(card_number, barHeight=10 * mm, barWidth=0.5)
    barcode.drawOn(c, 10 * mm, 8 * mm)

    # ✨ Mention publicitaire BilaSol APP
    c.setFont("Helvetica-Oblique", 6)
    c.setFillColor(colors.lightgrey)
    c.drawRightString(width - 5 * mm, 2 * mm, "BilaSol APP")

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf