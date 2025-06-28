#!/usr/bin/env python3
"""
Simple test script to diagnose container issues.
"""

import sys
import os
import traceback

def test_basic_functionality():
    """Test basic Python functionality and imports."""
    print("=" * 50)
    print("CONTAINER DIAGNOSTIC TEST")
    print("=" * 50)
    
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Test environment variables
    print("\nEnvironment Variables:")
    critical_vars = ["FRED_API_KEY", "AZURE_STORAGE_CONNECTION_STRING", "CONTAINER_NAME"]
    for var in critical_vars:
        value = os.environ.get(var, "NOT SET")
        # Don't print sensitive values, just check if they exist
        if var in ["FRED_API_KEY", "AZURE_STORAGE_CONNECTION_STRING"]:
            status = "SET" if value != "NOT SET" else "NOT SET"
            print(f"  {var}: {status}")
        else:
            print(f"  {var}: {value}")
    
    # Test basic imports
    print("\nTesting basic imports:")
    
    try:
        import pandas as pd
        print(f"  pandas: OK (version {pd.__version__})")
    except Exception as e:
        print(f"  pandas: FAILED - {e}")
        return False
    
    try:
        import numpy as np
        print(f"  numpy: OK (version {np.__version__})")
    except Exception as e:
        print(f"  numpy: FAILED - {e}")
        return False
    
    try:
        from azure.storage.blob import BlobServiceClient
        print(f"  azure.storage.blob: OK")
    except Exception as e:
        print(f"  azure.storage.blob: FAILED - {e}")
        return False
    
    # Test file system
    print("\nTesting file system:")
    try:
        # Test write permissions
        test_file = "/tmp/test_write.txt"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print("  Write permissions: OK")
    except Exception as e:
        print(f"  Write permissions: FAILED - {e}")
    
    # Test directories
    expected_dirs = ["/app", "/app/scraping", "/app/modelling", "/app/forecasting", "/mnt/fileshare"]
    for dir_path in expected_dirs:
        if os.path.exists(dir_path):
            print(f"  Directory {dir_path}: EXISTS")
        else:
            print(f"  Directory {dir_path}: MISSING")
    
    print("\n" + "=" * 50)
    print("BASIC TESTS COMPLETED")
    print("=" * 50)
    return True

def test_project_imports():
    """Test project-specific imports."""
    print("\nTesting project imports:")
    
    try:
        # Add project to path
        sys.path.insert(0, "/app")
        
        from scraping.update_all import DataUpdater
        print("  scraping.update_all: OK")
    except Exception as e:
        print(f"  scraping.update_all: FAILED - {e}")
        traceback.print_exc()
        return False
    
    try:
        from utils.storage_utils import upload_to_blob_storage
        print("  utils.storage_utils: OK")
    except Exception as e:
        print(f"  utils.storage_utils: FAILED - {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        if success:
            success = test_project_imports()
        
        if success:
            print("\nALL TESTS PASSED - Container environment looks good!")
            sys.exit(0)
        else:
            print("\nSOME TESTS FAILED - Check errors above")
            sys.exit(1)
            
    except Exception as e:
        print(f"CRITICAL ERROR in test script: {e}")
        traceback.print_exc()
        sys.exit(1)
