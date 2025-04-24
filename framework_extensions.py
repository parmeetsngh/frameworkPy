"""
Extensions for the Test Automation Framework that provide:
1. Better document parsing (using libraries)
2. NLP-based test case generation
3. Traceability reporting
"""

import re
import json
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path
import pandas as pd
import requests

# Note: These imports would need to be installed in a real implementation
# pip install python-docx pandas openpyxl nltk spacy gensim

try:
    import docx
    import pandas as pd
    import nltk
    import spacy
    from gensim.summarization import keywords

    # Download required NLTK data
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)

    # Load spaCy model
    nlp = spacy.load('en_core_web_sm')

    LIBRARIES_LOADED = True
except ImportError:
    LIBRARIES_LOADED = False
    logging.warning("Some libraries couldn't be imported. Advanced features will be disabled.")


class EnhancedDocxParser:
    """Enhanced parser for Word documents using python-docx"""

    def parse(self, file_path: str) -> Dict:
        if not LIBRARIES_LOADED:
            logging.warning("python-docx not available. Using basic parsing.")
            return {"content": f"Content from {file_path}", "sections": []}

        try:
            doc = docx.Document(file_path)

            # Extract document structure
            result = {
                "content": "",
                "sections": [],
                "headings": [],
                "tables": []
            }

            # Process paragraphs
            current_section = None
            for para in doc.paragraphs:
                # Add paragraph text to content
                result["content"] += para.text + "\n"

                # Check if this is a heading
                if para.style.name.startswith('Heading'):
                    heading_level = int(para.style.name.replace('Heading ', ''))
                    result["headings"].append({
                        "level": heading_level,
                        "text": para.text
                    })

                    # Create a new section
                    current_section = {
                        "heading": para.text,
                        "level": heading_level,
                        "content": ""
                    }
                    result["sections"].append(current_section)
                elif current_section:
                    current_section["content"] += para.text + "\n"

            # Process tables
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)

                result["tables"].append(table_data)

            return result

        except Exception as e:
            logging.error(f"Error parsing DOCX file {file_path}: {e}")
            return {"error": str(e)}


