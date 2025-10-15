#!/usr/bin/env python3
"""
Fix all JSONResponse issues in router files.
"""

import re

def fix_router_file(file_path):
    """Fix JSONResponse issues in a router file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove JSONResponse import
    content = re.sub(r'from fastapi\.responses import JSONResponse\n', '', content)
    
    # Fix return type annotations
    content = re.sub(r'\) -> JSONResponse:', ') -> dict:', content)
    
    # Fix JSONResponse calls with create_json_response
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
    
    # Fix function call syntax
    content = re.sub(
        r'create_json_response\(data=([^,]+),\s*([^)]+)\)',
        r'create_json_response(data=\1, message=\2)',
        content
    )
    
    content = re.sub(
        r'create_error_json_response\(([^,]+),\s*([^,]+),\s*([^)]+)\)',
        r'create_error_json_response(message=\1, status_code=\2, details=\3)',
        content
    )
    
    # Fix malformed function calls
    content = re.sub(r'message=message=', 'message=', content)
    content = re.sub(r'status_code=status_code=', 'status_code=', content)
    content = re.sub(r'details=details=', 'details=', content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")

def main():
    """Fix all router files."""
    files = [
        "app/routers/employees.py",
        "app/routers/cameras.py"
    ]
    
    for file_path in files:
        try:
            fix_router_file(file_path)
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

if __name__ == "__main__":
    main()
