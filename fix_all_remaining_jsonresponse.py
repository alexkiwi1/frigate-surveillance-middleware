#!/usr/bin/env python3
"""
Fix all remaining JSONResponse issues in both router files.
"""

import re

def fix_jsonresponse_issues():
    """Fix all remaining JSONResponse issues."""
    files = ["app/routers/employees.py", "app/routers/cameras.py"]
    
    for file_path in files:
        print(f"Fixing {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Remove JSONResponse import
        content = re.sub(r'from fastapi\.responses import JSONResponse\n', '', content)
        
        # Fix all JSONResponse patterns with create_error_json_response
        content = re.sub(
            r'return JSONResponse\(\s*content=create_error_json_response\(([^)]+)\),\s*status_code=status\.HTTP_\d+\s*\)',
            r'return create_error_json_response(\1)',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Fix all JSONResponse patterns with create_json_response
        content = re.sub(
            r'return JSONResponse\(\s*content=create_json_response\(([^)]+)\),\s*status_code=status\.HTTP_\d+\s*\)',
            r'return create_json_response(\1)',
            content,
            flags=re.MULTILINE | re.DOTALL
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
        
        # Fix malformed calls
        content = re.sub(r'message=message=', 'message=', content)
        content = re.sub(r'status_code=status_code=', 'status_code=', content)
        content = re.sub(r'details=details=', 'details=', content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_jsonresponse_issues()




