from ai_squad.core.scout_worker import ScoutWorker


def test_scout_worker_runs_tasks(tmp_path):
    worker = ScoutWorker(workspace_root=tmp_path)
    calls = []

    def step_one():
        calls.append("one")
        return 1

    def step_two():
        calls.append("two")
        return 2

    run = worker.run({"step_one": step_one, "step_two": step_two}, metadata={"kind": "healthcheck"})

    assert len(run.tasks) == 2
    assert all(t.status == "completed" for t in run.tasks)
    assert calls == ["one", "two"]

    checkpoint = (tmp_path / ".squad" / "scout_workers").glob("scout-*.json")
    assert any(checkpoint)
