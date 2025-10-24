#!/bin/bash

echo "Deploying Parquet Conversion Stack..."

# Deploy the stack
npx cdk deploy ParquetConversionStack --require-approval never

echo "Deployment complete!"
echo ""
echo "The stack will automatically:"
echo "1. Monitor s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_partitioned/ for new .gz files"
echo "2. Convert data to Parquet format in s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_parquet/"
echo "3. Update the Athena table: cdn_logs_alibaba_partitioned.cdn_logs_parquet"
echo "4. Delete the original .gz files after successful conversion"