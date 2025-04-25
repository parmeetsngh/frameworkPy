#!/usr/bin/env python3
"""
Common Utilities for Test Automation Framework

This module contains shared utility functions used across the test automation framework
to reduce code duplication and improve maintainability.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir, logger_name, log_prefix="test_generation"):
    """
    Set up logging configuration with standardized format
    
    Args:
        log_dir (str): Directory where log files will be saved
        logger_name (str): Name of the logger
        log_prefix (str): Prefix for the log file name
        
    Returns:
        logging.Logger: Configured logger object
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{log_prefix}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(logger_name)


def ensure_directory(directory_path):
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        directory_path (str): Path to directory
        
    Returns:
        Path: Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(exist_ok=True, parents=True)
    return path


def get_llm_api_key(provided_key=None, env_var_name="AZURE_API_KEY"):
    """
    Get LLM API key from provided argument or environment variable
    
    Args:
        provided_key (str, optional): API key provided as an argument
        env_var_name (str, optional): Name of environment variable containing the API key
        
    Returns:
        str: API key or None if not available
    """
    if provided_key:
        return provided_key
    
    return os.environ.get(env_var_name)


def batch_items(items, batch_size):
    """
    Split items into batches of specified size
    
    Args:
        items (list): List of items to batch
        batch_size (int): Size of each batch
        
    Yields:
        list: Batch of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def extract_example_steps(context_data):
    """
    Extract example steps from context data
    
    Args:
        context_data (dict): Context data containing documents
        
    Returns:
        list: List of example steps
    """
    example_steps = []
    
    # Look for feature files in context data
    for doc in context_data.get("documents", []):
        if doc.get("file_type") == ".feature":
            for scenario in doc.get("scenarios", []):
                for step in scenario.get("steps", []):
                    example_steps.append(f"{step['type']} {step['description']}")
    
    return example_steps


def extract_design_context(context_data):
    """
    Extract design context from context data
    
    Args:
        context_data (dict): Context data containing documents
        
    Returns:
        str: Design context text
    """
    design_context = ""
    
    # Look for design documents
    for doc in context_data.get("documents", []):
        if doc.get("file_type") in [".docx", ".doc"]:
            design_context += doc.get("content", "") + "\n\n"
    
    return design_context


def extract_data_examples(context_data):
    """
    Extract data examples from context data
    
    Args:
        context_data (dict): Context data containing documents
        
    Returns:
        list: List of data examples
    """
    data_examples = []
    
    # Look for Excel documents
    for doc in context_data.get("documents", []):
        if doc.get("file_type") in [".xlsx", ".xls"]:
            for sheet in doc.get("sheets", []):
                for row in sheet.get("data", [])[:5]:  # Take first 5 rows as examples
                    data_examples.append(str(row))
    
    return data_examples


def add_common_arguments(parser):
    """
    Add common command line arguments to an argument parser
    
    Args:
        parser (argparse.ArgumentParser): Argument parser to add arguments to
        
    Returns:
        argparse.ArgumentParser: Updated parser
    """
    # Common directories
    parser.add_argument(
        "--output-dir",
        default="output/features",
        help="Directory where feature files will be saved"
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved"
    )

    # LLM parameters
    parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service (can also use AZURE_API_KEY env var)"
    )

    parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test generation"
    )

    # Reporting
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate a detailed report of the test generation process"
    )
    
    return parser


def generate_report(stats, feature_files, args):
    """
    Generate a detailed report of the test generation process
    
    Args:
        stats (dict): Statistics about the test generation
        feature_files (list): List of generated feature files
        args (argparse.Namespace): Command line arguments
        
    Returns:
        str: Report text
    """
    report = "=== Test Generation Report ===\n\n"
    
    # Add general statistics
    report += "Generation Statistics:\n"
    report += f"- Total test scenarios: {stats['generated_scenarios']}\n"
    report += f"- Total test steps: {stats['generated_steps']}\n"
    if stats.get('generated_scenarios', 0) > 0:
        report += f"- Average steps per scenario: {stats['average_steps_per_scenario']:.2f}\n\n"
    
    # Add feature files information
    report += "Generated Feature Files:\n"
    for i, feature in enumerate(feature_files, 1):
        scenarios_count = len(feature.scenarios)
        steps_count = sum(len(scenario.steps) for scenario in feature.scenarios)
        report += f"  {i}. {feature.name}: {scenarios_count} scenarios, {steps_count} steps\n"
    
    # Add configuration information
    report += "\nConfiguration:\n"
    for arg, value in vars(args).items():
        if arg not in ['func']:  # Skip function references
            report += f"- {arg}: {value}\n"
    
    # Add timestamp
    report += f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report


def convert_to_test_scenarios(test_cases, test_scenario_class):
    """
    Convert test case dictionaries to TestScenario objects
    
    Args:
        test_cases (list): List of test case dictionaries
        test_scenario_class (class): TestScenario class to use
        
    Returns:
        list: List of TestScenario objects
    """
    scenarios = []
    
    for test_case in test_cases:
        scenario = test_scenario_class(
            name=test_case["name"],
            tags=test_case.get("tags", [])
        )
        
        # Convert steps
        for step_data in test_case.get("steps", []):
            step = test_scenario_class.step_class(
                step_type=step_data["type"],
                description=step_data["description"],
                data_reference=step_data.get("data_reference")
            )
            scenario.steps.append(step)
        
        scenarios.append(scenario)
    
    return scenarios