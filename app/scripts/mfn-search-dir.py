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
        """
        Load schema from YAML content.
        Alternative constructor that parses YAML and creates a schema instance.
        """
        data = yaml.safe_load(yaml_content)
        
        # Parse patterns from string if needed
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
        """Load schema from YAML file."""
        with open(filepath, 'r') as f:
            return cls.from_yaml(f.read())


@dataclass
class BusinessCardMetadata:
    """The extracted data from one specific business card file."""
    
    # File information
    filename: str = ""
    filepath: str = ""
    timestamp_extracted: Optional[str] = None
    
    # Core properties (required)
    description: str = ""
    category: str = ""
    contact_name: str = ""
    phone: str = ""
    context_note: str = ""
    
    # Optional properties
    phone_1800: str = ""
    cell: str = ""
    fax: str = ""
    email: str = ""
    company: str = ""
    location: str = ""
    instagram: str = ""
    url: str = ""
    recommendation: str = ""
    
    # Evaluation results
    confidence_score: float = 0.0
    pattern_matched: str = ""
    needs_review: bool = True
    
    # Schema reference
    schema_name: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding empty optional fields."""
        data = asdict(self)
        return {k: v for k, v in data.items() 
                if v not in ("", None, 0.0) or k in 
                ['description', 'category', 'contact_name', 'phone', 'context_note']}


class BusinessCardEvaluator:
    """Evaluates files against patterns defined in META-FILE-NODE schema."""
    
    def __init__(self, schema: MetaFileNodeSchema):
        """
        Initialize evaluator with a META-FILE-NODE schema.
        
        Args:
            schema: MetaFileNodeSchema object containing patterns and metadata
        """
        self.schema = schema
        self.base_path = Path(schema.path)
        
    def evaluate_file(self, filepath: str) -> Tuple[bool, float, BusinessCardMetadata]:
        """
        Evaluate if file matches business card patterns from schema.
        
        Args:
            filepath: Path to file to evaluate
            
        Returns:
            Tuple of (is_match, confidence, metadata)
        """
        file_path = Path(filepath)
        filename = file_path.name
        
        # Initialize metadata
        metadata = BusinessCardMetadata(
            filename=filename,
            filepath=str(file_path),
            schema_name=self.schema.name
        )
        
        # Check patterns from schema
        is_match, confidence, pattern = self._check_patterns(filename, file_path.suffix)
        
        if is_match:
            metadata.confidence_score = confidence
            metadata.pattern_matched = pattern
            metadata.needs_review = self.schema.user_review_required
            
            # Extract information from filename
            self._extract_from_filename(filename, metadata)
            
            # Extract timestamp if present
            metadata.timestamp_extracted = self._extract_timestamp(filename)
        
        return is_match, confidence, metadata
    
    def evaluate_directory(self, directory: str, min_confidence: float = 0.0) -> List[BusinessCardMetadata]:
        """
        Evaluate all files in a directory, returning matches.
        
        Args:
            directory: Directory path to scan
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            List of BusinessCardMetadata for matched files
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            print(f"Error: Directory '{directory}' does not exist")
            return []
        
        if not dir_path.is_dir():
            print(f"Error: '{directory}' is not a directory")
            return []
        
        results = []
        all_files = list(dir_path.iterdir())
        
        print(f"\nScanning directory: {directory}")
        print(f"Found {len(all_files)} total files/folders")
        print(f"Minimum confidence threshold: {min_confidence:.0%}\n")
        
        for file_path in all_files:
            if file_path.is_file():
                is_match, confidence, metadata = self.evaluate_file(str(file_path))
                
                if is_match and confidence >= min_confidence:
                    results.append(metadata)
                    print(f"✓ MATCH: {file_path.name} (confidence: {confidence:.0%})")
                else:
                    print(f"✗ Skip:  {file_path.name} (confidence: {confidence:.0%})")
        
        print(f"\n{'='*70}")
        print(f"Matched {len(results)} files out of {len([f for f in all_files if f.is_file()])} total files")
        print(f"{'='*70}\n")
        
        return results
    
    def _check_patterns(self, filename: str, extension: str) -> Tuple[bool, float, str]:
        """Check filename against patterns defined in schema."""
        matched = False
        max_confidence = 0.0
        matched_pattern = ""
        
        for pattern in self.schema.patterns:
            if pattern.pattern_type == "filename_contains":
                if pattern.pattern_value in filename:
                    conf = pattern.confidence
                    if conf > max_confidence:
                        max_confidence = conf
                        matched_pattern = pattern.pattern_value
                        matched = True
                        
            elif pattern.pattern_type == "file_extension":
                if extension.lower() == pattern.pattern_value.lower():
                    conf = pattern.confidence
                    if conf > max_confidence:
                        max_confidence = conf
                        matched_pattern = f"extension:{extension}"
                        matched = True
        
        return matched, max_confidence, matched_pattern
    
    def _extract_timestamp(self, filename: str) -> Optional[str]:
        """Extract timestamp from filename patterns like 2026_0101."""
        patterns = [
            r'(\d{4})_(\d{4})',  # 2026_0101
            r'(\d{4})(\d{2})(\d{2})',  # 20260101
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    if len(match.groups()) == 2:
                        year, mmdd = match.groups()
                        month = mmdd[:2]
                        day = mmdd[2:]
                    else:
                        year, month, day = match.groups()
                    
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime("%Y-%m-%d")
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_from_filename(self, filename: str, metadata: BusinessCardMetadata):
        """Extract business card details from filename structure."""
        name_parts = Path(filename).stem.split('-')
        
        # Skip timestamp part if present
        parts = [p for p in name_parts if not re.match(r'^\d{4}_?\d{4}$', p)]
        
        # Skip busCard/BusCard markers
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
        """Infer business category from keyword using schema's category_inference."""
        keyword_lower = keyword.lower()
        
        # Use schema's category inference if available
        if self.schema.category_inference:
            for category, keywords in self.schema.category_inference.items():
                if any(kw in keyword_lower for kw in keywords):
                    return category
        
        # Fallback to returning the keyword itself
        return keyword_lower
    
    def generate_report(self, metadata: BusinessCardMetadata) -> str:
        """Generate a human-readable report of extracted metadata."""
        report = f"""
Business Card Evaluation Report
================================
Schema: {metadata.schema_name}
File: {metadata.filename}
Confidence: {metadata.confidence_score:.0%}
Pattern Matched: {metadata.pattern_matched}
Date Extracted: {metadata.timestamp_extracted or 'Not found'}

Extracted Metadata:
-------------------
Category: {metadata.category or 'Unknown'}
Company: {metadata.company or 'Not extracted'}
Contact Name: {metadata.contact_name or 'Needs review'}
Description: {metadata.description or 'Needs review'}

Schema Patterns Available:
"""
        
        report += f"\nStatus: {'REVIEW REQUIRED' if metadata.needs_review else 'Ready'}"
        return report


def main():
    """Command-line interface for business card evaluation."""
    parser = argparse.ArgumentParser(
        description='Evaluate business card files using META-FILE-NODE schema patterns'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory to scan for business card files (default: current directory)'
    )
    parser.add_argument(
        '--schema',
        default=None,
        help='Path to YAML schema file (if not provided, uses embedded example)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold 0.0-1.0 (default: 0.5)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed reports for each match'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    # Load schema
    if args.schema:
        print(f"Loading schema from: {args.schema}")
        schema = MetaFileNodeSchema.from_yaml_file(args.schema)
    else:
        # Use embedded example schema
        yaml_schema = """
META-FILE-NODE: BusinessCard_20260121

name: "Business Card"
path: "E:\\\\Reference\\\\BusinessCards"
description: "Business card scans via dropbox or other, collected in-person or received"
purpose: "Searchable contact source information. Professional connections, trades and other service providers"

core_properties:
  - description
  - category
  - contact_name
  - phone
  - context_note

optional_properties:
  - phone_1800
  - cell
  - fax
  - email
  - company
  - location
  - instagram
  - url
  - recommendation

property_descriptions:
  description: "Brief description of services, products, or what this contact provides"
  category: "Type of service or business (electrician, lawyer, artist, food sales, etc.)"
  company: "Company or business name"
  contact_name: "Name of person on the card"
  phone: "Business phone number or direct to provider"

patterns: '[
  {"pattern_type": "filename_contains", "pattern_value": "busCard", "confidence": 0.95},
  {"pattern_type": "filename_contains", "pattern_value": "Buscard", "confidence": 0.95},
  {"pattern_type": "filename_contains", "pattern_value": "BusCard", "confidence": 0.95},
  {"pattern_type": "filename_contains", "pattern_value": "busCardish", "confidence": 0.85},
  {"pattern_type": "file_extension", "pattern_value": ".pdf", "confidence": 0.3}
]'

category_inference:
  electrician: [electric, electrical, electrician]
  plumber: [plumb, plumbing]
  carpenter: [carpenter, carpentry, woodwork]
  lawyer: [law, lawyer, attorney, legal]
  doctor: [doctor, medical, physician, clinic]
  contractor: [contractor, construction, builder]
  artist: [artist, art, gallery, design]
  food: [restaurant, cafe, food, catering]
  retail: [store, shop, retail, homedepot, lowes]

user_review_required: true
relocatable: true
review_priority: 5
"""
        schema = MetaFileNodeSchema.from_yaml(yaml_schema)
    
    # Create evaluator with schema
    evaluator = BusinessCardEvaluator(schema)
    
    # Evaluate directory
    results = evaluator.evaluate_directory(args.directory, args.min_confidence)
    
    # Output results
    if args.json:
        # JSON output
        json_results = [metadata.to_dict() for metadata in results]
        print(json.dumps(json_results, indent=2))
    
    elif args.report:
        # Detailed reports
        for metadata in results:
            print(evaluator.generate_report(metadata))
            print()
    
    else:
        # Summary output
        if results:
            print("\nMatched Files Summary:")
            print(f"{'Filename':<40} {'Confidence':<12} {'Category':<15} {'Company':<20}")
            print("=" * 90)
            for metadata in results:
                print(f"{metadata.filename:<40} {metadata.confidence_score:>10.0%}  "
                      f"{metadata.category:<15} {metadata.company:<20}")
        else:
            print("\nNo matching business card files found.")


if __name__ == "__main__":
    main()