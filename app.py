import os
from dotenv import load_dotenv
from flask import Flask

from services.db import init_db
from services.vector_store import vector_store
from blueprints.notebooks import notebooks_bp
from blueprints.main import main_bp
from blueprints.ai_routes import ai_bp


def create_app():
    load_dotenv()

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
    app.config["DATABASE"] = os.path.join(app.root_path, "notes.db")
    app.config["VECTOR_STORE_PATH"] = os.path.join(app.root_path, "vector_store")
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["VECTOR_STORE_PATH"], exist_ok=True)

    init_db(app)
    vector_store.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(notebooks_bp)
    app.register_blueprint(ai_bp)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)


