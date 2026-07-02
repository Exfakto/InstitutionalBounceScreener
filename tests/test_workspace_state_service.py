import json

from services.workspace_state_service import WorkspaceStateService


def test_workspace_state_missing_file_uses_defaults(tmp_path):
    service = WorkspaceStateService(tmp_path / "missing.json")

    state = service.load_state()

    assert state["window"]["size"] == [1600, 900]
    assert state["window"]["maximized"] is False
    assert state["splitters"] == {}


def test_workspace_state_malformed_file_uses_defaults(tmp_path):
    path = tmp_path / "workspace_state.json"
    path.write_text("{bad json", encoding="utf-8")

    state = WorkspaceStateService(path).load_state()

    assert state["window"]["size"] == [1600, 900]
    assert state["selected_ticker"] is None


def test_workspace_state_save_load_round_trip(tmp_path):
    path = tmp_path / "workspace_state.json"
    service = WorkspaceStateService(path)

    saved = service.save_state(
        {
            "window": {
                "size": [1200, 800],
                "position": [20, 30],
                "maximized": True,
            },
            "splitters": {
                "workspace_splitter": [500, 250],
            },
            "selected_ticker": "AAPL",
            "active_tab": 2,
            "active_workspace": "Watchlist",
            "active_screener_preset": "Momentum",
        }
    )
    loaded = service.load_state()

    assert saved == loaded
    assert loaded["window"]["size"] == [1200, 800]
    assert loaded["splitters"]["workspace_splitter"] == [500, 250]
    assert loaded["selected_ticker"] == "AAPL"
    assert loaded["active_screener_preset"] == "Momentum"


def test_workspace_state_clear_state(tmp_path):
    path = tmp_path / "workspace_state.json"
    service = WorkspaceStateService(path)
    service.save_state({"selected_ticker": "MSFT"})

    cleared = service.clear_state()

    assert not path.exists()
    assert cleared["selected_ticker"] is None
    assert service.load_state()["selected_ticker"] is None


def test_workspace_state_preserves_unknown_keys(tmp_path):
    path = tmp_path / "workspace_state.json"
    path.write_text(
        json.dumps(
            {
                "future": {"layout_version": 3},
                "window": {"size": [1000, 700]},
            }
        ),
        encoding="utf-8",
    )
    service = WorkspaceStateService(path)

    service.save_state({"selected_ticker": "NVDA"})
    loaded = service.load_state()

    assert loaded["future"] == {"layout_version": 3}
    assert loaded["selected_ticker"] == "NVDA"
    assert loaded["window"]["size"] == [1000, 700]
