from pathlib import Path

from ai_squad.core.delegation import DelegationManager, DelegationStatus


class DummySignal:
    def __init__(self):
        self.sent = []

    def send_message(self, **kwargs):
        self.sent.append(kwargs)


def test_create_and_complete_delegation(tmp_path: Path):
    signal = DummySignal()
    mgr = DelegationManager(workspace_root=tmp_path, signal_manager=signal)

    link = mgr.create_delegation(
        from_agent="architect",
        to_agent="engineer",
        work_item_id="ISSUE-1",
        scope="project",
        sla="24h",
    )

    assert link.id in [d.id for d in mgr.list()]
    assert signal.sent[-1]["recipient"] == "engineer"

    completed = mgr.complete_delegation(link.id, status=DelegationStatus.COMPLETED, details="done")
    assert completed.status == DelegationStatus.COMPLETED
    assert signal.sent[-1]["recipient"] == "architect"
    assert signal.sent[-1]["metadata"]["status"] == "completed"
