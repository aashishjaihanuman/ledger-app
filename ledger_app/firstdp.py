from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import datetime, timedelta
import io

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        phone TEXT UNIQUE,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY,
        phone TEXT,
        date TEXT,
        description TEXT,
        amount REAL,
        created_at TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        phone = request.form["phone"]
        password = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username,phone,password) VALUES (?,?,?)",
                      (username, phone, password))
            conn.commit()
        except:
            return "User already exists ❌"

        conn.close()
        return redirect("/")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE phone=? AND password=?",
                  (phone, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["phone"] = phone
            session["username"] = user[0]
            return redirect("/dashboard")

        return "Wrong login ❌"

    return render_template("login.html")

# ---------------- FORGOT ----------------
@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "POST":
        phone = request.form["phone"]
        new_pass = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE phone=?",
                  (new_pass, phone))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("forgot.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "phone" not in session:
        return redirect("/")

    phone = session["phone"]

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    if request.method == "POST":
        date = request.form["date"]
        desc = request.form["desc"]
        amount = float(request.form["amount"])
        now = datetime.now().isoformat()

        c.execute("INSERT INTO entries (phone,date,description,amount,created_at) VALUES (?,?,?,?,?)",
                  (phone, date, desc, amount, now))
        conn.commit()

    # Auto delete after 2 days
    cutoff = (datetime.now() - timedelta(days=2)).isoformat()
    c.execute("DELETE FROM entries WHERE created_at < ?", (cutoff,))
    conn.commit()

    c.execute("SELECT * FROM entries WHERE phone=?", (phone,))
    data = c.fetchall()

    total = sum([row[4] for row in data])

    conn.close()

    return render_template("dashboard.html", data=data, total=total)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
@app.route("/pdf")
def pdf():
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    import io

    phone = session.get("phone")
    username = session.get("username")

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT date,description,amount FROM entries WHERE phone=?", (phone,))
    rows = c.fetchall()
    conn.close()

    buffer = io.BytesIO()

    def draw_bg(canvas, doc):
        # LIGHT BACKGROUND (soft blue gradient feel)
        canvas.setFillColorRGB(0.95, 0.97, 1)
        canvas.rect(0, 0, 600, 850, fill=1)

        # HEADER STRIP
        canvas.setFillColorRGB(0.2, 0.4, 0.9)
        canvas.rect(0, 780, 600, 70, fill=1)

        # TITLE
        canvas.setFillColorRGB(1,1,1)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(200, 800, "Ledger Report")

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Spacer(1, 90))

    elements.append(Paragraph(f"<b>User: {username}</b>", styles['Heading2']))
    elements.append(Spacer(1, 20))

    data = [["Date", "Description", "Amount"]]
    total = 0

    for r in rows:
        data.append([r[0], r[1], r[2]])
        total += r[2]

    data.append(["", "Total", total])

    table = Table(data, colWidths=[100, 250, 100])

    table.setStyle(TableStyle([
        # HEADER
        ("BACKGROUND", (0,0), (-1,0), colors.blue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        # BODY
        ("BACKGROUND", (0,1), (-1,-2), colors.whitesmoke),

        # GRID
        ("GRID", (0,0), (-1,-1), 1, colors.grey),

        # TOTAL ROW
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightblue),

        # ALIGN
        ("ALIGN", (2,1), (2,-1), "RIGHT"),
    ]))

    elements.append(table)

    doc.build(elements, onFirstPage=draw_bg, onLaterPages=draw_bg)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="ledger_report.pdf",
                     mimetype="application/pdf")
# @app.route("/pdf")
# def pdf():
#     from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
#     from reportlab.lib import colors
#     from reportlab.lib.pagesizes import A4
#     from reportlab.lib.styles import getSampleStyleSheet
#     import io

#     phone = session.get("phone")
#     username = session.get("username")

#     conn = sqlite3.connect("data.db")
#     c = conn.cursor()
#     c.execute("SELECT date,description,amount FROM entries WHERE phone=?", (phone,))
#     rows = c.fetchall()
#     conn.close()

