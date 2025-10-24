#!/bin/bash

set -e

echo "🚀 Deploying Alibaba CDN Log Processor with CDK..."

# Install dependencies
echo "📦 Installing CDK dependencies..."
npm install

# Build layers
echo "🔨 Building Lambda layers..."
chmod +x build-layers.sh
./build-layers.sh


# Bootstrap CDK (if needed)
echo "🎆 Bootstrapping CDK..."
npm run bootstrap || echo "Bootstrap already done"

# Deploy with CDK
echo "🚀 Deploying stack..."
npm run deploy

echo "✅ Deployment complete!"
echo ""
echo "🧪 Test with:"
echo "aws lambda invoke --function-name \$(aws cloudformation describe-stacks --stack-name AlibabaCdnLogsStack --query 'Stacks[0].Outputs[?OutputKey==\`FunctionName\`].OutputValue' --output text --profile spl) --payload '{\"domain\":\"alibaba.servers8.com\",\"start_date\":\"2025-10-14\",\"end_date\":\"2025-10-14\"}' response.json --region me-central-1 --profile spl"