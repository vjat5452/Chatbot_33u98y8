"""Email contact management: CRUD, CSV import/export, validation, lead sync."""

import csv
import io
import re
from datetime import datetime

from backend.database import _get_conn

# ── Validation helpers ──

_EMAIL_SYNTAX_RE = re.compile(r'^[\w.+-]+@[\w.-]+\.\w{2,}$')

# Common disposable email domains (subset — extend as needed)
_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "10minutemail.com", "trashmail.com", "fakeinbox.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "dispostable.com",
    "temp-mail.org", "getnada.com", "mailnesia.com", "maildrop.cc",
}

_ROLE_PREFIXES = {
    "info", "admin", "support", "noreply", "no-reply", "webmaster",
    "postmaster", "hostmaster", "abuse", "sales", "marketing", "contact",
}


def validate_email_syntax(email: str) -> bool:
    return bool(_EMAIL_SYNTAX_RE.match(email.strip().lower()))


def is_disposable(email: str) -> bool:
    domain = email.strip().lower().split("@")[-1]
    return domain in _DISPOSABLE_DOMAINS


def is_role_based(email: str) -> bool:
    local = email.strip().lower().split("@")[0]
    return local in _ROLE_PREFIXES


def check_mx_record(domain: str) -> bool:
    """Check if a domain has MX records (requires dnspython)."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        return len(answers) > 0
    except Exception:
        return False


def validate_email_full(email: str) -> dict:
    """Run all validation checks on a single email. Returns a result dict."""
    email = email.strip().lower()
    result = {"email": email, "valid": True, "issues": []}

    if not validate_email_syntax(email):
        result["valid"] = False
        result["issues"].append("invalid_syntax")
        return result

    if is_disposable(email):
        result["valid"] = False
        result["issues"].append("disposable")

    if is_role_based(email):
        result["issues"].append("role_based")

    domain = email.split("@")[-1]
    if not check_mx_record(domain):
        result["valid"] = False
        result["issues"].append("no_mx_record")

    return result


# ── CRUD ──

def create_contact(email: str, name: str = "", company: str = "", phone: str = "",
                   source: str = "manual", tags: str = "") -> int | None:
    """Create a contact. Returns ID or None if duplicate."""
    conn = _get_conn()
    now = datetime.now().isoformat()
    try:
        cursor = conn.execute(
            """INSERT INTO email_contacts (email, name, company, phone, source, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (email.strip().lower(), name, company, phone, source, tags, now, now)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        # Duplicate email
        return None


def get_contact(contact_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM email_contacts WHERE id = ?", (contact_id,)).fetchone()
    return dict(row) if row else None


def get_contacts(status: str = None, tags: str = None, search: str = None,
                 limit: int = 50, offset: int = 0) -> dict:
    conn = _get_conn()
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if tags:
        conditions.append("tags LIKE ?")
        params.append(f"%{tags}%")
    if search:
        conditions.append("(email LIKE ? OR name LIKE ? OR company LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    total = conn.execute(f"SELECT COUNT(*) FROM email_contacts {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM email_contacts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    return {
        "total": total,
        "contacts": [dict(r) for r in rows],
        "limit": limit,
        "offset": offset,
    }


def update_contact(contact_id: int, **kwargs) -> bool:
    conn = _get_conn()
    allowed = {"name", "company", "phone", "tags", "status"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None and v != "":
            updates[k] = v
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [contact_id]
    conn.execute(f"UPDATE email_contacts SET {sets} WHERE id = ?", vals)
    conn.commit()
    return True


def delete_contacts(contact_ids: list[int]):
    conn = _get_conn()
    placeholders = ",".join("?" * len(contact_ids))
    conn.execute(f"DELETE FROM email_contacts WHERE id IN ({placeholders})", contact_ids)
    conn.commit()


# ── CSV Import / Export ──

def import_csv(csv_content: str, default_tags: str = "", default_source: str = "import") -> dict:
    """Import contacts from CSV string. Returns stats dict."""
    reader = csv.DictReader(io.StringIO(csv_content))
    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, 1):
        email = (row.get("email") or row.get("Email") or "").strip().lower()
        if not email or not validate_email_syntax(email):
            errors.append({"row": i, "email": email, "reason": "invalid_syntax"})
            skipped += 1
            continue

        name = row.get("name") or row.get("Name") or ""
        company = row.get("company") or row.get("Company") or ""
        phone = row.get("phone") or row.get("Phone") or ""
        tags = row.get("tags") or row.get("Tags") or default_tags

        result = create_contact(email, name, company, phone, default_source, tags)
        if result:
            created += 1
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "errors": errors, "total_rows": created + skipped}


def export_contacts_csv(status: str = None) -> str:
    conn = _get_conn()
    conditions = []
    params = []
    if status:
        conditions.append("status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = conn.execute(
        f"SELECT email, name, company, phone, tags, status, source, created_at FROM email_contacts {where} ORDER BY created_at DESC",
        params
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["email", "name", "company", "phone", "tags", "status", "source", "created_at"])
    for r in rows:
        writer.writerow([r["email"], r["name"], r["company"], r["phone"], r["tags"], r["status"], r["source"], r["created_at"]])
    return buf.getvalue()


# ── Lead Sync ──

def sync_from_leads() -> dict:
    """Sync leads with email addresses into email_contacts table."""
    conn = _get_conn()
    now = datetime.now().isoformat()

    leads = conn.execute(
        "SELECT id, email, name, phone, company FROM leads WHERE email != '' AND email IS NOT NULL"
    ).fetchall()

    created = 0
    skipped = 0
    for lead in leads:
        email = lead["email"].strip().lower()
        if not email:
            continue
        try:
            conn.execute(
                """INSERT INTO email_contacts (email, name, company, phone, source, lead_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'lead_sync', ?, ?, ?)""",
                (email, lead["name"], lead["company"], lead["phone"], lead["id"], now, now)
            )
            created += 1
        except Exception:
            skipped += 1

    conn.commit()
    return {"synced": created, "skipped": skipped, "total_leads": len(leads)}


# ── Bulk Validation ──

def validate_contacts(contact_ids: list[int] = None) -> dict:
    """Validate contacts and return detailed results. If no IDs, validates all active."""
    conn = _get_conn()
    if contact_ids:
        placeholders = ",".join("?" * len(contact_ids))
        rows = conn.execute(
            f"SELECT id, email FROM email_contacts WHERE id IN ({placeholders})", contact_ids
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, email FROM email_contacts WHERE status = 'active'").fetchall()

    results = {"total": len(rows), "valid": 0, "invalid": 0, "disposable": 0, "role_based": 0, "no_mx": 0, "details": []}

    for r in rows:
        check = validate_email_full(r["email"])
        check["contact_id"] = r["id"]
        results["details"].append(check)

        if check["valid"]:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            # Auto-update status to 'cleaned' for invalid emails
            conn.execute(
                "UPDATE email_contacts SET status = 'cleaned', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), r["id"])
            )

        if "disposable" in check.get("issues", []):
            results["disposable"] += 1
        if "role_based" in check.get("issues", []):
            results["role_based"] += 1
        if "no_mx_record" in check.get("issues", []):
            results["no_mx"] += 1

    conn.commit()
    return results
