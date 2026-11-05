"""Converts parsed SQL tables and PDF pages into text chunks for embedding."""

import hashlib
from dataclasses import dataclass

from backend.sql_parser import ParsedTable
from backend.pdf_parser import ParsedPDF


@dataclass
class Chunk:
    id: str
    text: str
    table: str  # table name for SQL, filename for PDF
    chunk_type: str  # "schema", "rows", "summary", "pdf_page", "pdf_section", "website", "golden_qa"
    url: str = ""  # source URL for website chunks


def _make_chunk_id(source: str, chunk_type: str, index: int = 0) -> str:
    """Create a deterministic chunk ID using SHA256."""
    raw = f"{source}:{chunk_type}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CONTENT = 60  # skip near-empty pages


def _split_into_segments(text: str) -> list[str]:
    """Split text into segments for chunking.

    Tries paragraph breaks first, then single newlines, then sentence boundaries.
    """
    # Try paragraph breaks first
    paragraphs = text.split('\n\n')
    if len(paragraphs) > 1 and all(len(p.strip()) < MAX_CHUNK_CHARS for p in paragraphs if p.strip()):
        return [p.strip() for p in paragraphs if p.strip()]

    # Fall back to single newlines
    lines = text.split('\n')
    if len(lines) > 1:
        return [line.strip() for line in lines if line.strip()]

    # Last resort: split on sentence boundaries (. followed by space/capital)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def create_pdf_chunks(parsed_pdf: ParsedPDF) -> list[Chunk]:
    """Generate text chunks from a parsed PDF."""
    chunks = []
    name = parsed_pdf.filename

    for page in parsed_pdf.pages:
        page_num = page["page_num"]
        text = page["text"]

        # Skip near-empty pages
        if len(text) < MIN_CHUNK_CONTENT:
            continue

        # Short pages → single chunk
        if len(text) <= MAX_CHUNK_CHARS:
            chunks.append(Chunk(
                id=_make_chunk_id(name, "pdf_page", page_num),
                text=f"[{name} — Page {page_num}]\n{text}",
                table=name,
                chunk_type="pdf_page",
            ))
        else:
            # Split into segments and group into chunks under the limit
            segments = _split_into_segments(text)
            section_idx = 0
            current = []
            current_len = 0

            for seg in segments:
                if not seg:
                    continue
                # If a single segment exceeds limit, force-split it
                if len(seg) > MAX_CHUNK_CHARS:
                    # Flush current buffer first
                    if current:
                        chunk_text = f"[{name} — Page {page_num}, Section {section_idx + 1}]\n" + '\n\n'.join(current)
                        chunks.append(Chunk(
                            id=_make_chunk_id(name, "pdf_section", page_num * 1000 + section_idx),
                            text=chunk_text,
                            table=name,
                            chunk_type="pdf_section",
                        ))
                        section_idx += 1
                        current = []
                        current_len = 0
                    # Force-split the long segment
                    for i in range(0, len(seg), MAX_CHUNK_CHARS):
                        part = seg[i:i + MAX_CHUNK_CHARS]
                        chunk_text = f"[{name} — Page {page_num}, Section {section_idx + 1}]\n{part}"
                        chunks.append(Chunk(
                            id=_make_chunk_id(name, "pdf_section", page_num * 1000 + section_idx),
                            text=chunk_text,
                            table=name,
                            chunk_type="pdf_section",
                        ))
                        section_idx += 1
                    continue

                if current_len + len(seg) + 1 > MAX_CHUNK_CHARS and current:
                    chunk_text = f"[{name} — Page {page_num}, Section {section_idx + 1}]\n" + '\n\n'.join(current)
                    chunks.append(Chunk(
                        id=_make_chunk_id(name, "pdf_section", page_num * 1000 + section_idx),
                        text=chunk_text,
                        table=name,
                        chunk_type="pdf_section",
                    ))
                    section_idx += 1
                    current = []
                    current_len = 0
                current.append(seg)
                current_len += len(seg) + 1

            if current:
                joined = '\n\n'.join(current)
                if len(joined) >= MIN_CHUNK_CONTENT:
                    chunk_text = f"[{name} — Page {page_num}, Section {section_idx + 1}]\n" + joined
                    chunks.append(Chunk(
                        id=_make_chunk_id(name, "pdf_section", page_num * 1000 + section_idx),
                        text=chunk_text,
                        table=name,
                        chunk_type="pdf_section",
                    ))

    return chunks


