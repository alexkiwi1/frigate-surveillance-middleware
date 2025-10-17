#!/usr/bin/env python3
"""
Migration script to integrate improved FastAPI best practices.

This script helps migrate the existing codebase to use the improved
modules and patterns following FastAPI best practices.
"""

import os
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backup_existing_files():
    """Create backup of existing files before migration."""
    logger.info("Creating backup of existing files...")
    
    backup_dir = Path("backup_before_migration")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "app/main.py",
        "app/config.py",
        "app/dependencies.py",
        "app/routers/violations.py",
        "app/routers/employees.py",
        "app/routers/cameras.py",
        "app/utils/formatting.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = backup_dir / Path(file_path).name
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backed up {file_path} to {backup_path}")
    
    logger.info("Backup completed successfully")


def update_imports_in_file(file_path: str, old_imports: dict, new_imports: dict):
    """Update imports in a file."""
    if not os.path.exists(file_path):
        logger.warning(f"File {file_path} does not exist, skipping...")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    updated = False
    for old_import, new_import in old_imports.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            updated = True
            logger.info(f"Updated import in {file_path}: {old_import} -> {new_import}")
    
    if updated:
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Updated imports in {file_path}")


def migrate_violations_router():
    """Migrate violations router to use improved patterns."""
    logger.info("Migrating violations router...")
    
    file_path = "app/routers/violations.py"
    
    # Define import replacements
    old_imports = {
        "from ..utils.formatting import format_success_response, format_error_response": 
        "from ..utils.response_formatter import create_json_response, create_error_json_response",
        
        "from ..utils.formatting import format_violation_data, format_hourly_trend_data":
        "from ..utils.response_formatter import format_violation_data, format_hourly_trend_data, handle_api_error",
        
        "from ..config import CacheKeys, settings":
        "from ..config import CacheKeys, settings\nfrom ..utils.errors import ValidationError, NotFoundError, DatabaseError, CacheError"
    }
    
    update_imports_in_file(file_path, old_imports, {})
    
    # Update function calls
    function_replacements = {
        "format_success_response(": "create_json_response(data=",
        "format_error_response(": "create_error_json_response(",
        "JSONResponse(\n            content=format_success_response(": "create_json_response(",
        "JSONResponse(\n            content=format_error_response(": "create_error_json_response("
    }
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    for old_call, new_call in function_replacements.items():
        if old_call in content:
            content = content.replace(old_call, new_call)
            logger.info(f"Updated function call in {file_path}: {old_call} -> {new_call}")
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info("Violations router migration completed")


def migrate_employees_router():
    """Migrate employees router to use improved patterns."""
    logger.info("Migrating employees router...")
    
    file_path = "app/routers/employees.py"
    
    # Define import replacements
    old_imports = {
        "from ..utils.formatting import format_success_response, format_error_response": 
        "from ..utils.response_formatter import create_json_response, create_error_json_response",
        
        "from ..config import CacheKeys, settings":
        "from ..config import CacheKeys, settings\nfrom ..utils.errors import ValidationError, NotFoundError, DatabaseError, CacheError"
    }
    
    update_imports_in_file(file_path, old_imports, {})
    
    logger.info("Employees router migration completed")


def migrate_cameras_router():
    """Migrate cameras router to use improved patterns."""
    logger.info("Migrating cameras router...")
    
    file_path = "app/routers/cameras.py"
    
    # Define import replacements
    old_imports = {
        "from ..utils.formatting import format_success_response, format_error_response": 
        "from ..utils.response_formatter import create_json_response, create_error_json_response",
        
        "from ..config import CacheKeys, settings":
        "from ..config import CacheKeys, settings\nfrom ..utils.errors import ValidationError, NotFoundError, DatabaseError, CacheError"
    }
    
    update_imports_in_file(file_path, old_imports, {})
    
    logger.info("Cameras router migration completed")


def create_migration_guide():
    """Create a migration guide for manual steps."""
    migration_guide = """
# Migration Guide for FastAPI Best Practices

## Automated Migration Completed

The following files have been automatically migrated:
- app/routers/violations.py
- app/routers/employees.py  
- app/routers/cameras.py

## Manual Migration Steps Required

### 1. Update Main Application
Replace the current main.py with main_improved.py:
```bash
cp app/main_improved.py app/main.py
```

### 2. Update Configuration
Replace the current config.py with config_improved.py:
```bash
cp app/config_improved.py app/config.py
```

### 3. Update Dependencies
Replace the current dependencies.py with dependencies_improved.py:
```bash
cp app/dependencies_improved.py app/dependencies.py
```

### 4. Update Response Formatting
Replace the current formatting.py with response_formatter.py:
```bash
cp app/utils/response_formatter.py app/utils/formatting.py
```

### 5. Test the Migration
Run the test suite to ensure everything works:
```bash
python3 test_api.py
```

### 6. Update Docker Configuration
Update docker-compose.yml to use the new configuration structure if needed.

## Benefits After Migration

1. **Improved Error Handling**: Custom error types with proper HTTP status codes
2. **Better Type Safety**: Complete type hints throughout the codebase
3. **Enhanced Performance**: Optimized response formatting and caching
4. **Better Documentation**: Comprehensive API documentation and examples
5. **Production Ready**: Robust error handling and monitoring

## Rollback Instructions

If issues occur, restore from backup:
```bash
cp backup_before_migration/* app/
```

## Verification Checklist

- [ ] All endpoints return proper HTTP status codes
- [ ] Error responses are user-friendly and consistent
- [ ] Performance remains at 0.001s average response time
- [ ] All tests pass
- [ ] API documentation is accessible at /docs
- [ ] Health checks work properly
- [ ] Background tasks are running
- [ ] Cache operations work correctly
"""
    
    with open("MIGRATION_GUIDE.md", "w") as f:
        f.write(migration_guide)
    
    logger.info("Migration guide created: MIGRATION_GUIDE.md")


def main():
    """Main migration function."""
    logger.info("Starting FastAPI best practices migration...")
    
    try:
        # Step 1: Create backup
        backup_existing_files()
        
        # Step 2: Migrate routers
        migrate_violations_router()
        migrate_employees_router()
        migrate_cameras_router()
        
        # Step 3: Create migration guide
        create_migration_guide()
        
        logger.info("Migration completed successfully!")
        logger.info("Please follow the MIGRATION_GUIDE.md for manual steps")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()





