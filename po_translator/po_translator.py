#!/usr/bin/env python3
"""
Simple PO File Translator using Azure OpenAI API
"""

import os
import re
import sys
import time
import argparse
from typing import List, Dict, Tuple
from openai import AzureOpenAI
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class POTranslator:
    def __init__(self, azure_endpoint: str, api_key: str, deployment_name: str = "gpt-4o-mini",
                 target_language: str = "Korean", chunk_size: int = 50, retranslate: bool = False):
        """Initialize translator with Azure OpenAI credentials."""
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-12-01-preview"
        )
        self.deployment_name = deployment_name
        self.target_language = target_language
        self.chunk_size = chunk_size
        self.retranslate = retranslate
        
    def extract_entries(self, content: str) -> List[Tuple[int, str, str]]:
        """Extract msgid/msgstr pairs that need translation."""
        entries = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                i += 1
                continue
                
            # Look for msgid
            if line.startswith('msgid "'):
                msgid = self._extract_string(line)
                i += 1
                
                # Handle multiline msgid
                while i < len(lines) and lines[i].strip().startswith('"'):
                    msgid += self._extract_string(lines[i].strip())
                    i += 1
                
                # Look for msgstr
                if i < len(lines) and lines[i].strip().startswith('msgstr'):
                    msgstr_line_num = i
                    msgstr = self._extract_string(lines[i].strip())
                    i += 1
                    
                    # Handle multiline msgstr
                    while i < len(lines) and lines[i].strip().startswith('"'):
                        msgstr += self._extract_string(lines[i].strip())
                        i += 1
                    
                    # Skip empty msgid (header entry)
                    if msgid.strip():
                        # Include all entries if retranslate is True, otherwise only empty msgstr
                        if self.retranslate or not msgstr.strip():
                            entries.append((msgstr_line_num, msgid, msgstr))
            else:
                i += 1
                
        return entries
    
    def _extract_string(self, line: str) -> str:
        """Extract string content from quoted line."""
        match = re.search(r'"(.*)"', line)
        return match.group(1) if match else ""
    
    def translate_chunk(self, entries: List[Tuple[int, str, str]]) -> Dict[int, str]:
        """Translate a chunk of entries."""
        if not entries:
            return {}

        # Prepare texts for translation with numbering for better matching
        texts_with_numbers = []
        for i, (_, msgid, _) in enumerate(entries):
            texts_with_numbers.append(f"{i+1}. {msgid}")

        # Create simple prompt
        prompt = f"""Translate these English texts to {self.target_language}.
Return ONLY the translations, one per line, in the exact same order with the same numbering.
Preserve placeholders like {{0}}, %s, and formatting.
Format: "1. [translation]", "2. [translation]", etc.

{chr(10).join(texts_with_numbers)}"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate to {self.target_language}. Preserve formatting and placeholders. Keep the numbering format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )

            # Parse response - extract numbered translations
            response_text = response.choices[0].message.content.strip()
            translations = []

            for line in response_text.split('\n'):
                line = line.strip()
                if line:
                    # Extract translation after number (e.g., "1. translation" -> "translation")
                    match = re.match(r'^\d+\.\s*(.+)$', line)
                    if match:
                        translations.append(match.group(1))
                    else:
                        translations.append(line)  # Fallback if no numbering

            # Map translations to line numbers
            result = {}
            for i, (line_num, msgid, _) in enumerate(entries):
                if i < len(translations) and translations[i]:
                    result[line_num] = translations[i]
                    logger.debug(f"Mapped: '{msgid}' -> '{translations[i]}'")
                else:
                    logger.warning(f"No translation for entry {i+1}: '{msgid}'")

            return result

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {}
    
    def update_file(self, file_path: str, translations: Dict[int, str]) -> bool:
        """Update PO file with translations."""
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Create backup once
            backup_path = f"{file_path}.backup"
            if not os.path.exists(backup_path):
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                logger.info(f"Backup created: {backup_path}")
            
            # Update translations
            updated = 0
            for line_num, translation in translations.items():
                if line_num < len(lines):
                    original = lines[line_num].strip()
                    if original.startswith('msgstr'):
                        # Escape quotes in translation
                        escaped = translation.replace('"', '\\"')
                        lines[line_num] = f'msgstr "{escaped}"\n'
                        updated += 1
            
            # Write updated file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info(f"Updated {updated} translations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update file: {e}")
            return False
    
    def translate_file(self, file_path: str, start_line: int = 0, max_entries: int = None) -> bool:
        """Translate entire PO file."""
        try:
            logger.info(f"Translating {file_path}")
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract entries
            entries = self.extract_entries(content)
            logger.info(f"Found {len(entries)} entries to translate")
            
            if not entries:
                logger.info("No entries to translate")
                return True
            
            # Filter entries
            if start_line > 0:
                entries = [e for e in entries if e[0] >= start_line]
                logger.info(f"Starting from line {start_line}: {len(entries)} entries")
            
            if max_entries:
                entries = entries[:max_entries]
                logger.info(f"Limited to {max_entries} entries")
            
            # Process in chunks
            total_translated = 0
            for i in range(0, len(entries), self.chunk_size):
                chunk = entries[i:i + self.chunk_size]
                chunk_num = i // self.chunk_size + 1
                total_chunks = (len(entries) + self.chunk_size - 1) // self.chunk_size
                
                logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} entries)")
                
                # Translate chunk
                translations = self.translate_chunk(chunk)
                
                if translations:
                    if self.update_file(file_path, translations):
                        total_translated += len(translations)
                    else:
                        return False
                
                # Rate limiting
                if i + self.chunk_size < len(entries):
                    time.sleep(1)
            
            logger.info(f"Translation completed: {total_translated} entries translated")
            return True
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return False

def load_config():
    """Load configuration from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    return {
        'azure_endpoint': os.getenv('AZURE_ENDPOINT'),
        'api_key': os.getenv('AZURE_API_KEY'),
        'deployment_name': os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4.1-mini'),
        'target_language': os.getenv('TARGET_LANGUAGE', 'Korean'),
        'chunk_size': int(os.getenv('CHUNK_SIZE', '50'))
    }