def create_chunks(parsed_tables: list[ParsedTable], rows_per_group: int = 3) -> list[Chunk]:
    """Generate schema, row-group, and summary chunks for all tables."""
    chunks = []

    for table in parsed_tables:
        name = table.schema.name
        columns = table.schema.columns

        # 1. Schema chunk
        schema_text = _build_schema_text(name, columns)
        chunks.append(Chunk(
            id=_make_chunk_id(name, "schema"),
            text=schema_text,
            table=name,
            chunk_type="schema",
        ))

        # 2. Row group chunks
        if table.rows:
            col_names = [c['name'] for c in columns] if columns else [
                f"col{i}" for i in range(len(table.rows[0]))
            ]
            for i in range(0, len(table.rows), rows_per_group):
                batch = table.rows[i:i + rows_per_group]
                row_text = _build_row_text(name, col_names, batch, i)
                chunks.append(Chunk(
                    id=_make_chunk_id(name, "rows", i),
                    text=row_text,
                    table=name,
                    chunk_type="rows",
                ))

        # 3. Summary chunk
        if table.rows and columns:
            summary_text = _build_summary_text(name, columns, table.rows)
            chunks.append(Chunk(
                id=_make_chunk_id(name, "summary"),
                text=summary_text,
                table=name,
                chunk_type="summary",
            ))

    return chunks


def _build_schema_text(table_name: str, columns: list[dict]) -> str:
    """Build a human-readable schema description."""
    lines = [f"Table: {table_name}", "Columns:"]
    for col in columns:
        constraint_str = f" ({col['constraints']})" if col['constraints'] else ""
        lines.append(f"  - {col['name']}: {col['type']}{constraint_str}")
    return '\n'.join(lines)


def _build_row_text(table_name: str, col_names: list[str], rows: list[list[str]], offset: int) -> str:
    """Build a natural-language text chunk for a batch of rows.

    Generates readable sentences for each row so embeddings can match
    natural language queries like 'Bob Smith salary' or 'who works in Engineering'.
    """
    lines = [f"Table: {table_name} (rows {offset + 1}-{offset + len(rows)})"]
    for row in rows:
        pairs = {}
        for j, val in enumerate(row):
            col = col_names[j] if j < len(col_names) else f"col{j}"
            pairs[col] = val
        # Build a readable sentence: "first_name=Bob, last_name=Smith, ..."
        parts = [f"{k}={v}" for k, v in pairs.items()]
        lines.append("  " + ", ".join(parts))
    return '\n'.join(lines)


def _build_summary_text(table_name: str, columns: list[dict], rows: list[list[str]]) -> str:
    """Build a summary with row count and per-column stats."""
    lines = [f"Table: {table_name} — Summary", f"Total rows: {len(rows)}"]

    for i, col in enumerate(columns):
        col_values = [r[i] for r in rows if i < len(r) and r[i] != 'NULL']
        if not col_values:
            continue

        unique = set(col_values)
        line = f"  - {col['name']}: {len(unique)} unique values"

        # Try numeric stats
        numeric_vals = []
        for v in col_values:
            try:
                numeric_vals.append(float(v.replace(',', '')))
            except (ValueError, AttributeError):
                pass

        if numeric_vals and len(numeric_vals) == len(col_values):
            line += f", range [{min(numeric_vals):.4g} - {max(numeric_vals):.4g}]"
        elif len(unique) <= 10:
            # Show all unique values if few enough
            line += f": {', '.join(sorted(unique))}"

        lines.append(line)

    return '\n'.join(lines)
