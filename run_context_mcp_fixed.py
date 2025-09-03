#!/usr/bin/env python3
"""
Fixed Context Manager MCP Server Wrapper
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp_context_server_fixed import main
    import asyncio
    
    # Run the MCP server
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you have the required dependencies installed:")
    print("   pip install mcp")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting MCP server: {e}")
    sys.exit(1)























