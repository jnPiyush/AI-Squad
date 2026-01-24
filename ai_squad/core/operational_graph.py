"""Operational graph for work items, agents, skills, repos, and environments.

Represents the system as nodes with typed edges (depends_on, delegates_to, mirrors, owns, emits, consumes).
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Node types in the operational graph."""
    WORK_ITEM = "work_item"
    AGENT = "agent"
    SKILL = "skill"
    REPO = "repo"
    ENVIRONMENT = "environment"
    CAPABILITY = "capability"
    MODEL = "model"


class EdgeType(str, Enum):
    """Edge types representing relationships."""
    DEPENDS_ON = "depends_on"
    DELEGATES_TO = "delegates_to"
    MIRRORS = "mirrors"
    OWNS = "owns"
    EMITS = "emits"
    CONSUMES = "consumes"
    REQUIRES = "requires"
    USES = "uses"


@dataclass
class GraphNode:
    """A node in the operational graph."""
    id: str
    type: NodeType
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        data = data.copy()
        data["type"] = NodeType(data["type"])
        return cls(**data)


@dataclass
class GraphEdge:
    """A directed edge in the operational graph."""
    from_node: str
    to_node: str
    type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "type": self.type.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        data = data.copy()
        data["type"] = EdgeType(data["type"])
        return cls(**data)


