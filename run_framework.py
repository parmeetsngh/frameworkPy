import os
import logging
from test_automation_framework import TestAutomationFramework

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='framework_execution.log'
)


def main():
    # Define input and output paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    story_folder = os.path.join(script_dir, "input", "story")
    context_folder = os.path.join(script_dir, "input", "context")
    output_dir = os.path.join(script_dir, "output", "features")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize and run the framework
    framework = TestAutomationFramework(story_folder, context_folder, output_dir)
    feature_files = framework.generate_test_cases()

    print(f"Test generation complete!")
    print(f"Generated {len(feature_files)} feature files in {output_dir}")

    # Print summary of each feature file
    for i, feature in enumerate(feature_files, 1):
        print(f"\nFeature {i}: {feature.name}")
        print(f"  Description: {feature.description}")
        print(f"  Tags: {', '.join(feature.tags)}")
        print(f"  Scenarios: {len(feature.scenarios)}")


if __name__ == "__main__":
    main()