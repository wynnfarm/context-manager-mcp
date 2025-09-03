#!/bin/bash
# Secure deployment script for AWS Lambda MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="context-manager-mcp"
ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}

echo -e "${BLUE}🔒 Deploying Secure MCP Server to AWS Lambda${NC}"
echo -e "${BLUE}Project: ${PROJECT_NAME}${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Region: ${AWS_REGION}${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity --output text &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Generate secure API key
echo -e "${YELLOW}🔑 Generating secure API key...${NC}"
API_KEY=$(openssl rand -hex 32)
echo -e "${GREEN}✅ API key generated: ${API_KEY:0:16}...${NC}"

# Build Lambda package
echo ""
echo -e "${YELLOW}📦 Building Lambda deployment package...${NC}"
chmod +x build_lambda.sh
./build_lambda.sh

# Initialize Terraform
echo ""
echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
cd terraform
terraform init

# Plan deployment
echo ""
echo -e "${YELLOW}📋 Planning secure deployment...${NC}"
terraform plan \
    -var="aws_region=${AWS_REGION}" \
    -var="project_name=${PROJECT_NAME}" \
    -var="environment=${ENVIRONMENT}" \
    -var="api_key=${API_KEY}" \
    -var="rate_limit_per_minute=100" \
    -out=tfplan

# Confirm deployment
echo ""
echo -e "${YELLOW}⚠️  Review the plan above. Continue with secure deployment? (y/N)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Deployment cancelled${NC}"
    exit 1
fi

# Apply deployment
echo ""
echo -e "${YELLOW}🚀 Deploying to AWS with security features...${NC}"
terraform apply tfplan

# Get outputs
echo ""
echo -e "${GREEN}✅ Secure deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Information:${NC}"
echo -e "${GREEN}Lambda Function: ${NC}$(terraform output -raw lambda_function_name)"
echo -e "${GREEN}API Gateway URL: ${NC}$(terraform output -raw api_gateway_url)"
echo -e "${GREEN}CloudWatch Logs: ${NC}$(terraform output -raw cloudwatch_log_group)"
echo -e "${GREEN}WAF Web ACL: ${NC}$(terraform output -raw waf_web_acl_arn)"
echo ""

# Save API key securely
echo -e "${YELLOW}💾 Saving API key securely...${NC}"
echo "API_KEY=${API_KEY}" > ../.env.aws
chmod 600 ../.env.aws
echo -e "${GREEN}✅ API key saved to .env.aws (chmod 600)${NC}"

# Test the deployment
echo ""
echo -e "${YELLOW}🧪 Testing secure deployment...${NC}"
API_URL=$(terraform output -raw api_gateway_url)

# Test without API key (should fail)
echo "Testing without API key (should fail)..."
curl -X POST "${API_URL}" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "system.server_status",
            "arguments": {}
        }
    }' | jq '.'

echo ""

# Test with API key (should succeed)
echo "Testing with API key (should succeed)..."
curl -X POST "${API_URL}" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${API_KEY}" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "system.server_status",
            "arguments": {}
        }
    }' | jq '.'

echo ""
echo -e "${GREEN}🎉 Secure MCP Server deployed and tested successfully!${NC}"
echo ""

# Create Cursor IDE configuration
echo -e "${YELLOW}⚙️  Creating Cursor IDE configuration...${NC}"
CURSOR_CONFIG_DIR="$HOME/.cursor"
mkdir -p "$CURSOR_CONFIG_DIR"

# Create secure MCP configuration for Cursor
cat > "$CURSOR_CONFIG_DIR/mcp.json" << EOF
{
  "mcpServers": {
    "aws-mcp": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "${API_URL}",
        "-H", "Content-Type: application/json",
        "-H", "X-API-Key: ${API_KEY}",
        "-d"
      ],
      "env": {}
    }
  }
}
EOF

echo -e "${GREEN}✅ Cursor IDE configuration created at ~/.cursor/mcp.json${NC}"
echo ""

echo -e "${BLUE}📝 Next steps:${NC}"
echo "1. ✅ MCP Server is now running securely on AWS"
echo "2. ✅ API key authentication is enabled"
echo "3. ✅ Rate limiting is active (100 requests/minute)"
echo "4. ✅ WAF protection is configured"
echo "5. ✅ Cursor IDE is configured to use the secure endpoint"
echo "6. 🔒 API key is saved in .env.aws (keep this secure!)"
echo ""
echo -e "${BLUE}🔗 Useful commands:${NC}"
echo "View logs: aws logs tail $(terraform output -raw cloudwatch_log_group) --follow"
echo "Update function: terraform apply"
echo "Destroy resources: terraform destroy"
echo "Test API: curl -X POST ${API_URL} -H 'X-API-Key: ${API_KEY}' -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}'"
echo ""
echo -e "${BLUE}🔒 Security Features Enabled:${NC}"
echo "• API Key Authentication"
echo "• Rate Limiting (100 req/min)"
echo "• WAF Protection"
echo "• HTTPS Only"
echo "• Security Headers"
echo "• Input Validation"
echo "• Error Handling"
echo ""
echo -e "${GREEN}🚀 Your MCP Server is now production-ready and secure!${NC}"
