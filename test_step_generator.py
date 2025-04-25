#!/usr/bin/env python3
"""
Test Step Detail Generator

This module is responsible for generating detailed test steps for existing test cases
that only have high-level steps. It enhances each test step with specific details
on how to execute the step, expected results, and data requirements.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Import framework components
from test_automation_framework import (
    TestAutomationFramework,
    FeatureFileParser,
    FeatureFile,
    TestStep,
    GherkinFormatter
)

# Import utility functions
from utils import (
    setup_logging,
    ensure_directory,
    get_llm_api_key,
    extract_example_steps,
    extract_design_context
)

class TestStepDetailGenerator:
    """
    Generator for enhancing test steps with detailed instructions.
    
    This class takes existing test cases with high-level steps and enhances
    each step with specific implementation details.
    """
    
    def __init__(self, test_cases_dir, reference_dir, output_dir, llm_api_key=None, 
                 llm_model="gpt-4o", temperature=0.5):
        """
        Initialize the Test Step Detail Generator
        
        Args:
            test_cases_dir (str): Directory containing feature files to enhance
                                 or a path to a single feature file
            reference_dir (str): Directory containing reference context files
            output_dir (str): Directory where enhanced feature files will be saved
            llm_api_key (str, optional): API key for the LLM service
            llm_model (str, optional): LLM model to use (default: gpt-4o)
            temperature (float, optional): Temperature setting for LLM generation
        """
        self.logger = logging.getLogger(__name__)
        self.test_cases_dir = test_cases_dir
        self.reference_dir = reference_dir
        self.output_dir = output_dir
        
        self.framework = TestAutomationFramework()
        self.framework.initialize(llm_api_key, llm_model, temperature)
        
        # Create parser for feature files
        self.feature_parser = FeatureFileParser()
        
        # Ensure output directory exists
        ensure_directory(output_dir)
    
    def load_context_data(self):
        """
        Load context data from reference directory
        
        Returns:
            dict: Loaded context data
        """
        self.logger.info(f"Loading context data from {self.reference_dir}")
        context_path = Path(self.reference_dir) / "context"
        
        # Check if context directory exists
        if not context_path.exists():
            self.logger.warning(f"Context directory not found: {context_path}")
            return {}
        
        # Load context input file if it exists
        input_file = context_path / "input.txt"
        context_data = {}
        
        if input_file.exists():
            with open(input_file, "r") as f:
                context_data["description"] = f.read()
        
        # Load documents if they exist
        documents_dir = context_path / "documents"
        if documents_dir.exists():
            context_data["documents"] = []
            for doc_file in documents_dir.glob("*.*"):
                # Simple handling - just read the file content
                try:
                    with open(doc_file, "r") as f:
                        content = f.read()
                    
                    context_data["documents"].append({
                        "file_name": doc_file.name,
                        "file_type": doc_file.suffix,
                        "content": content
                    })
                except Exception as e:
                    self.logger.warning(f"Error loading document {doc_file}: {e}")
        
        return context_data
    
    def enhance_test_steps(self):
        """
        Enhance existing test cases with detailed steps
        
        Returns:
            list: List of enhanced FeatureFile objects
        """
        self.logger.info(f"Enhancing test steps from {self.test_cases_dir}")
        
        enhanced_feature_files = []
        # Check if test_cases_dir is a file or directory
        test_cases_path = Path(self.test_cases_dir)
        
        if test_cases_path.is_file() and test_cases_path.suffix.lower() == '.feature':
            # Process a single feature file
            enhanced_feature_files.append(self._enhance_feature_file(test_cases_path))
        elif test_cases_path.is_dir():
            # Process all feature files in the directory
            for feature_file in test_cases_path.glob('*.feature'):
                enhanced_feature_files.append(self._enhance_feature_file(feature_file))
            
            if not enhanced_feature_files:
                self.logger.warning(f"No feature files found in {self.test_cases_dir}")
        else:
            self.logger.error(f"Invalid test cases path: {self.test_cases_dir}")
            return []
        
        return enhanced_feature_files
    
    def _enhance_feature_file(self, feature_file_path):
        """
        Enhance a single feature file
        
        Args:
            feature_file_path (Path): Path to the feature file
            
        Returns:
            FeatureFile: Enhanced feature file object
        """
        self.logger.info(f"Enhancing feature file: {feature_file_path}")
        
        # Load source feature file
        feature_data = self.feature_parser.parse(str(feature_file_path))
        
        # Load context data
        context_data = self.load_context_data()
        
        # Create a feature file object
        feature_file = FeatureFile(
            name=feature_data["name"],
            description=feature_data["description"],
            scenarios=[]
        )
        
        # Process each scenario
        for scenario_data in feature_data["scenarios"]:
            # Create a new scenario with the same properties
            scenario = feature_file.create_scenario(
                name=scenario_data["name"],
                tags=scenario_data.get("tags", [])
            )
            
            # Add all steps from the source scenario
            for step_data in scenario_data["steps"]:
                step = TestStep(
                    step_type=step_data["type"],
                    description=step_data["description"]
                )
                scenario.steps.append(step)
            
            # Enhance the steps with detailed implementation
            self.enhance_scenario_steps(scenario, context_data)
        
        # Save the enhanced feature file
        output_path = Path(self.output_dir) / f"enhanced_{feature_file_path.name}"
        self.save_feature_file(feature_file, output_path)
        
        return feature_file
    
    def enhance_scenario_steps(self, scenario, context_data):
        """
        Enhance steps in a scenario with detailed implementation
        
        Args:
            scenario: Scenario object to enhance
            context_data (dict): Context data for enhancement
        """
        self.logger.info(f"Enhancing steps for scenario: {scenario.name}")
        
        # Extract example steps from context data if available
        example_steps = extract_example_steps(context_data)
        
        # Extract design context if available
        design_context = extract_design_context(context_data)
        
        # Build prompt for step enhancement
        prompt = self.build_step_enhancement_prompt(scenario, example_steps, design_context)
        
        # Call LLM to generate enhanced steps
        try:
            response = self.framework.call_llm(prompt)
            
            # Parse response to get enhanced steps
            enhanced_steps = self.parse_enhanced_steps(response)
            
            # Replace original steps with enhanced steps
            if enhanced_steps and len(enhanced_steps) > 0:
                scenario.steps = enhanced_steps
            else:
                self.logger.warning(f"Failed to enhance steps for scenario: {scenario.name}")
        
        except Exception as e:
            self.logger.error(f"Error enhancing steps for scenario {scenario.name}: {e}")
    
    def build_step_enhancement_prompt(self, scenario, example_steps, design_context):
        """
        Build a prompt for step enhancement
        
        Args:
            scenario: Scenario to enhance
            example_steps (list): List of example steps
            design_context (str): Design context for enhancement
            
        Returns:
            str: Generated prompt
        """
        prompt = f"""
        I need to enhance the following test scenario with detailed test steps.
        
        # Test Scenario
        {scenario.name}
        
        # Current High-Level Steps
        {self.format_steps_for_prompt(scenario.steps)}
        
        # Enhancement Task
        Please enhance each high-level step with more detailed sub-steps that explain exactly how to perform the test. 
        Include specific actions, input data, and expected results.
        
        # System Design Context
        {design_context[:2000]}  # Truncate if too long
        
        """
        
        # Add example steps if available
        if example_steps and len(example_steps) > 0:
            prompt += f"""
            # Example Test Steps (for reference)
            {chr(10).join(example_steps[:10])}
            """
        
        prompt += """
        # Response Format
        Please provide the enhanced steps in Gherkin format (Given/When/Then), maintaining the same high-level flow but with more detailed instructions. 
        Include only the steps, no explanations or other text.
        """
        
        return prompt
    
    def format_steps_for_prompt(self, steps):
        """
        Format steps for inclusion in a prompt
        
        Args:
            steps (list): List of TestStep objects
            
        Returns:
            str: Formatted steps text
        """
        return "\n".join([f"{step.step_type} {step.description}" for step in steps])
    
    def parse_enhanced_steps(self, response_text):
        """
        Parse enhanced steps from LLM response
        
        Args:
            response_text (str): Text response from LLM
            
        Returns:
            list: List of enhanced TestStep objects
        """
        enhanced_steps = []
        
        # Simple parsing for Gherkin steps
        for line in response_text.strip().split("\n"):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Look for Gherkin keywords
            keywords = ["Given", "When", "Then", "And", "But"]
            for keyword in keywords:
                if line.startswith(keyword + " "):
                    # Extract the step description
                    description = line[len(keyword) + 1:].strip()
                    step = TestStep(
                        step_type=keyword,
                        description=description
                    )
                    enhanced_steps.append(step)
                    break
        
        return enhanced_steps
    
    def save_feature_file(self, feature_file, output_path):
        """
        Save a feature file to disk
        
        Args:
            feature_file: FeatureFile object to save
            output_path (str or Path): Path where file will be saved
        """
        formatter = GherkinFormatter()
        feature_text = formatter.format_feature(feature_file)
        
        with open(output_path, "w") as f:
            f.write(feature_text)
        
        self.logger.info(f"Saved enhanced feature file to {output_path}")

def main():
    """Main function for test step enhancement"""
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Enhance test cases with detailed steps")
    
    parser.add_argument(
        "--test-cases-dir",
        required=True,
        help="Directory containing feature files or a single feature file to enhance"
    )
    
    parser.add_argument(
        "--reference-dir",
        required=True, 
        help="Directory containing reference files"
    )
    
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where enhanced feature files will be saved"
    )
    
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory where log files will be saved"
    )
    
    parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM service"
    )
    
    parser.add_argument(
        "--llm-model",
        default="gpt-4o",
        help="LLM model to use for test generation"
    )
    
    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.5,
        help="Temperature for LLM generation"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_dir, "test_step_generator", "test_step_generation")
    
    # Ensure output directory exists
    ensure_directory(args.output_dir)
    
    # Get LLM API key
    llm_api_key = get_llm_api_key(args.llm_api_key)
    
    if not llm_api_key:
        logger.error("No LLM API key provided. Set AZURE_API_KEY environment variable or use --llm-api-key argument.")
        return 1
    
    # Initialize enhancer
    enhancer = TestStepDetailGenerator(
        args.test_cases_dir,
        args.reference_dir,
        args.output_dir,
        llm_api_key,
        args.llm_model,
        args.llm_temperature
    )
    
    # Enhance test steps
    enhanced_feature_files = enhancer.enhance_test_steps()
    
    # Print summary
    print("\n===== Test Step Enhancement Summary =====")
    print(f"Enhanced test steps from {args.test_cases_dir}")
    print(f"Enhanced feature file saved to {args.output_dir}")
    
    for feature_file in enhanced_feature_files:
        scenario_count = len(feature_file.scenarios)
        step_count = sum(len(scenario.steps) for scenario in feature_file.scenarios)
        print(f"Feature: {feature_file.name}")
        print(f"  - {scenario_count} scenarios")
        print(f"  - {step_count} enhanced steps")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())