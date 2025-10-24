#!/usr/bin/env python3
import boto3
import time

def benchmark_queries():
    session = boto3.Session(profile_name='spl')
    athena = session.client('athena')
    
    bucket_name = "spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf"
    database_name = 'cdn_logs_alibaba_partitioned'
    result_location = f's3://{bucket_name}/athena-results/'
    
    def run_timed_query(query, description):
        print(f"\n🔍 Running {description}...")
        start_time = time.time()
        
        response = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={'OutputLocation': result_location}
        )
        
        query_id = response['QueryExecutionId']
        while True:
            result = athena.get_query_execution(QueryExecutionId=query_id)
            status = result['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(1)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if status == 'SUCCEEDED':
            # Get data scanned
            stats = result['QueryExecution']['Statistics']
            data_scanned = stats.get('DataScannedInBytes', 0) / (1024**3)  # GB
            print(f"✅ {description}: {duration:.1f}s | {data_scanned:.2f}GB scanned")
        else:
            # Get detailed error information
            error_info = result['QueryExecution']['Status'].get('StateChangeReason', 'No error details available')
            print(f"❌ {description} failed: {status}")
            print(f"   Error: {error_info}")
        
        return duration, status == 'SUCCEEDED'
    
    # Simple total volume query - using broader date range to find actual data
    base_query = """
    SELECT 
      COUNT(*) as total_requests,
      SUM(CAST(request_bytes AS BIGINT)) as total_request_bytes,
      SUM(CAST(response_bytes AS BIGINT)) as total_response_bytes,
      AVG(CAST(response_time AS DOUBLE)) as avg_response_time
    FROM {table_name}
    WHERE year = '2025' 
      AND month = '10'
      AND response_time IS NOT NULL
    """
    
    # Original gzipped table query
    original_query = base_query.format(table_name=f'"{database_name}".alibaba_cdn_logs')
    
    # Parquet table query (using different database for parquet)
    parquet_query = base_query.format(table_name=f'"cdn_logs_alibaba_live".alibaba_cdn_logs_parquet')
    
    print(f"📊 Benchmarking total volume query (Oct 2025)")
    print("=" * 50)
    
    # Run original query
    orig_time, orig_success = run_timed_query(original_query, "Original (gzipped)")
    
    # Run parquet query
    parquet_time, parquet_success = run_timed_query(parquet_query, "Parquet optimized")
    
    # Show comparison
    if orig_success and parquet_success:
        speedup = orig_time / parquet_time
        print(f"\n🚀 Performance improvement: {speedup:.1f}x faster with Parquet!")
        print(f"   Original (gzipped): {orig_time:.1f}s")
        print(f"   Parquet optimized:  {parquet_time:.1f}s")

if __name__ == "__main__":
    benchmark_queries()
    