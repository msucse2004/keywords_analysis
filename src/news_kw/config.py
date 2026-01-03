"""Configuration management using dataclass and YAML."""

import warnings
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class Config:
    """Configuration for keyword analysis pipeline."""
    
    KEYWORD_TOP_N: int = 50
    TREND_PLOT_TOP_N: int = 10
    COOC_NODE_TOP_N: int = 60
    COOC_EDGE_TOP_N: int = 300
    COOC_LABEL_TOP_N: int = 25
    WORDCLOUD_TOP_N: int = 200
    WORDCLOUD_MAX_WORDS: int = 200
    WORDCLOUD_WIDTH: int = 1400
    WORDCLOUD_HEIGHT: int = 900
    WORDCLOUD_BACKGROUND: str = "white"
    WORDCLOUD_OUTPUT_NAME: str = "py_wordcloud.png"
    
    @staticmethod
    def load_exclude_keywords(exclude_dir: Path) -> List[str]:
        """Load exclude keywords from data/exclude folder.
        
        Reads all .txt files in the exclude directory and extracts
        comma-separated keywords from each file.
        
        Args:
            exclude_dir: Directory containing exclude keyword files
            
        Returns:
            List of exclude keywords (lowercased, deduplicated)
        """
        exclude_keywords = []
        
        if not exclude_dir.exists():
            return exclude_keywords
        
        # Read all .txt files in exclude directory
        for txt_file in exclude_dir.glob('*.txt'):
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        # Split by comma and clean up
                        keywords = [kw.strip().lower() for kw in content.split(',') if kw.strip()]
                        exclude_keywords.extend(keywords)
            except Exception as e:
                warnings.warn(f"Error reading exclude file {txt_file}: {e}")
        
        # Remove duplicates and return
        return list(set(exclude_keywords))
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Config":
        """Load configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            Config instance with values from YAML (defaults for missing keys)
        """
        config = cls()
        
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
            
            for key, value in yaml_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'KEYWORD_TOP_N': self.KEYWORD_TOP_N,
            'TREND_PLOT_TOP_N': self.TREND_PLOT_TOP_N,
            'COOC_NODE_TOP_N': self.COOC_NODE_TOP_N,
            'COOC_EDGE_TOP_N': self.COOC_EDGE_TOP_N,
            'COOC_LABEL_TOP_N': self.COOC_LABEL_TOP_N,
            'WORDCLOUD_TOP_N': self.WORDCLOUD_TOP_N,
            'WORDCLOUD_MAX_WORDS': self.WORDCLOUD_MAX_WORDS,
            'WORDCLOUD_WIDTH': self.WORDCLOUD_WIDTH,
            'WORDCLOUD_HEIGHT': self.WORDCLOUD_HEIGHT,
            'WORDCLOUD_BACKGROUND': self.WORDCLOUD_BACKGROUND,
            'WORDCLOUD_OUTPUT_NAME': self.WORDCLOUD_OUTPUT_NAME,
        }

