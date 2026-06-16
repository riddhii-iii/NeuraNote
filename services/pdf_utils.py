import os
from typing import List
import PyPDF2


def extract_text_from_pdf(path: str) -> str:
    if not os.path.exists(path):
        return ""

    text = []
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content = page.extract_text() or ""
                text.append(content)
    except Exception:
        return ""

    return "\n".join(text)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
