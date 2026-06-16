import os
from flask import Blueprint, render_template, redirect, request, current_app, send_file
from services.db import get_db
from services.pdf_utils import extract_text_from_pdf
from services.ai_service import index_topic_content

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    db = get_db()
    notebooks = db.execute(
        "SELECT id, name, created_at FROM notebooks ORDER BY created_at DESC"
    ).fetchall()
    return render_template("dashboard.html", notebooks=notebooks)


@main_bp.route("/notebook/<int:notebook_id>", methods=["GET", "POST"])
def notebook(notebook_id):
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title")
        if title:
            db.execute(
                "INSERT INTO topics (notebook_id, title, content, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (notebook_id, title, ""),
            )
            db.commit()
    notebook = db.execute(
        "SELECT id, name, created_at FROM notebooks WHERE id = ?",
        (notebook_id,),
    ).fetchone()
    if not notebook:
        return "Notebook not found", 404
    topics = db.execute(
        "SELECT id, title, created_at FROM topics WHERE notebook_id = ? ORDER BY created_at DESC",
        (notebook_id,),
    ).fetchall()
    return render_template("notebook.html", notebook=notebook, topics=topics)


@main_bp.route("/notebook/create", methods=["POST"])
def create_notebook():
    name = request.form.get("name")
    if name:
        db = get_db()
        db.execute(
            "INSERT INTO notebooks (name, created_at) VALUES (?, CURRENT_TIMESTAMP)",
            (name,),
        )
        db.commit()
    return redirect("/")


@main_bp.route("/notebook/delete/<int:notebook_id>", methods=["POST"])
def delete_notebook(notebook_id):
    db = get_db()
    db.execute("DELETE FROM topics WHERE notebook_id = ?", (notebook_id,))
    db.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
    db.commit()
    return redirect("/")


@main_bp.route("/topic/delete/<int:topic_id>", methods=["POST"])
def delete_topic(topic_id):
    db = get_db()
    db.execute("DELETE FROM files WHERE topic_id = ?", (topic_id,))
    db.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    db.commit()
    return redirect("/")


@main_bp.route("/upload/<int:topic_id>", methods=["POST"])
def upload_file(topic_id):
    if "file" not in request.files:
        return redirect(request.referrer or "/")
    file = request.files["file"]
    if file.filename == "":
        return redirect(request.referrer or "/")
    filename = file.filename
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    path = os.path.join(upload_folder, filename)
    file.save(path)
    db = get_db()
    db.execute(
        "INSERT INTO files (topic_id, filename, path, uploaded_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (topic_id, filename, path),
    )
    db.commit()
    index_topic_content(topic_id)
    return redirect(request.referrer or "/")


@main_bp.route("/pdf/<int:file_id>")
def serve_pdf(file_id):
    db = get_db()
    file = db.execute("SELECT filename, path FROM files WHERE id = ?", (file_id,)).fetchone()
    if not file:
        return "File not found", 404
    if not os.path.exists(file["path"]):
        return "File path missing", 404
    return send_file(file["path"], as_attachment=False, download_name=file["filename"])
