import os
import re
import json
import glob
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestAutomationFramework")


@dataclass
class SourceReference:
    """Stores reference information for traceability"""
    source_type: str  # e.g., "Story", "Design Doc", "Transcript"
    link: str
    document_name: Optional[str] = None
    section: Optional[str] = None


@dataclass
class TestStep:
    """Represents a single test step in Gherkin format"""
    step_type: str  # "Given", "When", "Then", "And", "But"
    description: str
    data_reference: Optional[str] = None


@dataclass
class TestScenario:
    """Represents a test scenario containing multiple steps"""
    name: str
    steps: List[TestStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_references: List[SourceReference] = field(default_factory=list)


@dataclass
class FeatureFile:
    """Represents a complete Gherkin feature file"""
    name: str
    description: str
    scenarios: List[TestScenario] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def add_scenario(self, scenario: TestScenario):
        """Add a test scenario to this feature file"""
        self.scenarios.append(scenario)
        return self
    
    def add_tag(self, tag: str):
        """Add a tag to this feature file"""
        if tag not in self.tags:
            self.tags.append(tag)
        return self
    
    def get_total_steps_count(self) -> int:
        """Get the total number of steps across all scenarios"""
        return sum(len(scenario.steps) for scenario in self.scenarios)
    
    def get_scenarios_by_tag(self, tag: str) -> List[TestScenario]:
        """Get all scenarios that have the specified tag"""
        return [scenario for scenario in self.scenarios if tag in scenario.tags]
    
    def to_dict(self) -> Dict:
        """Convert the feature file to a dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "scenarios": [
                {
                    "name": scenario.name,
                    "tags": scenario.tags,
                    "steps": [
                        {
                            "type": step.step_type,
                            "description": step.description,
                            "data_reference": step.data_reference
                        } for step in scenario.steps
                    ],
                    "source_references": [
                        {
                            "source_type": ref.source_type,
                            "link": ref.link,
                            "document_name": ref.document_name,
                            "section": ref.section
                        } for ref in scenario.source_references
                    ]
                } for scenario in self.scenarios
            ]
        }
    
    def to_gherkin(self) -> str:
        """Convert the feature file to a Gherkin string representation"""
        lines = []
        
        # Write feature tags
        for tag in self.tags:
            lines.append(f"@{tag}")
        
        # Write feature header
        lines.append(f"Feature: {self.name}")
        lines.append(f"  {self.description}")
        lines.append("")
        
        # Write each scenario
        for scenario in self.scenarios:
            # Write scenario tags
            for tag in scenario.tags:
                if tag not in self.tags:  # Avoid duplicate tags
                    lines.append(f"  @{tag}")
            
            # Write scenario header
            lines.append(f"  Scenario: {scenario.name}")
            
            # Write scenario steps
            for step in scenario.steps:
                data_ref = f" {step.data_reference}" if step.data_reference else ""
                lines.append(f"    {step.step_type} {step.description}{data_ref}")
            
            # Add a blank line between scenarios
            lines.append("")
        
        return "\n".join(lines)
    
    def save_to_file(self, output_dir: str) -> str:
        """Save the feature file to disk and return the file path"""
        output_path = os.path.join(output_dir, f"{self.name}.feature")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.to_gherkin())
            return output_path
        except Exception as e:
            logger.error(f"Error writing feature file {output_path}: {e}")
            return None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeatureFile':
        """Create a FeatureFile object from a dictionary representation"""
        feature_file = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )
        
        for scenario_data in data.get("scenarios", []):
            scenario = TestScenario(
                name=scenario_data.get("name", ""),
                tags=scenario_data.get("tags", [])
            )
            
            # Add steps
            for step_data in scenario_data.get("steps", []):
                step = TestStep(
                    step_type=step_data.get("type", "Given"),
                    description=step_data.get("description", ""),
                    data_reference=step_data.get("data_reference")
                )
                scenario.steps.append(step)
            
            # Add source references
            for ref_data in scenario_data.get("source_references", []):
                source_ref = SourceReference(
                    source_type=ref_data.get("source_type", ""),
                    link=ref_data.get("link", ""),
                    document_name=ref_data.get("document_name"),
                    section=ref_data.get("section")
                )
                scenario.source_references.append(source_ref)
            
            # Add the scenario to the feature file
            feature_file.add_scenario(scenario)
        
        return feature_file
    
    @classmethod
    def from_file(cls, file_path: str) -> 'FeatureFile':
        """Create a FeatureFile object by parsing an existing feature file"""
        parser = FeatureFileParser()
        feature_data = parser.parse(file_path)
        
        feature_file = cls(
            name=feature_data.get("feature_name") or Path(file_path).stem,
            description=feature_data.get("description", ""),
            tags=feature_data.get("tags", [])
        )
        
        # Add scenarios
        for scenario_data in feature_data.get("scenarios", []):
            scenario = TestScenario(
                name=scenario_data.get("name", ""),
                tags=scenario_data.get("tags", [])
            )
            
            # Add steps
            for step_data in scenario_data.get("steps", []):
                step = TestStep(
                    step_type=step_data.get("type", "Given"),
                    description=step_data.get("description", "")
                )
                scenario.steps.append(step)
            
            # Add the scenario to the feature file
            feature_file.add_scenario(scenario)
        
        return feature_file


class DocumentParser:
    """Base class for parsing different document types"""

    def parse(self, file_path: str) -> Dict:
        """Parse the document and return extracted information"""
        raise NotImplementedError("Subclasses must implement parse method")

    def extract_links(self, content: str) -> List[str]:
        """Extract links from content"""
        # Simple regex for URLs
        url_pattern = r'https?://\S+'
        return re.findall(url_pattern, content)


class InputTxtParser(DocumentParser):
    """Parser for input.txt files"""

    def parse(self, file_path: str) -> Dict:
        result = {
            "story_link": None,
            "design_doc_links": [],
            "transcript_links": [],
            "sharepoint_links": [],
            "confluence_links": [],
            "jira_links": [],
            "reference_links": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

                # Extract links
                links = self.extract_links(content)

                for link in links:
                    if "jira" in link.lower():
                        result["jira_links"].append(link)
                    elif "confluence" in link.lower():
                        result["confluence_links"].append(link)
                    elif "sharepoint" in link.lower():
                        result["sharepoint_links"].append(link)
                    elif "story" in link.lower() and not result["story_link"]:
                        result["story_link"] = link
                    elif "design" in link.lower() or "doc" in link.lower():
                        result["design_doc_links"].append(link)
                    elif "transcript" in link.lower():
                        result["transcript_links"].append(link)
                    else:
                        result["reference_links"].append(link)

        except Exception as e:
            logger.error(f"Error parsing input.txt: {e}")

        return result


class DocxParser(DocumentParser):
    """Parser for Word documents"""

    def parse(self, file_path: str) -> Dict:
        # In a real implementation, you would use a library like python-docx
        # For this example, we'll return dummy data
        logger.info(f"Parsing DOCX document: {file_path}")
        return {
            "content": f"Content extracted from {file_path}",
            "sections": ["Introduction", "Requirements", "Design"],
            "links": self.extract_links(f"Dummy content with https://example.com/link")
        }


class FeatureFileParser(DocumentParser):
    """Parser for Gherkin feature files"""

    def parse(self, file_path: str) -> Dict:
        result = {
            "feature_name": "",
            "description": "",
            "tags": [],
            "scenarios": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.readlines()

                current_section = "header"
                current_scenario = None

                for line in content:
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith('@'):
                        tags = [tag.strip() for tag in line.split('@') if tag]
                        if current_scenario:
                            current_scenario["tags"].extend(tags)
                        else:
                            result["tags"].extend(tags)

                    elif line.startswith('Feature:'):
                        result["feature_name"] = line[8:].strip()
                        current_section = "description"

                    elif line.startswith('Scenario:') or line.startswith('Scenario Outline:'):
                        scenario_type = "outline" if "Outline" in line else "scenario"
                        scenario_name = line.split(':', 1)[1].strip()
                        current_scenario = {
                            "name": scenario_name,
                            "type": scenario_type,
                            "steps": [],
                            "tags": []
                        }
                        result["scenarios"].append(current_scenario)
                        current_section = "scenario"

                    elif current_section == "description" and not line.startswith('Scenario'):
                        if result["description"]:
                            result["description"] += "\n"
                        result["description"] += line

                    elif current_section == "scenario" and (
                            line.startswith('Given ') or
                            line.startswith('When ') or
                            line.startswith('Then ') or
                            line.startswith('And ') or
                            line.startswith('But ')
                    ):
                        step_type, step_desc = line.split(' ', 1)
                        step = {"type": step_type, "description": step_desc.strip()}
                        current_scenario["steps"].append(step)

        except Exception as e:
            logger.error(f"Error parsing feature file: {e}")

        return result


class ExcelParser(DocumentParser):
    """Parser for Excel test case documents"""

    def parse(self, file_path: str) -> Dict:
        # In a real implementation, you would use a library like pandas or openpyxl
        # For this example, we'll return dummy data
        logger.info(f"Parsing Excel document: {file_path}")
        return {
            "test_cases": [
                {
                    "id": "TC001",
                    "name": "Verify login functionality",
                    "description": "Test the user login feature",
                    "steps": [
                        "Open application",
                        "Enter username",
                        "Enter password",
                        "Click login button",
                        "Verify successful login"
                    ],
                    "expected_results": [
                        "Application opens",
                        "Username accepted",
                        "Password accepted",
                        "Login initiated",
                        "User logged in successfully"
                    ]
                }
            ]
        }


class TestCaseGenerator:
    """Generates test cases from parsed documentation"""

    def __init__(self, story_folder: str, context_folder: str):
        self.story_folder = Path(story_folder)
        self.context_folder = Path(context_folder)
        self.parsers = {
            ".txt": InputTxtParser(),
            ".docx": DocxParser(),
            ".feature": FeatureFileParser(),
            ".xlsx": ExcelParser(),
            ".xls": ExcelParser()
        }
        self.story_data = {}
        self.context_data = {}

    def load_source_data(self):
        """Load all source data from story and context folders"""
        logger.info("Loading source data...")

        # Load story data
        self.story_data = self._load_folder_data(self.story_folder)

        # Load context data
        self.context_data = self._load_folder_data(self.context_folder)

        logger.info("Source data loaded successfully")

    def _load_folder_data(self, folder_path: Path) -> Dict:
        """Load data from a specific folder"""
        result = {
            "input_txt": {},
            "documents": []
        }

        # First, look for input.txt
        input_txt_path = folder_path / "Input.txt"
        if input_txt_path.exists():
            result["input_txt"] = self.parsers[".txt"].parse(str(input_txt_path))

        # Then look for documents folder
        docs_folder = folder_path / "Documents"
        if docs_folder.exists() and docs_folder.is_dir():
            for file_path in docs_folder.glob("**/*.*"):
                file_extension = file_path.suffix.lower()
                if file_extension in self.parsers:
                    try:
                        parsed_data = self.parsers[file_extension].parse(str(file_path))
                        parsed_data["file_path"] = str(file_path)
                        parsed_data["file_name"] = file_path.name
                        parsed_data["file_type"] = file_extension
                        result["documents"].append(parsed_data)
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")

        return result

    def generate_test_cases(self) -> List[TestScenario]:
        """Generate test cases from source data"""
        logger.info("Generating test cases...")

        test_scenarios = []

        # Extract existing scenarios from context data
        existing_scenarios = self._extract_existing_scenarios()

        # Generate new scenarios from story data
        story_scenarios = self._generate_scenarios_from_story()

        # Merge and deduplicate scenarios
        test_scenarios = self._merge_scenarios(existing_scenarios, story_scenarios)

        logger.info(f"Generated {len(test_scenarios)} test scenarios")
        return test_scenarios

    def _extract_existing_scenarios(self) -> List[TestScenario]:
        """Extract existing scenarios from context data"""
        scenarios = []

        # Extract from feature files
        for doc in self.context_data.get("documents", []):
            if doc.get("file_type") == ".feature":
                for scenario_data in doc.get("scenarios", []):
                    scenario = TestScenario(
                        name=scenario_data["name"],
                        tags=scenario_data.get("tags", [])
                    )

                    for step_data in scenario_data.get("steps", []):
                        step = TestStep(
                            step_type=step_data["type"],
                            description=step_data["description"]
                        )
                        scenario.steps.append(step)

                    source_ref = SourceReference(
                        source_type="Feature File",
                        link="",
                        document_name=doc.get("file_name")
                    )
                    scenario.source_references.append(source_ref)
                    scenarios.append(scenario)

        return scenarios

    def _generate_scenarios_from_story(self) -> List[TestScenario]:
        """Generate scenarios from story data"""
        # In a real implementation, this would involve more sophisticated
        # processing of requirements, perhaps using NLP
        scenarios = []

        # For example purposes, we'll create a basic scenario
        scenario = TestScenario(
            name="Verify functionality from story requirements",
            tags=["automated", "story_based"]
        )

        # Add standard steps
        scenario.steps.append(TestStep(step_type="Given", description="the application is running"))
        scenario.steps.append(TestStep(step_type="When", description="the user performs the required action"))
        scenario.steps.append(TestStep(step_type="Then", description="the system responds correctly"))

        # Add source reference
        if self.story_data.get("input_txt", {}).get("story_link"):
            source_ref = SourceReference(
                source_type="Story",
                link=self.story_data["input_txt"]["story_link"]
            )
            scenario.source_references.append(source_ref)

        scenarios.append(scenario)
        return scenarios

    def _merge_scenarios(self, existing: List[TestScenario], new: List[TestScenario]) -> List[TestScenario]:
        """Merge and deduplicate scenarios"""
        # For simplicity, we'll just combine them
        # In a real implementation, you'd want to deduplicate properly
        combined = existing + new

        # Simple deduplication by scenario name
        unique_scenarios = {}
        for scenario in combined:
            if scenario.name not in unique_scenarios:
                unique_scenarios[scenario.name] = scenario

        return list(unique_scenarios.values())


class TestStepGenerator:
    """Generates test steps for test cases"""

    def __init__(self, test_scenarios: List[TestScenario], context_data: Dict):
        self.test_scenarios = test_scenarios
        self.context_data = context_data
        self.step_patterns = self._extract_step_patterns()

    def _extract_step_patterns(self) -> Dict:
        """Extract step patterns from existing feature files"""
        patterns = {
            "Given": set(),
            "When": set(),
            "Then": set(),
            "And": set(),
            "But": set()
        }

        # Extract patterns from context data
        for doc in self.context_data.get("documents", []):
            if doc.get("file_type") == ".feature":
                for scenario in doc.get("scenarios", []):
                    for step in scenario.get("steps", []):
                        step_type = step.get("type")
                        description = step.get("description")
                        if step_type and description:
                            patterns[step_type].add(description)

        return patterns

    def enhance_test_steps(self):
        """Enhance existing test steps with more details"""
        logger.info("Enhancing test steps...")

        for scenario in self.test_scenarios:
            # If there are no steps, generate them
            if not scenario.steps:
                self._generate_steps_for_scenario(scenario)
            else:
                # Otherwise, enhance existing steps
                self._enhance_existing_steps(scenario)

    def _generate_steps_for_scenario(self, scenario: TestScenario):
        """Generate basic steps for a scenario without steps"""
        # Start with a Given step
        given_steps = list(self.step_patterns["Given"])
        if given_steps:
            scenario.steps.append(TestStep(step_type="Given", description=given_steps[0]))
        else:
            scenario.steps.append(TestStep(step_type="Given", description="the application is ready"))

        # Add a When step
        scenario.steps.append(TestStep(step_type="When", description=f"the user interacts with {scenario.name}"))

        # Add a Then step
        scenario.steps.append(TestStep(step_type="Then", description="the system responds as expected"))

    def _enhance_existing_steps(self, scenario: TestScenario):
        """Enhance existing steps with more details"""
        # For this example, we'll just add data references to steps that don't have them
        for step in scenario.steps:
            if not step.data_reference and "user" in step.description.lower():
                step.data_reference = '{"user_id": "test_user", "password": "test_password"}'


class GherkinFormatter:
    """Formats test scenarios into Gherkin feature files"""

    def create_feature_files(self, test_scenarios: List[TestScenario], output_dir: str) -> List[FeatureFile]:
        """Group scenarios into feature files and write them to disk"""
        logger.info("Creating feature files...")

        # Group scenarios by tags for feature organization
        grouped_scenarios = self._group_scenarios_by_tags(test_scenarios)

        feature_files = []

        # Create a feature file for each group
        for group_name, scenarios in grouped_scenarios.items():
            feature_file = FeatureFile(
                name=f"{group_name}_feature",
                description=f"Feature file for {group_name} test scenarios",
                scenarios=scenarios,
                tags=self._extract_common_tags(scenarios)
            )
            feature_files.append(feature_file)

            # Write to disk
            self._write_feature_file(feature_file, output_dir)

        logger.info(f"Created {len(feature_files)} feature files")
        return feature_files

    def _group_scenarios_by_tags(self, scenarios: List[TestScenario]) -> Dict[str, List[TestScenario]]:
        """Group scenarios by their tags"""
        groups = {"default": []}

        for scenario in scenarios:
            assigned = False

            # Find a tag to group by (excluding common tags like 'automated')
            for tag in scenario.tags:
                if tag not in ["automated", "test", "regression"]:
                    if tag not in groups:
                        groups[tag] = []
                    groups[tag].append(scenario)
                    assigned = True
                    break

            # If no suitable tag found, add to default group
            if not assigned:
                groups["default"].append(scenario)

        return groups

    def _extract_common_tags(self, scenarios: List[TestScenario]) -> List[str]:
        """Extract tags common to all scenarios in a group"""
        if not scenarios:
            return []

        # Start with all tags from the first scenario
        common_tags = set(scenarios[0].tags)

        # Intersect with tags from other scenarios
        for scenario in scenarios[1:]:
            common_tags &= set(scenario.tags)

        return list(common_tags)

    def _write_feature_file(self, feature_file: FeatureFile, output_dir: str):
        """Write a feature file to disk"""
        output_path = Path(output_dir) / f"{feature_file.name}.feature"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write feature tags
                for tag in feature_file.tags:
                    f.write(f"@{tag}\n")

                # Write feature header
                f.write(f"Feature: {feature_file.name}\n")
                f.write(f"  {feature_file.description}\n\n")

                # Write each scenario
                for scenario in feature_file.scenarios:
                    # Write scenario tags
                    for tag in scenario.tags:
                        if tag not in feature_file.tags:  # Avoid duplicate tags
                            f.write(f"  @{tag}\n")

                    # Write scenario header
                    f.write(f"  Scenario: {scenario.name}\n")

                    # Write scenario steps
                    for step in scenario.steps:
                        data_ref = f" {step.data_reference}" if step.data_reference else ""
                        f.write(f"    {step.step_type} {step.description}{data_ref}\n")

                    # Add a blank line between scenarios
                    f.write("\n")

            logger.info(f"Wrote feature file to {output_path}")

        except Exception as e:
            logger.error(f"Error writing feature file {output_path}: {e}")


class TestAutomationFramework:
    """Main class for the test automation framework"""

    def __init__(self, story_folder: str, context_folder: str, output_dir: str):
        self.story_folder = story_folder
        self.context_folder = context_folder
        self.output_dir = output_dir
        
        # Additional attributes for enhanced functionality
        self.test_case_generator = None
        self.test_step_generator = None
        self.formatter = GherkinFormatter()
        self.llm_generator = None
        self.nlp_generator = None
        
        # Optional trackers for progress reporting
        self.total_scenarios = 0
        self.total_steps = 0
        self.feature_files = []

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def initialize_generators(self):
        """Initialize the test case and step generators"""
        # Initialize test case generator
        self.test_case_generator = TestCaseGenerator(self.story_folder, self.context_folder)
        self.test_case_generator.load_source_data()
        
        # Return the generators for API access if needed
        return self.test_case_generator

    def generate_test_cases(self, use_enhanced_steps=True):
        """Generate test cases and test steps from source data"""
        logger.info("Starting test case generation...")
        
        # Initialize generators if they haven't been initialized
        if not self.test_case_generator:
            self.initialize_generators()
        
        # Generate test scenarios from source data
        test_scenarios = self.test_case_generator.generate_test_cases()
        self.total_scenarios = len(test_scenarios)
        
        # Generate test steps for each test case if requested
        if use_enhanced_steps:
            self.test_step_generator = TestStepGenerator(test_scenarios, self.test_case_generator.context_data)
            self.test_step_generator.enhance_test_steps()
        
        # Format and output the feature files
        self.feature_files = self.formatter.create_feature_files(test_scenarios, self.output_dir)
        
        # Track total steps for reporting
        self.total_steps = sum(len(scenario.steps) for feature in self.feature_files
                              for scenario in feature.scenarios)
        
        logger.info(f"Test case generation complete. Generated {len(self.feature_files)} feature files with {self.total_scenarios} scenarios and {self.total_steps} steps.")
        return self.feature_files
    
    def generate_test_cases_only(self):
        """Generate test cases without detailed steps (first stage of two-stage process)"""
        logger.info("Starting test case generation (first stage)...")
        
        # Initialize generators if they haven't been initialized
        if not self.test_case_generator:
            self.initialize_generators()
        
        # Generate test scenarios with minimal steps
        test_scenarios = self.test_case_generator.generate_test_cases()
        
        # Apply minimal placeholder steps to scenarios without steps
        for scenario in test_scenarios:
            if not scenario.steps:
                # Add minimal placeholder steps
                scenario.steps.append(TestStep(step_type="Given", description="a basic setup"))
                scenario.steps.append(TestStep(step_type="When", description="the action is performed"))
                scenario.steps.append(TestStep(step_type="Then", description="the expected result is verified"))
        
        # Format and output the feature files
        self.feature_files = self.formatter.create_feature_files(test_scenarios, self.output_dir)
        
        logger.info(f"First stage complete. Generated {len(self.feature_files)} feature files with {len(test_scenarios)} test cases.")
        return self.feature_files
    
    def enhance_test_steps(self, feature_files_path):
        """Enhance existing test cases with detailed steps (second stage of two-stage process)"""
        logger.info("Starting test step enhancement (second stage)...")
        
        # Parse existing feature files
        parser = FeatureFileParser()
        enhanced_feature_files = []
        
        # Find all feature files in the specified directory
        feature_file_paths = []
        if os.path.isdir(feature_files_path):
            for file in os.listdir(feature_files_path):
                if file.endswith('.feature'):
                    feature_file_paths.append(os.path.join(feature_files_path, file))
        else:
            feature_file_paths = [feature_files_path]
        
        # Initialize context data if not already done
        if not self.test_case_generator:
            self.initialize_generators()
            
        context_data = self.test_case_generator.context_data
        
        # Process each feature file
        for file_path in feature_file_paths:
            feature_data = parser.parse(file_path)
            
            # Create scenarios from parsed data
            scenarios = []
            for scenario_data in feature_data.get('scenarios', []):
                scenario = TestScenario(
                    name=scenario_data['name'],
                    tags=scenario_data.get('tags', [])
                )
                
                # Convert steps
                steps = []
                for step_data in scenario_data.get('steps', []):
                    steps.append(TestStep(
                        step_type=step_data['type'],
                        description=step_data['description']
                    ))
                
                scenario.steps = steps
                scenarios.append(scenario)
            
            # Enhance the steps
            self.test_step_generator = TestStepGenerator(scenarios, context_data)
            self.test_step_generator.enhance_test_steps()
            
            # Create feature file
            feature_file = FeatureFile(
                name=feature_data.get('feature_name') or Path(file_path).stem,
                description=feature_data.get('description') or f"Feature file for {Path(file_path).stem}",
                scenarios=scenarios,
                tags=feature_data.get('tags', [])
            )
            
            # Write enhanced feature file
            enhanced_path = os.path.join(self.output_dir, os.path.basename(file_path))
            self.formatter._write_feature_file(feature_file, self.output_dir)
            
            enhanced_feature_files.append(feature_file)
        
        logger.info(f"Second stage complete. Enhanced {len(enhanced_feature_files)} feature files.")
        return enhanced_feature_files
    
    def set_llm_generator(self, llm_generator):
        """Set an LLM generator for enhanced test generation"""
        self.llm_generator = llm_generator
        return self
    
    def set_nlp_generator(self, nlp_generator):
        """Set an NLP generator for enhanced test generation"""
        self.nlp_generator = nlp_generator
        return self
    
    def generate_report(self):
        """Generate a report of the test generation statistics"""
        if not self.feature_files:
            return "No test cases have been generated yet."
        
        report = "=== Test Generation Report ===\n"
        report += f"Total feature files: {len(self.feature_files)}\n"
        report += f"Total test scenarios: {self.total_scenarios}\n"
        report += f"Total test steps: {self.total_steps}\n\n"
        
        # Feature files breakdown
        report += "Feature Files:\n"
        for i, feature in enumerate(self.feature_files, 1):
            scenarios_count = len(feature.scenarios)
            steps_count = sum(len(scenario.steps) for scenario in feature.scenarios)
            report += f"  {i}. {feature.name}: {scenarios_count} scenarios, {steps_count} steps\n"
        
        report += "\nOutput directory: " + self.output_dir
        
        return report


def main():
    # Configuration
    story_folder = "input/story"
    context_folder = "input/context"
    output_dir = "output/features"

    # Create the framework
    framework = TestAutomationFramework(story_folder, context_folder, output_dir)

    # Generate test cases
    feature_files = framework.generate_test_cases()

    print(f"Generated {len(feature_files)} feature files in {output_dir}")


if __name__ == "__main__":
    main()