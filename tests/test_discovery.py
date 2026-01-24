from ai_squad.core.discovery import DiscoveryIndex


def test_discovery_filters(tmp_path):
    idx = DiscoveryIndex(workspace_root=tmp_path)
    idx.add_remote("https://example.com/a", scopes=["project"], visibility="private", tags=["alpha"])
    idx.add_remote("https://example.com/b", scopes=["org"], visibility="org", tags=["beta"])
    idx.add_remote("https://example.com/c", scopes=["public"], visibility="public", tags=["alpha", "beta"])

    private = idx.query(visibility="private")
    assert len(private) == 1

    alpha = idx.query(tag="alpha")
    assert len(alpha) == 2

    org_scope = idx.query(scope="org")
    assert len(org_scope) == 1
