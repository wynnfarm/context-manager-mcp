#!/usr/bin/env python3
"""
Minimal MCP server runner
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from minimal_context_server import main
    import asyncio
    
    # Run the MCP server
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting MCP server: {e}")
    sys.exit(1)







