#!/bin/bash
# Deploy MCP Server to AWS Lambda using Terraform

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

echo -e "${BLUE}🚀 Deploying MCP Server to AWS Lambda${NC}"
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
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

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
echo -e "${YELLOW}📋 Planning deployment...${NC}"
terraform plan \
    -var="aws_region=${AWS_REGION}" \
    -var="project_name=${PROJECT_NAME}" \
    -var="environment=${ENVIRONMENT}" \
    -out=tfplan

# Confirm deployment
echo ""
echo -e "${YELLOW}⚠️  Review the plan above. Continue with deployment? (y/N)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Deployment cancelled${NC}"
    exit 1
fi

# Apply deployment
echo ""
echo -e "${YELLOW}🚀 Deploying to AWS...${NC}"
terraform apply tfplan

# Get outputs
echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Information:${NC}"
echo -e "${GREEN}Lambda Function: ${NC}$(terraform output -raw lambda_function_name)"
echo -e "${GREEN}API Gateway URL: ${NC}$(terraform output -raw api_gateway_url)"
echo -e "${GREEN}CloudWatch Logs: ${NC}$(terraform output -raw cloudwatch_log_group)"
echo ""

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
API_URL=$(terraform output -raw api_gateway_url)

# Test server status
echo "Testing server status..."
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
echo -e "${GREEN}🎉 MCP Server deployed and tested successfully!${NC}"
echo ""
echo -e "${BLUE}📝 Next steps:${NC}"
echo "1. Update your MCP configuration to use the API Gateway URL"
echo "2. Test the tools in your IDE"
echo "3. Monitor logs in CloudWatch"
echo ""
echo -e "${BLUE}🔗 Useful commands:${NC}"
echo "View logs: aws logs tail $(terraform output -raw cloudwatch_log_group) --follow"
echo "Update function: terraform apply"
echo "Destroy resources: terraform destroy"
