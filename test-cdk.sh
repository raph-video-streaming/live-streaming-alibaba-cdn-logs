#!/bin/bash

set -e

echo "🧪 Testing CDK configuration..."

# Check if AWS credentials are configured
echo "🔍 Checking AWS credentials..."
aws sts get-caller-identity --profile spl || {
    echo "❌ AWS credentials not configured for 'spl' profile"
    echo "Please run: aws configure --profile spl"
    exit 1
}

echo "✅ AWS credentials found"

# Test CDK bootstrap
echo "🎆 Testing CDK bootstrap..."
npx cdk bootstrap --app cdk.ci.json || echo "Bootstrap may already be done"

# Test CDK synth
echo "🔧 Testing CDK synth..."
npx cdk synth --app cdk.ci.json

echo "✅ CDK configuration test passed!"
