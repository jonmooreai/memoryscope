#!/usr/bin/env python3
"""
Comprehensive system verification script for Memory Scope API.
Checks all components without requiring services to be running.
"""
import sys
import os
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_mark(condition, message):
    """Print check result."""
    status = "✓" if condition else "✗"
    print(f"{status} {message}")
    return condition

def verify_python_imports():
    """Verify all Python modules can be imported."""
    print("\n=== Verifying Python Imports ===")
    results = []
    
    modules = [
        "app.main",
        "app.database",
        "app.models",
        "app.schemas",
        "app.config",
        "app.utils",
        "app.sanitization",
        "app.rate_limit",
        "app.errors",
        "app.middleware",
        "app.monitoring",
        "app.logging_config",
    ]
    
    for module_name in modules:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                results.append(check_mark(False, f"Module {module_name} not found"))
            else:
                module = importlib.import_module(module_name)
                results.append(check_mark(True, f"Module {module_name} imports successfully"))
        except Exception as e:
            results.append(check_mark(False, f"Module {module_name} failed: {str(e)[:100]}"))
    
    return all(results)

def verify_database_schema():
    """Verify database models and migrations."""
    print("\n=== Verifying Database Schema ===")
    results = []
    
    try:
        from app.models import App, Memory, ReadGrant, AuditEvent, SubscriptionPlan, Subscription
        results.append(check_mark(True, "All database models import successfully"))
        
        # Check that models have required attributes
        required_attrs = {
            'App': ['id', 'name', 'api_key_hash', 'user_id', 'created_at'],
            'Memory': ['id', 'user_id', 'scope', 'value_json', 'app_id'],
            'ReadGrant': ['id', 'revocation_token_hash', 'user_id', 'app_id'],
            'AuditEvent': ['id', 'event_type', 'timestamp'],
        }
        
        models_dict = {
            'App': App,
            'Memory': Memory,
            'ReadGrant': ReadGrant,
            'AuditEvent': AuditEvent,
        }
        
        for model_name, attrs in required_attrs.items():
            model = models_dict[model_name]
            for attr in attrs:
                if hasattr(model, attr):
                    results.append(check_mark(True, f"{model_name}.{attr} exists"))
                else:
                    results.append(check_mark(False, f"{model_name}.{attr} missing"))
    except Exception as e:
        results.append(check_mark(False, f"Database models error: {str(e)[:100]}"))
    
    # Check migrations exist
    migration_files = [
        "alembic/versions/001_initial_schema.py",
        "alembic/versions/002_add_billing_tables.py",
    ]
    
    for migration_file in migration_files:
        path = project_root / migration_file
        results.append(check_mark(path.exists(), f"Migration {migration_file} exists"))
    
    return all(results)

def verify_api_endpoints():
    """Verify API endpoints are defined."""
    print("\n=== Verifying API Endpoints ===")
    results = []
    
    try:
        from app.main import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, route.methods))
        
        expected_routes = [
            ("/healthz", {"GET"}),
            ("/healthz/ready", {"GET"}),
            ("/healthz/live", {"GET"}),
            ("/memory", {"POST"}),
            ("/memory/read", {"POST"}),
            ("/memory/read/continue", {"POST"}),
            ("/memory/revoke", {"POST"}),
        ]
        
        route_paths = {path: methods for path, methods in routes}
        
        for expected_path, expected_methods in expected_routes:
            if expected_path in route_paths:
                actual_methods = route_paths[expected_path]
                if expected_methods.intersection(actual_methods):
                    results.append(check_mark(True, f"Route {expected_path} exists"))
                else:
                    results.append(check_mark(False, f"Route {expected_path} missing methods {expected_methods}"))
            else:
                results.append(check_mark(False, f"Route {expected_path} not found"))
        
    except Exception as e:
        results.append(check_mark(False, f"API endpoints error: {str(e)[:100]}"))
    
    return all(results)

def verify_configuration():
    """Verify configuration files exist."""
    print("\n=== Verifying Configuration ===")
    results = []
    
    config_files = [
        "env.example",
        "alembic.ini",
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
    ]
    
    for config_file in config_files:
        path = project_root / config_file
        results.append(check_mark(path.exists(), f"Config file {config_file} exists"))
    
    # Check website config
    website_config_files = [
        "website/package.json",
        "website/next.config.ts",
        "website/tsconfig.json",
        "website/firebase.json",
    ]
    
    for config_file in website_config_files:
        path = project_root / config_file
        results.append(check_mark(path.exists(), f"Website config {config_file} exists"))
    
    return all(results)

def verify_website_structure():
    """Verify website structure."""
    print("\n=== Verifying Website Structure ===")
    results = []
    
    website_dir = project_root / "website"
    results.append(check_mark(website_dir.exists(), "Website directory exists"))
    
    required_dirs = [
        "website/app",
        "website/components",
        "website/lib",
        "website/public",
    ]
    
    for dir_path in required_dirs:
        path = project_root / dir_path
        results.append(check_mark(path.exists() and path.is_dir(), f"Directory {dir_path} exists"))
    
    # Check for key files
    key_files = [
        "website/app/layout.tsx",
        "website/app/page.tsx",
        "website/components/layout/header.tsx",
        "website/components/layout/footer.tsx",
    ]
    
    for file_path in key_files:
        path = project_root / file_path
        results.append(check_mark(path.exists(), f"File {file_path} exists"))
    
    return all(results)

def verify_tests():
    """Verify test files exist."""
    print("\n=== Verifying Tests ===")
    results = []
    
    test_dir = project_root / "tests"
    results.append(check_mark(test_dir.exists(), "Tests directory exists"))
    
    test_files = [
        "tests/test_memory_create.py",
        "tests/test_memory_read.py",
        "tests/test_policy.py",
        "tests/test_rate_limiting.py",
        "tests/test_revoke.py",
        "tests/test_integration.py",
    ]
    
    for test_file in test_files:
        path = project_root / test_file
        results.append(check_mark(path.exists(), f"Test file {test_file} exists"))
    
    return all(results)

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Memory Scope API - System Verification")
    print("=" * 60)
    
    checks = [
        ("Python Imports", verify_python_imports),
        ("Database Schema", verify_database_schema),
        ("API Endpoints", verify_api_endpoints),
        ("Configuration Files", verify_configuration),
        ("Website Structure", verify_website_structure),
        ("Test Files", verify_tests),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All checks passed!")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

