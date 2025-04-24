#!/usr/bin/env python3
"""
Integrated Test Automation Framework

This script demonstrates how to integrate all the components of the test automation framework
to create a complete solution for generating test cases from documentation.
"""

import os
import sys
import argparse
import logging
import json
import shutil
from pathlib import Path
from datetime import datetime

# Import the framework components
from test_automation_framework import (
    TestAutomationFramework,
    DocumentParser,
    InputTxtParser,
    DocxParser,
    FeatureFileParser,
    ExcelParser
)

# Import extended components
try:
    from framework_extensions import (
        EnhancedDocxParser,
        EnhancedExcelParser,
        NLPTestCaseGenerator,
        TraceabilityReporter
    )

    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    print("Extensions not available. Using base components only.")


def setup_logging(log_dir):
    """Set up logging configuration"""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"test_generation_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger("TestAutomationFramework")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test Automation Framework - Generate test cases from documentation"
    )

    parser.add_argument(
        "--story-folder",
        required=True,
        help="Path to story folder containing Input.txt and Documents"
    )

    parser.add_argument(
        "--context-folder",
        required=True,
        help="Path to context folder containing Input.txt and Documents"
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where generated feature files will be saved"
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved (default: logs)"
    )

    parser.add_argument(
        "--use-nlp",
        action="store_true",
        help="Enable NLP-based test case generation"
    )

    parser.add_argument(
        "--generate-reports",
        action="store_true",
        help="Generate traceability reports"
    )

    parser.add_argument(
        "--config",
        help="Path to configuration file (JSON)"
    )

    return parser.parse_args()


def load_config(config_file):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return {}


def initialize_parsers(enhanced=False):
    """Initialize document parsers"""
    parsers = {
        ".txt": InputTxtParser(),
        ".feature": FeatureFileParser()
    }

    if enhanced and EXTENSIONS_AVAILABLE:
        parsers[".docx"] = EnhancedDocxParser()
        parsers[".doc"] = EnhancedDocxParser()
        parsers[".xlsx"] = EnhancedExcelParser()
        parsers[".xls"] = EnhancedExcelParser()
    else:
        parsers[".docx"] = DocxParser()
        parsers[".doc"] = DocxParser()
        parsers[".xlsx"] = ExcelParser()
        parsers[".xls"] = ExcelParser()

    return parsers


def enhance_framework(framework, options):
    """Enhance the framework with additional capabilities"""
    enhanced_framework = framework

    # Add NLP capabilities if requested
    if options.get("use_nlp", False) and EXTENSIONS_AVAILABLE:
        try:
            nlp_generator = NLPTestCaseGenerator()
            # Attach to framework (this would need to be properly implemented)
            enhanced_framework.nlp_generator = nlp_generator
        except Exception as e:
            logging.error(f"Error initializing NLP generator: {e}")

    return enhanced_framework


def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()

    # Set up logging
    logger = setup_logging(args.log_dir)

    # Load configuration
    config = load_config(args.config) if args.config else {}

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Initialize parsers
    use_enhanced = args.use_nlp or config.get("use_enhanced_parsers", False)
    parsers = initialize_parsers(enhanced=use_enhanced)

    # Create the test automation framework
    framework = TestAutomationFramework(args.story_folder, args.context_folder, args.output_dir)

    # Enhance framework if needed
    if args.use_nlp or args.generate_reports:
        options = {
            "use_nlp": args.use_nlp,
            "generate_reports": args.generate_reports
        }
        framework = enhance_framework(framework, options)

    # Generate test cases
    logger.info("Starting test case generation...")
    feature_files = framework.generate_test_cases()

    # Generate traceability reports if requested
    if args.generate_reports and EXTENSIONS_AVAILABLE:
        try:
            reporter = TraceabilityReporter(args.output_dir)
            traceability_matrix = reporter.generate_traceability_matrix(
                # This would need proper adaptation to work with the actual framework
                [{"name": scenario.name, "steps": [s.description for s in scenario.steps]}
                 for scenario in framework.test_scenarios],
                framework.story_data
            )
            logger.info("Generated traceability reports")
        except Exception as e:
            logger.error(f"Error generating traceability reports: {e}")

    # Print summary
    print("\n===== Test Generation Summary =====")
    print(f"Generated {len(feature_files)} feature files in {args.output_dir}")
    print(f"Logs saved to {args.log_dir}")

    if args.generate_reports:
        print(f"Traceability reports saved to {args.output_dir}")

    print("\nGenerated Feature Files:")
    for i, feature in enumerate(feature_files, 1):
        print(f"  {i}. {feature.name} ({len(feature.scenarios)} scenarios)")


if __name__ == "__main__":
    main()