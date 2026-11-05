"""Parses PDF files — extracts text content page by page.

Uses pdfplumber for high-quality text extraction (falls back to PyPDF2).
For image-heavy pages with little text, uses OCR via pytesseract + PyMuPDF.
Includes text cleaning to fix common extraction artifacts.
"""

import io
import re
from dataclasses import dataclass

# Tesseract path (Windows — installed via winget)
TESSERACT_CMD = r"C:\Users\User\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# Pages with less text than this AND images → try OCR
OCR_TEXT_THRESHOLD = 50


@dataclass
class ParsedPDF:
    filename: str
    pages: list[dict]  # [{"page_num": 1, "text": "..."}, ...]
    total_pages: int


def _clean_text(text: str) -> str:
    """Clean extracted PDF text: fix spacing artifacts, normalize whitespace."""
    # Fix pattern: "word\n \nword" or "word\n  \nword" → "word word"
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Fix single newlines between words (not paragraph breaks) → space
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Collapse multiple spaces into one
    text = re.sub(r' {2,}', ' ', text)
    # Fix spaces before punctuation
    text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
    # Fix spaces after opening brackets
    text = re.sub(r'([(])\s+', r'\1', text)
    # Clean up excessive blank lines (max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip each line
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(lines)
    return text.strip()


def _ocr_page(pdf_bytes: bytes, page_idx: int) -> str:
    """Run OCR on a PDF page using PyMuPDF + pytesseract.

    Renders the page as a high-res image, then runs Tesseract OCR on it.
    Returns cleaned OCR text, or empty string on failure.
    """
    try:
        import pytesseract
        import fitz  # PyMuPDF
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_idx]

        # Render at 2x zoom for better OCR accuracy
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))

        text = pytesseract.image_to_string(img)
        doc.close()

        # Clean up OCR output
        text = _clean_ocr_text(text)
        return text
    except Exception as e:
        print(f"[PDF] OCR failed for page {page_idx + 1}: {e}")
        return ""


def _clean_ocr_text(text: str) -> str:
    """Clean OCR output: remove junk characters, short noise lines, etc."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        # Skip empty lines and very short noise (single chars, symbols)
        if not line:
            cleaned.append("")
            continue
        # Remove lines that are just symbols/single chars (OCR noise)
        if len(line) <= 2 and not line.isalnum():
            continue
        # Remove lines that are mostly non-alphanumeric (>50% symbols)
        alnum_count = sum(1 for c in line if c.isalnum() or c.isspace())
        if len(line) > 3 and alnum_count / len(line) < 0.4:
            continue
        cleaned.append(line)

    text = '\n'.join(cleaned)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _page_has_images(pdf_bytes: bytes, page_idx: int) -> bool:
    """Check if a PDF page contains images using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_idx]
        images = page.get_images(full=True)
        doc.close()
        return len(images) > 0
    except Exception:
        return False


def parse_pdf(pdf_bytes: bytes, filename: str) -> ParsedPDF:
    """Parse a PDF file and return structured page data.

    Strategy:
    1. Use pdfplumber for text extraction (best quality)
    2. For pages with <50 chars text but containing images → run OCR
    3. Fall back to PyPDF2 if pdfplumber fails entirely
    """
    pages = []
    total_pages = 0
    text_by_page = {}  # page_idx -> text from pdfplumber

    # Phase 1: Extract text with pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text = _clean_text(text)
                text_by_page[i] = text
    except Exception as e:
        print(f"[PDF] pdfplumber failed for {filename}: {e}, falling back to PyPDF2")
        # Fallback to PyPDF2
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = _clean_text(text)
            text_by_page[i] = text

    # Phase 2: For pages with little/no text but images, try OCR
    for i in range(total_pages):
        text = text_by_page.get(i, "")

        if len(text) < OCR_TEXT_THRESHOLD and _page_has_images(pdf_bytes, i):
            print(f"[PDF] Page {i + 1} has little text ({len(text)} chars) but images — running OCR")
            ocr_text = _ocr_page(pdf_bytes, i)
            if ocr_text and len(ocr_text) > len(text):
                # OCR found more content — use it (with marker)
                text = f"[OCR extracted] {ocr_text}"
                print(f"[PDF] OCR extracted {len(ocr_text)} chars from page {i + 1}")

        if text and len(text) > 20:
            pages.append({
                "page_num": i + 1,
                "text": text,
            })

    return ParsedPDF(filename=filename, pages=pages, total_pages=total_pages)
