"""
Codebase Search Tool

Searches and analyzes codebase for relevant context.
"""
from pathlib import Path
from typing import Dict, Any, List


class CodebaseSearch:
    """Search and analyze codebase for context"""
    
    def __init__(self):
        """Initialize codebase search"""
        self.root = Path.cwd()
        
    def get_context(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get relevant codebase context for issue
        
        Args:
            issue: GitHub issue details
            
        Returns:
            Dict with codebase context
        """
        context = {
            "similar_files": self._find_similar_files(issue),
            "related_issues": [],
            "architecture_files": self._find_architecture_files(),
            "similar_code": self._find_similar_code(issue),
            "test_patterns": self._find_test_patterns(),
            "ui_components": self._find_ui_components(),
            "design_patterns": self._find_design_patterns(),
            "similar_features": self._find_similar_features(issue),
        }
        
        return context
    
    def _find_similar_files(self, issue: Dict[str, Any]) -> List[str]:
        """Find files similar to issue topic"""
        keywords = self._extract_keywords(issue)
        similar_files = []
        
        # Search for files with matching keywords
        for ext in ['.cs', '.py', '.js', '.ts', '.tsx']:
            for file in self.root.rglob(f'*{ext}'):
                if any(keyword.lower() in file.name.lower() for keyword in keywords):
                    similar_files.append(str(file.relative_to(self.root)))
        
        return similar_files[:10]
    
    def _find_architecture_files(self) -> List[str]:
        """Find architecture-related files"""
        arch_files = []
        
        # Look for common architecture files
        patterns = [
            'docs/adr/*.md',
            'docs/architecture/*.md',
            'docs/specs/*.md',
            '**/ARCHITECTURE.md',
            '**/DESIGN.md',
        ]
        
        for pattern in patterns:
            for file in self.root.glob(pattern):
                arch_files.append(str(file.relative_to(self.root)))
        
        return arch_files
    
    def _find_similar_code(self, issue: Dict[str, Any]) -> List[str]:
        """Find similar code patterns"""
        # Simplified - would use semantic search in production
        keywords = self._extract_keywords(issue)
        similar = []
        
        for file in self.root.rglob('*.cs'):
            try:
                content = file.read_text(encoding='utf-8', errors='ignore')
                if any(keyword.lower() in content.lower() for keyword in keywords):
                    similar.append(f"{file.name}: {keywords[0]} related")
            except (OSError, IOError, UnicodeDecodeError):
                # Skip files that can't be read
                continue
        
        return similar[:5]
    
    def _find_test_patterns(self) -> List[str]:
        """Find test patterns in codebase"""
        test_files = []
        
        for pattern in ['**/tests/**/*.cs', '**/test_*.py', '**/*.test.ts']:
            for file in self.root.glob(pattern):
                test_files.append(str(file.relative_to(self.root)))
        
        return test_files[:5]
    
    def _find_ui_components(self) -> List[str]:
        """Find UI components"""
        components = []
        
        for pattern in ['**/components/**/*.tsx', '**/Components/**/*.cs']:
            for file in self.root.glob(pattern):
                components.append(file.stem)
        
        return components[:10]
    
    def _find_design_patterns(self) -> List[str]:
        """Find design patterns used in codebase"""
        patterns = []
        
        # Common patterns to look for
        pattern_indicators = {
            'Repository Pattern': ['Repository.cs', 'IRepository'],
            'Factory Pattern': ['Factory.cs', 'IFactory'],
            'Strategy Pattern': ['Strategy.cs', 'IStrategy'],
            'Observer Pattern': ['Observer.cs', 'IObserver'],
        }
        
        for pattern_name, indicators in pattern_indicators.items():
            for indicator in indicators:
                if list(self.root.rglob(f'**/*{indicator}*')):
                    patterns.append(pattern_name)
                    break
        
        return patterns
    
    def _find_similar_features(self, _issue: Dict[str, Any]) -> List[str]:
        """Find similar features"""
        # Would use semantic search in production
        return ["Similar feature 1", "Similar feature 2"]
    
    def _extract_keywords(self, issue: Dict[str, Any]) -> List[str]:
        """Extract keywords from issue"""
        title = issue.get("title", "")
        body = issue.get("body", "")
        
        # Simple keyword extraction
        text = f"{title} {body}".lower()
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = [w for w in text.split() if w not in common_words and len(w) > 3]
        
        return words[:5]

    def extract_keywords(self, issue: Dict[str, Any]) -> List[str]:
        """Public wrapper for keyword extraction."""
        return self._extract_keywords(issue)
