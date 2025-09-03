# AWS MCP Tool Hosting Guide

## 🚀 AWS Hosting Options for MCP Tools

AWS offers several excellent options for hosting MCP tools. Here are the best approaches:

### 1. **AWS Lambda** (Serverless - Recommended)

**Best for**: Lightweight MCP tools, cost-effective, auto-scaling

**Pros:**

- Pay only for execution time
- Automatic scaling
- No server management
- Free tier: 1M requests/month

**Cons:**

- Cold start latency
- 15-minute execution limit
- Limited to HTTP/WebSocket protocols

**Setup:**

```bash
# Deploy as Lambda function
aws lambda create-function \
  --function-name mcp-tools \
  --runtime python3.11 \
  --handler centralized_mcp_server.main \
  --zip-file fileb://mcp-tools.zip
```

### 2. **AWS ECS (Elastic Container Service)**

**Best for**: Complex MCP tools, persistent connections, full control

**Pros:**

- Full container control
- Persistent connections
- Auto-scaling
- Load balancing

**Cons:**

- More complex setup
- Higher cost for small workloads

**Setup:**

```yaml
# docker-compose.aws.yml
version: "3.8"
services:
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.centralized
    ports:
      - "8000:8000"
    environment:
      - AWS_REGION=us-east-1
    volumes:
      - mcp-data:/app/data
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

volumes:
  mcp-data:
    driver: local
```

### 3. **AWS EC2 (Elastic Compute Cloud)**

**Best for**: Simple deployment, full server control

**Pros:**

- Simple setup
- Full control
- Persistent storage
- Custom networking

**Cons:**

- Manual scaling
- Server management overhead
- Higher cost for small workloads

**Setup:**

```bash
# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx
```

### 4. **AWS App Runner**

**Best for**: Simple web services, automatic deployments

**Pros:**

- Automatic deployments from GitHub
- Built-in load balancing
- Auto-scaling
- Simple setup

**Cons:**

- Limited to HTTP protocols
- Less control over infrastructure

## 🔧 Recommended AWS Setup

### Option A: Lambda + API Gateway (Serverless)

```python
# lambda_handler.py
import json
from centralized_mcp_server import CentralizedMCPServer

def lambda_handler(event, context):
    """AWS Lambda handler for MCP tools"""
    server = CentralizedMCPServer()

    # Handle MCP protocol over HTTP
    if event['httpMethod'] == 'POST':
        body = json.loads(event['body'])
        tool_name = body.get('tool')
        arguments = body.get('arguments', {})

        # Route to appropriate tool handler
        result = await server._handle_tool_call(tool_name, arguments)

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
```

### Option B: ECS with Fargate (Container)

```yaml
# task-definition.json
{
  "family": "mcp-tools",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions":
    [
      {
        "name": "mcp-server",
        "image": "your-account.dkr.ecr.region.amazonaws.com/mcp-tools:latest",
        "portMappings": [{ "containerPort": 8000, "protocol": "tcp" }],
        "environment": [{ "name": "MCP_SERVER_MODE", "value": "production" }],
        "logConfiguration":
          {
            "logDriver": "awslogs",
            "options":
              { "awslogs-group": "/ecs/mcp-tools", "awslogs-region": "us-east-1", "awslogs-stream-prefix": "ecs" },
          },
      },
    ],
}
```

## 📊 Cost Comparison

| Service     | Free Tier   | Small Workload   | Medium Workload  |
| ----------- | ----------- | ---------------- | ---------------- |
| Lambda      | 1M requests | $0.20/M requests | $0.20/M requests |
| ECS Fargate | None        | ~$15/month       | ~$50/month       |
| EC2         | 750h/month  | ~$8/month        | ~$30/month       |
| App Runner  | None        | ~$12/month       | ~$40/month       |

## 🚀 Quick Start: Deploy to AWS

### 1. Build and Push Docker Image

```bash
# Build image
docker build -f Dockerfile.centralized -t mcp-tools .

# Tag for ECR
docker tag mcp-tools:latest your-account.dkr.ecr.region.amazonaws.com/mcp-tools:latest

# Push to ECR
aws ecr get-login-password --region region | docker login --username AWS --password-stdin your-account.dkr.ecr.region.amazonaws.com
docker push your-account.dkr.ecr.region.amazonaws.com/mcp-tools:latest
```

### 2. Deploy to ECS

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name mcp-tools-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster mcp-tools-cluster \
  --service-name mcp-tools-service \
  --task-definition mcp-tools:1 \
  --desired-count 1
```

### 3. Update MCP Configuration

```json
{
  "mcpServers": {
    "aws-mcp": {
      "command": "curl",
      "args": [
        "-X",
        "POST",
        "https://your-api-gateway-url.amazonaws.com/mcp",
        "-H",
        "Content-Type: application/json",
        "-d"
      ],
      "env": {}
    }
  }
}
```

## 🔒 Security Considerations

1. **IAM Roles**: Use least privilege access
2. **VPC**: Isolate in private subnets
3. **Secrets**: Use AWS Secrets Manager
4. **Encryption**: Enable encryption at rest and in transit
5. **Monitoring**: Set up CloudWatch alarms

## 📈 Monitoring and Scaling

### CloudWatch Metrics

- Request count
- Error rate
- Latency
- CPU/Memory usage

### Auto Scaling

- Scale based on CPU usage
- Scale based on custom metrics
- Scale based on schedule

## 💡 Best Practices

1. **Start with Lambda** for simple tools
2. **Use ECS** for complex, persistent tools
3. **Implement proper logging** and monitoring
4. **Use environment variables** for configuration
5. **Set up CI/CD** for automated deployments
6. **Test thoroughly** before production deployment