class EnhancedExcelParser:
    """Enhanced parser for Excel files using pandas"""

    def parse(self, file_path: str) -> Dict:
        if not LIBRARIES_LOADED:
            logging.warning("pandas not available. Using basic parsing.")
            return {"sheets": [{"name": "Sheet1", "data": [["Dummy data"]]}]}

        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            result = {
                "file_path": file_path,
                "sheets": []
            }

            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name)

                # Convert dataframe to dict for easier processing
                sheet_data = {
                    "name": sheet_name,
                    "headers": list(df.columns),
                    "data": df.to_dict(orient='records')
                }

                # Extract test cases if this looks like a test case sheet
                if any(col.lower() in ["test case", "test_case", "testcase", "tc_id", "test id"]
                       for col in df.columns):
                    sheet_data["test_cases"] = self._extract_test_cases(df)

                result["sheets"].append(sheet_data)

            return result

        except Exception as e:
            logging.error(f"Error parsing Excel file {file_path}: {e}")
            return {"error": str(e)}

    def _extract_test_cases(self, df: pd.DataFrame) -> List[Dict]:
        """Extract test cases from a dataframe"""
        test_cases = []

        # Try to identify key columns
        tc_id_col = self._find_column(df, ["test case id", "tc_id", "test id", "testcase id"])
        tc_name_col = self._find_column(df, ["test case name", "tc_name", "test name", "name", "summary"])
        tc_desc_col = self._find_column(df, ["description", "test description", "tc_desc"])
        tc_steps_col = self._find_column(df, ["steps", "test steps", "tc_steps"])
        tc_expected_col = self._find_column(df, ["expected results", "expected", "expectations"])

        # Process each row
        for _, row in df.iterrows():
            test_case = {}

            if tc_id_col:
                test_case["id"] = str(row[tc_id_col])

            if tc_name_col:
                test_case["name"] = str(row[tc_name_col])
            elif "id" in test_case:
                test_case["name"] = f"Test Case {test_case['id']}"
            else:
                test_case["name"] = "Unnamed Test Case"

            if tc_desc_col:
                test_case["description"] = str(row[tc_desc_col])

            # Extract steps
            if tc_steps_col:
                steps_text = str(row[tc_steps_col])
                # Try to split steps if they're in a numbered format
                if re.search(r'^\d+\.', steps_text):
                    steps = re.split(r'\d+\.', steps_text)
                    # Remove empty entries and strip whitespace
                    test_case["steps"] = [step.strip() for step in steps if step.strip()]
                else:
                    # Split by newlines if no numbering is found
                    steps = steps_text.split('\n')
                    test_case["steps"] = [step.strip() for step in steps if step.strip()]

            # Extract expected results
            if tc_expected_col:
                expected_text = str(row[tc_expected_col])
                if re.search(r'^\d+\.', expected_text):
                    expected = re.split(r'\d+\.', expected_text)
                    test_case["expected_results"] = [result.strip() for result in expected if result.strip()]
                else:
                    expected = expected_text.split('\n')
                    test_case["expected_results"] = [result.strip() for result in expected if result.strip()]

            test_cases.append(test_case)

        return test_cases

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find a column in the dataframe based on possible names"""
        for col in df.columns:
            if col.lower() in possible_names:
                return col
        return None


class NLPTestCaseGenerator:
    """Generates test cases using NLP techniques"""

    def __init__(self):
        self.nlp_available = LIBRARIES_LOADED

    def generate_test_scenarios_from_text(self, text: str) -> List[Dict]:
        """Generate test scenarios from raw text using NLP"""
        if not self.nlp_available:
            logging.warning("NLP libraries not available. Using basic test generation.")
            return [self._create_basic_scenario("Basic Test Scenario")]

        try:
            # Process text with spaCy
            doc = nlp(text)

            # Extract sentences
            sentences = [sent.text for sent in doc.sents]

            # Look for requirements and functionalities
            scenarios = []

            # Look for sentences that sound like requirements
            requirement_patterns = [
                r'(must|should|shall|will|needs to)',
                r'(is required to|are required to)',
                r'(functionality|feature|ability)'
            ]

            for sentence in sentences:
                # Check if sentence matches requirement patterns
                if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in requirement_patterns):
                    # Create a scenario from this requirement
                    scenario = self._create_scenario_from_requirement(sentence)
                    scenarios.append(scenario)

            # If no specific requirements found, create some basic scenarios
            if not scenarios:
                # Extract key topics from text
                key_phrases = self._extract_key_phrases(text)
                for phrase in key_phrases[:3]:  # Use top 3 key phrases
                    scenario = self._create_basic_scenario(f"Test {phrase}")
                    scenarios.append(scenario)

            return scenarios

        except Exception as e:
            logging.error(f"Error in NLP test generation: {e}")
            return [self._create_basic_scenario("Basic Test Scenario")]

    def _create_scenario_from_requirement(self, requirement: str) -> Dict:
        """Create a test scenario from a requirement sentence"""
        # Extract the main action from the requirement
        doc = nlp(requirement)

        # Find main verb and its object
        main_verb = None
        main_object = None

        for token in doc:
            if token.pos_ == "VERB" and not main_verb:
                main_verb = token.lemma_
            if token.dep_ in ("dobj", "pobj") and token.pos_ == "NOUN" and not main_object:
                main_object = token.text

        # Create scenario name
        if main_verb and main_object:
            scenario_name = f"Verify {main_verb} {main_object}"
        else:
            # Fallback to using the requirement directly
            scenario_name = f"Verify requirement: {requirement[:50]}..."

        # Create basic steps
        steps = [
            {"type": "Given", "description": "the system is ready"},
            {"type": "When",
             "description": f"the user performs actions related to '{main_object or 'the requirement'}'"},
            {"type": "Then", "description": f"the system should behave according to '{requirement[:50]}...'"}
        ]

        return {
            "name": scenario_name,
            "requirement": requirement,
            "steps": steps,
            "tags": ["automated", "requirement-based"]
        }

    def _create_basic_scenario(self, name: str) -> Dict:
        """Create a basic test scenario with standard steps"""
        return {
            "name": name,
            "steps": [
                {"type": "Given", "description": "the application is running"},
                {"type": "When", "description": "the user performs the required action"},
                {"type": "Then", "description": "the system responds correctly"}
            ],
            "tags": ["automated"]
        }

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text using NLP"""
        try:
            # Use gensim's keywords extraction
            key_phrases = keywords(text, words=5, split=True)
            return key_phrases
        except Exception:
            # Fallback to basic noun extraction with spaCy
            doc = nlp(text)
            nouns = [chunk.text for chunk in doc.noun_chunks]
            return nouns[:5]  # Return up to 5 noun phrases


