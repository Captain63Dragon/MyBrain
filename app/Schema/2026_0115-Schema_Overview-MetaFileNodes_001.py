# SCHEMA OVERVIEW - Draft 1

# NODE TYPES
# **********
#   META-FILE-NODE
#   FILE-NODE
#   TAG-NODE
#   PATTERN-NODE (Optional - may be embedded in META-FILE-NODE instead)


# FILE-NODE
# *********
# Core Properties:

# filepath (string, required) - absolute path to actual file
# description (string, optional) - human-readable summary of file content

# Dynamic Properties:

# Defined by associated META-FILE-NODE type
# Examples: contact_name, company, phone, vendor, amount, location, issue
# Populated via OCR suggestion + user confirmation
# Properties vary by file type

# Metadata:

# review_status (enum: unreviewed | reviewed | needs_review | archived)
# Note: following suppliment file system creation/modification contained in the file system records.
# node_created (datetime) - when FILE-NODE was created
# node_modified (datetime) - when FILE-NODE was last updated

# META-FILE-NODE
# *********
# Identity:

# name (string, required) - human-readable category name
# path (string, required) - physical folder or sub folder location in filesystem

# Purpose:

# description (string, required) - organizing principal behind creation of this category
# purpose (string, required) - functional role of this category

# Schema Definition:

# suggested_properties (list of strings) - property names that FILE-NODEs of this type should have
# property_descriptions (dictionary) - explanation of what each property means if not obvious. can be null set
# required_properties (list of strings) - subset of suggested_properties that must be filled

# Processing Rules:

# patterns (list of dictionaries) - matching rules for categorization

# pattern_type (filename_contains | date_range | file_extension | keyword)
# pattern_value (the actual pattern to match)
# confidence (float 0.0-1.0) - reliability of this pattern


# ocr_extract (boolean) - whether to run OCR on files of this type
# user_review_required (boolean) - whether suggestions need confirmation
# priority (integer) - for resolving conflicts when multiple META-FILE-NODEs match

# Relationships:

# parent_meta_node (optional) - for hierarchical folder structures
# similar_categories (list) - related META-FILE-NODEs to check if this doesn't match


# TAG-NODE
# Properties:

# name (string, required) - the tag itself
# category (string, optional) - type of tag (subject | person | project | location)
# created_date (datetime)

# Usage:

# Manual tags applied by user
# Auto-generated tags from OCR or filename parsing
# Used for cross-cutting organization beyond folder structure


# PATTERN-NODE (Optional - may be embedded in META-FILE-NODE instead)
# Properties:

# pattern_type (enum)
# pattern_value (string)
# confidence (float)

# Purpose:

# Reusable matching rules
# Can be shared across multiple META-FILE-NODEs
# Tracks effectiveness over time


# RELATIONSHIPS
# FILE-NODE Relationships:

# STORED_IN → META-FILE-NODE (current physical location)
# SUGGESTED_FOR → META-FILE-NODE (system thinks it belongs here)
# TAGGED_WITH → TAG-NODE (manual or auto tags)
# RELATES_TO → FILE-NODE (discovered connections)
# EXTRACTED_FROM → FILE-NODE (if this file was derived from another)

# META-FILE-NODE Relationships:

# PARENT_OF → META-FILE-NODE (folder hierarchy)
# MATCHES_PATTERN → PATTERN-NODE (categorization rules)
# SUGGESTS_CHECKING → META-FILE-NODE (alternative categories)
# CONFLICTS_WITH → META-FILE-NODE (mutually exclusive categories)

# TAG-NODE Relationships:

# APPLIED_TO → FILE-NODE (which files have this tag)
# RELATED_TAG → TAG-NODE (tag synonyms or associations)


# WORKFLOW OVERVIEW
# Phase 1: File Discovery

# Scan filesystem folder (e.g., Dropbox/Incoming)
# Create FILE-NODE for each file with filepath
# Parse filename using naming convention (YYYY_MMDD-type-subject.ext)
# Set initial review_status = "unreviewed"

# Phase 2: Categorization

# Extract filename components (date, type, subject)
# Check against all META-FILE-NODE patterns
# Find matching META-FILE-NODEs (may be multiple)
# Rank by confidence and priority
# Create SUGGESTED_FOR relationship to top candidate(s)

# Phase 3: Property Extraction

# If matched META-FILE-NODE has ocr_extract = true:

# Run OCR on file
# Extract suggested_properties based on META-FILE-NODE schema
# Store as temporary suggestions


# Generate auto-description from filename + OCR content

# Phase 4: User Review

# Present file to user with:

# Filename and preview
# Suggested META-FILE-NODE category
# Suggested property values (if OCR ran)
# Auto-generated description


# User confirms/edits:

# Accepts or changes category
# Confirms or modifies extracted properties
# Edits or approves description


# Update FILE-NODE with confirmed data
# Create STORED_IN relationship to confirmed META-FILE-NODE
# Set review_status = "reviewed"

# Phase 5: File Organization

# Move physical file to META-FILE-NODE path (optional)
# Or keep file where it is and rely on graph for organization
# Log action for potential undo

# Phase 6: Learning & Refinement

# Track which patterns successfully matched
# Update META-FILE-NODE confidence scores
# Suggest new patterns based on user corrections
# Flag META-FILE-NODEs that are never used (candidates for deletion)
# Identify frequently co-occurring tags (suggest new META-FILE-NODEs)


# EXTENSIBILITY POINTS
# ********************
# New File Types:

# Create new META-FILE-NODE with custom suggested_properties
# Define type-specific patterns
# No code changes needed

# New Extraction Methods:

# Beyond OCR: EXIF for photos, PDF metadata, etc.
# Hook into Phase 3 workflow
# Results populate FILE-NODE dynamic properties

# Custom Workflows:

# Add new review_status values
# Create workflow-specific relationships
# Chain multiple processing steps

# Integration Points:

# External tools can query graph for files
# Natural language query layer (future)
# Automated reporting/dashboards
# Mobile capture interface


# DESIGN PRINCIPLES

# Minimal duplication - Don't store what can be parsed or queried
# User in control - System suggests, user decides
# Extensible schemas - FILE-NODEs adapt to META-FILE-NODE definitions
# Learning system - Improves from user feedback
# Graceful degradation - Works even with incomplete metadata


# END SCHEMA OVERVIEW - Draft 1