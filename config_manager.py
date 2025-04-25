"""
Configuration module for the Test Automation Framework.

This module provides centralized configuration management for all framework components.
It loads settings from config.json and environment variables, with sensible defaults.
"""

import os
import json
import logging
from pathlib import Path

# Default configuration values
DEFAULT_CONFIG = {
    # General settings
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "console_format": "%(levelname)s: %(message)s"
    },
    
    # LLM settings
    "llm": {
        "enabled": True,
        "provider": "azure",  # Options: "azure", "openai", "anthropic", "local"
        "model": "gpt-4o",
        "temperature": 0.4,
        "api_version": "2024-08-01-preview",
        "azure_endpoint": "https://llm-test-automation.openai.azure.com/openai/deployments/gpt-4o/chat/completions",
        "timeout": 60,  # Timeout in seconds
        "max_retries": 3
    },
    
    # NLP settings
    "nlp": {
        "enabled": False,
        "library": "spacy",  # Options: "spacy", "nltk"
        "model": "en_core_web_sm"
    },
    
    # Test generation settings
    "test_generation": {
        "default_tags": ["automated", "generated"],
        "common_given_steps": [
            "the application is running",
            "the user is logged in",
            "the database is initialized"
        ],
        "max_scenarios_per_feature": 10,
        "group_by_tags": True,
        "two_stage_generation": True
    },
    
    # File paths and directories
    "directories": {
        "output_root": "output",
        "log_dir": "logs",
        "temp_dir": "temp",
        "features_dir": "output/features",
        "reports_dir": "output/reports"
    },
    
    # Feature file formatting
    "feature_format": {
        "indent_spaces": 2,
        "new_line_after_feature": True,
        "new_line_after_scenario": True,
        "tag_on_new_line": False
    }
}


class Config:
    """Configuration manager for the Test Automation Framework."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration if not already initialized."""
        if not getattr(self, "_initialized", False):
            self._config = DEFAULT_CONFIG.copy()
            self._load_from_file()
            self._load_from_env()
            self._initialized = True
    
    def _load_from_file(self):
        """Load configuration from config.json if it exists."""
        config_file = Path("config.json")
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    file_config = json.load(f)
                    self._update_nested_dict(self._config, file_config)
                logging.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logging.warning(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # LLM settings from environment variables
        if "AZURE_API_KEY" in os.environ:
            self._config["llm"]["api_key"] = os.environ["AZURE_API_KEY"]
        
        if "LLM_MODEL" in os.environ:
            self._config["llm"]["model"] = os.environ["LLM_MODEL"]
        
        if "LLM_TEMPERATURE" in os.environ:
            try:
                self._config["llm"]["temperature"] = float(os.environ["LLM_TEMPERATURE"])
            except ValueError:
                logging.warning(f"Invalid LLM_TEMPERATURE: {os.environ['LLM_TEMPERATURE']}")
        
        # Logging settings
        if "LOG_LEVEL" in os.environ:
            self._config["logging"]["level"] = os.environ["LOG_LEVEL"]
    
    def _update_nested_dict(self, d, u):
        """Update a nested dictionary with values from another dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
    
    def get(self, key, default=None):
        """Get a configuration value by key.
        
        Args:
            key (str): Dot-separated key path (e.g., "llm.model")
            default: Default value to return if key is not found
            
        Returns:
            The configuration value or default if not found
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """Set a configuration value by key.
        
        Args:
            key (str): Dot-separated key path (e.g., "llm.model")
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the innermost dict
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def save(self, file_path="config.json"):
        """Save the current configuration to a file.
        
        Args:
            file_path (str): Path to save the configuration to
        """
        try:
            # Create directory if needed
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Remove sensitive data before saving
            config_to_save = self._config.copy()
            if "llm" in config_to_save and "api_key" in config_to_save["llm"]:
                config_to_save["llm"]["api_key"] = "**REDACTED**"
            
            with open(file_path, "w") as f:
                json.dump(config_to_save, f, indent=2)
            
            logging.info(f"Configuration saved to {file_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def get_all(self):
        """Get the entire configuration dictionary.
        
        Returns:
            dict: A copy of the configuration dictionary
        """
        return self._config.copy()
    
    def reset_to_defaults(self):
        """Reset the configuration to default values."""
        self._config = DEFAULT_CONFIG.copy()
        self._load_from_env()


# Global configuration instance
config = Config()

# Configure logging based on the configuration
def configure_logging():
    """Configure logging based on the current configuration."""
    log_level = getattr(logging, config.get("logging.level", "INFO"), logging.INFO)
    log_format = config.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    logging.basicConfig(
        level=log_level,
        format=log_format
    )

# Call this at import time to configure logging
configure_logging()