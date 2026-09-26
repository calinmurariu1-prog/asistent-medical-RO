"""Generate a synthetic document for local verification."""
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
path = Path(__file__).resolve().parents[1] / "demo" / "analize-fictive.pdf"
path.parent.mkdir(exist_ok=True)
canvas = Canvas(str(path))
for y, line in enumerate(["DATE FICTIVE - TEST", "Glicemie 105 mg/dL (70 - 99)",
                          "Hemoglobina 13.5 g/dL (12 - 16)"]):
    canvas.drawString(50, 780 - y * 30, line)
canvas.save()
