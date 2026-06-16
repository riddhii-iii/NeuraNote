import sqlite3
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        database_path = app.config["DATABASE"]
        conn = sqlite3.connect(database_path, detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS notebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notebook_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (notebook_id) REFERENCES notebooks (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT,
                scope_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER,
                user_name TEXT,
                score INTEGER,
                answers TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                subject TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                daily_hours INTEGER NOT NULL,
                schedule TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT NOT NULL,
                topic_id INTEGER,
                source_type TEXT,
                source_id INTEGER,
                chunk_text TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
            """
        )

        conn.commit()

        # Run lightweight migrations to add missing timestamp columns when upgrading older DBs
        def add_column_if_missing(table, column_name, column_def, default_value=None):
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if column_name not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}")
                if default_value is not None:
                    cur.execute(
                        f"UPDATE {table} SET {column_name} = {default_value} WHERE {column_name} IS NULL"
                    )

        try:
            add_column_if_missing("notebooks", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("topics", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("files", "uploaded_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("messages", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("flashcards", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("quizzes", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("quiz_results", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("study_plans", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
            add_column_if_missing("embeddings", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
        except Exception:
            # Non-fatal: if ALTER fails (SQLite limitations) continue — app can still function.
            pass

        conn.commit()
        conn.close()
    app.teardown_appcontext(close_db)