class TraceabilityReporter:
    """Generates traceability reports between requirements and test cases"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def generate_traceability_matrix(self, test_scenarios: List[Dict], source_data: Dict) -> Dict:
        """Generate a traceability matrix between requirements and test scenarios"""
        # Extract requirements from source data
        requirements = self._extract_requirements(source_data)

        # Create the matrix
        matrix = {
            "requirements": requirements,
            "test_scenarios": [scenario["name"] for scenario in test_scenarios],
            "coverage": {}
        }

        # Map test scenarios to requirements
        for scenario in test_scenarios:
            scenario_name = scenario["name"]
            matrix["coverage"][scenario_name] = []

            # Check which requirements this scenario covers
            for req_id, req_text in requirements.items():
                # Simple check - see if requirement text appears in scenario or its steps
                scenario_text = json.dumps(scenario).lower()

                # Check if requirement keywords are in the scenario
                req_keywords = self._extract_requirement_keywords(req_text)
                if any(keyword.lower() in scenario_text for keyword in req_keywords):
                    matrix["coverage"][scenario_name].append(req_id)

        # Write the matrix to a file
        self._write_traceability_matrix(matrix)

        return matrix

    def _extract_requirements(self, source_data: Dict) -> Dict[str, str]:
        """Extract requirements from source data"""
        requirements = {}

        # Look for documents with requirements
        for doc in source_data.get("documents", []):
            # If it's a Word document, look for requirement-like sections
            if doc.get("file_type") == ".docx":
                for section in doc.get("sections", []):
                    if any(req_word in section.get("heading", "").lower()
                           for req_word in ["requirement", "specification", "functional"]):
                        # Extract numbered requirements from the section content
                        section_content = section.get("content", "")
                        req_pattern = r'(REQ-\d+|R\d+|FR\d+|NFR\d+|[Rr]equirement\s+\d+)[\.:\)\s]+(.*?)(?=\n\n|\n[A-Z]|$)'

                        for match in re.finditer(req_pattern, section_content, re.DOTALL):
                            req_id = match.group(1).strip()
                            req_text = match.group(2).strip()
                            requirements[req_id] = req_text

        # If no structured requirements found, create some from the design docs
        if not requirements:
            req_id = 1
            for doc in source_data.get("documents", []):
                doc_content = doc.get("content", "")
                sentences = nltk.sent_tokenize(doc_content) if LIBRARIES_LOADED else doc_content.split('.')

                for sentence in sentences:
                    if any(req_word in sentence.lower()
                           for req_word in ["must", "should", "shall", "required", "needs to"]):
                        req_id_str = f"REQ-{req_id:03d}"
                        requirements[req_id_str] = sentence.strip()
                        req_id += 1

        return requirements

    def _extract_requirement_keywords(self, req_text: str) -> List[str]:
        """Extract key words from a requirement text"""
        if not LIBRARIES_LOADED:
            # Basic extraction - split and take non-stopwords
            words = req_text.split()
            # Simple English stopwords
            stopwords = ["the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "as", "is", "are"]
            return [word for word in words if word.lower() not in stopwords and len(word) > 3]

        # Use spaCy for better keyword extraction
        doc = nlp(req_text)
        keywords = []

        for token in doc:
            # Include nouns, verbs, adjectives, and proper nouns
            if token.pos_ in ["NOUN", "VERB", "ADJ", "PROPN"] and not token.is_stop:
                keywords.append(token.text)

        return keywords

    def _write_traceability_matrix(self, matrix: Dict):
        """Write traceability matrix to a file"""
        output_path = self.output_dir / "traceability_matrix.json"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(matrix, f, indent=2)

            logging.info(f"Wrote traceability matrix to {output_path}")

            # Also generate HTML report
            self._generate_html_report(matrix)

        except Exception as e:
            logging.error(f"Error writing traceability matrix: {e}")

    def _generate_html_report(self, matrix: Dict):
        """Generate HTML report for traceability matrix"""
        output_path = self.output_dir / "traceability_report.html"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Test Traceability Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        tr:nth-child(even) { background-color: #f9f9f9; }
                        .covered { background-color: #d4edda; }
                        .not-covered { background-color: #f8d7da; }
                    </style>
                </head>
                <body>
                    <h1>Test Traceability Report</h1>
                """)

                # Requirements section
                f.write("<h2>Requirements</h2>")
                f.write("<table><tr><th>ID</th><th>Description</th></tr>")
                for req_id, req_text in matrix["requirements"].items():
                    f.write(f"<tr><td>{req_id}</td><td>{req_text}</td></tr>")
                f.write("</table>")

                # Test scenarios section
                f.write("<h2>Test Scenarios</h2>")
                f.write("<table><tr><th>Test Scenario</th><th>Requirements Covered</th></tr>")
                for scenario_name, covered_reqs in matrix["coverage"].items():
                    req_list = ", ".join(covered_reqs) if covered_reqs else "None"
                    coverage_class = "covered" if covered_reqs else "not-covered"
                    f.write(f"<tr class='{coverage_class}'><td>{scenario_name}</td><td>{req_list}</td></tr>")
                f.write("</table>")

                # Coverage matrix
                f.write("<h2>Coverage Matrix</h2>")
                f.write("<table><tr><th>Requirement ID</th>")
                for scenario in matrix["test_scenarios"]:
                    f.write(f"<th>{scenario}</th>")
                f.write("</tr>")

                for req_id in matrix["requirements"]:
                    f.write(f"<tr><td>{req_id}</td>")
                    for scenario in matrix["test_scenarios"]:
                        is_covered = req_id in matrix["coverage"].get(scenario, [])
                        coverage_mark = "✓" if is_covered else ""
                        cell_class = "covered" if is_covered else ""
                        f.write(f"<td class='{cell_class}'>{coverage_mark}</td>")
                    f.write("</tr>")
                f.write("</table>")

                f.write("</body></html>")

            logging.info(f"Wrote HTML traceability report to {output_path}")

        except Exception as e:
            logging.error(f"Error writing HTML report: {e}")


