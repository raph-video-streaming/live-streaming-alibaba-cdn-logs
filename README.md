# Alibaba CDN Log Processor - CDK Deployment

Automated AWS Lambda function to download Alibaba CDN logs, convert to Parquet format, and store in S3 with partitioned structure.
AWS CDK deployment for Alibaba CDN log processing with automated EventBridge scheduling.
## Features

- Downloads CDN logs from Alibaba Cloud API
- Converts gzipped text logs to compressed Parquet format
- Stores in S3 with partitioned structure: `year=YYYY/month=MM/day=DD/`
- Optimized for fast processing with minimal memory usage
- Secure credential management via AWS Secrets Manager

## Architecture

```
Lambda Function (ARM64) + Aliyun CLI Layer
    ↓
Alibaba CDN API → Download .gz logs
    ↓
Parse & Convert → Parquet (Snappy compression)
    ↓
S3 Upload → s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_parquet/
```


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

Deploy 2 stacks:
* **AlibabaCdnLogsStack** : to deploy the lambda and download the logs in S3
* **ParquetConversionStack** : to parse the gz logs and convert them into parquet files using s3 event triggers and lambda

(the other stack AlibabaCdnAthenaStack is just for historical record to see how to insert table in cdk )

## Manual Steps

1. **Install dependencies:**
```bash
npm install
```

2. **Build layers:**
```bash
./build-layers.sh
```

4. **Deploy:**
```bash
export AWS_PROFILE=spl && cdk deploy AlibabaCdnLogsStack ParquetConversionStack
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