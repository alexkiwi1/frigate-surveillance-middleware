#!/usr/bin/env python3
"""
Fix all syntax errors in router files.
"""

import re

def fix_syntax_errors():
    """Fix all syntax errors in router files."""
    files = ["app/routers/employees.py", "app/routers/cameras.py"]
    
    for file_path in files:
        print(f"Fixing {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix malformed function calls
        content = re.sub(r'message=message=', 'message=', content)
        content = re.sub(r'status_code=status_code=', 'status_code=', content)
        content = re.sub(r'details=details=', 'details=', content)
        
        # Fix broken function calls
        content = re.sub(
            r'create_error_json_response\(message=\s*([^,]+),\s*status_code=([^,]+),\s*details=([^)]+)\)',
            r'create_error_json_response(message=\1, status_code=\2, details=\3)',
            content
        )
        
        content = re.sub(
            r'create_json_response\(data=([^,]+),\s*([^)]+)\)',
            r'create_json_response(data=\1, message=\2)',
            content
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_syntax_errors()




