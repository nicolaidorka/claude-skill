#!/usr/bin/env python3
"""
Unistream Code Validator
Checks codebase for hardcoded values, unsafe fallbacks, and known bug patterns.
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import yaml


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"


@dataclass
class Finding:
    severity: Severity
    file_path: str
    line_number: int
    rule_name: str
    message: str
    code_snippet: str
    suggestion: str = ""

    def __str__(self):
        color_map = {
            Severity.ERROR: "\033[91m",  # Red
            Severity.WARNING: "\033[93m",  # Yellow
            Severity.INFO: "\033[94m",  # Blue
            Severity.OK: "\033[92m",  # Green
        }
        reset = "\033[0m"
        color = color_map.get(self.severity, "")

        output = f"{color}[{self.severity.value}]{reset} {self.file_path}:{self.line_number}\n"
        output += f"  {self.message}\n"
        output += f"  Code: {self.code_snippet.strip()}\n"
        if self.suggestion:
            output += f"  Fix: {self.suggestion}\n"
        return output


class CodeValidator:
    def __init__(self, rules_path: Path):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)
        self.findings: List[Finding] = []

    def validate_directory(self, directory: Path, check_types: List[str] = None):
        """Validate all Python files in directory."""
        print(f"Scanning {directory}...")

        # Get all Python files
        python_files = []
        for pattern in ['**/*.py']:
            python_files.extend(directory.glob(pattern))

        # Filter excluded directories
        excluded = self.rules.get('global_excludes', {}).get('directories', [])
        python_files = [
            f for f in python_files
            if not any(excl in str(f) for excl in excluded)
        ]

        print(f"Found {len(python_files)} Python files to check\n")

        # Run checks
        for py_file in python_files:
            self.validate_file(py_file, check_types)

        return self.findings

    def validate_file(self, file_path: Path, check_types: List[str] = None):
        """Validate a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return

        # Determine which checks to run
        checks_to_run = []
        if check_types:
            for check_type in check_types:
                if check_type == 'pixel_size':
                    checks_to_run.append('hardcoded_pixel_sizes')
                elif check_type == 'fallbacks':
                    checks_to_run.append('unsafe_fallbacks')
                elif check_type == 'coordinates':
                    checks_to_run.append('coordinate_bugs')
                elif check_type == 'config':
                    checks_to_run.append('hardcoded_config')
                else:
                    checks_to_run.append(check_type)
        else:
            # Run all checks
            checks_to_run = [
                'hardcoded_pixel_sizes',
                'unsafe_fallbacks',
                'coordinate_bugs',
                'hardcoded_config',
                'missing_validation',
                'import_issues',
                'code_quality'
            ]

        # Run each check
        for check_name in checks_to_run:
            if check_name in self.rules:
                self.run_check(file_path, lines, check_name)

    def run_check(self, file_path: Path, lines: List[str], check_name: str):
        """Run a specific validation check."""
        check_config = self.rules[check_name]
        severity = Severity[check_config.get('severity', 'WARNING')]
        patterns = check_config.get('patterns', [])

        # Check if this file should be checked
        if 'files' in check_config:
            file_patterns = check_config['files']
            if not any(pattern in str(file_path) for pattern in file_patterns):
                return

        # Check patterns
        for pattern_config in patterns:
            if isinstance(pattern_config, dict):
                pattern = pattern_config.get('regex')
                message = pattern_config.get('message', 'Pattern match')
                suggestion = pattern_config.get('suggestion', '')
                pattern_severity = Severity[pattern_config.get('severity', severity.value)]
            else:
                pattern = pattern_config
                message = f"Matched pattern: {pattern}"
                suggestion = ""
                pattern_severity = severity

            # Check each line
            for line_num, line in enumerate(lines, start=1):
                if re.search(pattern, line):
                    # Check if this is an allowed context
                    if self.is_allowed_context(file_path, line, lines, line_num, check_config):
                        continue

                    # Add finding
                    finding = Finding(
                        severity=pattern_severity,
                        file_path=str(file_path.relative_to(file_path.parents[len(file_path.parts) - 1])),
                        line_number=line_num,
                        rule_name=check_name,
                        message=message,
                        code_snippet=line.strip(),
                        suggestion=suggestion
                    )
                    self.findings.append(finding)

    def is_allowed_context(self, file_path: Path, line: str, all_lines: List[str],
                           line_num: int, check_config: Dict) -> bool:
        """Check if a match is in an allowed context (exception)."""
        allowed = check_config.get('allowed_contexts', [])

        for context in allowed:
            context_pattern = context.get('pattern')

            # Check if in tests/ directory
            if context_pattern == 'tests/' and 'tests/' in str(file_path):
                return True

            # Check if line has comment indicating allowed usage
            if context_pattern in line:
                return True

            # Check surrounding lines for context
            context_lines = check_config.get('context_lines', 2)
            start = max(0, line_num - context_lines - 1)
            end = min(len(all_lines), line_num + context_lines)
            context_text = ''.join(all_lines[start:end])

            if context_pattern in context_text:
                return True

        return False

    def print_summary(self):
        """Print summary of findings."""
        if not self.findings:
            print("\033[92m✓ No issues found!\033[0m\n")
            return

        # Group by severity
        errors = [f for f in self.findings if f.severity == Severity.ERROR]
        warnings = [f for f in self.findings if f.severity == Severity.WARNING]
        info = [f for f in self.findings if f.severity == Severity.INFO]

        print("\n" + "="*80)
        print("VALIDATION RESULTS")
        print("="*80 + "\n")

        # Print errors first
        if errors:
            print(f"\n\033[91m━━━ ERRORS ({len(errors)}) ━━━\033[0m\n")
            for finding in errors:
                print(finding)

        # Then warnings
        if warnings:
            print(f"\n\033[93m━━━ WARNINGS ({len(warnings)}) ━━━\033[0m\n")
            for finding in warnings:
                print(finding)

        # Then info
        if info:
            print(f"\n\033[94m━━━ INFO ({len(info)}) ━━━\033[0m\n")
            for finding in info:
                print(finding)

        # Summary
        print("="*80)
        print(f"Total: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")
        print("="*80 + "\n")

        # Return exit code
        return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate Unistream codebase for common issues"
    )
    parser.add_argument(
        'directory',
        type=Path,
        help="Directory to validate"
    )
    parser.add_argument(
        '--check',
        action='append',
        help="Specific check to run (can specify multiple times)"
    )
    parser.add_argument(
        '--rules',
        type=Path,
        default=Path(__file__).parent / 'validation_rules.yaml',
        help="Path to validation rules YAML"
    )

    args = parser.parse_args()

    if not args.directory.exists():
        print(f"Error: Directory {args.directory} does not exist")
        return 1

    if not args.rules.exists():
        print(f"Error: Rules file {args.rules} does not exist")
        return 1

    # Run validation
    validator = CodeValidator(args.rules)
    validator.validate_directory(args.directory, args.check)
    exit_code = validator.print_summary()

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
