from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB = "vulndb.db"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        domain TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS company_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        version INTEGER NOT NULL,
        tags TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(company_id) REFERENCES companies(id)
    )
    """)

    conn.commit()
    conn.close()

@app.route("/")
def index():
    q = request.args.get("q", "")
    conn = db()

    companies = conn.execute("""
        SELECT c.id, c.name, c.domain,
               v.tags, v.created_at
        FROM companies c
        JOIN company_versions v
          ON v.id = (
            SELECT id FROM company_versions
            WHERE company_id = c.id
            ORDER BY version DESC LIMIT 1
          )
        WHERE c.name LIKE ? OR c.domain LIKE ? OR v.tags LIKE ? OR v.notes LIKE ?
        ORDER BY v.created_at DESC
    """, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()

    conn.close()
    return render_template("templates_index.html", companies=companies, q=q)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        domain = request.form["domain"]
        tags = request.form["tags"]
        notes = request.form["notes"]

        conn = db()
        cur = conn.execute("""
            INSERT INTO companies (name, domain, created_at)
            VALUES (?, ?, ?)
        """, (name, domain, datetime.utcnow().isoformat()))
        cid = cur.lastrowid

        conn.execute("""
            INSERT INTO company_versions
            (company_id, version, tags, notes, created_at)
            VALUES (?, 1, ?, ?, ?)
        """, (cid, tags, notes, datetime.utcnow().isoformat()))

        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("templates_add.html")

@app.route("/company/<int:cid>")
def company(cid):
    conn = db()

    company = conn.execute(
        "SELECT * FROM companies WHERE id = ?", (cid,)
    ).fetchone()

    versions = conn.execute("""
        SELECT * FROM company_versions
        WHERE company_id = ?
        ORDER BY version DESC
    """, (cid,)).fetchall()

    conn.close()
    return render_template(
        "templates_detail.html",
        company=company,
        versions=versions
    )

@app.route("/company/<int:cid>/edit", methods=["POST"])
def edit(cid):
    tags = request.form["tags"]
    notes = request.form["notes"]

    conn = db()

    last_version = conn.execute("""
        SELECT MAX(version)
        FROM company_versions
        WHERE company_id = ?
    """, (cid,)).fetchone()[0] or 0

    conn.execute("""
        INSERT INTO company_versions
        (company_id, version, tags, notes, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (cid, last_version + 1, tags, notes, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    return redirect(f"/company/{cid}")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
