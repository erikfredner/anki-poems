#!/usr/bin/env python3
"""
Interactive script to add new poems to the collection.

This script prompts for metadata, creates a properly formatted .md file
in the poems/ directory, and opens it in the user's default text editor.
"""

import sys
import subprocess
import platform
from pathlib import Path
from slugify import slugify


def get_validated_input(prompt, validator=None, required=True, default=None):
    """Get user input with optional validation."""
    if default:
        prompt += f" (default: {default})"
    prompt += ": "
    
    while True:
        value = input(prompt).strip()
        
        if not value:
            if default:
                return default
            elif not required:
                return None
            else:
                print("This field is required. Please enter a value.")
                continue
        
        if validator:
            result = validator(value)
            if result is not None:
                return result
            # validator prints its own error message
        else:
            return value


def validate_year(year_str):
    """Validate and convert year input."""
    if not year_str:
        return None
    
    try:
        year = int(year_str)
        if 1000 <= year <= 2100:  # Reasonable range for poetry
            return year
        else:
            print("Please enter a year between 1000 and 2100.")
            return None
    except ValueError:
        print("Please enter a valid year (numbers only).")
        return None


def validate_url(url_str):
    """Basic URL validation."""
    if not url_str:
        return None
    
    if url_str.startswith(('http://', 'https://')):
        return url_str
    else:
        print("URL should start with http:// or https://")
        return None


def create_yaml_frontmatter(title, author, collection=None, year=None, url=None):
    """Create YAML frontmatter content."""
    content = ["---", f'title: "{title}"', f'author: "{author}"']
    
    if collection:
        content.append(f'collection: "{collection}"')
    if year:
        content.append(f'year: {year}')
    if url:
        content.append(f'url: "{url}"')
    
    content.extend(["---", "", "Delete this line and paste your poem here.", ""])
    return '\n'.join(content)


def create_filename(title, author):
    """Create a safe filename from title and author."""
    base_name = slugify(title, max_length=50)
    
    if len(base_name) < 10 or base_name in ['poem', 'sonnet', 'ode', 'song']:
        author_slug = slugify(author, max_length=20)
        base_name = f"{author_slug}_{base_name}"
    
    return f"{base_name}.md"
    """Create a safe filename from title and author."""
    # Use title as primary identifier
    base_name = slugify(title, max_length=50)
    
    # If title is very short or generic, add author
    if len(base_name) < 10 or base_name in ['poem', 'sonnet', 'ode', 'song']:
        author_slug = slugify(author, max_length=20)
        base_name = f"{author_slug}_{base_name}"
    
    return f"{base_name}.md"


def open_file_in_editor(file_path):
    """Open the file in the user's default text editor."""
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(["open", file_path], check=True)
        elif system == "Windows":
            import os
            os.startfile(file_path)  # type: ignore
        else:  # Linux and others
            editors = ["xdg-open", "gedit", "kate", "nano", "vim"]
            for editor in editors:
                try:
                    subprocess.run([editor, file_path], check=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            print(f"Could not open editor. Please manually edit: {file_path}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error opening editor: {e}")
        print(f"Please manually edit: {file_path}")
        return False


def main():
    print("Poetry to Anki - Add New Poem")
    print("=" * 40)
    
    poems_dir = Path("poems")
    poems_dir.mkdir(exist_ok=True)
    
    print("Enter poem information (* = required):")
    
    title = get_validated_input("* Poem title", required=True)
    author = get_validated_input("* Author name", required=True)
    collection = get_validated_input("Collection/Book name", required=False)
    year = get_validated_input("Publication year", validator=validate_year, required=False)
    url = get_validated_input("Source URL", validator=validate_url, required=False)
    
    # Create and write file
    filename = create_filename(title, author)
    file_path = poems_dir / filename
    
    if file_path.exists():
        overwrite = input(f"\nFile '{filename}' exists. Overwrite? (y/N): ").strip().lower()
        if overwrite not in ['y', 'yes']:
            print("Operation cancelled.")
            return 1
    
    try:
        file_path.write_text(create_yaml_frontmatter(title, author, collection, year, url), encoding='utf-8')
        
        print(f"\n✓ Created: {file_path}")
        metadata_parts = [f"Title: {title}", f"Author: {author}"]
        if collection:
            metadata_parts.append(f"Collection: {collection}")
        if year:
            metadata_parts.append(f"Year: {year}")
        if url:
            metadata_parts.append(f"Source: {url}")
        print("✓ " + " | ".join(metadata_parts))
        
        if open_file_in_editor(str(file_path)):
            print("✓ Opened in editor")
            print("\nNext: Add poem text, save, then run 'python poetry_to_anki.py'")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