def prompt_for_config(config):
    """Prompt for missing configuration."""
    if not config['azure_endpoint']:
        config['azure_endpoint'] = input("Enter Azure OpenAI Endpoint: ").strip()
    
    if not config['api_key']:
        config['api_key'] = input("Enter Azure OpenAI API Key: ").strip()
    
    return config['azure_endpoint'] and config['api_key']

def main():
    parser = argparse.ArgumentParser(description='Translate PO files using Azure OpenAI')
    parser.add_argument('file_path', nargs='?', help='Path to PO file')
    parser.add_argument('--azure-endpoint', help='Azure OpenAI endpoint')
    parser.add_argument('--api-key', help='Azure OpenAI API key')
    parser.add_argument('--deployment-name', help='Deployment name')
    parser.add_argument('--target-language', help='Target language')
    parser.add_argument('--start-line', type=int, default=0, help='Start from line number')
    parser.add_argument('--max-entries', type=int, help='Maximum entries to translate')
    parser.add_argument('--chunk-size', type=int, help='Chunk size')
    parser.add_argument('--retranslate', action='store_true', help='Retranslate existing translations')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Override with command line arguments
    if args.azure_endpoint:
        config['azure_endpoint'] = args.azure_endpoint
    if args.api_key:
        config['api_key'] = args.api_key
    if args.deployment_name:
        config['deployment_name'] = args.deployment_name
    if args.target_language:
        config['target_language'] = args.target_language
    if args.chunk_size:
        config['chunk_size'] = args.chunk_size
    
    # Prompt for missing config
    if not config['azure_endpoint'] or not config['api_key']:
        if not prompt_for_config(config):
            logger.error("Azure endpoint and API key are required")
            sys.exit(1)
    
    # Get file path
    if not args.file_path:
        locale_dir = Path("apps/occam/occam/locale")
        if locale_dir.exists():
            po_files = list(locale_dir.glob("*-ko.po"))
            if po_files:
                print("Available PO files:")
                for i, po_file in enumerate(po_files, 1):
                    print(f"  {i}. {po_file.name}")
                
                while True:
                    choice = input("\nSelect file (number or path): ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(po_files):
                        args.file_path = str(po_files[int(choice) - 1])
                        break
                    elif os.path.exists(choice):
                        args.file_path = choice
                        break
                    else:
                        print("Invalid choice")
        
        if not args.file_path:
            args.file_path = input("Enter PO file path: ").strip()
    
    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        sys.exit(1)
    
    # Initialize translator
    translator = POTranslator(
        azure_endpoint=config['azure_endpoint'],
        api_key=config['api_key'],
        deployment_name=config['deployment_name'],
        target_language=config['target_language'],
        chunk_size=config['chunk_size'],
        retranslate=args.retranslate
    )
    
    # Translate
    success = translator.translate_file(
        args.file_path,
        start_line=args.start_line,
        max_entries=args.max_entries
    )
    
    if success:
        logger.info("Translation completed successfully!")
        sys.exit(0)
    else:
        logger.error("Translation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
