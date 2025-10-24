#!/usr/bin/env python3
"""
Convert existing S3 CDN logs to Parquet format using Athena CTAS
This is the fastest way to convert your existing partitioned logs
"""
import boto3
import time

def convert_logs_to_parquet():
    session = boto3.Session(profile_name='spl')
    athena = session.client('athena')
    
    bucket_name = "spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf"
    source_logs_path = "logs/alibaba-cdn_partitioned/"
    target_parquet_path = "logs/alibaba-cdn_parquet/"
    database_name = 'cdn_logs_alibaba_parquet'
    result_location = f's3://{bucket_name}/athena-results/'
    
    def run_query(query, description):
        print(f"{description}...")
        response = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={'OutputLocation': result_location}
        )
        query_id = response['QueryExecutionId']
        
        # Wait for completion
        while True:
            result = athena.get_query_execution(QueryExecutionId=query_id)
            status = result['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(5)
            print(f"  Status: {status}")
        
        if status == 'FAILED':
            error = result['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
            print(f"❌ Query failed: {error}")
            return None
        
        print(f"✅ {description} completed")
        return query_id
    
    # First, create a temporary table to read from your existing partitioned logs
    temp_table_query = f"""
    CREATE EXTERNAL TABLE {database_name}.temp_alibaba_logs (
      date_time STRING,
      timezone STRING,
      client_ip STRING,
      proxy_ip STRING,
      response_time STRING,
      referrer STRING,
      http_method STRING,
      request_url STRING,
      http_status STRING,
      request_bytes STRING,
      response_bytes STRING,
      cache_status STRING,
      user_agent STRING,
      file_type STRING,
      access_ip STRING
    )
    PARTITIONED BY (
      year STRING,
      month STRING,
      day STRING
    )
    ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
    WITH SERDEPROPERTIES (
        'input.regex' = '\\\\[([^\\\\s]+)\\\\s+([^\\\\]]+)\\\\]\\\\s+([^\\\\s]+)\\\\s+([^\\\\s]+)\\\\s+([^\\\\s]+)\\\\s+"([^"]*)"\\\\s+"([^\\\\s]+)\\\\s+([^\\\\s]+)"\\\\s+([^\\\\s]+)\\\\s+([^\\\\s]+)\\\\s+([^\\\\s]+)\\\\s+([^\\\\s]+)\\\\s+"([^"]*)"\\\\s+"([^"]*)"\\\\s+([^\\\\s]+)'
    )
    LOCATION 's3://{bucket_name}/{source_logs_path}/'
    TBLPROPERTIES (
      'has_encrypted_data'='false',
      'compressionType'='gzip',
      'projection.enabled'='true',
      'projection.year.type'='integer',
      'projection.year.range'='2024,2026',
      'projection.month.type'='integer',
      'projection.month.range'='01,12',
      'projection.month.digits'='2',
      'projection.day.type'='integer',
      'projection.day.range'='01,31',
      'projection.day.digits'='2',
      'storage.location.template'='s3://{bucket_name}/{source_logs_path}/year=${{year}}/month=${{month}}/day=${{day}}/'
    )
    """
    
    run_query(temp_table_query, "Creating temporary table to read existing logs")
    
    # Repair table to load partitions
    run_query(f"MSCK REPAIR TABLE {database_name}.temp_alibaba_logs", "Loading partitions")
    
    # Convert to Parquet using CTAS (Create Table As Select)
    ctas_query = f"""
    CREATE TABLE {database_name}.alibaba_cdn_logs_parquet
    WITH (
      format = 'PARQUET',
      parquet_compression = 'SNAPPY',
      partitioned_by = ARRAY['year', 'month', 'day'],
      external_location = 's3://{bucket_name}/{target_parquet_path}/'
    )
    AS
    SELECT 
      CAST(date_time AS TIMESTAMP) as date_time,
      timezone,
      client_ip,
      proxy_ip,
      CAST(response_time AS DOUBLE) as response_time,
      referrer,
      http_method,
      request_url,
      CAST(http_status AS INT) as http_status,
      CAST(request_bytes AS BIGINT) as request_bytes,
      CAST(response_bytes AS BIGINT) as response_bytes,
      cache_status,
      user_agent,
      file_type,
      access_ip,
      year,
      month,
      day
    FROM {database_name}.temp_alibaba_logs
    WHERE year IS NOT NULL 
      AND month IS NOT NULL 
      AND day IS NOT NULL
    """
    
    print("🚀 Starting conversion to Parquet format...")
    print("⏳ This may take several minutes depending on data size...")
    
    run_query(ctas_query, "Converting logs to Parquet format")
    
    # Create optimized view
    view_query = f"""
    CREATE OR REPLACE VIEW {database_name}.alibaba_cdn_logs_view AS
    SELECT 
      date_time,
      timezone,
      client_ip,
      proxy_ip,
      response_time,
      referrer,
      http_method,
      request_url,
      http_status,
      request_bytes,
      response_bytes,
      cache_status,
      user_agent,
      file_type,
      access_ip,
      year,
      month,
      day,
      -- Add computed columns for common queries
      CASE 
        WHEN http_status BETWEEN 200 AND 299 THEN '2xx'
        WHEN http_status BETWEEN 300 AND 399 THEN '3xx'
        WHEN http_status BETWEEN 400 AND 499 THEN '4xx'
        WHEN http_status BETWEEN 500 AND 599 THEN '5xx'
        ELSE 'other'
      END as status_category,
      -- Extract domain from request_url
      regexp_extract(request_url, 'https?://([^/]+)', 1) as domain,
      -- Extract file extension
      regexp_extract(request_url, '\\.([^.]+)$', 1) as file_extension
    FROM {database_name}.alibaba_cdn_logs_parquet
    """
    
    run_query(view_query, "Creating optimized view")
    
    # Clean up temporary table
    run_query(f"DROP TABLE {database_name}.temp_alibaba_logs", "Cleaning up temporary table")
    
    print("\n✅ Conversion complete!")
    print(f"📊 Database: {database_name}")
    print(f"📊 Table: {database_name}.alibaba_cdn_logs_parquet")
    print(f"📊 View: {database_name}.alibaba_cdn_logs_view")
    print(f"📁 Parquet files location: s3://{bucket_name}/{target_parquet_path}/")
    
    # Test query to verify data
    test_query = f"""
    SELECT COUNT(*) as total_records,
           COUNT(DISTINCT year) as years,
           COUNT(DISTINCT month) as months,
           MIN(date_time) as earliest_log,
           MAX(date_time) as latest_log
    FROM {database_name}.alibaba_cdn_logs_parquet
    """
    
    print("\n🔍 Running verification query...")
    run_query(test_query, "Verifying converted data")

if __name__ == "__main__":
    convert_logs_to_parquet()


