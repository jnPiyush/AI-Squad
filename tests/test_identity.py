from ai_squad.core.identity import IdentityManager


def test_identity_dossier_persist(tmp_path):
    mgr = IdentityManager(workspace_root=tmp_path)
    dossier = mgr.build(
        workspace_name="Test Workspace",
        agents=["pm", "engineer", "architect"],
        author="tester",
        commit_sha="abc123",
        extra={"env": "ci"},
    )
    path = mgr.save(dossier)

    loaded = mgr.load()
    assert path.exists()
    assert loaded is not None
    assert loaded.workspace_name == "Test Workspace"
    assert set(loaded.agents) == {"pm", "engineer", "architect"}
    assert loaded.extra.get("env") == "ci"
