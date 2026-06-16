import json
from flask import current_app
from services.db import get_db
from services.pdf_utils import extract_text_from_pdf, chunk_text
from services.vector_store import vector_store
from services.embeddings import completion


def build_topic_corpus(topic_id):
    db = get_db()
    topic = db.execute("SELECT title, content FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        return ""

    content = [topic["title"], topic["content"] or ""]
    rows = db.execute("SELECT path FROM files WHERE topic_id = ?", (topic_id,)).fetchall()
    for row in rows:
        if row["path"].lower().endswith(".pdf"):
            content.append(extract_text_from_pdf(row["path"]))
    return "\n\n".join(content).strip()


def index_topic_content(topic_id):
    db = get_db()
    topic = db.execute("SELECT title, content FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if not topic:
        return

    corpus = build_topic_corpus(topic_id)
    chunks = chunk_text(corpus, chunk_size=400, overlap=100)
    if not chunks:
        return

    metadatas = []
    for chunk in chunks:
        metadatas.append(
            {
                "topic_id": topic_id,
                "source_type": "topic",
                "source_name": topic["title"],
            }
        )

    ids = vector_store.add_documents(chunks, metadatas)
    for chunk_id, chunk_text in zip(ids, chunks):
        db.execute(
            "INSERT INTO embeddings (chunk_id, topic_id, source_type, source_id, chunk_text, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, topic_id, "topic", topic_id, chunk_text, json.dumps({"title": topic["title"]})),
        )
    db.commit()


def rag_answer(question, topic_id):
    context_chunks = vector_store.query(question, n_results=5)
    context_texts = []
    for index, chunk in enumerate(context_chunks, start=1):
        metadata = chunk.get("metadata", {})
        source_text = chunk.get("text", "")
        source_label = metadata.get("source_name") or metadata.get("source_type", "content")
        context_texts.append(f"Chunk {index} from {source_label}:\n{source_text}")

    context_payload = "\n\n".join(context_texts)
    if not context_payload:
        return "No indexed content is available yet. Upload a PDF or save notes to generate answers from your learning materials."

    prompt = (
        "You are an AI learning assistant. Use only the context provided below to answer the user's question. "
        "Do not invent facts, and say you don't know if the answer is not supported by the content.\n\n"
        f"Context:\n{context_payload}\n\n"
        f"Question: {question}\n\n"
        "Answer in a clear, concise way and cite the relevant content if possible."
    )
    return completion(prompt, system_prompt="You are a helpful AI assistant focusing on accurate answers from provided source text.")


def summarize_topic(topic_id):
    corpus = build_topic_corpus(topic_id)
    if not corpus:
        return {
            "short_summary": "No content is available yet.",
            "detailed_summary": "No content is available yet.",
            "key_takeaways": "No content is available yet.",
            "definitions": "No content is available yet.",
            "revision_notes": "No content is available yet.",
        }

    prompt = (
        "Read the following learning material and produce the requested sections.\n\n"
        f"Material:\n{corpus}\n\n"
        "Generate:\n"
        "1. Short Summary\n"
        "2. Detailed Summary\n"
        "3. Key Takeaways\n"
        "4. Important Definitions\n"
        "5. Exam Revision Notes\n"
        "Format the response with clear headings for each section."
    )
    answer = completion(prompt, system_prompt="You are an educational assistant that summarizes notes for study and exam preparation.")
    return {
        "short_summary": answer,
        "detailed_summary": answer,
        "key_takeaways": answer,
        "definitions": answer,
        "revision_notes": answer,
    }


def generate_quiz(topic_id):
    corpus = build_topic_corpus(topic_id)
    if not corpus:
        return "No content is available yet to generate a quiz."

    prompt = (
        "Create 10 multiple-choice questions with four answer options each based on the following study material. "
        "Include the correct answer and a short explanation for each question. "
        "Format the output as:\nQuestion 1: ...\nA. ...\nB. ...\nC. ...\nD. ...\nAnswer: ...\nExplanation: ...\n\n"
        f"Material:\n{corpus}"
    )
    return completion(prompt, system_prompt="You are an educational AI that generates high-quality multiple-choice quizzes from source material.")


def create_flashcards(topic_id):
    corpus = build_topic_corpus(topic_id)
    if not corpus:
        return "No content is available yet to generate flashcards."

    prompt = (
        "Create up to 12 flashcards from the following content. "
        "Format each card as Question: ...\nAnswer: ...\n\n"
        f"Content:\n{corpus}"
    )
    answer = completion(prompt, system_prompt="You are an educational AI that creates concise flashcards for study.")

    cards = []
    for block in answer.split("\n\n"):
        if not block.strip():
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        question = ""
        answer_text = ""
        for line in lines:
            if line.lower().startswith("question:"):
                question = line.split(":", 1)[1].strip()
            elif line.lower().startswith("answer:"):
                answer_text = line.split(":", 1)[1].strip()
        if question and answer_text:
            cards.append((question, answer_text))

    db = get_db()
    for question, answer_text in cards:
        db.execute(
            "INSERT INTO flashcards (topic_id, question, answer, source) VALUES (?, ?, ?, ?)",
            (topic_id, question, answer_text, "generated"),
        )
    db.commit()

    return f"Stored {len(cards)} flashcards for review."


def plan_study(topic_id, subject, exam_date, difficulty, daily_hours):
    corpus = build_topic_corpus(topic_id)
    prompt = (
        "Create a personalized study plan for a student preparing for an exam. "
        f"Subject: {subject}\n"
        f"Exam date: {exam_date}\n"
        f"Difficulty level: {difficulty}\n"
        f"Daily available hours: {daily_hours}\n"
        "Use the available notes and PDFs to organize the plan into study blocks, milestones, and review sessions."
        f"\n\nLearning content:\n{corpus}"
    )
    schedule = completion(prompt, system_prompt="You are a study planner AI that creates practical daily schedules for exam preparation.")
    db = get_db()
    db.execute(
        "INSERT INTO study_plans (topic_id, subject, exam_date, difficulty, daily_hours, schedule) VALUES (?, ?, ?, ?, ?, ?)",
        (topic_id, subject, exam_date, difficulty, daily_hours, schedule),
    )
    db.commit()
    return schedule


def semantic_search(query):
    results = vector_store.query(query, n_results=5)
    if not results:
        return [
            {
                "title": "No results found",
                "snippet": "No semantically similar passages are indexed yet. Please upload material and save your notes.",
            }
        ]

    response = []
    for item in results:
        metadata = item.get("metadata", {})
        response.append(
            {
                "title": metadata.get("source_name", metadata.get("source_type", "Learning material")),
                "snippet": item.get("text", ""),
            }
        )
    return response
