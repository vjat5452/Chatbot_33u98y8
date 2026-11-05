"""
Generate a PDF overview document from DOCUMENTATION.md
Uses fpdf2 to create a professionally formatted PDF.
"""

import re
import os
from fpdf import FPDF


def sanitize(text):
    """Replace Unicode chars that latin-1 core fonts can't encode."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '-',    # bullet
        '\u2192': '->',   # right arrow
        '\u2190': '<-',   # left arrow
        '\u2194': '<->',  # left-right arrow
        '\u2265': '>=',   # greater than or equal
        '\u2264': '<=',   # less than or equal
        '\u2260': '!=',   # not equal
        '\u00d7': 'x',    # multiplication sign
        '\u2248': '~=',   # approximately equal
        '\u20b9': 'Rs.',  # Indian Rupee
        '\u2116': 'No.',  # numero sign
        '\u25cf': '*',    # black circle
        '\u25cb': 'o',    # white circle
        '\u2610': '[ ]',  # ballot box
        '\u2611': '[x]',  # ballot box with check
        '\u2713': 'v',    # check mark
        '\u2717': 'x',    # ballot x
        '\u2502': '|',    # box drawings light vertical
        '\u250c': '+',    # box drawings light down and right
        '\u2510': '+',    # box drawings light down and left
        '\u2514': '+',    # box drawings light up and right
        '\u2518': '+',    # box drawings light up and left
        '\u251c': '+',    # box drawings light vertical and right
        '\u2524': '+',    # box drawings light vertical and left
        '\u252c': '+',    # box drawings light down and horizontal
        '\u2534': '+',    # box drawings light up and horizontal
        '\u253c': '+',    # box drawings light vertical and horizontal
        '\u2500': '-',    # box drawings light horizontal
        '\u2550': '=',    # box drawings double horizontal
        '\u2551': '|',    # box drawings double vertical
        '\u2552': '+',    # box drawings
        '\u2553': '+',
        '\u2554': '+',
        '\u2555': '+',
        '\u2556': '+',
        '\u2557': '+',
        '\u2558': '+',
        '\u2559': '+',
        '\u255a': '+',
        '\u255b': '+',
        '\u255c': '+',
        '\u255d': '+',
        '\u255e': '+',
        '\u255f': '+',
        '\u2560': '+',
        '\u2561': '+',
        '\u2562': '+',
        '\u2563': '+',
        '\u2564': '+',
        '\u2565': '+',
        '\u2566': '+',
        '\u2567': '+',
        '\u2568': '+',
        '\u2569': '+',
        '\u256a': '+',
        '\u256b': '+',
        '\u256c': '+',
        '\u25b6': '>',    # right-pointing triangle
        '\u25c0': '<',    # left-pointing triangle
        '\u25b2': '^',    # up-pointing triangle
        '\u25bc': 'v',    # down-pointing triangle
        '\u2588': '#',    # full block
        '\u2591': '.',    # light shade
        '\u2592': ':',    # medium shade
        '\u2593': '#',    # dark shade
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    # Fallback: replace any remaining non-latin-1 chars
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)


class OverviewPDF(FPDF):
    """Custom PDF with header/footer for documentation."""

    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=20)
        self.current_section = ""

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, "Sparrow Interactive RAG Chatbot - Documentation", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, 14, 200, 14)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def cover_page(self):
        self.add_page()
        self.ln(60)
        # Title
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(20, 20, 60)
        self.cell(0, 16, "Sparrow Interactive", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(215, 0, 77)  # #D7004D
        self.cell(0, 14, "RAG Chatbot", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        # Subtitle
        self.set_font("Helvetica", "", 16)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, "Complete System Documentation", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        # Line
        self.set_draw_color(215, 0, 77)
        self.set_line_width(0.8)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(12)
        # Details
        self.set_font("Helvetica", "", 11)
        self.set_text_color(100, 100, 100)
        details = [
            "Stack: FastAPI + Qdrant + Sarvam AI + React + Node.js",
            "Components: Chat Widget | Admin Dashboard | WhatsApp Bridge | Email System",
            "Generated: March 14, 2026"
        ]
        for d in details:
            self.cell(0, 8, d, align="C", new_x="LMARGIN", new_y="NEXT")

    def section_title(self, num, title):
        """Render a top-level section heading (## level)."""
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(20, 20, 60)
        label = f"{num}. {title}" if num else title
        self.cell(0, 12, sanitize(label), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(215, 0, 77)
        self.set_line_width(0.6)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(6)
        self.current_section = title

    def sub_heading(self, title):
        """Render a sub-heading (### level)."""
        self.ln(3)
        if self.get_y() > 260:
            self.add_page()
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(40, 40, 80)
        self.cell(0, 9, sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_sub_heading(self, title):
        """Render a sub-sub-heading (#### level)."""
        self.ln(2)
        if self.get_y() > 265:
            self.add_page()
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 100)
        self.cell(0, 7, sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        """Render normal paragraph text."""
        if not text.strip():
            return
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        # Handle inline formatting
        clean = text.strip()
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)  # bold markers
        clean = re.sub(r'\*(.+?)\*', r'\1', clean)       # italic markers
        clean = re.sub(r'`(.+?)`', r'\1', clean)         # code markers
        clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean) # links
        self.multi_cell(0, 5.5, sanitize(clean), new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullet_item(self, text, indent=0):
        """Render a bullet point."""
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        clean = text.strip().lstrip('-*').strip()
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
        clean = re.sub(r'`(.+?)`', r'\1', clean)
        clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
        x_start = 14 + indent * 6
        bullet_char = "-"
        self.set_x(x_start)
        w = 190 - indent * 6
        self.cell(5, 5.5, bullet_char)
        self.multi_cell(w - 5, 5.5, sanitize(clean), new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def code_block(self, lines):
        """Render a code/preformatted block."""
        self.ln(1)
        self.set_fill_color(245, 245, 248)
        self.set_font("Courier", "", 8)
        self.set_text_color(50, 50, 50)
        for line in lines:
            if self.get_y() > 270:
                self.add_page()
            clean = sanitize(line.rstrip())
            self.set_x(12)
            self.cell(186, 4.5, clean, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def render_table(self, headers, rows):
        """Render a simple table."""
        self.ln(1)
        if self.get_y() > 240:
            self.add_page()

        num_cols = len(headers)
        usable_w = 186

        # Calculate column widths based on content
        col_widths = []
        if num_cols == 2:
            col_widths = [60, 126]
        elif num_cols == 3:
            col_widths = [40, 50, 96]
        elif num_cols == 4:
            col_widths = [35, 40, 40, 71]
        elif num_cols == 5:
            col_widths = [35, 30, 25, 30, 66]
        else:
            col_widths = [usable_w // num_cols] * num_cols
            col_widths[-1] = usable_w - sum(col_widths[:-1])

        # Header row
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 30, 65)
        self.set_text_color(255, 255, 255)
        x_start = 12
        self.set_x(x_start)
        for i, h in enumerate(headers):
            clean = sanitize(h.strip().strip('*'))
            self.cell(col_widths[i], 7, clean, border=1, fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(40, 40, 40)
        fill = False
        for row in rows:
            if self.get_y() > 272:
                self.add_page()
                # Re-draw header
                self.set_font("Helvetica", "B", 8)
                self.set_fill_color(30, 30, 65)
                self.set_text_color(255, 255, 255)
                self.set_x(x_start)
                for i, h in enumerate(headers):
                    clean = sanitize(h.strip().strip('*'))
                    self.cell(col_widths[i], 7, clean, border=1, fill=True)
                self.ln()
                self.set_font("Helvetica", "", 7.5)
                self.set_text_color(40, 40, 40)
                fill = False

            if fill:
                self.set_fill_color(248, 248, 252)
            else:
                self.set_fill_color(255, 255, 255)

            # Calculate row height based on longest cell
            max_lines = 1
            cell_texts = []
            for i, cell in enumerate(row):
                clean = cell.strip()
                clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
                clean = re.sub(r'`(.+?)`', r'\1', clean)
                clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
                cell_texts.append(clean)
                lines_needed = max(1, len(clean) // max(1, (col_widths[i] // 2)) + 1)
                if lines_needed > max_lines:
                    max_lines = min(lines_needed, 4)

            row_h = 6
            self.set_x(x_start)
            for i, ct in enumerate(cell_texts):
                w = col_widths[i]
                self.cell(w, row_h, sanitize(ct[:int(w/1.6)]), border=1, fill=True)
            self.ln()
            fill = not fill

        self.ln(2)


def parse_and_generate():
    """Parse DOCUMENTATION.md and generate a formatted PDF."""

    doc_path = os.path.join(os.path.dirname(__file__), "DOCUMENTATION.md")
    output_path = os.path.join(os.path.expanduser("~"), "Desktop", "overview.pdf")

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    pdf = OverviewPDF()
    pdf.alias_nb_pages()

    # Cover page
    pdf.cover_page()

    # Table of Contents
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 20, 60)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    toc_items = re.findall(r'^#{1,3}\s+(?:\d+[\.\d]*\.?\s+)?(.+)', content, re.MULTILINE)
    # Extract numbered sections from the TOC in the markdown
    toc_section = re.search(r'## Table of Contents\n(.*?)\n---', content, re.DOTALL)
    if toc_section:
        toc_lines = toc_section.group(1).strip().split('\n')
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(50, 50, 50)
        for line in toc_lines:
            clean = line.strip()
            if not clean:
                continue
            # Remove markdown link syntax
            clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
            clean = clean.lstrip('0123456789. ')
            # Get the number
            num_match = re.match(r'(\d+)\.\s', line.strip())
            if num_match:
                num = num_match.group(1)
                clean = line.strip()
                clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
                indent = 0
                if clean.startswith('   '):
                    indent = 1
                pdf.set_x(14 + indent * 8)
                pdf.set_font("Helvetica", "", 11)
                pdf.cell(0, 7, sanitize(clean.strip().lstrip('- ')), new_x="LMARGIN", new_y="NEXT")
            else:
                clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', line.strip())
                pdf.set_x(22)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 6.5, sanitize(clean.lstrip('- ')), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(50, 50, 50)

    # Process the rest of the markdown
    lines = content.split('\n')
    i = 0
    in_code_block = False
    code_lines = []
    in_table = False
    table_headers = []
    table_rows = []
    skip_toc = False

    # Map section numbers
    section_num = 0

    while i < len(lines):
        line = lines[i]

        # Skip the title and initial metadata (already on cover page)
        if i < 10 and (line.startswith('# ') or line.startswith('> ') or line == '---'):
            i += 1
            continue

        # Skip TOC section
        if '## Table of Contents' in line:
            skip_toc = True
            i += 1
            continue
        if skip_toc:
            if line.startswith('## ') and 'Table of Contents' not in line:
                skip_toc = False
            elif line == '---':
                skip_toc = False
                i += 1
                continue
            else:
                i += 1
                continue

        # Code block toggle
        if line.strip().startswith('```'):
            if in_code_block:
                pdf.code_block(code_lines)
                code_lines = []
                in_code_block = False
            else:
                # Flush any pending table
                if in_table and table_headers:
                    pdf.render_table(table_headers, table_rows)
                    in_table = False
                    table_headers = []
                    table_rows = []
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Table detection
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            # Check if separator row
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_headers = cells
            else:
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table and table_headers:
                pdf.render_table(table_headers, table_rows)
                in_table = False
                table_headers = []
                table_rows = []

        # Headings
        if line.startswith('## ') and not line.startswith('### '):
            title = line[3:].strip()
            # Extract number if present
            num_match = re.match(r'^(\d+)\.\s+(.+)', title)
            if num_match:
                pdf.section_title(num_match.group(1), num_match.group(2))
            else:
                pdf.section_title("", title)
            i += 1
            continue

        if line.startswith('### '):
            title = line[4:].strip()
            pdf.sub_heading(title)
            i += 1
            continue

        if line.startswith('#### '):
            title = line[5:].strip()
            pdf.sub_sub_heading(title)
            i += 1
            continue

        # Horizontal rule
        if line.strip() == '---':
            i += 1
            continue

        # Bullet points
        if re.match(r'^[-*]\s', line.strip()):
            indent = 0
            if line.startswith('  ') or line.startswith('\t'):
                indent = 1
            pdf.bullet_item(line, indent)
            i += 1
            continue

        # Numbered list
        if re.match(r'^\d+\.\s', line.strip()):
            pdf.bullet_item(line.strip(), 0)
            i += 1
            continue

        # Regular text
        if line.strip():
            pdf.body_text(line)

        i += 1

    # Flush any remaining table
    if in_table and table_headers:
        pdf.render_table(table_headers, table_rows)

    # Save
    pdf.output(output_path)
    print(f"PDF saved to: {output_path}")
    print(f"Total pages: {pdf.page_no()}")


if __name__ == "__main__":
    parse_and_generate()
