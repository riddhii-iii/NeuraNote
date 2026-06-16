from flask import Blueprint, render_template, request, redirect
from services.db import get_db
from services.ai_service import rag_answer, summarize_topic, generate_quiz, create_flashcards, plan_study, semantic_search

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/topic/<int:topic_id>/ask", methods=["POST"])
def ask_topic(topic_id):
    question = request.form.get("ai_question", "").strip()
    answer = "Please provide a question to continue."
    if question:
        answer = rag_answer(question, topic_id)
    return render_template("ai_answer.html", answer=answer, topic_id=topic_id)


@ai_bp.route("/topic/<int:topic_id>/summarize", methods=["POST"])
def summarize(topic_id):
    summary = summarize_topic(topic_id)
    return render_template("summary.html", topic_id=topic_id, summary=summary)


@ai_bp.route("/topic/<int:topic_id>/quiz", methods=["POST"])
def quiz(topic_id):
    quiz_text = generate_quiz(topic_id)
    db = get_db()
    db.execute(
        "INSERT INTO quizzes (topic_id, title, content) VALUES (?, ?, ?)",
        (topic_id, "Generated quiz", quiz_text),
    )
    db.commit()
    return render_template("quiz.html", topic_id=topic_id, quiz_text=quiz_text)


@ai_bp.route("/topic/<int:topic_id>/flashcards", methods=["POST"])
def flashcards(topic_id):
    result_message = create_flashcards(topic_id)
    return render_template("flashcards.html", topic_id=topic_id, message=result_message)


@ai_bp.route("/topic/<int:topic_id>/study-plan", methods=["POST"])
def study_plan(topic_id):
    subject = request.form.get("subject", "")
    exam_date = request.form.get("exam_date", "")
    difficulty = request.form.get("difficulty", "Medium")
    daily_hours = int(request.form.get("daily_hours", 1))
    schedule = plan_study(topic_id, subject, exam_date, difficulty, daily_hours)
    return render_template(
        "study_plan.html",
        topic_id=topic_id,
        schedule=schedule,
        subject=subject,
        exam_date=exam_date,
        difficulty=difficulty,
        daily_hours=daily_hours,
    )


@ai_bp.route("/search", methods=["GET", "POST"])
def search():
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            results = semantic_search(query)
    return render_template("search.html", results=results, query=query)
