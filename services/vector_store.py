import os
import uuid
import chromadb
from chromadb.config import Settings
from flask import current_app
from services.embeddings import get_embedding


class VectorStore:
    def __init__(self):
        self.client = None
        self.collection = None

    def init_app(self, app):
        persist_path = app.config["VECTOR_STORE_PATH"]
        self.client = chromadb.Client(
            settings=Settings(
                persist_directory=persist_path,
                is_persistent=True,
                anonymized_telemetry=False,
            )
        )
        self.collection = self.client.get_or_create_collection(
            name="educational_content",
            metadata={"source": "ai_learning_assistant"},
        )

    def add_documents(self, texts, metadatas):
        if not texts:
            return []

        ids = [str(uuid.uuid4()) for _ in texts]
        embeddings = [get_embedding(text) for text in texts]
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        self.client.persist()
        return ids

    def query(self, query_text, n_results=5):
        if not query_text or self.collection is None:
            return []

        query_embedding = get_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        hits = []
        for text, metadata in zip(results.get("documents", [[]])[0], results.get("metadatas", [[]])[0]):
            hits.append({"text": text, "metadata": metadata})
        return hits


vector_store = VectorStore()
