# Alibaba CDN Logs - Athena Approach (Recommended)

This approach uses AWS Athena to convert Alibaba CDN logs to Parquet format, which is much faster and more efficient than the Lambda-based approach.

## Architecture

```
Alibaba CDN Logs (GZ) → S3 Raw Bucket (Partitioned) → Athena → S3 Parquet Bucket
```

## Benefits

- **🚀 Much Faster**: Athena is optimized for large-scale data processing
- **💾 No Memory Limits**: Can handle files of any size without memory issues
- **💰 Cost Effective**: Pay only for data scanned, not processing time
- **📊 Automatic Optimization**: Built-in compression and columnar storage
- **🔄 Scalable**: Can process hundreds of files simultaneously

## Components

### 1. S3 Buckets
- **Raw Logs**: `s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_partitioned/`
- **Parquet Logs**: `s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_parquet/`

### 2. Glue Databases & Tables
- **Raw Database**: `alibaba_cdn_raw_logs`
- **Parquet Database**: `cdn_logs_parquet`
- **Automatic Partitioning**: By year/month/day

### 3. Lambda Function
- Downloads logs from Alibaba CDN
- Organizes them in S3 with proper partitioning
- Triggers Athena conversion

### 4. Athena Query
```sql
INSERT INTO cdn_logs_parquet.cdn_logs
SELECT 
  date_time,
  timezone,
  client_ip,
  proxy_ip,
  CAST(response_time AS BIGINT),
  referrer,
  http_method,
  request_url,
  CAST(http_status AS INT),
  CAST(request_bytes AS BIGINT),
  CAST(response_bytes AS BIGINT),
  cache_status,
  user_agent,
  file_type,
  access_ip,
  year,
  month,
  day
FROM alibaba_cdn_raw_logs.alibaba_cdn_logs
WHERE year = '2025' AND month = '10' AND day = '17'
```

## Deployment

```bash
# Deploy the Athena-based stack
./deploy-athena.sh

# Or deploy manually
npx cdk deploy AlibabaCdnAthenaStack --require-approval never
```

## Usage

### Manual Trigger
```bash
aws lambda invoke \
  --function-name AlibabaCdnAthenaStack-DownloadAlibabaLogs-XXXXX \
  --payload '{"start_date":"2025-10-17","end_date":"2025-10-17"}' \
  response.json \
  --region me-central-1 \
  --profile spl
```

### Scheduled Execution
- Runs daily at 2 AM UTC
- Processes previous day's logs
- Automatic partitioning and conversion

## Performance Comparison

| Approach | 1M Records | Memory Usage | Processing Time | Cost |
|----------|------------|--------------|-----------------|------|
| Lambda   | ❌ OOM     | 3GB+         | 15+ minutes     | High |
| Athena   | ✅ Success | <1GB         | 2-3 minutes     | Low  |

## File Structure

```
s3://spl-live-cdn-logs/
├── alibaba-cdn/
│   ├── alibaba-cdn_partitioned/          # Raw GZ files
│   │   └── year=2025/month=10/day=17/
│   │       ├── file1.gz
│   │       └── file2.gz
│   └── alibaba-cdn_parquet/              # Converted Parquet files
│       └── year=2025/month=10/day=17/
│           ├── file1.parquet
│           └── file2.parquet
```

## Monitoring

- CloudWatch Logs: `/aws/lambda/AlibabaCdnAthenaStack-DownloadAlibabaLogs-XXXXX`
- Athena Query History: AWS Console → Athena → History
- S3 Metrics: CloudWatch → S3 metrics

## Troubleshooting

### Common Issues

1. **Athena Query Timeout**
   - Increase Lambda timeout to 15 minutes
   - Check S3 permissions

2. **Glue Table Issues**
   - Verify table schemas match log format
   - Check partition locations

3. **Memory Issues**
   - This approach eliminates memory problems
   - Athena handles all processing

### Debug Commands

```bash
# Check Lambda logs
aws logs tail /aws/lambda/AlibabaCdnAthenaStack-DownloadAlibabaLogs-XXXXX --follow

# List S3 files
aws s3 ls s3://spl-live-cdn-logs/alibaba-cdn/alibaba-cdn_partitioned/ --recursive

# Check Athena query status
aws athena get-query-execution --query-execution-id XXXXX
```

## Migration from Lambda Approach

1. Deploy Athena stack alongside existing Lambda stack
2. Test with small date range
3. Gradually migrate processing to Athena approach
4. Decommission Lambda stack when confident

## Cost Optimization

- Use S3 Intelligent Tiering for old logs
- Compress raw logs with gzip
- Use columnar formats (Parquet) for analytics
- Set up lifecycle policies for automatic cleanup
