#!/usr/bin/env python3
"""
Simple PO file merger: Merge xxx-yy.po files into yy.po
Usage: python merge_po.py [target_lang]
Example: python merge_po.py ko  # merges *-ko.po files into ko.po
"""

import os
import sys
import glob
import re
from datetime import datetime

def extract_entries(po_content):
    """Extract msgid/msgstr pairs from PO content"""
    entries = {}
    
    # Split into blocks by double newlines
    blocks = re.split(r'\n\s*\n', po_content)
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Look for msgid/msgstr pairs
        msgid_match = re.search(r'msgid\s+"((?:[^"\\]|\\.)*)"', block)
        msgstr_match = re.search(r'msgstr\s+"((?:[^"\\]|\\.)*)"', block)
        
        if msgid_match and msgstr_match:
            msgid = msgid_match.group(1)
            msgstr = msgstr_match.group(1)
            
            # Skip empty msgid (header) but keep non-empty translations
            if msgid and msgstr:
                entries[msgid] = {
                    'msgstr': msgstr,
                    'block': block.strip()
                }
    
    return entries

def create_header(lang):
    """Create PO file header"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M+0000')
    
    return f'''# {lang.upper()} translations merged from multiple sources
# Copyright (C) 2025 GizAI
msgid ""
msgstr ""
"Project-Id-Version: Occam 1.0\\n"
"POT-Creation-Date: {now}\\n"
"PO-Revision-Date: {now}\\n"
"Language: {lang}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

'''

def merge_po_files(target_lang, source_dir="../occam/locale"):
    """Merge all *-{target_lang}.po files into {target_lang}.po"""
    
    # Find all matching files
    pattern = os.path.join(source_dir, f"*-{target_lang}.po")
    po_files = glob.glob(pattern)
    
    if not po_files:
        print(f"❌ No *-{target_lang}.po files found in {source_dir}")
        return False
    
    print(f"🔍 Found {len(po_files)} files to merge:")
    for f in po_files:
        print(f"  📁 {os.path.basename(f)}")
    
    # Merge all entries
    all_entries = {}
    
    for po_file in po_files:
        print(f"📖 Reading {os.path.basename(po_file)}...")
        
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entries = extract_entries(content)
            print(f"  ✅ {len(entries)} entries")
            
            # Merge (later files override earlier ones)
            all_entries.update(entries)
            
        except Exception as e:
            print(f"  ❌ Error reading {po_file}: {e}")
            continue
    
    if not all_entries:
        print("❌ No entries found to merge")
        return False
    
    # Write merged file
    output_file = os.path.join(source_dir, f"{target_lang}.po")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(create_header(target_lang))
            
            # Write all entries sorted by msgid
            for msgid in sorted(all_entries.keys()):
                f.write(all_entries[msgid]['block'])
                f.write('\n\n')
        
        print(f"✅ Merged {len(all_entries)} entries into {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error writing {output_file}: {e}")
        return False

def main():
    """Main function"""
    # Get target language from command line or default to 'ko'
    target_lang = sys.argv[1] if len(sys.argv) > 1 else 'ko'
    
    print(f"🚀 Merging *-{target_lang}.po files...")
    
    success = merge_po_files(target_lang)
    
    if success:
        print("🎉 Merge completed successfully!")
        print("💡 Next: bench build --app occam")
    else:
        print("❌ Merge failed")
    
    return success

if __name__ == "__main__":
    main()
