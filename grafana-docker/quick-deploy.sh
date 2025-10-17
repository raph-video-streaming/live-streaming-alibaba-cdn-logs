#!/bin/bash

# Quick Deployment Script for Grafana with Aliyun Plugin
# Supports multiple deployment platforms

set -e

echo "🚀 Grafana with Aliyun Plugin - Quick Deploy"
echo "=============================================="

# Function to show help
show_help() {
    echo "Usage: $0 [platform]"
    echo ""
    echo "Platforms:"
    echo "  render     Deploy to Render.com (fastest)"
    echo "  fly        Deploy to Fly.io"
    echo "  aws-ecs    Deploy to AWS ECS using CDK"
    echo "  aws-ec2    Deploy to AWS EC2"
    echo "  local      Run locally with Docker"
    echo ""
    echo "Examples:"
    echo "  $0 render    # Deploy to Render.com"
    echo "  $0 fly       # Deploy to Fly.io"
    echo "  $0 local     # Run locally"
}

# Function to deploy to Render.com
deploy_render() {
    echo "🌐 Deploying to Render.com..."
    echo ""
    echo "📋 Steps:"
    echo "1. Push your code to GitHub"
    echo "2. Go to https://render.com"
    echo "3. Connect your GitHub repository"
    echo "4. Select 'Web Service'"
    echo "5. Use these settings:"
    echo "   - Build Command: (leave empty)"
    echo "   - Start Command: (leave empty)"
    echo "   - Environment: Docker"
    echo "   - Dockerfile Path: ./grafana-docker/Dockerfile"
    echo "   - Docker Context: ./grafana-docker"
    echo "6. Add environment variables:"
    echo "   - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=aliyun-log-service-datasource"
    echo "   - GF_SECURITY_ADMIN_USER=admin"
    echo "   - GF_SECURITY_ADMIN_PASSWORD=admin"
    echo ""
    echo "✅ Your render.yaml is already configured!"
}

# Function to deploy to Fly.io
deploy_fly() {
    echo "🪰 Deploying to Fly.io..."
    
    # Check if flyctl is installed
    if ! command -v flyctl &> /dev/null; then
        echo "📦 Installing flyctl..."
        curl -L https://fly.io/install.sh | sh
        export PATH="$HOME/.fly/bin:$PATH"
    fi
    
    echo "🔐 Logging in to Fly.io..."
    flyctl auth login
    
    echo "🚀 Deploying application..."
    flyctl launch --no-deploy
    
    echo "🔨 Building and deploying..."
    flyctl deploy
    
    echo "✅ Deployment complete!"
    echo "🌐 Your app will be available at: https://$(flyctl info --json | jq -r '.Hostname')"
}

# Function to deploy to AWS ECS
deploy_aws_ecs() {
    echo "☁️ Deploying to AWS ECS..."
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        echo "📦 Installing AWS CDK..."
        npm install -g aws-cdk
    fi
    
    echo "🔧 Installing dependencies..."
    npm install
    
    echo "🚀 Deploying CDK stack..."
    cdk deploy --require-approval never
    
    echo "✅ Deployment complete!"
}

# Function to deploy to AWS EC2
deploy_aws_ec2() {
    echo "🖥️ Deploying to AWS EC2..."
    echo ""
    echo "📋 Steps:"
    echo "1. Launch an EC2 instance (t3.small or larger)"
    echo "2. Configure security group to allow HTTP (port 80) and SSH (port 22)"
    echo "3. SSH into your instance"
    echo "4. Run: curl -sSL https://raw.githubusercontent.com/your-repo/grafana-docker/main/deploy-aws-ec2.sh | bash"
    echo ""
    echo "Or manually:"
    echo "1. Copy the grafana-docker folder to your EC2 instance"
    echo "2. Run: ./deploy-aws-ec2.sh"
}

# Function to run locally
deploy_local() {
    echo "🏠 Running locally..."
    
    if [ -f "docker-compose.yml" ]; then
        echo "🐳 Starting with Docker Compose..."
        docker-compose up -d --build
    else
        echo "🐳 Starting with Docker..."
        docker build -t grafana-aliyun .
        docker run -d --name grafana-aliyun -p 3000:3000 grafana-aliyun
    fi
    
    echo "✅ Grafana started locally!"
    echo "🌐 Access at: http://localhost:3000"
    echo "👤 Credentials: admin / admin"
}

# Main script logic
case "${1:-help}" in
    "render")
        deploy_render
        ;;
    "fly")
        deploy_fly
        ;;
    "aws-ecs")
        deploy_aws_ecs
        ;;
    "aws-ec2")
        deploy_aws_ec2
        ;;
    "local")
        deploy_local
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown platform: $1"
        show_help
        exit 1
        ;;
esac