class LLMTestCaseGenerator:
    """Class to generate test cases using an LLM API"""

    def __init__(self, api_key, model="gpt-4", temperature=0.7):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        # Updated to use the completions endpoint for newer OpenAI models
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def generate_test_cases(self, context_data):
        """Generate test cases using the LLM.

        Args:
            context_data (dict): Input data for generating test cases.

        Returns:
            list: Generated test cases.
        """
        try:
            prompt = self.format_prompt(context_data)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Updated payload format for chat completions API
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": 1500
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            # Updated to handle the chat completions API response format
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            test_cases = content.split("\n")

            # Process and structure the test cases
            processed_cases = []
            current_case = None

            for line in test_cases:
                line = line.strip()
                if not line:
                    continue

                # Check if this line starts a new test case
                if line.startswith("Test Case") or line.startswith("Scenario:"):
                    if current_case:
                        processed_cases.append(current_case)
                    current_case = {"name": line, "steps": []}
                elif current_case and (line.startswith("Given") or line.startswith("When") or line.startswith(
                        "Then") or line.startswith("And")):
                    # This is a step
                    step_type, description = line.split(" ", 1)
                    current_case["steps"].append({"type": step_type, "description": description.strip()})
                elif current_case:
                    # This is additional info for the current case
                    if "description" not in current_case:
                        current_case["description"] = line
                    else:
                        current_case["description"] += "\n" + line

            # Add the last test case if there is one
            if current_case:
                processed_cases.append(current_case)

            return processed_cases or [self._create_fallback_test_case()]

        except Exception as e:
            logging.error(f"Error generating test cases: {e}")
            return [self._create_fallback_test_case()]

    def format_prompt(self, context_data):
        """Format the input data into a prompt for the LLM.

        Args:
            context_data (dict): Input data for generating test cases.

        Returns:
            str: Formatted prompt.
        """
        requirements = context_data.get("requirements", [])
        scenarios = context_data.get("scenarios", [])
        additional_context = context_data.get("additional_context", "")

        prompt = "Generate test cases in Gherkin format based on the following requirements and scenarios:\n\n"

        if requirements:
            prompt += "Requirements:\n"
            for idx, req in enumerate(requirements, 1):
                prompt += f"{idx}. {req}\n"
            prompt += "\n"

        if scenarios:
            prompt += "Scenarios:\n"
            for idx, scenario in enumerate(scenarios, 1):
                prompt += f"{idx}. {scenario}\n"
            prompt += "\n"

        if additional_context:
            prompt += f"Additional Context:\n{additional_context}\n\n"

        prompt += """For each test case, include:
1. A descriptive name
2. Gherkin steps (Given, When, Then, And)
3. Make steps detailed and specific

Format your response as follows:
Scenario: [Test Case Name]
Given [precondition]
When [action]
Then [expected result]
And [additional verification if needed]
"""
        return prompt

    def _create_fallback_test_case(self):
        """Create a fallback test case when generation fails"""
        return {
            "name": "Basic Test Case",
            "description": "This is a fallback test case created when LLM generation failed.",
            "steps": [
                {"type": "Given", "description": "the system is ready"},
                {"type": "When", "description": "the user performs an action"},
                {"type": "Then", "description": "the system responds correctly"}
            ]
        }