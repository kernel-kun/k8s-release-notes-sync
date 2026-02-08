#!/usr/bin/env python3
"""
Script to compress release notes JSON file by extracting only essential fields.

This script reads a release notes JSON file and creates a compressed version
containing only PR number, text, and pr_url for each entry.

Usage:
    python compress_release_notes.py <input_file> <output_file>
    
Example:
    python compress_release_notes.py sample.json compressed.json
"""

import json
import sys
import os


def compress_release_notes(input_file, output_file):
    """
    Extract PR number, text, and pr_url from release notes JSON.
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str): Path to the output JSON file
    """
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    # Read the input JSON file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read input file: {e}")
        sys.exit(1)
    
    # Create compressed version with only required fields
    compressed_data = {}
    
    for pr_number, pr_data in data.items():
        compressed_data[pr_number] = {
            "pr_number": pr_data.get("pr_number"),
            "text": pr_data.get("text"),
            "pr_url": pr_data.get("pr_url")
        }
    
    # Write the compressed data to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(compressed_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully created compressed file: {output_file}")
        print(f"Processed {len(compressed_data)} PR entries")
    except Exception as e:
        print(f"Error: Failed to write output file: {e}")
        sys.exit(1)


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) != 3:
        print("Usage: python compress_release_notes.py <input_file> <output_file>")
        print("\nExample:")
        print("  python compress_release_notes.py sample.json compressed.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    compress_release_notes(input_file, output_file)


if __name__ == "__main__":
    main()
