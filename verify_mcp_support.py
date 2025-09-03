#!/usr/bin/env python3
"""
MCP Support Verification
"""

import sys
import os
from pathlib import Path

def verify_mcp_support():
    """Verify MCP support"""
    print("🔍 Verifying MCP Support")
    print("=" * 40)
    
    try:
        # Check MCP library
        import mcp
        print("✅ MCP library imported successfully")
        
        # Check server components
        from mcp.server import Server
        print("✅ MCP Server imported successfully")
        
        # Check types
        from mcp.types import Tool, ListToolsResult, CallToolResult
        print("✅ MCP types imported successfully")
        
        # Check stdio
        from mcp.server.stdio import stdio_server
        print("✅ MCP stdio imported successfully")
        
        # Check configuration
        config_path = Path.home() / ".cursor" / "mcp.json"
        if config_path.exists():
            print("✅ Cursor MCP configuration found")
            with open(config_path) as f:
                import json
                config = json.load(f)
                servers = config.get("mcpServers", {})
                print(f"✅ Found {len(servers)} MCP servers configured")
                for name in servers:
                    print(f"   - {name}")
        else:
            print("❌ Cursor MCP configuration not found")
        
        print("\n🎉 MCP support verification complete!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = verify_mcp_support()
    if success:
        print("\n✅ MCP is properly configured!")
    else:
        print("\n❌ MCP has configuration issues")























