import json
from pathlib import Path

from app.main import app

CONTRACT = Path(__file__).resolve().parent.parent / "contracts" / "optimizer-v1.json"


def test_the_versioned_contract_matches_the_application():
    versioned = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert versioned == json.loads(json.dumps(app.openapi()))
