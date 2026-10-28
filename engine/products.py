from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .common import EngineError, save_json
from .media import font_path, wrap_pixels


def product_pack(entries, destination, *, fixture=False):
    """One image-based page per board avoids PDF Arabic shaping inconsistencies."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if not entries:
        raise EngineError("No accepted images available for a product pack")
    if not fixture and any(e.get("fixture") for e in entries):
        raise EngineError("Test images cannot enter a real product pack")
    if not fixture and any(e.get("source") != "pollinations" or not e.get("vision_approved") for e in entries):
        raise EngineError("Product packs require AI provenance and approved image checks")
    pdfmetrics.registerFont(TTFont("DesignSans", font_path()))
    paths = [destination / name for name in ("mood-boards.pdf", "palette-sheets.pdf", "style-guide.pdf")]
    mood, palette, guide = [canvas.Canvas(str(path), pagesize=A4) for path in paths]
    width, height = A4
    for document, title in ((mood, "Mood boards"), (palette, "Color palette sheets"), (guide, "Residential style guide")):
        document.setTitle(("TEST - " if fixture else "") + title)
        document.setAuthor("Design Engine")
    for n, entry in enumerate(entries):
        image = Path(entry["path"])
        board = Image.new("RGB", (1240, 1754), "#F5F1E9")
        draw = ImageDraw.Draw(board)
        title_font = ImageFont.truetype(font_path(), 46)
        body_font = ImageFont.truetype(font_path(), 28)
        title = entry["style"] + " / " + entry["palette_name"]
        lines = wrap_pixels(draw, title, title_font, 1120)
        for i, line in enumerate(lines[:2]):
            draw.text((60, 55 + i * 60), line, font=title_font, fill="#293734")
        visual = ImageOps.fit(Image.open(image).convert("RGB"), (1120, 1190), method=Image.Resampling.LANCZOS)
        board.paste(visual, (60, 200))
        for i, hex_ in enumerate(entry["colors"]):
            x = 60 + i * 375
            draw.rectangle((x, 1430, x + 340, 1500), fill=hex_)
            draw.text((x, 1514), hex_, font=body_font, fill="#293734")
        label = "TEST FIXTURE - NOT FOR SALE" if fixture else "AI-generated concept / inspiration only"
        draw.text((60, 1630), label, font=body_font, fill="#293734")
        page = destination / f"board-{n:03}.jpg"
        board.save(page, quality=90)
        mood.drawImage(str(page), 0, 0, width=width, height=height)
        mood.showPage()
        for document, heading in ((palette, "Palette: " + entry["palette_name"]), (guide, "Style: " + entry["style"])):
            document.setFillColor(colors.HexColor("#293734"))
            document.setFont("DesignSans", 19)
            document.drawString(40, height - 55, heading)
            document.drawImage(str(image), 40, height - 400, width=210, height=315, preserveAspectRatio=True)
            document.setFont("DesignSans", 11)
            content = [entry.get("tip", "Compare material samples in the room's own light."), "Use these as approximate screen colors; check physical samples.", "Concept furniture is not a representation of an exact retail product.", "Review dimensions, delivery access and material suitability before buying."]
            y = height - 440
            for paragraph in content:
                words, line = paragraph.split(), ""
                for word in words:
                    trial = (line + " " + word).strip()
                    if pdfmetrics.stringWidth(trial, "DesignSans", 11) > width - 80:
                        document.drawString(40, y, line)
                        y -= 17
                        line = word
                    else:
                        line = trial
                document.drawString(40, y, line)
                y -= 30
            for i, color in enumerate(entry["colors"]):
                document.setFillColor(colors.HexColor(color))
                document.rect(280, height - 160 - i * 95, 110, 55, fill=1, stroke=0)
                document.setFillColor(colors.HexColor("#293734"))
                document.drawString(280, height - 178 - i * 95, color)
            document.setFont("DesignSans", 9)
            document.drawString(40, 35, label + f" | {n + 1}")
            document.showPage()
    for document in (mood, palette, guide):
        document.save()
    save_json(destination / "provenance.json", [{k: v for k, v in entry.items() if k != "path"} for entry in entries])
    (destination / "READ-ME.txt").write_text(
        ("TEST PACK - DO NOT SELL.\n" if fixture else "DRAFT PACK - review every page before listing.\n") +
        "AI-generated interior concepts. Colors are approximate. Furniture suggestions are not exact retail matches.\n"
        "Review image rights and the marketplace's current AI disclosure requirements before listing.\n"
        "No affiliate links are embedded in these PDFs. Add your own listing, price and usage license.\n",
        encoding="utf-8",
    )
    return paths
