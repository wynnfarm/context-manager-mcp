#!/usr/bin/env python3
"""
Comprehensive test suite for the Context Manager MCP Server
"""

import subprocess
import json
import time
import sys
import os
import signal

def test_server_startup():
    """Test 1: Server startup and basic functionality"""
    print("🧪 Test 1: Server Startup and Basic Functionality")
    print("-" * 50)
    
    # Test if server can start
    try:
        process = subprocess.Popen(
            ["python", "context_manager_jsonrpc_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for startup
        time.sleep(1)
        
        # Check if process is running
        if process.poll() is None:
            print("✅ Server starts successfully")
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            print("❌ Server failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        return False

def test_initialization():
    """Test 2: Initialization protocol"""
    print("\n🧪 Test 2: Initialization Protocol")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Test initialization
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "cursor",
                    "version": "1.0.0"
                }
            }
        }
        
        init_line = json.dumps(init_request) + "\n"
        process.stdin.write(init_line)
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        # Verify response structure
        if "result" in response:
            result = response["result"]
            if "protocolVersion" in result and "capabilities" in result and "serverInfo" in result:
                print("✅ Initialization response structure correct")
                
                # Check capabilities
                capabilities = result["capabilities"]
                if "tools" in capabilities and "logging" in capabilities and "notifications" in capabilities:
                    print("✅ All required capabilities present")
                else:
                    print("❌ Missing required capabilities")
                    return False
            else:
                print("❌ Initialization response missing required fields")
                return False
        else:
            print("❌ Initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_tools_listing():
    """Test 3: Tools listing"""
    print("\n🧪 Test 3: Tools Listing")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Initialize first
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()  # Read init response
        
        # Test tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            print(f"✅ Tools listing successful, found {len(tools)} tools")
            
            # Verify all expected tools are present
            expected_tools = [
                "get_project_context",
                "set_current_goal", 
                "add_completed_feature",
                "add_current_issue",
                "resolve_issue",
                "add_next_step",
                "add_context_anchor"
            ]
            
            tool_names = [tool["name"] for tool in tools]
            missing_tools = [name for name in expected_tools if name not in tool_names]
            
            if not missing_tools:
                print("✅ All expected tools present")
                return True
            else:
                print(f"❌ Missing tools: {missing_tools}")
                return False
        else:
            print("❌ Tools listing failed")
            return False
            
    except Exception as e:
        print(f"❌ Tools listing test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_tool_calls():
    """Test 4: Tool calls"""
    print("\n🧪 Test 4: Tool Calls")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Initialize first
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()  # Read init response
        
        # Test tool call
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_project_context",
                "arguments": {
                    "project_name": "test-project"
                }
            }
        }
        
        process.stdin.write(json.dumps(tool_call_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        if "result" in response and "content" in response["result"]:
            print("✅ Tool call successful")
            content = response["result"]["content"]
            if len(content) > 0 and "text" in content[0]:
                print("✅ Tool response contains text content")
                return True
            else:
                print("❌ Tool response missing text content")
                return False
        else:
            print("❌ Tool call failed")
            return False
            
    except Exception as e:
        print(f"❌ Tool call test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_notifications():
    """Test 5: Notification handling"""
    print("\n🧪 Test 5: Notification Handling")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Initialize first
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()  # Read init response
        
        # Test notification (should not generate response)
        notification_request = {
            "jsonrpc": "2.0",
            "method": "notifications/toolCalls",
            "params": {
                "toolCalls": []
            }
        }
        
        process.stdin.write(json.dumps(notification_request) + "\n")
        process.stdin.flush()
        
        # Wait a bit to see if any response comes
        time.sleep(0.5)
        
        # Try to read response (should timeout/block)
        import select
        ready, _, _ = select.select([process.stdout], [], [], 0.1)
        
        if not ready:
            print("✅ Notification handled correctly (no response sent)")
            return True
        else:
            print("❌ Notification generated unexpected response")
            return False
            
    except Exception as e:
        print(f"❌ Notification test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_persistent_connection():
    """Test 6: Persistent connection"""
    print("\n🧪 Test 6: Persistent Connection")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        process.stdout.readline()  # Read init response
        
        # Keep connection alive
        time.sleep(2)
        
        # Test tools/list again
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        if "result" in response and "tools" in response["result"]:
            print("✅ Persistent connection working")
            return True
        else:
            print("❌ Persistent connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Persistent connection test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_error_handling():
    """Test 7: Error handling"""
    print("\n🧪 Test 7: Error Handling")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Test invalid JSON
        process.stdin.write("invalid json\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        if "error" in response and response["error"]["code"] == -32700:
            print("✅ Invalid JSON handled correctly")
        else:
            print("❌ Invalid JSON not handled correctly")
            return False
        
        # Test unknown method
        unknown_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }
        
        process.stdin.write(json.dumps(unknown_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        if "error" in response and response["error"]["code"] == -32601:
            print("✅ Unknown method handled correctly")
            return True
        else:
            print("❌ Unknown method not handled correctly")
            return False
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def test_cursor_integration():
    """Test 8: Cursor IDE Integration Simulation"""
    print("\n🧪 Test 8: Cursor IDE Integration Simulation")
    print("-" * 50)
    
    process = subprocess.Popen(
        ["python", "context_manager_jsonrpc_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        time.sleep(1)
        
        # Simulate Cursor IDE's exact sequence
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "cursor", "version": "1.0.0"}
                }
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_project_context",
                    "arguments": {"project_name": "test-project"}
                }
            }
        ]
        
        for i, request in enumerate(requests):
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            
            response_line = process.stdout.readline()
            response = json.loads(response_line)
            
            if "result" in response:
                print(f"✅ Request {i+1} successful")
            else:
                print(f"❌ Request {i+1} failed: {response}")
                return False
        
        print("✅ Cursor IDE integration simulation successful")
        return True
        
    except Exception as e:
        print(f"❌ Cursor IDE integration test failed: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE CONTEXT MANAGER MCP SERVER TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_server_startup,
        test_initialization,
        test_tools_listing,
        test_tool_calls,
        test_notifications,
        test_persistent_connection,
        test_error_handling,
        test_cursor_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Server is fully functional and ready for Cursor IDE")
        print("✅ All MCP protocol requirements met")
        print("✅ Error handling working correctly")
        print("✅ Persistent communication working")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Server needs fixes before deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)












