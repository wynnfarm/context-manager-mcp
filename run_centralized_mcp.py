#!/usr/bin/env python3
"""
Centralized MCP Server Wrapper

Simple wrapper to run the centralized MCP server for Cursor IDE integration.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from centralized_mcp_server import main
    import asyncio
    
    # Run the centralized MCP server
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you have the required dependencies installed:")
    print("   pip install mcp")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting centralized MCP server: {e}")
    sys.exit(1)
