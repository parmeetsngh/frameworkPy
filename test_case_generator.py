#!/usr/bin/env python3
"""
Test Case Generator

This script generates test cases (without detailed steps) from story requirements
and context information using Azure OpenAI's LLM capabilities.

It reads from story and context folders and generates initial feature files with
test case titles and minimal placeholder steps.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
import re

# Import the framework components
from test_automation_framework import (
    TestAutomationFramework,
    TestCaseGenerator,
    TestScenario,
    TestStep,
    FeatureFile,
    SourceReference,
    GherkinFormatter
)

# Import common utilities
from utils import (
    setup_logging,
    ensure_directory,
    get_llm_api_key,
    add_common_arguments,
    extract_example_steps,
    extract_design_context
)

# Import extended components for LLM
try:
    from framework_extensions import LLMTestCaseGenerator
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    print("Extensions not available. LLM test case generation will not work.")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test Case Generator - Generate test cases (without detailed steps) from documentation"
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

    # Add common arguments using utility function
    parser = add_common_arguments(parser)

    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.3,
        help="Temperature setting for LLM generation (default: 0.3)"
    )

    return parser.parse_args()


class TestCaseOnlyGenerator:
    """Generates test cases (without detailed steps) using LLM"""

    def __init__(self, story_folder, context_folder, output_dir, llm_api_key, llm_model="gpt-4o", llm_temperature=0.3):
        self.story_folder = Path(story_folder)
        self.context_folder = Path(context_folder)
        self.output_dir = Path(output_dir)
        ensure_directory(self.output_dir)
        
        # Set up LLM generator
        if EXTENSIONS_AVAILABLE and llm_api_key:
            self.llm_generator = LLMTestCaseGenerator(
                api_key=llm_api_key,
                model=llm_model,
                temperature=llm_temperature
            )
            logging.info("LLM test case generator initialized successfully")
        else:
            self.llm_generator = None
            logging.warning("LLM generator not available - will use basic test generation")
            
        # Initialize a standard TestCaseGenerator to read the files
        self.case_generator = TestCaseGenerator(story_folder, context_folder)
    
    def generate_test_cases(self):
        """Generate test cases using LLM and existing data"""
        logging.info("Starting test case generation (without detailed steps)...")
        
        # Load source data
        self.case_generator.load_source_data()
        
        # Extract context data for LLM
        context_data = self._prepare_context_data()
        
        # Generate test cases via LLM
        if self.llm_generator:
            test_cases = self._generate_cases_with_llm(context_data)
        else:
            # Fallback to basic generation
            test_cases = self._generate_basic_cases()
        
        # Convert to test scenarios
        test_scenarios = self._convert_to_scenarios(test_cases)
        
        # Format and save to feature files
        formatter = GherkinFormatter()
        feature_files = formatter.create_feature_files(test_scenarios, self.output_dir)
        
        logging.info(f"Test case generation complete. Generated {len(feature_files)} feature files.")
        return feature_files
    
    def _prepare_context_data(self):
        """Prepare context data for LLM"""
        context_data = {
            "requirements": [],
            "scenarios": [],
            "additional_context": ""
        }
        
        # Extract requirements from story data
        story_data = self.case_generator.story_data
        
        # Add story link as additional context
        if story_data.get("input_txt", {}).get("story_link"):
            context_data["additional_context"] += f"Story link: {story_data['input_txt']['story_link']}\n"
            
        # Extract requirements from documents
        for doc in story_data.get("documents", []):
            if doc.get("file_type") in [".docx", ".txt"]:
                if "content" in doc:
                    # Split the content into sentences and find requirement-like statements
                    sentences = re.split(r'[.!?]\s+', doc.get("content", ""))
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in ["must", "should", "shall", "will", "needs to", "required"]):
                            context_data["requirements"].append(sentence.strip())
        
        # Extract existing scenarios from context data
        context_data_obj = self.case_generator.context_data
        
        # Use utility function to extract example steps
        example_steps = extract_example_steps(context_data_obj)
        if example_steps:
            context_data["additional_context"] += "\nExample steps from existing tests:\n" + "\n".join(example_steps[:10])
        
        # Extract scenarios from feature files
        for doc in context_data_obj.get("documents", []):
            if doc.get("file_type") == ".feature":
                for scenario_data in doc.get("scenarios", []):
                    context_data["scenarios"].append(scenario_data.get("name", ""))
            elif doc.get("file_type") in [".xlsx", ".xls"]:
                for test_case in doc.get("test_cases", []):
                    context_data["scenarios"].append(test_case.get("name", ""))
        
        # Use utility function to extract design context
        design_context = extract_design_context(context_data_obj)
        if design_context:
            context_data["additional_context"] += f"\nDesign Context:\n{design_context[:1000]}..."
        
        return context_data
    
    def _generate_cases_with_llm(self, context_data):
        """Generate test cases using LLM"""
        # Customize the prompt for test cases only (without detailed steps)
        custom_prompt = """
        Generate test cases in Gherkin format based on the following requirements and scenarios.
        
        Focus ONLY on creating meaningful test case titles and descriptions. DO NOT create detailed steps.
        Use only placeholder steps (Given a setup, When an action occurs, Then a result is verified).
        
        The test steps will be created in a separate process, so focus on covering all test scenarios
        and edge cases implied by the requirements.
        
        Each test case should:
        1. Have a clear, descriptive name that explains what is being tested
        2. Include appropriate tags to categorize the test
        3. Include minimal placeholder steps (Given/When/Then) without details
        4. Cover positive scenarios, negative scenarios, and edge cases
        
        Format each test case as:
        
        @tag1 @tag2
        Scenario: Descriptive test case name
          Given a basic setup
          When the primary action occurs
          Then the expected result is verified
        """
        
        # Override the prompt
        original_prompt = self.llm_generator.generate_test_cases
        
        # Override the default prompt mechanism with our custom one
        def custom_generate_test_cases(context_data):
            # Extract data from context_data
            requirements = context_data.get("requirements", [])
            scenarios = context_data.get("scenarios", [])
            additional_context = context_data.get("additional_context", "")

            # Construct the prompt
            prompt = f"""
            {custom_prompt}

            Requirements:
            {' '.join(requirements)}

            Scenarios:
            {' '.join(scenarios)}

            Additional Context:
            {additional_context}
            """

            # Call the API
            messages = [
                {"role": "system", "content": "You are a QA automation expert specializing in test case generation."},
                {"role": "user", "content": prompt}
            ]

            try:
                response_content = self.llm_generator.call_azure_openai(messages)
                test_cases = self.llm_generator.extract_test_cases(response_content)
                return test_cases if test_cases else [self.llm_generator._create_fallback_test_case()]
            except Exception as e:
                logging.error(f"Error generating test cases with Azure OpenAI: {e}")
                return [self.llm_generator._create_fallback_test_case()]
                
        # Call our custom implementation
        return custom_generate_test_cases(context_data)
    
    def _generate_basic_cases(self):
        """Generate basic test cases without LLM"""
        # Create basic test cases with generic names based on any requirements found
        basic_cases = []
        
        # Look for any requirements in the story data
        story_data = self.case_generator.story_data
        requirements = []
        
        for doc in story_data.get("documents", []):
            if "content" in doc:
                sentences = re.split(r'[.!?]\s+', doc.get("content", ""))
                for sentence in sentences:
                    if any(keyword in sentence.lower() for keyword in ["must", "should", "shall", "will", "needs to", "required"]):
                        requirements.append(sentence.strip())
        
        # Create a basic case for each requirement, or a default one if none found
        if requirements:
            for i, req in enumerate(requirements[:10]):  # Limit to first 10 to avoid too many
                basic_cases.append({
                    "name": f"Verify requirement: {req[:50]}...",
                    "steps": [
                        {"type": "Given", "description": "a basic setup"},
                        {"type": "When", "description": "the action is performed"},
                        {"type": "Then", "description": "the requirement is verified"}
                    ],
                    "tags": ["automated", "requirement-based"]
                })
        else:
            # Default case if no requirements found
            basic_cases.append({
                "name": "Basic functionality test",
                "steps": [
                    {"type": "Given", "description": "a basic setup"},
                    {"type": "When", "description": "the action is performed"},
                    {"type": "Then", "description": "the expected result is verified"}
                ],
                "tags": ["automated"]
            })
        
        return basic_cases
    
    def _convert_to_scenarios(self, test_cases):
        """Convert LLM-generated test cases to TestScenario objects"""
        scenarios = []
        
        for test_case in test_cases:
            scenario = TestScenario(
                name=test_case["name"],
                tags=test_case.get("tags", ["automated"])
            )
            
            # Add placeholder steps if they don't exist
            if not test_case.get("steps"):
                scenario.steps.append(TestStep(step_type="Given", description="a basic setup"))
                scenario.steps.append(TestStep(step_type="When", description="the action is performed"))
                scenario.steps.append(TestStep(step_type="Then", description="the expected result is verified"))
            else:
                for step in test_case.get("steps", []):
                    scenario.steps.append(TestStep(
                        step_type=step["type"],
                        description=step["description"]
                    ))
            
            # Add a source reference if available
            story_link = self.case_generator.story_data.get("input_txt", {}).get("story_link")
            if story_link:
                scenario.source_references.append(SourceReference(
                    source_type="Story",
                    link=story_link
                ))
            
            scenarios.append(scenario)
        
        return scenarios


def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()

    # Set up logging using the common utility
    logger = setup_logging(args.log_dir, "TestCaseGenerator", "test_case_generation")

    # Ensure output directory exists
    ensure_directory(args.output_dir)

    # Check if LLM API key is available using common utility
    llm_api_key = get_llm_api_key(args.llm_api_key)
    
    if not llm_api_key:
        logger.warning("No LLM API key provided. Will use basic test case generation.")

    # Initialize test case generator
    generator = TestCaseOnlyGenerator(
        args.story_folder,
        args.context_folder,
        args.output_dir,
        llm_api_key,
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


if __name__ == "__main__":
    main()