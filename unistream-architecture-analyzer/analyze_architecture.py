#!/usr/bin/env python3
"""
Unistream Architecture Analyzer
Maps command flows, builds dependency graphs, suggests abstractions.
"""

import ast
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import yaml


@dataclass
class Module:
    """Represents a Python module in the codebase."""
    path: Path
    name: str
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    line_count: int = 0
    layer: Optional[str] = None


@dataclass
class ArchitectureViolation:
    """Represents a violation of architecture rules."""
    severity: str
    rule: str
    file_path: str
    message: str
    suggestion: str = ""

    def __str__(self):
        color_map = {"ERROR": "\033[91m", "WARNING": "\033[93m", "INFO": "\033[94m"}
        color = color_map.get(self.severity, "")
        reset = "\033[0m"

        output = f"{color}[{self.severity}]{reset} {self.rule}\n"
        output += f"  File: {self.file_path}\n"
        output += f"  {self.message}\n"
        if self.suggestion:
            output += f"  Fix: {self.suggestion}\n"
        return output


class ArchitectureAnalyzer:
    def __init__(self, rules_path: Path):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)

        self.modules: Dict[str, Module] = {}
        self.violations: List[ArchitectureViolation] = []
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)

    def analyze_directory(self, directory: Path):
        """Analyze all Python files in directory."""
        print(f"Analyzing architecture of {directory}...\n")

        # Find all Python files
        python_files = list(directory.glob('**/*.py'))

        # Filter excluded
        excluded = ['.git', '__pycache__', 'venv', 'cache']
        python_files = [f for f in python_files if not any(ex in str(f) for ex in excluded)]

        print(f"Found {len(python_files)} Python files\n")

        # Parse each file
        for py_file in python_files:
            module = self.parse_module(py_file, directory)
            if module:
                rel_path = str(py_file.relative_to(directory))
                self.modules[rel_path] = module

        # Build dependency graph
        self.build_dependency_graph()

        # Check architecture rules
        self.check_architecture_rules()

        return self.modules, self.dependency_graph, self.violations

    def parse_module(self, file_path: Path, base_dir: Path) -> Optional[Module]:
        """Parse a Python file to extract structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Parse AST
            tree = ast.parse(content)

            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Extract classes and functions
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            # Determine layer
            layer = self.determine_layer(file_path, base_dir)

            rel_path = file_path.relative_to(base_dir)
            module = Module(
                path=file_path,
                name=str(rel_path),
                imports=imports,
                classes=classes,
                functions=functions,
                line_count=len(lines),
                layer=layer
            )

            return module

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return None

    def determine_layer(self, file_path: Path, base_dir: Path) -> Optional[str]:
        """Determine which architectural layer a file belongs to."""
        rel_path = str(file_path.relative_to(base_dir))

        layers_config = self.rules.get('layers', {})
        for layer_name, layer_info in layers_config.items():
            directories = layer_info.get('directories', [])
            for dir_pattern in directories:
                # Simple glob-like matching
                pattern = dir_pattern.replace('**', '.*').replace('*', '[^/]*')
                if re.match(pattern, rel_path):
                    return layer_name

        return None

    def build_dependency_graph(self):
        """Build a graph of module dependencies."""
        for module_name, module in self.modules.items():
            for import_name in module.imports:
                # Try to find matching module in our codebase
                for other_name, other_module in self.modules.items():
                    # Check if import matches this module
                    other_module_path = str(other_module.path.with_suffix('')).replace('/', '.')
                    if import_name in other_module_path or other_module_path.endswith(import_name):
                        self.dependency_graph[module_name].add(other_name)

    def check_architecture_rules(self):
        """Check for violations of architecture rules."""
        # Check layer skipping
        self.check_layer_violations()

        # Check for circular dependencies
        self.check_circular_dependencies()

        # Check file complexity
        self.check_complexity()

        # Check for missing abstractions
        self.check_duplicate_logic()

    def check_layer_violations(self):
        """Check for layer skipping violations."""
        layers_config = self.rules.get('layers', {})

        for module_name, module in self.modules.items():
            if not module.layer:
                continue

            layer_info = layers_config.get(module.layer, {})
            forbidden = layer_info.get('forbidden_imports', [])

            # Check each import
            for import_name in module.imports:
                # Check if this import is forbidden
                for forbidden_pattern in forbidden:
                    pattern = forbidden_pattern.replace('**', '.*').replace('*', '[^.]*')
                    if re.match(pattern, import_name):
                        violation = ArchitectureViolation(
                            severity="ERROR",
                            rule="no_layer_skipping",
                            file_path=module_name,
                            message=f"Layer '{module.layer}' should not import '{import_name}'",
                            suggestion=f"Access through allowed layers instead"
                        )
                        self.violations.append(violation)

    def check_circular_dependencies(self):
        """Detect circular dependencies."""
        def has_path(start: str, end: str, visited: Set[str]) -> bool:
            if start == end:
                return True
            if start in visited:
                return False
            visited.add(start)
            for neighbor in self.dependency_graph.get(start, []):
                if has_path(neighbor, end, visited.copy()):
                    return True
            return False

        checked = set()
        for module_a in self.dependency_graph:
            for module_b in self.dependency_graph[module_a]:
                pair = tuple(sorted([module_a, module_b]))
                if pair in checked:
                    continue
                checked.add(pair)

                # Check if b imports a (circular)
                if has_path(module_b, module_a, set()):
                    violation = ArchitectureViolation(
                        severity="ERROR",
                        rule="no_circular_dependencies",
                        file_path=module_a,
                        message=f"Circular dependency: {module_a} ↔ {module_b}",
                        suggestion="Refactor to remove circular dependency"
                    )
                    self.violations.append(violation)

    def check_complexity(self):
        """Check for overly complex files."""
        thresholds = self.rules.get('complexity_thresholds', {})

        for module_name, module in self.modules.items():
            # Check line count
            if module.line_count > thresholds.get('lines', {}).get('error', 1000):
                violation = ArchitectureViolation(
                    severity="ERROR",
                    rule="single_responsibility",
                    file_path=module_name,
                    message=f"File too large: {module.line_count} lines",
                    suggestion="Consider splitting into smaller modules"
                )
                self.violations.append(violation)
            elif module.line_count > thresholds.get('lines', {}).get('warning', 500):
                violation = ArchitectureViolation(
                    severity="WARNING",
                    rule="single_responsibility",
                    file_path=module_name,
                    message=f"File is large: {module.line_count} lines",
                    suggestion="Consider refactoring"
                )
                self.violations.append(violation)

            # Check method count
            method_count = len(module.functions)
            if method_count > thresholds.get('methods', {}).get('error', 30):
                violation = ArchitectureViolation(
                    severity="ERROR",
                    rule="single_responsibility",
                    file_path=module_name,
                    message=f"Too many methods: {method_count}",
                    suggestion="Split into multiple classes"
                )
                self.violations.append(violation)

    def check_duplicate_logic(self):
        """Check for duplicate logic patterns that should be abstracted."""
        indicators = self.rules.get('abstraction_indicators', {}).get('duplicate_logic', {})
        patterns = indicators.get('patterns', [])
        threshold = indicators.get('threshold', 3)

        for pattern_info in patterns:
            pattern_name = pattern_info.get('name')
            regex = pattern_info.get('regex')
            suggestion = pattern_info.get('suggestion')

            # Find all files matching this pattern
            matches = []
            for module_name, module in self.modules.items():
                try:
                    with open(module.path, 'r') as f:
                        content = f.read()
                        if re.search(regex, content):
                            matches.append(module_name)
                except:
                    pass

            # If threshold exceeded, suggest abstraction
            if len(matches) >= threshold:
                for match in matches:
                    violation = ArchitectureViolation(
                        severity="INFO",
                        rule="duplicate_logic",
                        file_path=match,
                        message=f"Duplicate pattern '{pattern_name}' found in {len(matches)} files",
                        suggestion=suggestion
                    )
                    self.violations.append(violation)

    def print_dependency_graph(self, start_module: Optional[str] = None, max_depth: int = 3):
        """Print dependency graph as a tree."""
        print("\n" + "="*80)
        print("DEPENDENCY GRAPH")
        print("="*80 + "\n")

        if start_module:
            # Show dependencies of specific module
            if start_module in self.modules:
                self._print_deps_tree(start_module, 0, max_depth, set())
            else:
                print(f"Module '{start_module}' not found")
        else:
            # Show top-level modules (no incoming dependencies)
            roots = [m for m in self.modules if not any(m in deps for deps in self.dependency_graph.values())]
            for root in roots[:10]:  # Limit to first 10
                self._print_deps_tree(root, 0, max_depth, set())

    def _print_deps_tree(self, module: str, depth: int, max_depth: int, visited: Set[str]):
        """Recursively print dependency tree."""
        if depth > max_depth or module in visited:
            return

        visited.add(module)
        indent = "  " * depth
        prefix = "├─ " if depth > 0 else ""

        module_info = self.modules.get(module)
        layer_tag = f"[{module_info.layer}]" if module_info and module_info.layer else ""

        print(f"{indent}{prefix}{module} {layer_tag}")

        # Print dependencies
        for dep in sorted(self.dependency_graph.get(module, [])):
            self._print_deps_tree(dep, depth + 1, max_depth, visited.copy())

    def print_violations(self):
        """Print architecture violations."""
        if not self.violations:
            print("\n\033[92m✓ No architecture violations found!\033[0m\n")
            return 0

        # Group by severity
        errors = [v for v in self.violations if v.severity == "ERROR"]
        warnings = [v for v in self.violations if v.severity == "WARNING"]
        info = [v for v in self.violations if v.severity == "INFO"]

        print("\n" + "="*80)
        print("ARCHITECTURE VIOLATIONS")
        print("="*80 + "\n")

        if errors:
            print(f"\033[91m━━━ ERRORS ({len(errors)}) ━━━\033[0m\n")
            for v in errors:
                print(v)

        if warnings:
            print(f"\033[93m━━━ WARNINGS ({len(warnings)}) ━━━\033[0m\n")
            for v in warnings:
                print(v)

        if info:
            print(f"\033[94m━━━ SUGGESTIONS ({len(info)}) ━━━\033[0m\n")
            for v in info:
                print(v)

        print("="*80)
        print(f"Total: {len(errors)} errors, {len(warnings)} warnings, {len(info)} suggestions")
        print("="*80 + "\n")

        return 1 if errors else 0

    def print_summary(self):
        """Print summary of codebase architecture."""
        print("\n" + "="*80)
        print("ARCHITECTURE SUMMARY")
        print("="*80 + "\n")

        print(f"Total modules: {len(self.modules)}")
        print(f"Total lines: {sum(m.line_count for m in self.modules.values())}")
        print(f"Total dependencies: {sum(len(deps) for deps in self.dependency_graph.values())}\n")

        # Group by layer
        layers = defaultdict(list)
        for module_name, module in self.modules.items():
            if module.layer:
                layers[module.layer].append(module)

        print("Modules by layer:")
        for layer_name, modules in layers.items():
            total_lines = sum(m.line_count for m in modules)
            print(f"  {layer_name}: {len(modules)} modules, {total_lines} lines")

        print()


def main():
    parser = argparse.ArgumentParser(description="Analyze Unistream architecture")
    parser.add_argument('directory', type=Path, help="Directory to analyze")
    parser.add_argument('--deps', help="Show dependencies of specific module")
    parser.add_argument('--check-rules', action='store_true', help="Check architecture rules")
    parser.add_argument('--max-depth', type=int, default=3, help="Max depth for dependency tree")
    parser.add_argument('--rules', type=Path,
                       default=Path(__file__).parent / 'architecture_patterns.yaml',
                       help="Path to architecture rules")

    args = parser.parse_args()

    if not args.directory.exists():
        print(f"Error: Directory {args.directory} does not exist")
        return 1

    # Run analysis
    analyzer = ArchitectureAnalyzer(args.rules)
    analyzer.analyze_directory(args.directory)

    # Print results
    analyzer.print_summary()

    if args.deps:
        analyzer.print_dependency_graph(args.deps, args.max_depth)
    else:
        analyzer.print_dependency_graph(max_depth=2)

    if args.check_rules or not args.deps:
        exit_code = analyzer.print_violations()
        return exit_code

    return 0


if __name__ == '__main__':
    sys.exit(main())
