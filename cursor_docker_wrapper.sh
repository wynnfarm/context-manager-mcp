#!/bin/bash
# Wrapper script for Cursor IDE to connect to Docker MCP server

# Simply run the container interactively and execute the MCP server
# This way stdin/stdout will be properly connected
exec docker run -i --rm \
    -v "$(pwd)/contexts:/app/contexts" \
    mcp-context-server:latest \
    python working_mcp_server.py
