import json
from pathlib import Path

from app.main import app

DOCS_PATH = Path(__file__).parent.parent / "docs.json"


def test_openapi_schema_documents_all_routes() -> None:
    document = app.openapi()
    assert document["openapi"].startswith("3.")
    paths = document["paths"]
    assert "post" in paths["/search"]
    assert "delete" in paths["/posts/{post_id}"]
    assert "get" in paths["/health/live"]
    assert "get" in paths["/health/ready"]
    assert "503" in paths["/search"]["post"]["responses"]
    assert "503" in paths["/posts/{post_id}"]["delete"]["responses"]
    assert "503" in paths["/health/ready"]["get"]["responses"]


def test_docs_json_is_valid_and_in_sync() -> None:
    exported = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
    assert exported == app.openapi()
