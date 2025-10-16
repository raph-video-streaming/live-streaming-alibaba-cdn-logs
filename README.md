# Alibaba CDN Log Processor - CDK Deployment

AWS CDK deployment for Alibaba CDN log processing with automated EventBridge scheduling.

## Quick Deploy

```bash
cd cdk-deployment
./deploy.sh
```

## Architecture

- **Lambda Function**: ARM64 Python 3.12 runtime (15min timeout, 1GB memory)
- **Aliyun CLI Layer**: Alibaba Cloud CLI binary with requests library
- **EventBridge Rules**: Automated execution at noon and midnight UTC
- **S3 Output**: `s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_parquet/`
- **Partitioning**: `year=YYYY/month=MM/day=DD/` structure for Athena queries

## Current Status

⚠️ **Known Issues:**
- AWS managed pandas layer not available in me-central-1 region
- EventBridge rules defined in CDK but may not appear in Console until TypeScript is compiled
- Lambda performance: 9+ minutes to process and convert logs to Parquet
- Date format compatibility issues with existing Parquet schema

## Manual Steps

1. **Install dependencies:**
```bash
npm install
```

2. **Build layers:**
```bash
./build-layers.sh
```

3. **Compile TypeScript:**
```bash
npm run build
```

4. **Deploy:**
```bash
export AWS_PROFILE=spl && cdk deploy --require-approval never
```

## Test

**Manual Execution:**
```bash
FUNCTION_NAME=$(aws cloudformation describe-stacks --stack-name AlibabaCdnLogsStack --query 'Stacks[0].Outputs[?OutputKey==`FunctionName`].OutputValue' --output text --profile spl --region me-central-1)

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"domain":"alibaba-live.servers8.com","start_date":"2025-10-14","end_date":"2025-10-14"}' \
    response.json \
    --region me-central-1 \
    --profile spl
```

**Scheduled Execution:**
- Noon UTC (12:00): Collects previous day's logs
- Midnight UTC (00:00): Collects previous day's logs
- EventBridge automatically calculates date range

## Troubleshooting

**EventBridge Rules Not Visible:**
1. Ensure TypeScript is compiled: `npm run build`
2. Redeploy: `export AWS_PROFILE=spl && cdk deploy`
3. Check CloudFormation stack for rule creation

**Lambda Performance Issues:**
- Current: 9+ minutes processing time
- Bottlenecks: Parquet conversion, network I/O
- Consider: Parallel processing, streaming conversion

**Date Format Issues:**
- Logs contain: `10/Oct/2025:09:42:11`
- Must preserve exact string format for Athena compatibility
- Avoid datetime conversion in pandas

**Layer Dependencies:**
- Aliyun CLI Layer: Contains CLI binary + requests library
- No pandas layer due to me-central-1 region limitations
- Function includes pandas/pyarrow in deployment package