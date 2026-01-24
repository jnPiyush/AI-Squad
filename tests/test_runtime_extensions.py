from datetime import datetime, timedelta
from pathlib import Path

from ai_squad.core.convoy import Convoy, ConvoyMember, ConvoyStatus
from ai_squad.core.patrol import PatrolManager
from ai_squad.core.recon import ReconManager
from ai_squad.core.reporting import ReportManager
from ai_squad.core.signal import SignalManager
from ai_squad.core.theater import TheaterRegistry
from ai_squad.core.workstate import WorkStateManager, WorkStatus


def test_theater_registry_routes_and_staging(tmp_path: Path):
    config = {"theater": {"default": "alpha"}}
    registry = TheaterRegistry(workspace_root=tmp_path, config=config)

    registry.add_sector("alpha", "sector-a", repo_path=str(tmp_path / "repo-a"))
    registry.set_route("alpha", "feat-", "sector-a")

    sector = registry.resolve_sector("feat-", "alpha")
    assert sector is not None
    assert sector.name == "sector-a"

    staging_paths = registry.ensure_staging_areas("alpha")
    assert staging_paths
    assert staging_paths[0].exists()


def test_recon_summary_includes_workstate_and_signal(tmp_path: Path):
    workstate = WorkStateManager(workspace_root=tmp_path)
    workstate.create_work_item(title="Test work", description="desc")

    signal = SignalManager(workspace_root=tmp_path)
    recon = ReconManager(
        workspace_root=tmp_path,
        workstate_manager=workstate,
        signal_manager=signal,
        routing_config={"window": 10},
    )

    summary = recon.build_summary()
    assert summary.work_state["total"] == 1
    assert "by_status" in summary.work_state
    assert "by_status" in summary.signal


def test_patrol_detects_stale_items(tmp_path: Path):
    workstate = WorkStateManager(workspace_root=tmp_path)
    item = workstate.create_work_item(title="Stale work", description="desc")
    workstate.transition_status(item.id, WorkStatus.IN_PROGRESS)

    stale_time = datetime.now() - timedelta(minutes=180)
    workstate.set_updated_at(item.id, stale_time.isoformat())

    patrol = PatrolManager(
        workspace_root=tmp_path,
        workstate_manager=workstate,
        stale_minutes=120,
    )
    events = patrol.run()
    assert len(events) == 1
    assert events[0].work_item_id == item.id


def test_after_operation_report_written(tmp_path: Path):
    report_mgr = ReportManager(workspace_root=tmp_path)
    convoy = Convoy(id="convoy-1", name="Test Convoy", status=ConvoyStatus.COMPLETED)
    convoy.members = [
        ConvoyMember(agent_type="pm", work_item_id="w1", status="completed"),
        ConvoyMember(agent_type="engineer", work_item_id="w2", status="failed"),
    ]
    convoy.errors = ["engineer/w2: failure"]

    report_path = report_mgr.write_convoy_report(convoy)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "After-Operation Report" in content
    assert "Completed" in content
