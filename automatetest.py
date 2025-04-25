#!/usr/bin/env python3
"""
AutomateTest - Unified CLI for Test Automation Framework

This script provides a single command-line interface for all the framework operations:
- test-case-generation (without detailed steps)
- test-step-generation (enhancing existing test cases with detailed steps)
- two-stage-generation (combined process)
- report-generation (create traceability reports)

Usage:
    python automatetest.py <command> [options]

For help on specific commands:
    python automatetest.py <command> --help
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Import the framework components
from test_automation_framework import (
    TestAutomationFramework,
    FeatureFileParser,  # Changed from GherkinParser
    TestStep,
    FeatureFile,
    GherkinFormatter
)

from test_case_generator import TestCaseOnlyGenerator
from test_step_generator import TestStepDetailGenerator

# Import integrated solution for combined operations
from integrated_solution import setup_logging
from two_stage_test_generator import TwoStageTestGenerator

def setup_parser():
    """Set up command-line argument parser with subcommands"""
    # Main parser
    parser = argparse.ArgumentParser(
        description="AutomateTest - Unified CLI for Test Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add version
    parser.add_argument('--version', action='version', version='Test Automation Framework v1.0.0')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # --- Test Case Generation Command ---
    test_case_parser = subparsers.add_parser(
        'generate-cases',
        help='Generate test cases without detailed steps'
    )
    
    test_case_parser.add_argument(
        "--story-folder",
        required=True,
        help="Path to story folder containing Input.txt and Documents"
    )
    
    test_case_parser.add_argument(
        "--context-folder",
        required=True,
        help="Path to context folder containing Input.txt and Documents"
    )
    
    test_case_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where generated feature files will be saved"
    )
    
    test_case_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved (default: logs)"
    )
    
    test_case_parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service"
    )
    
    test_case_parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test generation (default: gpt-4o)"
    )
    
    test_case_parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.3,
        help="Temperature setting for LLM generation (default: 0.3)"
    )
    
    # --- Test Step Generation Command ---
    test_step_parser = subparsers.add_parser(
        'enhance-steps',
        help='Enhance existing test cases with detailed steps'
    )
    
    test_step_parser.add_argument(
        "--test-cases-dir",
        required=True,
        help="Directory containing feature files with test cases"
    )
    
    test_step_parser.add_argument(
        "--reference-dir",
        required=True,
        help="Directory containing reference files"
    )
    
    test_step_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where enhanced feature files will be saved"
    )
    
    test_step_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved (default: logs)"
    )
    
    test_step_parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service"
    )
    
    test_step_parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test step generation (default: gpt-4o)"
    )
    
    test_step_parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.5,
        help="Temperature setting for LLM generation (default: 0.5)"
    )
    
    # --- Two Stage Test Generation Command ---
    two_stage_parser = subparsers.add_parser(
        'two-stage',
        help='Complete two-stage test generation (cases + steps)'
    )
    
    two_stage_parser.add_argument(
        "--story-folder",
        required=True,
        help="Path to story folder containing Input.txt and Documents"
    )
    
    two_stage_parser.add_argument(
        "--context-folder",
        required=True,
        help="Path to context folder containing Input.txt and Documents"
    )
    
    two_stage_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where generated feature files will be saved"
    )
    
    two_stage_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved (default: logs)"
    )
    
    two_stage_parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service"
    )
    
    two_stage_parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test generation (default: gpt-4o)"
    )
    
    two_stage_parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.4,
        help="Temperature setting for LLM generation (default: 0.4)"
    )
    
    two_stage_parser.add_argument(
        "--skip-traceability",
        action="store_true",
        help="Skip generating traceability reports"
    )
    
    # --- Report Generation Command ---
    report_parser = subparsers.add_parser(
        'generate-reports',
        help='Generate traceability reports from existing test cases'
    )
    
    report_parser.add_argument(
        "--test-cases-dir",
        required=True,
        help="Directory containing feature files with test cases"
    )
    
    report_parser.add_argument(
        "--story-folder",
        required=True,
        help="Path to story folder containing Input.txt and Documents"
    )
    
    report_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where reports will be saved"
    )
    
    report_parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved (default: logs)"
    )
    
    return parser

def command_generate_cases(args):
    """Execute the generate-cases command"""
    # Set up logging
    logger = setup_logging(args.log_dir, "test_case_generation")
    
    logger.info("Starting test case generation")
    
    # Check if LLM API key is available
    if not args.llm_api_key and "AZURE_API_KEY" in os.environ:
        args.llm_api_key = os.environ["AZURE_API_KEY"]
        logger.info("Using AZURE_API_KEY from environment variables")
    
    # Initialize test case generator
    generator = TestCaseOnlyGenerator(
        args.story_folder,
        args.context_folder,
        args.output_dir,
        args.llm_api_key,
        args.llm_model,
        args.llm_temperature
    )
    
    # Generate test cases
    feature_files = generator.generate_test_cases()
    
    # Print summary
    print("\n===== Test Case Generation Summary =====")
    print(f"Generated {len(feature_files)} feature files in {args.output_dir}")
    print(f"Logs saved to {args.log_dir}")
    
    print("\nGenerated Feature Files (test cases only):")
    for i, feature in enumerate(feature_files, 1):
        print(f"  {i}. {feature.name} ({len(feature.scenarios)} test cases)")
    
    return 0

def command_enhance_steps(args):
    """Execute the enhance-steps command"""
    # Set up logging
    logger = setup_logging(args.log_dir, "test_step_generation")
    
    logger.info("Starting test step enhancement")
    
    # Check if LLM API key is available
    if not args.llm_api_key and "AZURE_API_KEY" in os.environ:
        args.llm_api_key = os.environ["AZURE_API_KEY"]
        logger.info("Using AZURE_API_KEY from environment variables")
    
    # Initialize test step enhancer
    enhancer = TestStepDetailGenerator(
        args.test_cases_dir,
        args.reference_dir,
        args.output_dir,
        args.llm_api_key,
        args.llm_model,
        args.llm_temperature
    )
    
    # Enhance test steps
    enhanced_feature_files = enhancer.enhance_test_steps()
    
    # Print summary
    print("\n===== Test Step Enhancement Summary =====")
    print(f"Enhanced {len(enhanced_feature_files)} feature files in {args.output_dir}")
    print(f"Logs saved to {args.log_dir}")
    
    print("\nEnhanced Feature Files (with detailed steps):")
    for i, feature in enumerate(enhanced_feature_files, 1):
        scenarios_count = len(feature.scenarios)
        steps_count = sum(len(scenario.steps) for scenario in feature.scenarios)
        print(f"  {i}. {feature.name} ({scenarios_count} test cases, {steps_count} steps)")
    
    return 0

def command_two_stage(args):
    """Execute the two-stage command"""
    # Set up logging
    logger = setup_logging(args.log_dir, "two_stage_test_generation")
    
    logger.info("Starting two-stage test generation")
    
    # Check if LLM API key is available
    if not args.llm_api_key and "AZURE_API_KEY" in os.environ:
        args.llm_api_key = os.environ["AZURE_API_KEY"]
        logger.info("Using AZURE_API_KEY from environment variables")
    
    # Initialize two-stage generator
    generator = TwoStageTestGenerator(
        args.story_folder,
        args.context_folder,
        args.output_dir,
        args.llm_api_key,
        args.llm_model,
        args.llm_temperature,
        generate_traceability=(not args.skip_traceability)
    )
    
    # Generate test cases and steps
    feature_files, traceability_report = generator.generate_test_cases()
    
    # Print summary
    print("\n===== Two-Stage Test Generation Summary =====")
    print(f"Generated {len(feature_files)} feature files in {args.output_dir}")
    print(f"Logs saved to {args.log_dir}")
    
    if traceability_report and not args.skip_traceability:
        print(f"Traceability report generated in {args.output_dir}")
    
    print("\nGenerated Feature Files (with detailed steps):")
    for i, feature in enumerate(feature_files, 1):
        scenarios_count = len(feature.scenarios)
        steps_count = sum(len(scenario.steps) for scenario in feature.scenarios)
        print(f"  {i}. {feature.name} ({scenarios_count} test cases, {steps_count} steps)")
    
    return 0

def command_generate_reports(args):
    """Execute the generate-reports command"""
    from framework_extensions import TraceabilityReporter
    from test_automation_framework import TestCaseGenerator, FeatureFileParser
    import json
    
    # Set up logging
    logger = setup_logging(args.log_dir, "report_generation")
    
    logger.info("Starting report generation")
    
    # Initialize parsers
    feature_parser = FeatureFileParser()
    
    # Create test case generator to access story data
    test_case_generator = TestCaseGenerator(args.story_folder, args.context_folder)
    test_case_generator.load_source_data()
    
    # Load test scenarios from feature files
    scenarios = []
    feature_files = list(Path(args.test_cases_dir).glob("**/*.feature"))
    
    for feature_file_path in feature_files:
        try:
            feature_data = feature_parser.parse(str(feature_file_path))
            for scenario in feature_data.get("scenarios", []):
                scenarios.append({
                    "name": scenario["name"],
                    "steps": [{"description": step["description"]} for step in scenario.get("steps", [])]
                })
        except Exception as e:
            logger.error(f"Error parsing feature file {feature_file_path}: {e}")
    
    # Generate traceability matrix
    reporter = TraceabilityReporter(args.output_dir)
    traceability_matrix = reporter.generate_traceability_matrix(
        scenarios,
        test_case_generator.story_data
    )
    
    # Print summary
    print("\n===== Report Generation Summary =====")
    print(f"Generated traceability reports in {args.output_dir}")
    print(f"Logs saved to {args.log_dir}")
    
    # Print coverage statistics
    coverage_count = 0
    for scenario_name, covered_reqs in traceability_matrix.get("coverage", {}).items():
        if covered_reqs:
            coverage_count += 1
    
    total_scenarios = len(traceability_matrix.get("test_scenarios", []))
    total_requirements = len(traceability_matrix.get("requirements", {}))
    
    if total_scenarios > 0:
        coverage_percent = (coverage_count / total_scenarios) * 100
        print(f"\nRequirements Coverage: {coverage_percent:.1f}% ({coverage_count}/{total_scenarios} scenarios)")
    
    print(f"Total Requirements: {total_requirements}")
    print(f"Total Test Scenarios: {total_scenarios}")
    
    return 0

def main():
    """Main entry point"""
    # Setup argument parser
    parser = setup_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is specified, show help
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute the appropriate command
    if args.command == 'generate-cases':
        return command_generate_cases(args)
    elif args.command == 'enhance-steps':
        return command_enhance_steps(args)
    elif args.command == 'two-stage':
        return command_two_stage(args)
    elif args.command == 'generate-reports':
        return command_generate_reports(args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())