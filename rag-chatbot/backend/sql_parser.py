"""Parses .sql dump files — extracts table schemas and row data."""

import re
from dataclasses import dataclass, field


@dataclass
class TableSchema:
    name: str
    columns: list[dict]  # [{"name": "id", "type": "INT", "constraints": "PRIMARY KEY"}, ...]


@dataclass
class ParsedTable:
    schema: TableSchema
    rows: list[list[str]] = field(default_factory=list)


def parse_sql(sql_text: str) -> list[ParsedTable]:
    """Parse a SQL dump and return structured table data."""
    # Remove SQL comments
    sql_text = re.sub(r'--.*$', '', sql_text, flags=re.MULTILINE)
    sql_text = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)

    tables = {}

    # Extract CREATE TABLE statements
    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?\s*\((.*?)\)\s*;',
        re.IGNORECASE | re.DOTALL,
    )
    for match in create_pattern.finditer(sql_text):
        table_name = match.group(1).lower()
        body = match.group(2)
        columns = _parse_columns(body)
        if columns:
            tables[table_name] = ParsedTable(
                schema=TableSchema(name=table_name, columns=columns)
            )

    # Extract INSERT INTO statements
    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+[`"\[]?(\w+)[`"\]]?\s*'
        r'(?:\(.*?\)\s*)?'
        r'VALUES\s*(.*?)\s*;',
        re.IGNORECASE | re.DOTALL,
    )
    for match in insert_pattern.finditer(sql_text):
        table_name = match.group(1).lower()
        values_block = match.group(2)
        rows = _parse_values(values_block)

        if table_name not in tables:
            # INSERT without prior CREATE TABLE — create a placeholder schema
            tables[table_name] = ParsedTable(
                schema=TableSchema(name=table_name, columns=[])
            )
        tables[table_name].rows.extend(rows)

    return list(tables.values())


def _parse_columns(body: str) -> list[dict]:
    """Parse column definitions from a CREATE TABLE body."""
    columns = []
    # Split on commas that are not inside parentheses
    parts = _split_respecting_parens(body)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Skip table-level constraints
        upper = part.upper().lstrip()
        if any(upper.startswith(kw) for kw in [
            'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'CONSTRAINT', 'INDEX', 'KEY'
        ]):
            continue

        # Parse: column_name TYPE [constraints...]
        tokens = part.split()
        if len(tokens) < 2:
            continue

        col_name = tokens[0].strip('`"[]')
        col_type = tokens[1].strip('`"[]')
        # Capture type with size, e.g. VARCHAR(100)
        if len(tokens) > 2 and tokens[1].endswith('(') or '(' in col_type:
            # Rebuild type with parenthetical size
            type_str = ' '.join(tokens[1:])
            paren_match = re.match(r'(\w+\([^)]*\))', type_str)
            if paren_match:
                col_type = paren_match.group(1)

        constraints = ' '.join(tokens[2:]) if len(tokens) > 2 else ''
        # Clean constraints of any leftover type info
        constraints = re.sub(r'^\([^)]*\)\s*', '', constraints)

        columns.append({
            'name': col_name,
            'type': col_type.upper(),
            'constraints': constraints.strip(),
        })

    return columns


def _split_respecting_parens(text: str) -> list[str]:
    """Split text by commas, but ignore commas inside parentheses."""
    parts = []
    depth = 0
    current = []
    for char in text:
        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current))
    return parts


def _parse_values(values_block: str) -> list[list[str]]:
    """Parse the VALUES portion of an INSERT statement into rows of strings."""
    rows = []
    # Find each (...) group
    row_pattern = re.compile(r'\(([^)]*(?:\([^)]*\)[^)]*)*)\)')

    for match in row_pattern.finditer(values_block):
        row_str = match.group(1)
        values = _parse_row_values(row_str)
        rows.append(values)

    return rows


def _parse_row_values(row_str: str) -> list[str]:
    """Parse a single row's comma-separated values, respecting quoted strings."""
    values = []
    current = []
    in_quote = False
    quote_char = None
    i = 0

    while i < len(row_str):
        ch = row_str[i]

        if in_quote:
            if ch == '\\' and i + 1 < len(row_str):
                # Escaped character
                current.append(row_str[i + 1])
                i += 2
                continue
            elif ch == quote_char:
                # Check for escaped quote by doubling (e.g. '')
                if i + 1 < len(row_str) and row_str[i + 1] == quote_char:
                    current.append(ch)
                    i += 2
                    continue
                in_quote = False
            else:
                current.append(ch)
        else:
            if ch in ("'", '"'):
                in_quote = True
                quote_char = ch
            elif ch == ',':
                values.append(''.join(current).strip())
                current = []
                i += 1
                continue
            else:
                current.append(ch)
        i += 1

    values.append(''.join(current).strip())
    return [v if v.upper() != 'NULL' else 'NULL' for v in values]