class OperationalGraph:
    """Manages the operational graph with nodes and typed edges."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.graph_dir = self.workspace_root / ".squad" / "graph"
        self.nodes_file = self.graph_dir / "nodes.json"
        self.edges_file = self.graph_dir / "edges.json"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._load()

    def add_node(self, node_id: str, node_type: NodeType, metadata: Optional[Dict[str, Any]] = None) -> GraphNode:
        """Add or update a node in the graph."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.metadata.update(metadata or {})
            node.updated_at = datetime.now().isoformat()
        else:
            node = GraphNode(id=node_id, type=node_type, metadata=metadata or {})
            self._nodes[node_id] = node
        
        self._save()
        logger.info("graph_node_added", extra={"node": node.to_dict()})
        return node

    def add_edge(self, from_node: str, to_node: str, edge_type: EdgeType, metadata: Optional[Dict[str, Any]] = None) -> GraphEdge:
        """Add an edge between two nodes."""
        if from_node not in self._nodes:
            raise ValueError(f"Source node {from_node} does not exist")
        if to_node not in self._nodes:
            raise ValueError(f"Target node {to_node} does not exist")
        
        # Check if edge already exists
        for edge in self._edges:
            if edge.from_node == from_node and edge.to_node == to_node and edge.type == edge_type:
                edge.metadata.update(metadata or {})
                self._save()
                return edge
        
        edge = GraphEdge(from_node=from_node, to_node=to_node, type=edge_type, metadata=metadata or {})
        self._edges.append(edge)
        self._save()
        logger.info("graph_edge_added", extra={"edge": edge.to_dict()})
        return edge

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_nodes(self) -> List[GraphNode]:
        """Get all nodes."""
        return list(self._nodes.values())

    def get_edges(self) -> List[GraphEdge]:
        """Get all edges."""
        return list(self._edges)

    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.type == node_type]

    def get_outgoing_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[GraphEdge]:
        """Get all outgoing edges from a node, optionally filtered by type."""
        edges = [e for e in self._edges if e.from_node == node_id]
        if edge_type:
            edges = [e for e in edges if e.type == edge_type]
        return edges

    def get_incoming_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[GraphEdge]:
        """Get all incoming edges to a node, optionally filtered by type."""
        edges = [e for e in self._edges if e.to_node == node_id]
        if edge_type:
            edges = [e for e in edges if e.type == edge_type]
        return edges

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all nodes that this node depends on."""
        edges = self.get_outgoing_edges(node_id, EdgeType.DEPENDS_ON)
        return [e.to_node for e in edges]

    def get_dependents(self, node_id: str) -> List[str]:
        """Get all nodes that depend on this node."""
        edges = self.get_incoming_edges(node_id, EdgeType.DEPENDS_ON)
        return [e.from_node for e in edges]

    def traverse(self, start_node: str, edge_type: Optional[EdgeType] = None, max_depth: int = 10) -> List[str]:
        """Traverse the graph from a starting node, following edges of specified type."""
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(start_node, 0)]
        result: List[str] = []
        
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            result.append(node_id)
            
            edges = self.get_outgoing_edges(node_id, edge_type)
            for edge in edges:
                if edge.to_node not in visited:
                    queue.append((edge.to_node, depth + 1))
        
        return result

    def find_path(self, from_node: str, to_node: str, edge_type: Optional[EdgeType] = None) -> Optional[List[str]]:
        """Find a path between two nodes."""
        if from_node not in self._nodes or to_node not in self._nodes:
            return None
        
        visited: Set[str] = set()
        queue: List[tuple[str, List[str]]] = [(from_node, [from_node])]
        
        while queue:
            node_id, path = queue.pop(0)
            if node_id == to_node:
                return path
            
            if node_id in visited:
                continue
            visited.add(node_id)
            
            edges = self.get_outgoing_edges(node_id, edge_type)
            for edge in edges:
                if edge.to_node not in visited:
                    queue.append((edge.to_node, path + [edge.to_node]))
        
        return None

    def impact_analysis(self, node_id: str) -> Dict[str, Any]:
        """Analyze the impact of changes to a node."""
        if node_id not in self._nodes:
            return {"error": "Node not found"}

        direct_dependents = self.get_dependents(node_id)
        all_dependents = self._collect_dependents(node_id)

        owners = [e.from_node for e in self.get_incoming_edges(node_id, EdgeType.OWNS)]
        consumers = [e.from_node for e in self.get_incoming_edges(node_id, EdgeType.CONSUMES)]

        return {
            "node": node_id,
            "direct_dependents": direct_dependents,
            "total_affected": len(set(all_dependents)),
            "owners": owners,
            "consumers": consumers,
            "affected_nodes": list(set(all_dependents)),
        }

    def export_mermaid(self) -> str:
        """Export graph as Mermaid diagram."""
        lines = ["graph TD"]
        node_id_map = {node_id: self._safe_id(node_id) for node_id in self._nodes}

        for node in self._nodes.values():
            safe_id = node_id_map[node.id]
            label = f"{node.type.value}: {node.id}"
            lines.append(f"  {safe_id}[{label}]")
        
        for edge in self._edges:
            from_id = node_id_map.get(edge.from_node, self._safe_id(edge.from_node))
            to_id = node_id_map.get(edge.to_node, self._safe_id(edge.to_node))
            lines.append(f"  {from_id} -->|{edge.type.value}| {to_id}")
        
        return "\n".join(lines)

    def detect_cycles(self, edge_type: Optional[EdgeType] = None) -> List[List[str]]:
        """Detect cycles in the graph (returns list of cycles)."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        stack: Set[str] = set()

        def _visit(node_id: str, path: List[str]) -> None:
            if node_id in stack:
                cycle_start = path.index(node_id) if node_id in path else 0
                cycles.append(path[cycle_start:] + [node_id])
                return
            if node_id in visited:
                return
            visited.add(node_id)
            stack.add(node_id)

            for edge in self.get_outgoing_edges(node_id, edge_type):
                _visit(edge.to_node, path + [edge.to_node])

            stack.remove(node_id)

        for node_id in self._nodes:
            _visit(node_id, [node_id])

        return cycles

    def _save(self) -> None:
        """Save graph to disk."""
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        nodes_data = {node_id: node.to_dict() for node_id, node in self._nodes.items()}
        self.nodes_file.write_text(json.dumps(nodes_data, ensure_ascii=True, indent=2), encoding="utf-8")
        
        edges_data = [edge.to_dict() for edge in self._edges]
        self.edges_file.write_text(json.dumps(edges_data, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Load graph from disk."""
        if self.nodes_file.exists():
            try:
                data = json.loads(self.nodes_file.read_text(encoding="utf-8"))
                self._nodes = {node_id: GraphNode.from_dict(node_data) for node_id, node_data in data.items()}
            except json.JSONDecodeError:
                self._backup_corrupt_file(self.nodes_file)
                logger.warning("Nodes file corrupted; resetting")
                self._nodes = {}
        
        if self.edges_file.exists():
            try:
                data = json.loads(self.edges_file.read_text(encoding="utf-8"))
                self._edges = [GraphEdge.from_dict(edge_data) for edge_data in data]
            except json.JSONDecodeError:
                self._backup_corrupt_file(self.edges_file)
                logger.warning("Edges file corrupted; resetting")
                self._edges = []

    def _collect_dependents(self, node_id: str) -> List[str]:
        """Collect all dependents using reverse dependency traversal."""
        dependents: Set[str] = set()
        queue: List[str] = [node_id]
        while queue:
            current = queue.pop(0)
            incoming = [e.from_node for e in self.get_incoming_edges(current, EdgeType.DEPENDS_ON)]
            for dependent in incoming:
                if dependent not in dependents:
                    dependents.add(dependent)
                    queue.append(dependent)
        return list(dependents)

    @staticmethod
    def _backup_corrupt_file(path: Path) -> None:
        backup = path.with_suffix(path.suffix + ".corrupt")
        try:
            if path.exists():
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except (OSError, ValueError) as exc:
            logger.warning("Failed to back up corrupt file %s: %s", path, exc)

    @staticmethod
    def _safe_id(node_id: str) -> str:
        """Sanitize node IDs for Mermaid identifiers."""
        safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in node_id)
        if not safe:
            return "node"
        if safe[0].isdigit():
            safe = f"n_{safe}"
        return safe
