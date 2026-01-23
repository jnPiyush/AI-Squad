"""
Performance Benchmark Suite

Benchmarks for AI-Squad operations to track performance and detect regressions.
"""
import time
import statistics
from typing import Callable, List, Dict, Any
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock

from ai_squad.core.config import Config
from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.agents.architect import ArchitectAgent
from ai_squad.agents.engineer import EngineerAgent
from ai_squad.tools.github import GitHubTool
from ai_squad.core.status import StatusManager, IssueStatus
from ai_squad.core.agent_comm import AgentCommunicator
from ai_squad.core.storage import PersistentStorage


class Benchmark:
    """Individual benchmark"""
    
    def __init__(self, name: str, func: Callable, iterations: int = 10):
        """
        Initialize benchmark
        
        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
        """
        self.name = name
        self.func = func
        self.iterations = iterations
        self.results = []
    
    def run(self) -> Dict[str, Any]:
        """Run benchmark and return results"""
        print(f"Running {self.name}... ", end="", flush=True)
        
        times = []
        for i in range(self.iterations):
            start = time.perf_counter()
            self.func()
            end = time.perf_counter()
            times.append(end - start)
        
        result = {
            "name": self.name,
            "iterations": self.iterations,
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0
        }
        
        print(f"✓ Mean: {result['mean']*1000:.2f}ms")
        return result


class BenchmarkSuite:
    """Collection of benchmarks"""
    
    def __init__(self):
        """Initialize benchmark suite"""
        self.benchmarks = []
        self.results = []
    
    def add(self, name: str, func: Callable, iterations: int = 10):
        """Add a benchmark"""
        self.benchmarks.append(Benchmark(name, func, iterations))
    
    def run_all(self) -> List[Dict[str, Any]]:
        """Run all benchmarks"""
        print("\n" + "="*60)
        print("AI-Squad Performance Benchmark Suite")
        print("="*60 + "\n")
        
        self.results = []
        for benchmark in self.benchmarks:
            result = benchmark.run()
            self.results.append(result)
        
        self._print_summary()
        return self.results
    
    def _print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*60)
        print("Summary")
        print("="*60 + "\n")
        
        print(f"{'Benchmark':<40} {'Mean':<12} {'Median':<12}")
        print("-" * 64)
        
        for result in self.results:
            print(
                f"{result['name']:<40} "
                f"{result['mean']*1000:>10.2f}ms "
                f"{result['median']*1000:>10.2f}ms"
            )
        
        print()


def setup_test_environment():
    """Setup test environment for benchmarks"""
    temp_dir = Path(tempfile.mkdtemp())
    
    config = Config({
        "project": {"name": "Benchmark", "github_repo": "test", "github_owner": "test"},
        "agents": {"pm": {"enabled": True}, "architect": {"enabled": True}, "engineer": {"enabled": True}},
        "output": {
            "prd_dir": str(temp_dir / "prd"),
            "adr_dir": str(temp_dir / "adr"),
            "specs_dir": str(temp_dir / "specs")
        }
    })
    
    # Create directories
    for dir_name in ["prd", "adr", "specs"]:
        (temp_dir / dir_name).mkdir(exist_ok=True)
    
    # Mock GitHub
    github = Mock(spec=GitHubTool)
    github.get_issue.return_value = {
        "number": 123,
        "title": "Test Issue",
        "body": "Test body",
        "labels": [],
        "state": "open"
    }
    github.update_issue_status.return_value = True
    github.add_labels.return_value = True
    github.add_comment.return_value = True
    github._is_configured.return_value = False  # Use mock mode
    
    return config, github, temp_dir


def cleanup_test_environment(temp_dir: Path):
    """Cleanup test environment"""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def benchmark_agent_initialization():
    """Benchmark agent initialization"""
    config, github, temp_dir = setup_test_environment()
    
    def test():
        pm = ProductManagerAgent(config, sdk=None)
        pm.github = github
    
    suite = BenchmarkSuite()
    suite.add("Agent Initialization", test, iterations=100)
    results = suite.run_all()
    
    cleanup_test_environment(temp_dir)
    return results


def benchmark_status_transitions():
    """Benchmark status transitions"""
    _, github, temp_dir = setup_test_environment()
    
    def test():
        manager = StatusManager(github)
        manager.transition(123, IssueStatus.READY, "pm")
        manager.transition(123, IssueStatus.IN_PROGRESS, "engineer")
        manager.transition(123, IssueStatus.IN_REVIEW, "engineer")
    
    suite = BenchmarkSuite()
    suite.add("Status Transitions (3)", test, iterations=50)
    results = suite.run_all()
    
    cleanup_test_environment(temp_dir)
    return results


