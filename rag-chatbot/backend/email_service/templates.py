"""Email template CRUD and Jinja2 rendering."""

import json
from datetime import datetime

from jinja2 import Template, BaseLoader, Environment, TemplateSyntaxError

from backend.database import _get_conn


_jinja_env = Environment(loader=BaseLoader(), autoescape=True)


# ── CRUD ──

def create_template(name: str, subject: str = "", html_body: str = "",
                    text_body: str = "", category: str = "promotion",
                    variables: list[str] | None = None) -> int:
    conn = _get_conn()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO email_templates (name, subject, html_body, text_body, category, variables, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, subject, html_body, text_body, category, json.dumps(variables or []), now, now)
    )
    conn.commit()
    return cursor.lastrowid


def get_template(template_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        return None
    t = dict(row)
    t["variables"] = json.loads(t.get("variables") or "[]")
    return t


def get_templates(category: str = None, active_only: bool = True) -> list[dict]:
    conn = _get_conn()
    conditions = []
    params = []
    if category:
        conditions.append("category = ?")
        params.append(category)
    if active_only:
        conditions.append("is_active = 1")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM email_templates {where} ORDER BY updated_at DESC", params
    ).fetchall()
    templates = []
    for row in rows:
        t = dict(row)
        t["variables"] = json.loads(t.get("variables") or "[]")
        templates.append(t)
    return templates


def update_template(template_id: int, **kwargs) -> bool:
    conn = _get_conn()
    allowed = {"name", "subject", "html_body", "text_body", "category", "variables", "is_active"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k == "variables":
                updates[k] = json.dumps(v)
            else:
                updates[k] = v
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [template_id]
    conn.execute(f"UPDATE email_templates SET {sets} WHERE id = ?", vals)
    conn.commit()
    return True


def duplicate_template(template_id: int) -> int | None:
    t = get_template(template_id)
    if not t:
        return None
    return create_template(
        name=f"{t['name']} (Copy)",
        subject=t["subject"],
        html_body=t["html_body"],
        text_body=t["text_body"],
        category=t["category"],
        variables=t["variables"],
    )


def delete_template(template_id: int) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
    conn.commit()
    return cursor.rowcount > 0


# ── Rendering ──

def render_template(html_body: str, data: dict) -> str:
    """Render a template HTML with Jinja2 variables. Missing vars become empty string."""
    try:
        tpl = _jinja_env.from_string(html_body)
        return tpl.render(**{k: (v if v is not None else "") for k, v in data.items()})
    except TemplateSyntaxError:
        # Fallback: simple string replace for {{var}} patterns
        result = html_body
        for k, v in data.items():
            result = result.replace("{{" + k + "}}", str(v or ""))
        return result


def render_text(text_body: str, data: dict) -> str:
    """Render plain-text body with variables."""
    try:
        tpl = _jinja_env.from_string(text_body)
        return tpl.render(**{k: (v if v is not None else "") for k, v in data.items()})
    except TemplateSyntaxError:
        result = text_body
        for k, v in data.items():
            result = result.replace("{{" + k + "}}", str(v or ""))
        return result


def preview_template(template_id: int, sample_data: dict = None) -> dict | None:
    """Render a template with sample data for preview."""
    t = get_template(template_id)
    if not t:
        return None

    # Default sample data for common variables
    defaults = {
        "name": "John Doe",
        "first_name": "John",
        "company": "Acme Corp",
        "email": "john@acme.com",
        "lead_score": "75",
        "source_page": "https://sparrowi.com",
    }
    data = {**defaults, **(sample_data or {})}

    return {
        "subject": render_text(t["subject"], data),
        "html_body": render_template(t["html_body"], data),
        "text_body": render_text(t["text_body"], data),
    }
