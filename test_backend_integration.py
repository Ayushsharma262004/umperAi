"""
Test Backend Integration

This script tests the backend API integration with the UmpirAI system.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"✅ Root: {response.json()}")
    return response.status_code == 200

def test_status():
    """Test status endpoint"""
    print("\nTesting status endpoint...")
    response = requests.get(f"{BASE_URL}/api/status")
    data = response.json()
    print(f"✅ Status: Running={data['running']}, FPS={data['fps']}, Cameras={data['cameras']}")
    return response.status_code == 200

def test_start():
    """Test start endpoint"""
    print("\nTesting start endpoint...")
    response = requests.post(f"{BASE_URL}/api/start")
    data = response.json()
    print(f"✅ Start: {data['message']}")
    return response.status_code == 200 and data['success']

def test_decisions():
    """Test decisions endpoint"""
    print("\nTesting decisions endpoint...")
    response = requests.get(f"{BASE_URL}/api/decisions?limit=10")
    data = response.json()
    print(f"✅ Decisions: Total={data['total']}, Returned={len(data['decisions'])}")
    if data['decisions']:
        print(f"   Latest: {data['decisions'][-1]['type']} @ {data['decisions'][-1]['timestamp']}")
    return response.status_code == 200

def test_analytics():
    """Test analytics endpoints"""
    print("\nTesting analytics endpoints...")
    
    # Summary
    response = requests.get(f"{BASE_URL}/api/analytics/summary")
    data = response.json()
    print(f"✅ Analytics Summary:")
    print(f"   Total Decisions: {data['totalDecisions']}")
    print(f"   Avg Confidence: {data['avgConfidence']}%")
    print(f"   Review Rate: {data['reviewRate']}%")
    
    # Performance
    response = requests.get(f"{BASE_URL}/api/analytics/performance")
    data = response.json()
    print(f"✅ Performance Metrics: {len(data['metrics'])} data points")
    
    return True

def test_settings():
    """Test settings endpoints"""
    print("\nTesting settings endpoints...")
    
    # Get settings
    response = requests.get(f"{BASE_URL}/api/settings")
    data = response.json()
    print(f"✅ Settings:")
    print(f"   Model: {data.get('detectionModel', 'N/A')}")
    print(f"   FPS: {data.get('targetFPS', 'N/A')}")
    print(f"   GPU: {data.get('enableGPU', 'N/A')}")
    
    return response.status_code == 200

def test_stop():
    """Test stop endpoint"""
    print("\nTesting stop endpoint...")
    response = requests.post(f"{BASE_URL}/api/stop")
    data = response.json()
    print(f"✅ Stop: {data['message']}")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("="*70)
    print("🏏 UmpirAI Backend Integration Test")
    print("="*70)
    
    tests = [
        ("Root Endpoint", test_root),
        ("Status Endpoint", test_status),
        ("Start System", test_start),
    ]
    
    # Run initial tests
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            results.append((name, False))
    
    # Wait for some processing
    print("\n⏳ Waiting 10 seconds for processing...")
    time.sleep(10)
    
    # Test after processing
    post_tests = [
        ("Decisions Endpoint", test_decisions),
        ("Analytics Endpoints", test_analytics),
        ("Settings Endpoints", test_settings),
        ("Stop System", test_stop),
    ]
    
    for name, test_func in post_tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend integration is working!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to backend server")
        print("   Make sure the backend is running: python backend/api_server.py")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
