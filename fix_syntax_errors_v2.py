#!/usr/bin/env python3
"""
Fix syntax errors in router files.
"""

import re

def fix_employees_router():
    """Fix syntax errors in employees router."""
    file_path = "app/routers/employees.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix malformed function calls
    content = re.sub(
        r'message=message=',
        r'message=',
        content
    )
    
    content = re.sub(
        r'status_code=status_code=',
        r'status_code=',
        content
    )
    
    content = re.sub(
        r'details=details=',
        r'details=',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed employees router syntax errors")

def fix_cameras_router():
    """Fix syntax errors in cameras router."""
    file_path = "app/routers/cameras.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix malformed function calls
    content = re.sub(
        r'message=message=',
        r'message=',
        content
    )
    
    content = re.sub(
        r'status_code=status_code=',
        r'status_code=',
        content
    )
    
    content = re.sub(
        r'details=details=',
        r'details=',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed cameras router syntax errors")

if __name__ == "__main__":
    fix_employees_router()
    fix_cameras_router()




