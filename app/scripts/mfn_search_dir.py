#!/usr/bin/env python3
"""
Business Card File Processor

Evaluates business card scans using filename patterns from META-FILE-NODE schema.
Extracts metadata according to BusinessCard_20260121 schema.

Author: Generated for business card organization system
Date: 2026-01-22
"""

import os
import re
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import json


@dataclass
class FilePattern:
    """Represents a pattern for matching files."""
    pattern_type: str
    pattern_value: str
    confidence: float
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FilePattern':
        """Create FilePattern from dictionary."""
        return cls(
            pattern_type=data['pattern_type'],
            pattern_value=data['pattern_value'],
            confidence=data['confidence']
        )


@dataclass
class MetaFileNodeSchema:
    """Defines the rules for identifying and processing a file type."""
    name: str
    path: str
    description: str
    purpose: str
    core_properties: List[str]
    optional_properties: List[str]
    property_descriptions: Dict[str, str]
    patterns: List[FilePattern]
    user_review_required: bool = True
    relocatable: bool = True
    review_priority: int = 5
    remove_source: Dict[str, any] = field(default_factory=dict)
    category_inference: Dict[str, List[str]] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'MetaFileNodeSchema':
        data = yaml.safe_load(yaml_content)
        patterns_data = data.get('patterns', [])
        if isinstance(patterns_data, str):
            patterns_data = json.loads(patterns_data)
        patterns = [FilePattern.from_dict(p) for p in patterns_data]
        return cls(
            name=data.get('name', ''),
            path=data.get('path', ''),
            description=data.get('description', ''),
            purpose=data.get('purpose', ''),
            core_properties=data.get('core_properties', []),
            optional_properties=data.get('optional_properties', []),
            property_descriptions=data.get('property_descriptions', {}),
            patterns=patterns,
            user_review_required=data.get('user_review_required', True),
            relocatable=data.get('relocatable', True),
            review_priority=data.get('review_priority', 5),
            remove_source=data.get('remove_source', {}),
            category_inference=data.get('category_inference', {})
        )
    
    @classmethod
    def from_yaml_file(cls, filepath: str) -> 'MetaFileNodeSchema':
        with open(filepath, 'r') as f:
            return cls.from_yaml(f.read())


@dataclass
class BusinessCardMetadata:
    filename: str = ""
    filepath: str = ""
    timestamp_extracted: Optional[str] = None
    description: str = ""
    category: str = ""
    contact_name: str = ""
    phone: str = ""
    context_note: str = ""
    phone_1800: str = ""
    cell: str = ""
    fax: str = ""
    email: str = ""
    company: str = ""
    location: str = ""
    instagram: str = ""
    url: str = ""
    recommendation: str = ""
    confidence_score: float = 0.0
    pattern_matched: str = ""
    needs_review: bool = True
    schema_name: str = ""
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        return {k: v for k, v in data.items() 
                if v not in ("", None, 0.0) or k in 
                ['description', 'category', 'contact_name', 'phone', 'context_note']}


class BusinessCardEvaluator:
    def __init__(self, schema: MetaFileNodeSchema):
        self.schema = schema
        self.base_path = Path(schema.path)
        
    def evaluate_file(self, filepath: str) -> Tuple[bool, float, BusinessCardMetadata]:
        file_path = Path(filepath)
        filename = file_path.name
        metadata = BusinessCardMetadata(filename=filename, filepath=str(file_path), schema_name=self.schema.name)
        is_match, confidence, pattern = self._check_patterns(filename, file_path.suffix)
        if is_match:
            metadata.confidence_score = confidence
            metadata.pattern_matched = pattern
            metadata.needs_review = self.schema.user_review_required
            self._extract_from_filename(filename, metadata)
            metadata.timestamp_extracted = self._extract_timestamp(filename)
        return is_match, confidence, metadata
    
    def evaluate_directory(self, directory: str, min_confidence: float = 0.0) -> List[BusinessCardMetadata]:
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        results = []
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                is_match, confidence, metadata = self.evaluate_file(str(file_path))
                if is_match and confidence >= min_confidence:
                    results.append(metadata)
        return results
    
    def _check_patterns(self, filename: str, extension: str) -> Tuple[bool, float, str]:
        matched, max_confidence, matched_pattern = False, 0.0, ""
        for pattern in self.schema.patterns:
            if pattern.pattern_type == "filename_contains" and pattern.pattern_value in filename:
                if pattern.confidence > max_confidence:
                    max_confidence, matched_pattern, matched = pattern.confidence, pattern.pattern_value, True
            elif pattern.pattern_type == "file_extension" and extension.lower() == pattern.pattern_value.lower():
                if pattern.confidence > max_confidence:
                    max_confidence, matched_pattern, matched = pattern.confidence, f"extension:{extension}", True
        return matched, max_confidence, matched_pattern
    
    def _extract_timestamp(self, filename: str) -> Optional[str]:
        for pattern in [r'(\d{4})_(\d{4})', r'(\d{4})(\d{2})(\d{2})']:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 2:
                        year, mmdd = groups
                        month, day = mmdd[:2], mmdd[2:]
                    else:
                        year, month, day = groups
                    return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
                except (ValueError, IndexError):
                    continue
        return None
    
    def _extract_from_filename(self, filename: str, metadata: BusinessCardMetadata):
        name_parts = Path(filename).stem.split('-')
        parts = [p for p in name_parts if not re.match(r'^\d{4}_?\d{4}$', p)]
        parts = [p for p in parts if 'buscard' not in p.lower() or p.lower() == 'buscardish']
        if len(parts) >= 1:
            category_guess = self._infer_category(parts[0])
            if category_guess:
                metadata.category = category_guess
                metadata.description = f"{category_guess.title()} services"
        if len(parts) >= 2:
            metadata.company = parts[1].replace('_', ' ').title()
        if metadata.company:
            metadata.context_note = f"Card received - {metadata.company}"
    
    def _infer_category(self, keyword: str) -> str:
        keyword_lower = keyword.lower()
        if self.schema.category_inference:
            for category, keywords in self.schema.category_inference.items():
                if any(kw in keyword_lower for kw in keywords):
                    return category
        return keyword_lower
    
    def generate_report(self, metadata: BusinessCardMetadata) -> str:
        return (f"File: {metadata.filename}\nConfidence: {metadata.confidence_score:.0%}\n"
                f"Category: {metadata.category or 'Unknown'}\nCompany: {metadata.company or 'Not extracted'}")


if __name__ == "__main__":
    pass
