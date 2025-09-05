#!/bin/bash
"""
Docker MCP Server for Cursor IDE

This script creates a Docker-based MCP server that Cursor can connect to
via a local wrapper script.
"""

set -e

echo "🐳 Setting up Docker MCP server for Cursor IDE..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t mcp-context-server:latest .

echo "✅ Docker image built successfully!"

# Create a local wrapper script that Cursor can use
cat > cursor_docker_wrapper.sh << 'EOF'
#!/bin/bash
# Wrapper script for Cursor IDE to connect to Docker MCP server

# Ensure the container is running
if ! docker ps | grep -q mcp-context-server; then
    echo "🚀 Starting MCP server container..." >&2
    docker run -d \
        --name mcp-context-server \
        --restart unless-stopped \
        -v "$(pwd)/contexts:/app/contexts" \
        mcp-context-server:latest
    sleep 2
fi

# Execute the MCP server in the container
exec docker exec -i mcp-context-server python run_context_mcp.py
EOF

chmod +x cursor_docker_wrapper.sh

echo "✅ Created cursor_docker_wrapper.sh"

# Update Cursor configuration
echo "📝 Updating Cursor IDE configuration..."
cat > ~/.cursor/mcp.json << 'EOF'
{
  "mcpServers": {
    "context-manager": {
      "command": "./cursor_docker_wrapper.sh",
      "args": []
    }
  }
}
EOF

echo "✅ Updated ~/.cursor/mcp.json"

echo ""
echo "🎯 Setup complete! Next steps:"
echo "1. Restart Cursor IDE"
echo "2. The context-manager MCP server should now be available"
echo ""
echo "🔍 To view logs: docker logs -f mcp-context-server"
echo "🛑 To stop: docker stop mcp-context-server"
echo "🔄 To restart: docker restart mcp-context-server"

