"""Configuration management using dataclass and YAML."""

import warnings
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Union


@dataclass
class Config:
    """Configuration for keyword analysis pipeline."""
    
    # DATA_SOURCE_GROUPS can be:
    # - List of strings (single folder per group): ["meeting", "news"]
    # - List of lists (multiple folders per group): [["meeting"], ["news", "reddit"]]
    # - Mixed: ["meeting", ["news", "reddit"]]
    # Will be converted to Dict[str, List[str]] in from_yaml
    DATA_SOURCE_GROUPS: Union[List[Union[str, List[str]]], Dict[str, List[str]]] = field(default_factory=lambda: [["meeting", "news", "reddit"]])
    # Legacy support: if DATA_SOURCE_GROUPS not set, use DATA_SOURCE_FOLDERS
    DATA_SOURCE_FOLDERS: List[str] = field(default_factory=lambda: ["meeting", "news", "reddit"])
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
    def _normalize_data_source_groups(cls, groups: Union[List[Union[str, List[str]]], Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """Normalize DATA_SOURCE_GROUPS to Dict[str, List[str]] format.
        
        Args:
            groups: Can be list of strings/lists or dict
            
        Returns:
            Dict mapping group names to folder lists
        """
        if isinstance(groups, dict):
            return groups
        
        if not isinstance(groups, list):
            # Single string or other type - wrap it
            groups = [groups]
        
        normalized = {}
        for item in groups:
            if isinstance(item, str):
                # Single folder - use folder name as group name
                normalized[item] = [item]
            elif isinstance(item, list):
                # Multiple folders - create group name from folder names
                if len(item) == 1:
                    group_name = item[0]
                else:
                    group_name = '_'.join(item)
                normalized[group_name] = item
            else:
                warnings.warn(f"Invalid group item: {item}, skipping")
        
        return normalized
    
    @staticmethod
    def validate_folders(folders: List[str], input_dir: Path) -> tuple[bool, List[str], List[str]]:
        """Validate that folder names exist in the input directory.
        
        Args:
            folders: List of folder names to validate
            input_dir: Base input directory (e.g., data/raw_txt)
            
        Returns:
            Tuple of (is_valid, valid_folders, invalid_folders)
        """
        if not input_dir.exists():
            return False, [], folders
        
        # Get all subdirectories in input_dir
        existing_folders = {d.name for d in input_dir.iterdir() if d.is_dir()}
        
        valid_folders = []
        invalid_folders = []
        
        for folder in folders:
            if folder in existing_folders:
                valid_folders.append(folder)
            else:
                invalid_folders.append(folder)
        
        is_valid = len(invalid_folders) == 0
        return is_valid, valid_folders, invalid_folders
    
    @classmethod
    def from_yaml(cls, yaml_path: Path, input_dir: Optional[Path] = None) -> "Config":
        """Load configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            input_dir: Optional input directory for folder validation (e.g., data/raw_txt)
            
        Returns:
            Config instance with values from YAML (defaults for missing keys)
            
        Raises:
            ValueError: If folder validation fails
        """
        config = cls()
        
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
            
            for key, value in yaml_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Normalize DATA_SOURCE_GROUPS to Dict format
        if hasattr(config, 'DATA_SOURCE_GROUPS') and config.DATA_SOURCE_GROUPS:
            config.DATA_SOURCE_GROUPS = cls._normalize_data_source_groups(config.DATA_SOURCE_GROUPS)
        
        # Legacy support: if DATA_SOURCE_GROUPS is not set but DATA_SOURCE_FOLDERS is,
        # create a default group
        if (not config.DATA_SOURCE_GROUPS or 
            (isinstance(config.DATA_SOURCE_GROUPS, dict) and not config.DATA_SOURCE_GROUPS)):
            if yaml_data.get('DATA_SOURCE_FOLDERS'):
                folders = yaml_data['DATA_SOURCE_FOLDERS']
                if isinstance(folders, list) and folders:
                    # Create a single group with all folders
                    group_name = '_'.join(folders) if len(folders) > 1 else folders[0]
                    config.DATA_SOURCE_GROUPS = {group_name: folders}
        
        # Validate folders if input_dir is provided
        if input_dir and config.DATA_SOURCE_GROUPS:
            if isinstance(config.DATA_SOURCE_GROUPS, dict):
                all_folders = set()
                for folders_list in config.DATA_SOURCE_GROUPS.values():
                    all_folders.update(folders_list)
                
                is_valid, valid_folders, invalid_folders = cls.validate_folders(
                    list(all_folders), input_dir
                )
                
                if not is_valid:
                    existing_folders = sorted({d.name for d in input_dir.iterdir() if d.is_dir()})
                    error_msg = (
                        f"폴더명 검증 실패: 다음 폴더들이 '{input_dir}' 아래에 존재하지 않습니다:\n"
                        f"  잘못된 폴더명: {', '.join(invalid_folders)}\n"
                        f"  올바른 폴더명: {', '.join(valid_folders) if valid_folders else '(없음)'}\n"
                        f"  실제 존재하는 폴더: {', '.join(existing_folders) if existing_folders else '(없음)'}\n"
                        f"\nconfig/default.yaml의 DATA_SOURCE_GROUPS를 확인하고 수정해주세요."
                    )
                    raise ValueError(error_msg)
        
        return config
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'DATA_SOURCE_GROUPS': self.DATA_SOURCE_GROUPS,
            'DATA_SOURCE_FOLDERS': self.DATA_SOURCE_FOLDERS,
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

