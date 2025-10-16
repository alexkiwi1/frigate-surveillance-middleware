#!/usr/bin/env python3
"""
Fix syntax errors in migrated files.
"""

import os
import re

def fix_file(file_path):
    """Fix syntax errors in a file."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist, skipping...")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix JSONResponse with create_json_response calls
    content = re.sub(
        r'JSONResponse\(\s*content=create_json_response\(([^)]+)\),\s*status_code=status\.HTTP_200_OK\s*\)',
        r'create_json_response(\1)',
        content
    )
    
    content = re.sub(
        r'JSONResponse\(\s*content=create_error_json_response\(([^)]+)\),\s*status_code=status\.HTTP_\d+\s*\)',
        r'create_error_json_response(\1)',
        content
    )
    
    # Fix format_success_response calls
    content = re.sub(
        r'format_success_response\(',
        'create_json_response(data=',
        content
    )
    
    content = re.sub(
        r'format_error_response\(',
        'create_error_json_response(',
        content
    )
    
    # Fix function call syntax
    content = re.sub(
        r'create_json_response\(data=([^,]+),\s*([^)]+)\)',
        r'create_json_response(data=\1, message=\2)',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed syntax errors in {file_path}")
    else:
        print(f"No syntax errors found in {file_path}")

def main():
    """Fix syntax errors in all router files."""
    files_to_fix = [
        "app/routers/violations.py",
        "app/routers/employees.py",
        "app/routers/cameras.py"
    ]
    
    for file_path in files_to_fix:
        fix_file(file_path)
    
    print("Syntax error fixes completed!")

if __name__ == "__main__":
    main()

