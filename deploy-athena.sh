#!/bin/bash

set -e

echo "🚀 Deploying Alibaba CDN Log Processor with Athena (Recommended Approach)..."

# Install dependencies
echo "📦 Installing CDK dependencies..."
npm install

# Deploy only the Athena stack
echo "🎆 Deploying Athena-based stack..."
npx cdk deploy AlibabaCdnAthenaStack --require-approval never

echo "✅ Athena-based deployment complete!"
echo ""
echo "🧪 Test with:"
echo "aws lambda invoke --function-name \$(aws cloudformation describe-stacks --stack-name AlibabaCdnAthenaStack --query 'Stacks[0].Outputs[?OutputKey==\`FunctionName\`].OutputValue' --output text --profile spl) --payload '{\"start_date\":\"2025-10-17\",\"end_date\":\"2025-10-17\"}' response.json --region me-central-1 --profile spl"
echo ""
echo "📊 Benefits of Athena approach:"
echo "  - Much faster processing (Athena is optimized for large datasets)"
echo "  - No memory limitations"
echo "  - Automatic partitioning"
echo "  - Cost-effective for large volumes"
echo "  - Built-in compression and optimization"
