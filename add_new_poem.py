#!/usr/bin/env python3
"""
Interactive script to add new poems to the collection.

This script prompts for metadata, creates a properly formatted .md file
in the poems/ directory, and opens it in the user's default text editor.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from slugify import slugify


def get_user_input(prompt, required=True, default=None):
    """Get user input with optional default value."""
    if default:
        prompt += f" (default: {default})"
    prompt += ": "
    
    while True:
        value = input(prompt).strip()
        
        if value:
            return value
        elif default:
            return default
        elif not required:
            return None
        else:
            print("This field is required. Please enter a value.")


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


def create_filename(title, author):
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
            os.startfile(file_path)
        elif system == "Linux":
            # Try common Linux editors
            editors = ["xdg-open", "gedit", "kate", "nano", "vim"]
            for editor in editors:
                try:
                    subprocess.run([editor, file_path], check=True)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            else:
                print(f"Could not open editor. Please manually edit: {file_path}")
                return False
        
        return True
        
    except Exception as e:
        print(f"Error opening editor: {e}")
        print(f"Please manually edit: {file_path}")
        return False


def main():
    print("=" * 60)
    print("Poetry to Anki - Add New Poem")
    print("=" * 60)
    print()
    print("This script will help you add a new poem to your collection.")
    print("It will create a properly formatted .md file and open it for editing.")
    print()
    
    # Ensure poems directory exists
    poems_dir = Path("poems")
    poems_dir.mkdir(exist_ok=True)
    
    # Collect metadata
    print("Please enter the poem information:")
    print("(Required fields are marked with *)")
    print()
    
    title = get_user_input("* Poem title", required=True)
    author = get_user_input("* Author name", required=True)
    
    # Optional fields
    collection = get_user_input("Collection/Book name", required=False)
    
    # Year with validation
    while True:
        year_input = get_user_input("Publication year", required=False)
        if not year_input:
            year = None
            break
        year = validate_year(year_input)
        if year is not None:
            break
    
    # URL with validation
    while True:
        url_input = get_user_input("Source URL", required=False)
        if not url_input:
            url = None
            break
        url = validate_url(url_input)
        if url is not None:
            break
    
    # Create filename
    filename = create_filename(title, author)
    file_path = poems_dir / filename
    
    # Check if file already exists
    if file_path.exists():
        print(f"\nWarning: File '{filename}' already exists!")
        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if overwrite not in ['y', 'yes']:
            print("Operation cancelled.")
            return
    
    # Create YAML frontmatter
    frontmatter_lines = ["---"]
    frontmatter_lines.append(f'title: "{title}"')
    frontmatter_lines.append(f'author: "{author}"')
    
    if collection:
        frontmatter_lines.append(f'collection: "{collection}"')
    
    if year:
        frontmatter_lines.append(f'year: {year}')
    
    if url:
        frontmatter_lines.append(f'url: "{url}"')
    
    frontmatter_lines.append("---")
    frontmatter_lines.append("")  # Empty line after frontmatter
    frontmatter_lines.append("Delete this line and paste your poem here.")
    frontmatter_lines.append("")
    
    # Write the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(frontmatter_lines))
        
        print(f"\n✓ Created file: {file_path}")
        print(f"✓ Metadata added with title: {title}")
        print(f"✓ Author: {author}")
        
        if collection:
            print(f"✓ Collection: {collection}")
        if year:
            print(f"✓ Year: {year}")
        if url:
            print(f"✓ Source URL: {url}")
        
        print("\nOpening file in your default text editor...")
        print("Please add the poem text and save the file.")
        print()
        
        # Open in editor
        if open_file_in_editor(str(file_path)):
            print("✓ File opened in editor")
        
        print("\nNext steps:")
        print("1. Add your poem text to the file (replace the comments)")
        print("2. Save and close the file")
        print("3. Run 'python poetry_to_anki.py' to generate Anki cards")
        print()
        print("The poem will be automatically included in your deck!")
        
    except Exception as e:
        print(f"Error creating file: {e}")
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
