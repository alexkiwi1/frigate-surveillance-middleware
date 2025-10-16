#!/usr/bin/env python3
"""
Fix employees router JSONResponse issues.
"""

import re

def fix_employees_router():
    """Fix JSONResponse issues in employees router."""
    file_path = "app/routers/employees.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
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
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed employees router JSONResponse issues")

if __name__ == "__main__":
    fix_employees_router()