def benchmark_agent_communication():
    """Benchmark agent communication"""
    _, github, temp_dir = setup_test_environment()
    
    def test():
        comm = AgentCommunicator(execution_mode="automated", github=github)
        q1 = comm.ask("architect", "pm", "Question 1", {}, 123)
        comm.respond(q1, "Answer 1", "pm")
        q2 = comm.ask("engineer", "architect", "Question 2", {}, 123)
        comm.respond(q2, "Answer 2", "architect")
    
    suite = BenchmarkSuite()
    suite.add("Agent Communication (2 Q&A)", test, iterations=50)
    results = suite.run_all()
    
    cleanup_test_environment(temp_dir)
    return results


def benchmark_persistent_storage():
    """Benchmark persistent storage operations"""
    db_path = Path(tempfile.mktemp(suffix=".db"))
    
    def test():
        storage = PersistentStorage(str(db_path))
        
        # Save messages
        from ai_squad.core.agent_comm import AgentMessage, MessageType
        msg = AgentMessage(
            from_agent="architect",
            to_agent="pm",
            message_type=MessageType.QUESTION,
            content="Test question",
            issue_number=123
        )
        storage.save_message(msg)
        
        # Query messages
        storage.get_messages_for_issue(123)
        
        # Save transition
        from ai_squad.core.status import StatusTransition
        from datetime import datetime
        transition = StatusTransition(
            issue_number=123,
            from_status=IssueStatus.READY,
            to_status=IssueStatus.IN_PROGRESS,
            agent="engineer",
            timestamp=datetime.now()
        )
        storage.save_transition(transition)
        
        # Query transitions
        storage.get_transitions_for_issue(123)
    
    suite = BenchmarkSuite()
    suite.add("Persistent Storage (2 saves + 2 queries)", test, iterations=50)
    results = suite.run_all()
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()
    
    return results


def benchmark_full_workflow():
    """Benchmark full workflow execution"""
    config, github, temp_dir = setup_test_environment()
    
    # Create PRD for prerequisites
    prd_file = temp_dir / "prd" / "PRD-123.md"
    prd_file.write_text("# PRD")
    
    def test():
        # PM execution
        pm = ProductManagerAgent(config, sdk=None)
        pm.github = github
        pm.execute(123)
        
        # Architect execution
        architect = ArchitectAgent(config, sdk=None)
        architect.github = github
        architect.execute(123)
        
        # Status transitions
        manager = StatusManager(github)
        manager.transition(123, IssueStatus.READY, "pm")
        manager.transition(123, IssueStatus.IN_PROGRESS, "engineer")
    
    suite = BenchmarkSuite()
    suite.add("Full Workflow (PM + Architect + Status)", test, iterations=10)
    results = suite.run_all()
    
    cleanup_test_environment(temp_dir)
    return results


def run_all_benchmarks():
    """Run all benchmark suites"""
    print("\n" + "="*60)
    print("AI-Squad Complete Performance Benchmark Suite")
    print("="*60 + "\n")
    
    all_results = []
    
    print("\n### Agent Initialization ###")
    all_results.extend(benchmark_agent_initialization())
    
    print("\n### Status Transitions ###")
    all_results.extend(benchmark_status_transitions())
    
    print("\n### Agent Communication ###")
    all_results.extend(benchmark_agent_communication())
    
    print("\n### Persistent Storage ###")
    all_results.extend(benchmark_persistent_storage())
    
    print("\n### Full Workflow ###")
    all_results.extend(benchmark_full_workflow())
    
    # Overall summary
    print("\n" + "="*60)
    print("Overall Results")
    print("="*60 + "\n")
    
    print(f"{'Benchmark':<45} {'Mean Time':<15}")
    print("-" * 60)
    
    for result in all_results:
        print(f"{result['name']:<45} {result['mean']*1000:>10.2f}ms")
    
    # Calculate totals
    total_time = sum(r['mean'] * r['iterations'] for r in all_results)
    total_iterations = sum(r['iterations'] for r in all_results)
    
    print("\n" + "-" * 60)
    print(f"Total iterations: {total_iterations}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average per operation: {(total_time/total_iterations)*1000:.2f}ms")
    print()
    
    return all_results


def save_benchmark_results(results: List[Dict[str, Any]], output_file: str = "benchmark_results.json"):
    """Save benchmark results to file"""
    import json
    from datetime import datetime
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": results
    }
    
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")


if __name__ == "__main__":
    results = run_all_benchmarks()
    save_benchmark_results(results)
