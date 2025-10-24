#!/usr/bin/env python3
"""
Athena deployment with Parquet format for alibaba-live CDN logs
Parquet provides better compression, columnar storage, and faster queries
"""
import boto3
import time
"""
old way to create table
CREATE EXTERNAL TABLE cdn_logs_alibaba_live.alibaba_cdn_logs (
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
        'input.regex' = '\\[([^\\s]+)\\s+([^\\]]+)\\]\\s+([^\\s]+)\\s+([^\\s]+)\\s+([^\\s]+)\\s+"([^"]*)"\\s+"([^\\s]+)\\s+([^\\s]+)"\\s+([^\\s]+)\\s+([^\\s]+)\\s+([^\\s]+)\\s+([^\\s]+)\\s+"([^"]*)"\\s+"([^"]*)"\\s+([^\\s]+)'
    )
    LOCATION 's3://spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf/logs/alibaba-live-cdn/'
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
      'storage.location.template'='s3://spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf/logs/alibaba-live-cdn/year=${year}/month=${month}/day=${day}/'
    )
    
"""
def setup_athena_parquet():
    session = boto3.Session(profile_name='spl')
    athena = session.client('athena')
    
    bucket_name = "spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf"
    logs_path = "logs/alibaba-cdn_parquet/"
    database_name = 'cdn_logs_alibaba_parquet'
    result_location = f's3://{bucket_name}/athena-results/'
    
    def run_query(query, description):
        print(f"{description}...")
        response = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={'OutputLocation': result_location}
        )
        time.sleep(3)
        return response['QueryExecutionId']
    
    # Drop and recreate database
    run_query(f"DROP DATABASE IF EXISTS {database_name} CASCADE", "Dropping database")
    run_query(f"CREATE DATABASE {database_name}", "Creating database")
    
    # Create Parquet table with optimized schema
    create_table = f"""
    CREATE EXTERNAL TABLE {database_name}.alibaba_cdn_logs_parquet (
      date_time TIMESTAMP,
      timezone STRING,
      client_ip STRING,
      proxy_ip STRING,
      response_time DOUBLE,
      referrer STRING,
      http_method STRING,
      request_url STRING,
      http_status INT,
      request_bytes BIGINT,
      response_bytes BIGINT,
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
    STORED AS PARQUET
    LOCATION 's3://{bucket_name}/{logs_path}/'
    TBLPROPERTIES (
      'has_encrypted_data'='false',
      'parquet.compression'='SNAPPY',
      'projection.enabled'='true',
      'projection.year.type'='integer',
      'projection.year.range'='2024,2026',
      'projection.month.type'='integer',
      'projection.month.range'='01,12',
      'projection.month.digits'='2',
      'projection.day.type'='integer',
      'projection.day.range'='01,31',
      'projection.day.digits'='2',
      'storage.location.template'='s3://{bucket_name}/{logs_path}/year=${{year}}/month=${{month}}/day=${{day}}/'
    )
    """
    
    run_query(create_table, "Creating Parquet table")
    
    # Create a view for easier querying with proper data types
    create_view = f"""
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
    
    run_query(create_view, "Creating optimized view")
    
    print("✅ Parquet setup complete!")
    print(f"✅ Database: {database_name}")
    print(f"✅ Table: {database_name}.alibaba_cdn_logs_parquet")
    print(f"✅ View: {database_name}.alibaba_cdn_logs_view")
    print("\n📊 Performance benefits:")
    print("  • Columnar storage for faster analytics")
    print("  • Snappy compression for reduced storage costs")
    print("  • Optimized data types (INT, BIGINT, TIMESTAMP)")
    print("  • Pre-computed status categories and domain extraction")
    print("\n💡 Usage example:")
    print(f"  SELECT * FROM {database_name}.alibaba_cdn_logs_view")
    print("  WHERE year = '2024' AND month = '12' AND status_category = '4xx'")
    print("  LIMIT 10;")

if __name__ == "__main__":
    setup_athena_parquet()