#     buffer = io.BytesIO()

#     def draw_bg(canvas, doc):
#         # DARK BACKGROUND
#         canvas.setFillColorRGB(0.05, 0.1, 0.15)
#         canvas.rect(0, 0, 600, 850, fill=1)

#         # HEADER BAR
#         canvas.setFillColorRGB(0, 0.8, 1)
#         canvas.rect(0, 780, 600, 70, fill=1)

#         canvas.setFillColorRGB(0,0,0)
#         canvas.setFont("Helvetica-Bold", 18)
#         canvas.drawString(200, 800, "LEDGER PRO")

#     doc = SimpleDocTemplate(buffer, pagesize=A4)

#     elements = []
#     styles = getSampleStyleSheet()

#     elements.append(Spacer(1, 80))

#     elements.append(Paragraph(f"<font color='white'><b>User: {username}</b></font>", styles['Heading2']))
#     elements.append(Spacer(1, 20))

#     data = [["Date", "Description", "Amount"]]
#     total = 0

#     for r in rows:
#         data.append([r[0], r[1], r[2]])
#         total += r[2]

#     data.append(["", "Total", total])

#     table = Table(data, colWidths=[100, 250, 100])

#     table.setStyle(TableStyle([
#         ("BACKGROUND", (0,0), (-1,0), colors.black),
#         ("TEXTCOLOR", (0,0), (-1,0), colors.white),

#         ("BACKGROUND", (0,1), (-1,-2), colors.darkgrey),
#         ("TEXTCOLOR", (0,1), (-1,-1), colors.white),

#         ("GRID", (0,0), (-1,-1), 1, colors.cyan),

#         ("BACKGROUND", (0,-1), (-1,-1), colors.cyan),
#         ("TEXTCOLOR", (0,-1), (-1,-1), colors.black),

#         ("ALIGN", (2,1), (2,-1), "RIGHT"),
#     ]))

#     elements.append(table)

#     doc.build(elements, onFirstPage=draw_bg, onLaterPages=draw_bg)

#     buffer.seek(0)

#     return send_file(buffer, as_attachment=True,
#                      download_name="ledger_pro.pdf",
#                      mimetype="application/pdf")
# ---------------- PDF ----------------
# @app.route("/pdf")
# def pdf():
#     from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
#     from reportlab.lib import colors
#     from reportlab.lib.pagesizes import A4
#     from reportlab.lib.styles import getSampleStyleSheet

#     phone = session.get("phone")
#     username = session.get("username")

#     conn = sqlite3.connect("data.db")
#     c = conn.cursor()
#     c.execute("SELECT date,description,amount FROM entries WHERE phone=?", (phone,))
#     rows = c.fetchall()
#     conn.close()

#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(buffer, pagesize=A4)

#     elements = []
#     styles = getSampleStyleSheet()

#     elements.append(Paragraph(f"<b>{username}'s Ledger</b>", styles['Title']))
#     elements.append(Spacer(1, 15))

#     data = [["Date", "Description", "Amount"]]
#     total = 0

#     for r in rows:
#         data.append([r[0], r[1], r[2]])
#         total += r[2]

#     data.append(["", "Total", total])

#     table = Table(data, colWidths=[100, 250, 100])

#     table.setStyle(TableStyle([
#         ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
#         ("TEXTCOLOR", (0,0), (-1,0), colors.white),
#         ("GRID", (0,0), (-1,-1), 1, colors.grey),
#         ("BACKGROUND", (0,-1), (-1,-1), colors.lightblue),
#         ("ALIGN", (2,1), (2,-1), "RIGHT"),
#     ]))

#     elements.append(table)
#     doc.build(elements)

#     buffer.seek(0)

#     return send_file(buffer, as_attachment=True,
#                      download_name="ledger.pdf",
#                      mimetype="application/pdf")

# ---------------- RUN ----------------

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
