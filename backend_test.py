#!/usr/bin/env python3
import requests
import json
import pandas as pd
import io
import base64
import time
import os
import sys
from pathlib import Path

# Get the backend URL from frontend/.env
def get_backend_url():
    env_path = Path('/app/frontend/.env')
    if not env_path.exists():
        print("Error: frontend/.env file not found")
        sys.exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=', 1)[1].strip('"\'')
    
    print("Error: REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

# Base URL for API calls
BASE_URL = f"{get_backend_url()}/api"
print(f"Using backend URL: {BASE_URL}")

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def run_test(test_name, test_func):
    """Run a test and track results"""
    print(f"\n{'='*80}\nRunning test: {test_name}\n{'='*80}")
    start_time = time.time()
    try:
        result = test_func()
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    
    duration = time.time() - start_time
    
    if success:
        print(f"✅ PASSED: {test_name} ({duration:.2f}s)")
        test_results["passed"] += 1
    else:
        print(f"❌ FAILED: {test_name} ({duration:.2f}s)")
        print(f"Error: {error}")
        test_results["failed"] += 1
    
    test_results["tests"].append({
        "name": test_name,
        "success": success,
        "duration": duration,
        "error": error,
        "result": result
    })
    
    return success, result

def test_api_health():
    """Test 1: Basic API Health Check"""
    response = requests.get(f"{BASE_URL}/")
    response.raise_for_status()
    data = response.json()
    
    assert "message" in data, "Response should contain 'message' field"
    assert data["message"] == "Ask Your Data API is running!", "Unexpected message in response"
    
    return data

def create_sample_csv():
    """Create a sample CSV file for testing"""
    data = {
        "product": ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard"],
        "category": ["Electronics", "Electronics", "Electronics", "Electronics", "Accessories"],
        "sales": [1200, 1500, 800, 500, 200],
        "price": [1200, 800, 300, 250, 50],
        "in_stock": [True, True, False, True, True]
    }
    df = pd.DataFrame(data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def create_sample_json():
    """Create a sample JSON file for testing"""
    data = [
        {"product": "Laptop", "category": "Electronics", "sales": 1200, "price": 1200, "in_stock": True},
        {"product": "Phone", "category": "Electronics", "sales": 1500, "price": 800, "in_stock": True},
        {"product": "Tablet", "category": "Electronics", "sales": 800, "price": 300, "in_stock": False},
        {"product": "Monitor", "category": "Electronics", "sales": 500, "price": 250, "in_stock": True},
        {"product": "Keyboard", "category": "Accessories", "sales": 200, "price": 50, "in_stock": True}
    ]
    return json.dumps(data)

def test_upload_csv():
    """Test 2: Upload CSV Dataset"""
    csv_data = create_sample_csv()
    files = {
        'file': ('sample_data.csv', csv_data, 'text/csv')
    }
    
    response = requests.post(f"{BASE_URL}/upload-dataset", files=files)
    response.raise_for_status()
    data = response.json()
    
    # Verify response structure
    assert "id" in data, "Response should contain dataset ID"
    assert "name" in data, "Response should contain dataset name"
    assert "columns" in data, "Response should contain columns"
    assert "row_count" in data, "Response should contain row count"
    assert "data_preview" in data, "Response should contain data preview"
    
    # Verify data content
    assert data["name"] == "sample_data.csv", "Dataset name should match uploaded file"
    assert data["file_type"] == "csv", "File type should be CSV"
    assert "product" in data["columns"], "Columns should include 'product'"
    assert "sales" in data["columns"], "Columns should include 'sales'"
    assert "category" in data["columns"], "Columns should include 'category'"
    assert data["row_count"] == 5, "Dataset should have 5 rows"
    assert len(data["data_preview"]) > 0, "Data preview should not be empty"
    
    return data

def test_upload_json():
    """Test 3: Upload JSON Dataset"""
    json_data = create_sample_json()
    files = {
        'file': ('sample_data.json', json_data, 'application/json')
    }
    
    response = requests.post(f"{BASE_URL}/upload-dataset", files=files)
    response.raise_for_status()
    data = response.json()
    
    # Verify response structure
    assert "id" in data, "Response should contain dataset ID"
    assert "name" in data, "Response should contain dataset name"
    assert "columns" in data, "Response should contain columns"
    assert "row_count" in data, "Response should contain row count"
    assert "data_preview" in data, "Response should contain data preview"
    
    # Verify data content
    assert data["name"] == "sample_data.json", "Dataset name should match uploaded file"
    assert data["file_type"] == "json", "File type should be JSON"
    assert "product" in data["columns"], "Columns should include 'product'"
    assert "sales" in data["columns"], "Columns should include 'sales'"
    assert "category" in data["columns"], "Columns should include 'category'"
    assert data["row_count"] == 5, "Dataset should have 5 rows"
    assert len(data["data_preview"]) > 0, "Data preview should not be empty"
    
    return data

def test_get_datasets():
    """Test 4: Get Datasets API"""
    response = requests.get(f"{BASE_URL}/datasets")
    response.raise_for_status()
    data = response.json()
    
    assert isinstance(data, list), "Response should be a list of datasets"
    assert len(data) > 0, "At least one dataset should be returned"
    
    # Verify dataset structure
    dataset = data[0]
    assert "id" in dataset, "Dataset should have an ID"
    assert "name" in dataset, "Dataset should have a name"
    assert "columns" in dataset, "Dataset should have columns"
    
    return data

def test_natural_language_query_table():
    """Test 5: Natural Language Query - Table Result"""
    # First get a dataset ID
    response = requests.get(f"{BASE_URL}/datasets")
    response.raise_for_status()
    datasets = response.json()
    
    if not datasets:
        raise Exception("No datasets available for testing queries")
    
    dataset_id = datasets[0]["id"]
    
    # Make a query that should return a table
    query_data = {
        "dataset_id": dataset_id,
        "query_text": "Show me the total sales by category"
    }
    
    response = requests.post(f"{BASE_URL}/query", json=query_data)
    response.raise_for_status()
    data = response.json()
    
    # Verify response structure
    assert "id" in data, "Response should contain query ID"
    assert "dataset_id" in data, "Response should contain dataset ID"
    assert "query_text" in data, "Response should contain query text"
    assert "generated_code" in data, "Response should contain generated code"
    assert "result_type" in data, "Response should contain result type"
    
    # Verify the code was generated
    assert len(data["generated_code"]) > 0, "Generated code should not be empty"
    
    # Check if we got a table result
    if data["result_type"] == "table":
        assert "result_data" in data, "Table result should include result_data"
        assert "data" in data["result_data"], "Table result should include data array"
        assert isinstance(data["result_data"]["data"], list), "Table data should be a list"
    elif data["result_type"] == "error":
        print(f"Query returned an error: {data.get('error_message')}")
    
    return data

def test_natural_language_query_chart():
    """Test 6: Natural Language Query - Chart Result"""
    # First get a dataset ID
    response = requests.get(f"{BASE_URL}/datasets")
    response.raise_for_status()
    datasets = response.json()
    
    if not datasets:
        raise Exception("No datasets available for testing queries")
    
    dataset_id = datasets[0]["id"]
    
    # Make a query that should return a chart
    query_data = {
        "dataset_id": dataset_id,
        "query_text": "Create a bar chart of sales by product"
    }
    
    response = requests.post(f"{BASE_URL}/query", json=query_data)
    response.raise_for_status()
    data = response.json()
    
    # Verify response structure
    assert "id" in data, "Response should contain query ID"
    assert "dataset_id" in data, "Response should contain dataset ID"
    assert "query_text" in data, "Response should contain query text"
    assert "generated_code" in data, "Response should contain generated code"
    assert "result_type" in data, "Response should contain result type"
    
    # Verify the code was generated
    assert len(data["generated_code"]) > 0, "Generated code should not be empty"
    
    # Check if we got a chart result
    if data["result_type"] == "chart":
        assert "result_data" in data, "Chart result should include result_data"
        assert "data" in data["result_data"], "Chart result should include base64 data"
        # Verify it's a valid base64 string
        try:
            base64.b64decode(data["result_data"]["data"])
        except:
            assert False, "Chart data is not a valid base64 string"
    elif data["result_type"] == "plotly":
        assert "result_data" in data, "Plotly result should include result_data"
        assert "data" in data["result_data"], "Plotly result should include HTML data"
        assert "<div" in data["result_data"]["data"], "Plotly HTML should contain div elements"
    elif data["result_type"] == "error":
        print(f"Query returned an error: {data.get('error_message')}")
    
    return data

def test_get_queries():
    """Test 7: Get Queries API"""
    # First get a dataset ID
    response = requests.get(f"{BASE_URL}/datasets")
    response.raise_for_status()
    datasets = response.json()
    
    if not datasets:
        raise Exception("No datasets available for testing queries")
    
    dataset_id = datasets[0]["id"]
    
    # Get queries for this dataset
    response = requests.get(f"{BASE_URL}/queries/{dataset_id}")
    response.raise_for_status()
    data = response.json()
    
    assert isinstance(data, list), "Response should be a list of queries"
    
    # If we have queries, verify their structure
    if data:
        query = data[0]
        assert "id" in query, "Query should have an ID"
        assert "dataset_id" in query, "Query should have a dataset ID"
        assert "query_text" in query, "Query should have query text"
        assert "generated_code" in query, "Query should have generated code"
    
    return data

def main():
    """Run all tests"""
    print(f"Starting backend API tests against {BASE_URL}")
    
    # Run tests
    run_test("API Health Check", test_api_health)
    csv_success, csv_data = run_test("Upload CSV Dataset", test_upload_csv)
    json_success, json_data = run_test("Upload JSON Dataset", test_upload_json)
    
    if csv_success or json_success:
        run_test("Get Datasets", test_get_datasets)
        run_test("Natural Language Query - Table", test_natural_language_query_table)
        run_test("Natural Language Query - Chart", test_natural_language_query_chart)
        run_test("Get Queries", test_get_queries)
    
    # Print summary
    print("\n" + "="*80)
    print(f"TEST SUMMARY: {test_results['passed']} passed, {test_results['failed']} failed")
    print("="*80)
    
    # Return non-zero exit code if any tests failed
    return 1 if test_results["failed"] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
