#!/usr/bin/env python3
"""
MDX to Korean Translation Script
Translates all MDX files while preserving code blocks and structure.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional
import sys
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
SOURCE_DIRS = ["world-id", "mini-apps", "agents", "world-chain", "snippets"]
OUTPUT_DIR = "docs/ko"
CACHE_FILE = ".translation-cache.json"
MODEL = "gpt-4-turbo"

def load_cache() -> dict:
    """Load translation cache."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict):
    """Save translation cache."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def extract_frontmatter(content: str) -> tuple[str, str]:
    """Extract frontmatter from MDX file."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return "", content

def preserve_code_blocks(content: str) -> tuple[str, dict]:
    """Extract code blocks to preserve them."""
    code_blocks = {}
    counter = 0
    
    # Match code blocks with ``` or ```language
    pattern = r'```(?:[a-z\-]*\n)?[\s\S]*?```'
    
def replace_code(match):
        nonlocal counter
        placeholder = f"__CODE_BLOCK_{counter}__"
        code_blocks[placeholder] = match.group(0)
        counter += 1
        return placeholder
    
    modified_content = re.sub(pattern, replace_code, content)
    return modified_content, code_blocks

def restore_code_blocks(content: str, code_blocks: dict) -> str:
    """Restore code blocks."""
    for placeholder, code in code_blocks.items():
        content = content.replace(placeholder, code)
    return content

def preserve_jsx_components(content: str) -> tuple[str, dict]:
    """Preserve JSX components like <Card>, <Note>, etc."""
    jsx_blocks = {}
    counter = 0
    
    # Match JSX components
    pattern = r'<[A-Z][^>]*(?:>[^<]*?</[A-Z][^>]*>|/>)'
    
def replace_jsx(match):
        nonlocal counter
        placeholder = f"__JSX_BLOCK_{counter}__"
        jsx_blocks[placeholder] = match.group(0)
        counter += 1
        return placeholder
    
    modified_content = re.sub(pattern, replace_jsx, content)
    return modified_content, jsx_blocks

def restore_jsx_blocks(content: str, jsx_blocks: dict) -> str:
    """Restore JSX blocks."""
    for placeholder, jsx in jsx_blocks.items():
        content = content.replace(placeholder, jsx)
    return content

def translate_text(text: str, cache: dict) -> str:
    """Translate text to Korean using OpenAI."""
    if not text.strip():
        return text
    
    # Check cache
    cache_key = f"md5_{hash(text) % ((sys.maxsize + 1) * 2)}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional Korean translator. Translate the given text to Korean. Preserve markdown formatting, links, and placeholders. Only translate actual content, not code or technical terms that should remain in English."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.3,
            max_tokens=4000,
            timeout=30
        )
        
        translated = response.choices[0].message.content
        cache[cache_key] = translated
        return translated
    except Exception as e:
        print(f"Warning: Translation failed: {e}")
        return text

def translate_frontmatter(frontmatter: str, cache: dict) -> str:
    """Translate frontmatter fields."""
    lines = frontmatter.split('\n')
    translated_lines = []
    
    for line in lines:
        if ':' in line and not line.strip().startswith('#'):
            key, value = line.split(':', 1)
            # Translate certain fields
            if any(field in key for field in ['title', 'description', 'sidebarTitle']):
                value = translate_text(value.strip(), cache)
                line = f"{key}: {value}"
        translated_lines.append(line)
    
    return '\n'.join(translated_lines)

def translate_mdx_file(input_path: str, cache: dict) -> str:
    """Translate MDX file content."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract frontmatter
    frontmatter, body = extract_frontmatter(content)
    
    # Preserve code blocks
    body_without_code, code_blocks = preserve_code_blocks(body)
    
    # Preserve JSX components
    body_without_code_jsx, jsx_blocks = preserve_jsx_components(body_without_code)
    
    # Translate remaining content
    translated_body = translate_text(body_without_code_jsx, cache)
    
    # Restore JSX and code blocks
    translated_body = restore_jsx_blocks(translated_body, jsx_blocks)
    translated_body = restore_code_blocks(translated_body, code_blocks)
    
    # Translate frontmatter
    if frontmatter:
        translated_frontmatter = translate_frontmatter(frontmatter, cache)
        result = f"---\n{translated_frontmatter}\n---\n{translated_body}"
    else:
        result = translated_body
    
    return result

def process_mdx_files():
    """Process all MDX files."""
    cache = load_cache()
    processed = 0
    
    for source_dir in SOURCE_DIRS:
        if not os.path.exists(source_dir):
            print(f"Skipping {source_dir} - directory not found")
            continue
        
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.mdx'):
                    input_path = os.path.join(root, file)
                    
                    # Create output path
                    rel_path = os.path.relpath(input_path, source_dir)
                    output_path = os.path.join(OUTPUT_DIR, source_dir, rel_path)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    print(f"Translating: {input_path}...", end=" ", flush=True)
                    
                    try:
                        translated = translate_mdx_file(input_path, cache)
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(translated)
                        print("✓")
                        processed += 1
                    except Exception as e:
                        print(f"✗ Error: {e}")
    
    # Save cache
    save_cache(cache)
    print(f"\nTranslation complete! Processed {processed} files.")
    print(f"Output: {OUTPUT_DIR}/")

def main():
    """Main entry point."""
    print("MDX to Korean Translator")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    process_mdx_files()

if __name__ == "__main__":
    main()
