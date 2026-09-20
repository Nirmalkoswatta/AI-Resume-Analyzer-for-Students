import json
from pathlib import Path

from app.main import create_app

DESTINATION = Path(__file__).resolve().parents[3] / "packages" / "schema" / "openapi.json"


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    spec = create_app().openapi()
    DESTINATION.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {DESTINATION}")


if __name__ == "__main__":
    main()
