"""Turn assistant output into a downloadable file: Excel (.xlsx), Word (.docx), PowerPoint (.pptx) or Markdown (.md).

Everything goes through one small document model, so a record list and a written summary render the same way:

    Document(title, subtitle, sections=[Section(heading, paragraphs, bullets, table)])

A record export is a document with one section holding a table; a summary the model wrote is sections of text.
Excel shows the tables (one sheet each); the other formats show everything.
"""

import base64
import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from docx import Document as WordDocument
from docx.enum.section import WD_ORIENT
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Inches
from pptx.util import Pt as SlidePt
from pydantic import BaseModel, Field

from app.schemas.assistant import ExportedFile, ExportFormat

MIME_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "md": "text/markdown",
}
FORMAT_NAMES = {"xlsx": "Excel", "docx": "Word", "pptx": "PowerPoint", "md": "Markdown"}

# Most table rows each format holds. Excel and Markdown take a full export; a Word table or a deck of slides
# that long is unreadable (and slow to build), so those show the first rows and say so.
ROW_LIMITS = {"xlsx": 5000, "md": 5000, "docx": 1000, "pptx": 120}
SLIDE_ROWS = 12  # table rows per slide
SLIDE_COLUMNS = 6  # the first columns are the important ones; more don't fit on a slide
SLIDE_BULLETS = 8


class Table(BaseModel):
    columns: list[str]
    rows: list[list[Any]]  # typed values (dates, numbers) so Excel can sort and sum them
    total: int | None = None  # how many rows exist in all, when `rows` holds only the first of them


class Section(BaseModel):
    heading: str | None = None
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    table: Table | None = None


class Document(BaseModel):
    title: str
    subtitle: str | None = None
    sections: list[Section]


# The same shapes as the model writes them (the export_document tool's arguments): text only, fully typed, since
# Gemini's function schemas need a type for every array item.
class WrittenTable(BaseModel):
    columns: list[str] = Field(description="Column headings")
    rows: list[list[str]] = Field(description="One list of cell texts per row, in column order")


class WrittenSection(BaseModel):
    heading: str | None = Field(None, description="Section heading (a slide title in PowerPoint)")
    paragraphs: list[str] = Field(default_factory=list, description="Paragraphs of text")
    bullets: list[str] = Field(default_factory=list, description="Bullet points")
    table: WrittenTable | None = Field(None, description="An optional table")


def render(document: Document, format: ExportFormat) -> ExportedFile:
    if format == "xlsx" and not any(section.table for section in document.sections):
        raise ValueError("An Excel file needs a table. Use Word, PowerPoint or Markdown for text.")
    content = RENDERERS[format](document, ROW_LIMITS[format])
    return ExportedFile(
        filename=f"{_slug(document.title)}.{format}",
        format=format,
        mime_type=MIME_TYPES[format],
        content_base64=base64.b64encode(content).decode(),
    )


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].rstrip("-")
    return slug or "export"


def _text(value: Any) -> str:
    """A cell value as text, for the formats that only hold text."""
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal, float)):
        return f"{value:,.2f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    return str(value)


def _rows(table: Table, limit: int) -> tuple[list[list[Any]], str | None]:
    """The rows that fit, and a note saying how many were left out."""
    total = max(table.total or 0, len(table.rows))
    rows = table.rows[:limit]
    if len(rows) < total:
        return rows, f"Showing the first {len(rows)} of {total} rows. Export to Excel for the full list."
    return rows, None


# --- Excel ----------------------------------------------------------------------------------------------------

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")


def _cell_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    return value


def _sheet_title(heading: str | None, index: int, used: set[str]) -> str:
    name = re.sub(r"[\[\]:*?/\\]", " ", heading or "").strip()[:31] or f"Sheet{index}"
    while name in used:
        name = f"{name[:28]}_{index}"
    used.add(name)
    return name


def _xlsx(document: Document, limit: int) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    used: set[str] = set()
    for index, section in enumerate((s for s in document.sections if s.table), start=1):
        sheet = workbook.create_sheet(_sheet_title(section.heading or document.title, index, used))
        rows, note = _rows(section.table, limit)
        sheet.append(section.table.columns)
        for row in rows:
            sheet.append([_cell_value(value) for value in row])
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(vertical="center")
        # CRM text (e.g. a lead name from a web form) must never run as a formula when the file is opened.
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"
                if isinstance(cell.value, (date, datetime)):
                    cell.number_format = "yyyy-mm-dd"
        if note:
            sheet.append([])
            sheet.append([note])
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(section.table.columns))}{len(rows) + 1}"
        for column, header in enumerate(section.table.columns, start=1):
            longest = max([len(header), *(len(_text(row[column - 1])) for row in rows[:200] if column <= len(row))])
            sheet.column_dimensions[get_column_letter(column)].width = min(max(longest + 2, 10), 50)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --- Word -----------------------------------------------------------------------------------------------------


