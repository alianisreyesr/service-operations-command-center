from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_renders_without_exceptions():
    app = AppTest.from_file(Path(__file__).parents[1] / "dashboard.py")

    app.run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "Service Operations Command Center"
    assert len(app.metric) == 5


def test_dashboard_handles_an_empty_repository():
    from app import main
    from app.repository import InMemoryIncidentRepository

    main.incidents = InMemoryIncidentRepository([])  # restored by the autouse fixture's monkeypatch
    app = AppTest.from_file(Path(__file__).parents[1] / "dashboard.py")
    app.run(timeout=15)
    assert not app.exception
    assert app.metric[0].value == "0"


def test_dashboard_filters_breached_only():
    app = AppTest.from_file(Path(__file__).parents[1] / "dashboard.py")
    app.run(timeout=15)
    app.toggle[0].set_value(True).run(timeout=15)
    assert not app.exception
    table = app.dataframe[0].value
    assert list(table["title"]) == ["Checkout latency above target"]
