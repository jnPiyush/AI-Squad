"""Tests for operational graph."""
import pytest
from pathlib import Path

from ai_squad.core.operational_graph import (
    OperationalGraph,
    NodeType,
    EdgeType,
)


def test_add_nodes_and_edges(tmp_path):
    graph = OperationalGraph(workspace_root=tmp_path)
    
    # Add nodes
    wi = graph.add_node("issue-123", NodeType.WORK_ITEM, {"title": "Add login"})
    agent = graph.add_node("pm", NodeType.AGENT, {"role": "product_manager"})
    skill = graph.add_node("requirements", NodeType.SKILL, {"version": "1.0"})
    
    assert wi.id == "issue-123"
    assert agent.type == NodeType.AGENT
    
    # Add edges
    edge1 = graph.add_edge("issue-123", "pm", EdgeType.OWNS)
    edge2 = graph.add_edge("pm", "requirements", EdgeType.USES)
    
    assert edge1.from_node == "issue-123"
    assert edge2.type == EdgeType.USES


def test_dependencies_and_dependents(tmp_path):
    graph = OperationalGraph(workspace_root=tmp_path)
    
    graph.add_node("feature-a", NodeType.WORK_ITEM)
    graph.add_node("feature-b", NodeType.WORK_ITEM)
    graph.add_node("feature-c", NodeType.WORK_ITEM)
    
    graph.add_edge("feature-b", "feature-a", EdgeType.DEPENDS_ON)
    graph.add_edge("feature-c", "feature-a", EdgeType.DEPENDS_ON)
    
    deps = graph.get_dependencies("feature-b")
    assert "feature-a" in deps
    
    dependents = graph.get_dependents("feature-a")
    assert set(dependents) == {"feature-b", "feature-c"}


def test_impact_analysis(tmp_path):
    graph = OperationalGraph(workspace_root=tmp_path)
    
    graph.add_node("api", NodeType.CAPABILITY)
    graph.add_node("service-a", NodeType.AGENT)
    graph.add_node("service-b", NodeType.AGENT)
    graph.add_node("feature-x", NodeType.WORK_ITEM)
    
    graph.add_edge("service-a", "api", EdgeType.DEPENDS_ON)
    graph.add_edge("service-b", "api", EdgeType.DEPENDS_ON)
    graph.add_edge("feature-x", "service-a", EdgeType.DEPENDS_ON)
    
    impact = graph.impact_analysis("api")
    
    assert impact["node"] == "api"
    assert set(impact["direct_dependents"]) == {"service-a", "service-b"}
    assert impact["total_affected"] >= 2


def test_traverse_graph(tmp_path):
    graph = OperationalGraph(workspace_root=tmp_path)
    
    graph.add_node("a", NodeType.WORK_ITEM)
    graph.add_node("b", NodeType.WORK_ITEM)
    graph.add_node("c", NodeType.WORK_ITEM)
    graph.add_node("d", NodeType.WORK_ITEM)
    
    graph.add_edge("a", "b", EdgeType.DEPENDS_ON)
    graph.add_edge("b", "c", EdgeType.DEPENDS_ON)
    graph.add_edge("c", "d", EdgeType.DEPENDS_ON)
    
    path = graph.traverse("a", EdgeType.DEPENDS_ON)
    assert "a" in path
    assert "b" in path
    assert "c" in path
    assert "d" in path


def test_persistence(tmp_path):
    graph1 = OperationalGraph(workspace_root=tmp_path)
    graph1.add_node("test-node", NodeType.AGENT, {"key": "value"})
    graph1.add_node("test-node-2", NodeType.SKILL)
    graph1.add_edge("test-node", "test-node-2", EdgeType.USES)
    
    # Load in new instance
    graph2 = OperationalGraph(workspace_root=tmp_path)
    node = graph2.get_node("test-node")
    
    assert node is not None
    assert node.metadata["key"] == "value"
    
    edges = graph2.get_outgoing_edges("test-node")
    assert len(edges) == 1
    assert edges[0].type == EdgeType.USES
