import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_vercel_services_configuration_is_same_origin_and_bounded() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert "experimentalServices" not in config
    assert config["services"] == {
        "web": {"root": "apps/web", "framework": "nextjs"},
        "simulation": {
            "root": "apps/simulation-api",
            "framework": "fastapi",
            "entrypoint": "app.main:app",
        },
    }
    assert config["rewrites"] == [
        {"source": "/api/simulation/(.*)", "destination": {"service": "simulation"}},
        {"source": "/(.*)", "destination": {"service": "web"}},
    ]
    serialized = json.dumps(config)
    assert "http://" not in serialized
    assert "https://" not in serialized.replace("https://openapi.vercel.sh/vercel.json", "")


def test_python_entrypoint_matches_services_configuration() -> None:
    pyproject = (ROOT / "apps/simulation-api/pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.vercel]\nentrypoint = "app.main:app"' in pyproject