def _docx(document: Document, limit: int) -> bytes:
    word = WordDocument()
    if any(section.table and len(section.table.columns) > 6 for section in document.sections):
        page = word.sections[0]  # wide tables need a landscape page
        page.orientation = WD_ORIENT.LANDSCAPE
        page.page_width, page.page_height = page.page_height, page.page_width
    word.add_heading(document.title, level=0)
    if document.subtitle:
        word.add_paragraph().add_run(document.subtitle).italic = True
    for section in document.sections:
        if section.heading:
            word.add_heading(section.heading, level=1)
        for paragraph in section.paragraphs:
            word.add_paragraph(paragraph)
        for bullet in section.bullets:
            word.add_paragraph(bullet, style="List Bullet")
        if section.table:
            rows, note = _rows(section.table, limit)
            columns = section.table.columns
            table = word.add_table(rows=1, cols=len(columns))
            table.style = "Table Grid"
            for cell, header in zip(table.rows[0].cells, columns):
                cell.text = header
                cell.paragraphs[0].runs[0].bold = True
            for row in rows:
                for cell, value in zip(table.add_row().cells, row):
                    cell.text = _text(value)
            for row in table.rows:
                for cell in row.cells:
                    for run in cell.paragraphs[0].runs:
                        run.font.size = Pt(9)
            if note:
                word.add_paragraph().add_run(note).italic = True
    buffer = io.BytesIO()
    word.save(buffer)
    return buffer.getvalue()


# --- PowerPoint -----------------------------------------------------------------------------------------------


def _chunks(items: list, size: int) -> list[list]:
    return [items[start : start + size] for start in range(0, len(items), size)] or [[]]


def _pptx(document: Document, limit: int) -> bytes:
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)  # 16:9
    title_layout, content_layout, title_only_layout = deck.slide_layouts[0], deck.slide_layouts[1], deck.slide_layouts[5]

    cover = deck.slides.add_slide(title_layout)
    cover.shapes.title.text = document.title
    cover.placeholders[1].text = document.subtitle or f"{date.today():%d %B %Y}"

    for section in document.sections:
        heading = section.heading or document.title
        lines = [*section.paragraphs, *section.bullets]
        for part, chunk in enumerate(_chunks(lines, SLIDE_BULLETS) if lines else []):
            slide = deck.slides.add_slide(content_layout)
            slide.shapes.title.text = heading if part == 0 else f"{heading} (continued)"
            body = slide.placeholders[1]
            body.left, body.top, body.width, body.height = Inches(0.7), Inches(1.6), Inches(11.9), Inches(5.4)
            frame = body.text_frame
            frame.word_wrap = True
            for index, line in enumerate(chunk):
                paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
                paragraph.text = line
                paragraph.font.size = SlidePt(20)
        if section.table:
            rows, note = _rows(section.table, limit)
            columns = section.table.columns[:SLIDE_COLUMNS]
            pages = _chunks(rows, SLIDE_ROWS)
            for page, chunk in enumerate(pages, start=1):
                slide = deck.slides.add_slide(title_only_layout)
                slide.shapes.title.text = heading if len(pages) == 1 else f"{heading} ({page}/{len(pages)})"
                shape = slide.shapes.add_table(
                    len(chunk) + 1, len(columns), Inches(0.5), Inches(1.5), Inches(12.3), Inches(0.4) * (len(chunk) + 1)
                )
                cells = shape.table
                for column, header in enumerate(columns):
                    cells.cell(0, column).text = header
                for row_index, row in enumerate(chunk, start=1):
                    for column in range(len(columns)):
                        cells.cell(row_index, column).text = _text(row[column]) if column < len(row) else ""
                for row in cells.rows:
                    for cell in row.cells:
                        for paragraph in cell.text_frame.paragraphs:
                            paragraph.font.size = SlidePt(12)
                if note and page == len(pages):
                    box = slide.shapes.add_textbox(Inches(0.5), Inches(6.9), Inches(12.3), Inches(0.4))
                    box.text_frame.text = note
                    box.text_frame.paragraphs[0].font.size = SlidePt(12)
    buffer = io.BytesIO()
    deck.save(buffer)
    return buffer.getvalue()


# --- Markdown -------------------------------------------------------------------------------------------------


def _md_cell(value: Any) -> str:
    return _text(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _md(document: Document, limit: int) -> bytes:
    lines = [f"# {document.title}", ""]
    if document.subtitle:
        lines += [f"_{document.subtitle}_", ""]
    for section in document.sections:
        if section.heading:
            lines += [f"## {section.heading}", ""]
        for paragraph in section.paragraphs:
            lines += [paragraph, ""]
        if section.bullets:
            lines += [*(f"- {bullet}" for bullet in section.bullets), ""]
        if section.table:
            rows, note = _rows(section.table, limit)
            columns = section.table.columns
            lines.append("| " + " | ".join(map(_md_cell, columns)) + " |")
            lines.append("|" + "---|" * len(columns))
            lines += ["| " + " | ".join(_md_cell(value) for value in row) + " |" for row in rows]
            lines.append("")
            if note:
                lines += [f"_{note}_", ""]
    return "\n".join(lines).encode()


RENDERERS = {"xlsx": _xlsx, "docx": _docx, "pptx": _pptx, "md": _md}
