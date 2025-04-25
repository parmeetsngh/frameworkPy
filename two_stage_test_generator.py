#!/usr/bin/env python3
"""
Two-Stage Test Generation Process

This script coordinates the two-stage test generation process:
1. Generate test cases with minimal placeholder steps
2. Enhance those test cases with detailed steps

The separation of these concerns allows for better quality test cases
and more detailed, specific test steps.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime

# Import the core framework
from test_automation_framework import (
    TestCaseGenerator,
    FeatureFileParser,
    FeatureFile,
    TestScenario,
    TestStep
)

# Import the LLM extension
try:
    from framework_extensions import LLMTestCaseGenerator
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    print("Extensions not available. LLM test generation will not work.")


def setup_logging(log_dir):
    """Set up logging configuration"""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"two_stage_test_generation_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger("TwoStageTestGeneration")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Two-Stage Test Generation Process"
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
        "--intermediate-dir",
        default="output/test_cases",
        help="Directory where intermediate test case files will be saved"
    )

    parser.add_argument(
        "--output-dir",
        default="output/features",
        help="Directory where final feature files with detailed steps will be saved"
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved"
    )

    parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service (can also use AZURE_API_KEY env var)"
    )

    parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test generation"
    )

    parser.add_argument(
        "--skip-step-generation",
        action="store_true",
        help="Skip the second stage (step generation)"
    )

    parser.add_argument(
        "--skip-case-generation",
        action="store_true",
        help="Skip the first stage (case generation) and use existing test cases"
    )

    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate a detailed report of the test generation process"
    )

    return parser.parse_args()


def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()

    # Set up logging
    logger = setup_logging(args.log_dir)
    logger.info("Starting two-stage test generation process")

    # Create directories
    Path(args.intermediate_dir).mkdir(exist_ok=True, parents=True)
    Path(args.output_dir).mkdir(exist_ok=True, parents=True)

    # Check if LLM API key is available
    if not args.llm_api_key and "AZURE_API_KEY" in os.environ:
        args.llm_api_key = os.environ["AZURE_API_KEY"]
        logger.info("Using AZURE_API_KEY from environment variables")
    
    # Initialize LLM generator if API key is available
    llm_generator = None
    if EXTENSIONS_AVAILABLE and args.llm_api_key:
        try:
            llm_generator = LLMTestCaseGenerator(
                api_key=args.llm_api_key,
                model=args.llm_model,
                temperature=0.5
            )
            logger.info("LLM generator initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LLM generator: {e}")
            sys.exit(1)
    elif not args.llm_api_key:
        logger.warning("No LLM API key provided. Basic generation will be used.")
        logger.error("LLM API key is required for test generation.")
        sys.exit(1)

    # Create a TestCaseGenerator to access source data
    test_case_generator = TestCaseGenerator(args.story_folder, args.context_folder)
    test_case_generator.load_source_data()
    
    # Prepare context data for LLM
    context_data = {
        "requirements": [],
        "scenarios": [],
        "additional_context": ""
    }
    
    # Extract requirements from the source data
    story_data = test_case_generator.story_data
    for doc in story_data.get("documents", []):
        if "content" in doc:
            context_data["additional_context"] += doc.get("content", "") + "\n\n"
    
    # Add document titles as context
    for doc in story_data.get("documents", []):
        if "file_name" in doc:
            context_data["requirements"].append(f"Document: {doc.get('file_name', '')}")
    
    # Run Stage 1: Test Case Generation (unless skipped)
    if not args.skip_case_generation:
        logger.info("Running Stage 1: Test Case Generation")
        
        # Generate test cases only (without detailed steps)
        test_cases = llm_generator.generate_test_cases_only(context_data)
        
        # Convert to FeatureFile objects and save to intermediate directory
        feature_files = []
        for i, test_cases_batch in enumerate(batch_test_cases(test_cases, 5)):  # 5 test cases per feature file
            feature_name = f"test_cases_batch_{i+1}"
            
            # Create a FeatureFile object
            feature_file = FeatureFile(
                name=feature_name,
                description=f"Test cases batch {i+1} generated in first stage",
                scenarios=convert_to_test_scenarios(test_cases_batch),
                tags=["automated", "first-stage"]
            )
            
            # Save to file
            feature_file.save_to_file(args.intermediate_dir)
            feature_files.append(feature_file)
        
        logger.info(f"Stage 1 complete: Generated {len(test_cases)} test cases in {len(feature_files)} feature files")
    else:
        logger.info("Skipping Stage 1 (test case generation) as requested")
        # Verify that intermediate files exist
        feature_file_paths = list(Path(args.intermediate_dir).glob("**/*.feature"))
        if not feature_file_paths:
            logger.error(f"No feature files found in intermediate directory: {args.intermediate_dir}")
            logger.error("Cannot skip case generation without existing test cases")
            sys.exit(1)

    # Run Stage 2: Test Step Generation (unless skipped)
    if not args.skip_step_generation:
        logger.info("Running Stage 2: Test Step Enhancement")
        
        # Gather feature files from intermediate directory
        feature_file_paths = list(Path(args.intermediate_dir).glob("**/*.feature"))
        
        # Parse feature files to extract test cases
        parser = FeatureFileParser()
        test_cases = []
        
        for file_path in feature_file_paths:
            feature_data = parser.parse(str(file_path))
            for scenario_data in feature_data.get("scenarios", []):
                test_case = {
                    "name": scenario_data["name"],
                    "steps": [
                        {
                            "type": step["type"],
                            "description": step["description"]
                        } for step in scenario_data.get("steps", [])
                    ],
                    "tags": scenario_data.get("tags", [])
                }
                test_cases.append(test_case)
        
        # Prepare reference data for step enhancement
        reference_data = {
            "example_steps": extract_example_steps(test_case_generator.context_data),
            "design_context": extract_design_context(test_case_generator.context_data),
            "data_examples": extract_data_examples(test_case_generator.context_data)
        }
        
        # Enhance test steps
        enhanced_test_cases = llm_generator.enhance_test_steps(test_cases, reference_data)
        
        # Convert to FeatureFile objects and save to output directory
        enhanced_feature_files = []
        for i, test_cases_batch in enumerate(batch_test_cases(enhanced_test_cases, 5)):
            feature_name = f"enhanced_test_cases_{i+1}"
            
            # Create a FeatureFile object
            feature_file = FeatureFile(
                name=feature_name,
                description=f"Enhanced test cases batch {i+1} with detailed steps",
                scenarios=convert_to_test_scenarios(test_cases_batch),
                tags=["automated", "enhanced"]
            )
            
            # Save to file
            feature_file.save_to_file(args.output_dir)
            enhanced_feature_files.append(feature_file)
        
        # Generate report if requested
        if args.generate_report:
            stats = llm_generator.generate_report()
            report = generate_detailed_report(stats, enhanced_feature_files, args)
            report_path = os.path.join(args.output_dir, "generation_report.txt")
            with open(report_path, 'w') as f:
                f.write(report)
            logger.info(f"Generation report saved to {report_path}")
        
        logger.info(f"Stage 2 complete: Enhanced {len(enhanced_test_cases)} test cases in {len(enhanced_feature_files)} feature files")
    else:
        logger.info("Skipping Stage 2 (test step generation) as requested")

    # Print summary
    print("\n===== Two-Stage Test Generation Complete =====")
    print(f"Test cases directory: {args.intermediate_dir}")
    print(f"Final feature files directory: {args.output_dir}")
    print(f"Logs saved to: {args.log_dir}")
    if args.generate_report:
        print(f"Detailed report saved to: {os.path.join(args.output_dir, 'generation_report.txt')}")
    print("\nProcess completed successfully!")


def batch_test_cases(test_cases, batch_size):
    """Split test cases into batches"""
    for i in range(0, len(test_cases), batch_size):
        yield test_cases[i:i + batch_size]


def convert_to_test_scenarios(test_cases):
    """Convert test case dictionaries to TestScenario objects"""
    scenarios = []
    
    for test_case in test_cases:
        scenario = TestScenario(
            name=test_case["name"],
            tags=test_case.get("tags", [])
        )
        
        # Convert steps
        for step_data in test_case.get("steps", []):
            step = TestStep(
                step_type=step_data["type"],
                description=step_data["description"],
                data_reference=step_data.get("data_reference")
            )
            scenario.steps.append(step)
        
        scenarios.append(scenario)
    
    return scenarios


def extract_example_steps(context_data):
    """Extract example steps from context data"""
    example_steps = []
    
    # Look for feature files in context data
    for doc in context_data.get("documents", []):
        if doc.get("file_type") == ".feature":
            for scenario in doc.get("scenarios", []):
                for step in scenario.get("steps", []):
                    example_steps.append(f"{step['type']} {step['description']}")
    
    return example_steps


def extract_design_context(context_data):
    """Extract design context from context data"""
    design_context = ""
    
    # Look for design documents
    for doc in context_data.get("documents", []):
        if doc.get("file_type") in [".docx", ".doc"]:
            design_context += doc.get("content", "") + "\n\n"
    
    return design_context


def extract_data_examples(context_data):
    """Extract data examples from context data"""
    data_examples = []
    
    # Look for Excel documents
    for doc in context_data.get("documents", []):
        if doc.get("file_type") in [".xlsx", ".xls"]:
            for sheet in doc.get("sheets", []):
                for row in sheet.get("data", [])[:5]:  # Take first 5 rows as examples
                    data_examples.append(str(row))
    
    return data_examples


def generate_detailed_report(stats, feature_files, args):
    """Generate a detailed report of the test generation process"""
    report = "=== Two-Stage Test Generation Report ===\n\n"
    
    # Add general statistics
    report += "Generation Statistics:\n"
    report += f"- Total test scenarios: {stats['generated_scenarios']}\n"
    report += f"- Total test steps: {stats['generated_steps']}\n"
    report += f"- Average steps per scenario: {stats['average_steps_per_scenario']:.2f}\n\n"
    
    # Add feature files information
    report += "Generated Feature Files:\n"
    for i, feature in enumerate(feature_files, 1):
        scenarios_count = len(feature.scenarios)
        steps_count = sum(len(scenario.steps) for scenario in feature.scenarios)
        report += f"  {i}. {feature.name}: {scenarios_count} scenarios, {steps_count} steps\n"
    
    # Add configuration information
    report += "\nConfiguration:\n"
    report += f"- Story folder: {args.story_folder}\n"
    report += f"- Context folder: {args.context_folder}\n"
    report += f"- LLM model: {args.llm_model}\n"
    report += f"- Intermediate directory: {args.intermediate_dir}\n"
    report += f"- Output directory: {args.output_dir}\n"
    
    # Add timestamp
    report += f"\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report


if __name__ == "__main__":
    main()