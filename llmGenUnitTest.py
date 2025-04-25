# test_llm.py
import logging
import os
from framework_extensions import LLMTestCaseGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize the generator with your API key
api_key = os.getenv("AZURE_API_KEY")
generator = LLMTestCaseGenerator(api_key=api_key)
logging.info("LLM Generator initialized successfully!")

# Test with sample data
test_data = {
    "requirements": ["The system must allow users to log in", "Users should be able to reset their password"],
    "scenarios": ["User login with valid credentials", "User attempts to log in with invalid password"],
    "additional_context": "This is a web-based application with standard authentication flows."
}

test_cases = generator.generate_test_cases(test_data)
logging.info(f"Generated {len(test_cases)} test cases")
for idx, tc in enumerate(test_cases, 1):
    logging.info(f"Test Case {idx}: {tc['name']}")
    for step in tc['steps']:
        logging.info(f"  {step['type']} {step['description']}")