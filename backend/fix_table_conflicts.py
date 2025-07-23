#!/usr/bin/env python3
"""
QuantMatrix V1 - Fix Table Conflicts
====================================

Automatically adds extend_existing=True to all model table_args
to resolve SQLAlchemy table redefinition conflicts.
"""

import os
import re
from pathlib import Path

def fix_table_args_in_file(file_path):
    """Fix table_args in a specific file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Pattern to match __table_args__ = ( ... )
        pattern = r'(__table_args__ = \([^)]*)\)(?!\s*\})'
        
        def replacement(match):
            table_args = match.group(1)
            # If extend_existing is already there, don't modify
            if 'extend_existing' in table_args:
                return match.group(0)
            
            # Add extend_existing=True
            if table_args.strip().endswith(','):
                return table_args + "\n        {'extend_existing': True}\n    )"
            else:
                return table_args + ",\n        {'extend_existing': True}\n    )"
        
        # Apply the replacement
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        # Only write if content changed
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⏭️ Skipped: {file_path} (already fixed)")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def fix_all_models():
    """Fix all model files."""
    models_dir = Path("backend/models")
    
    files_to_fix = [
        "signals.py",
        "audit.py", 
        "tax_lots.py",
        "strategies.py",
        "users.py",
        "accounts.py",
        "transactions.py",
        "positions.py",
        "instruments.py",
        "market_data.py",
        "notifications.py"
    ]
    
    fixed_count = 0
    
    for file_name in files_to_fix:
        file_path = models_dir / file_name
        if file_path.exists():
            if fix_table_args_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️ File not found: {file_path}")
    
    print(f"\n🎉 Fixed {fixed_count} model files!")
    print("✅ All table conflicts should now be resolved!")

if __name__ == "__main__":
    print("🔧 Fixing table conflicts in all model files...")
    fix_all_models() 