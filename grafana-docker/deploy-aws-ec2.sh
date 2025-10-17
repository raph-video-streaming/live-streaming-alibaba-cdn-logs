#!/bin/bash

# AWS EC2 Deployment Script for Grafana with Aliyun Plugin

set -e

echo "🚀 Deploying Grafana with Aliyun Plugin to AWS EC2..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install it first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
export PUBLIC_IP

echo "🌐 Public IP: $PUBLIC_IP"

# Update system
echo "📦 Updating system packages..."
sudo yum update -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker ec2-user
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create application directory
APP_DIR="/opt/grafana-aliyun"
sudo mkdir -p $APP_DIR
sudo chown ec2-user:ec2-user $APP_DIR

# Copy files
echo "📁 Copying application files..."
cp -r . $APP_DIR/
cd $APP_DIR

# Build and start services
echo "🔨 Building and starting Grafana..."
docker-compose -f docker-compose.aws.yml up -d --build

# Wait for service to be ready
echo "⏳ Waiting for Grafana to start..."
sleep 30

# Check if service is running
if docker-compose -f docker-compose.aws.yml ps | grep -q "Up"; then
    echo "✅ Grafana deployed successfully!"
    echo "🌐 Access Grafana at: http://$PUBLIC_IP"
    echo "👤 Default credentials: admin / admin"
    echo ""
    echo "📊 To configure Aliyun Log Service:"
    echo "   1. Go to Configuration → Data Sources"
    echo "   2. Add 'Aliyun Log Service' data source"
    echo "   3. Enter your Aliyun credentials"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker-compose -f docker-compose.aws.yml logs -f"
    echo "   Stop: docker-compose -f docker-compose.aws.yml down"
    echo "   Restart: docker-compose -f docker-compose.aws.yml restart"
else
    echo "❌ Failed to start Grafana"
    echo "📋 Checking logs..."
    docker-compose -f docker-compose.aws.yml logs
    exit 1
fi

