#!/usr/bin/env python3
"""
Fix all remaining JSONResponse calls in cameras.py
"""

def fix_final_cameras():
    """Fix all remaining JSONResponse calls in cameras.py"""
    file_path = "app/routers/cameras.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove JSONResponse import
    content = content.replace('from fastapi.responses import JSONResponse\n', '')
    
    # Fix all remaining JSONResponse patterns
    import re
    
    # Pattern 1: JSONResponse with create_error_json_response
    content = re.sub(
        r'return JSONResponse\(\s*content=create_error_json_response\(([^)]+)\),\s*status_code=status\.HTTP_\d+\s*\)',
        r'return create_error_json_response(\1)',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Pattern 2: JSONResponse with create_json_response
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
    
    print("Fixed final cameras.py JSONResponse issues")

if __name__ == "__main__":
    fix_final_cameras()

