from flask import Blueprint, render_template, request, redirect
from services.db import get_db
from services.ai_service import index_topic_content

notebooks_bp = Blueprint("notebooks", __name__)


@notebooks_bp.route("/topic/<int:topic_id>", methods=["GET", "POST"])
def topic(topic_id):
    db = get_db()
    if request.method == "POST":
        if "content" in request.form:
            content = request.form.get("content", "")
            db.execute("UPDATE topics SET content = ? WHERE id = ?", (content, topic_id))
            db.commit()
            index_topic_content(topic_id)
        return redirect(request.referrer or "/")

    topic = db.execute("SELECT id, title, content FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        return "Topic not found", 404
    files = db.execute("SELECT id, filename FROM files WHERE topic_id = ? ORDER BY uploaded_at DESC", (topic_id,)).fetchall()
    return render_template("topic.html", topic=topic, files=files)


@notebooks_bp.route("/topic/edit/<int:notebook_id>", methods=["POST"])
def edit_notebook(notebook_id):
    new_name = request.form.get("new_name")
    if new_name:
        db = get_db()
        db.execute("UPDATE notebooks SET name = ? WHERE id = ?", (new_name, notebook_id))
        db.commit()
    return redirect(request.referrer or "/")
