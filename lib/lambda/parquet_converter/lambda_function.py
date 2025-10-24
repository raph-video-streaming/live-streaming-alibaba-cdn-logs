import json
import boto3
import gzip
import re
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from urllib.parse import unquote
import io

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    athena_client = boto3.client('athena')
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote(record['s3']['object']['key'])
        
        if not key.endswith('.gz'):
            continue
            
        print(f"Processing: s3://{bucket}/{key}")
        
        # Extract partition info from S3 key
        match = re.search(r'year=(\d{4})/month=(\d{2})/day=(\d{2})', key)
        if not match:
            print(f"Could not extract partition info from {key}")
            continue
            
        year, month, day = match.groups()
        
        # Process file in chunks to avoid memory issues
        process_file_in_chunks(s3_client, athena_client, bucket, key, year, month, day)
    
    return {'statusCode': 200, 'body': json.dumps('Processing complete')}

def process_file_in_chunks(s3_client, athena_client, bucket, key, year, month, day):
    CHUNK_SIZE = 50000  # Process 50k lines at a time
    
    # Download and stream gz file
    response = s3_client.get_object(Bucket=bucket, Key=key)
    gz_size = response['ContentLength']
    print(f"📥 Processing gz file: {gz_size} bytes")
    
    chunk_num = 0
    total_processed = 0
    
    with gzip.GzipFile(fileobj=response['Body']) as gz_file:
        lines_buffer = []
        
        for line in gz_file:
            line = line.decode('utf-8').strip()
            if line:
                lines_buffer.append(line)
                
                # Process chunk when buffer is full
                if len(lines_buffer) >= CHUNK_SIZE:
                    processed = process_chunk(s3_client, lines_buffer, bucket, key, year, month, day, chunk_num)
                    total_processed += processed
                    chunk_num += 1
                    lines_buffer = []  # Clear buffer
                    print(f"📦 Processed chunk {chunk_num}: {processed} entries")
        
        # Process remaining lines
        if lines_buffer:
            processed = process_chunk(s3_client, lines_buffer, bucket, key, year, month, day, chunk_num)
            total_processed += processed
            chunk_num += 1
            print(f"📦 Processed final chunk: {processed} entries")
    
    # Add partition after all chunks are processed
    add_partition_query = f"""
    ALTER TABLE cdn_logs_alibaba_partitioned.cdn_logs_parquet 
    ADD IF NOT EXISTS PARTITION (year='{year}', month='{month}', day='{day}')
    LOCATION 's3://{bucket}/alibaba-cdn/alibaba-cdn_parquet/year={year}/month={month}/day={day}/'
    """
    
    athena_client.start_query_execution(
        QueryString=add_partition_query,
        ResultConfiguration={'OutputLocation': 's3://spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf/athena-results/'}
    )
    
    print(f"✅ Total processed: {total_processed} entries in {chunk_num} chunks")

def process_chunk(s3_client, lines, bucket, key, year, month, day, chunk_num):
    # Parse lines in chunk
    parsed_logs = []
    for line in lines:
        parsed_log = parse_log_line(line)
        if parsed_log:
            parsed_logs.append(parsed_log)
    
    if not parsed_logs:
        return 0
    
    # Convert to parquet
    df = pd.DataFrame(parsed_logs)
    
    # Convert data types
    df['response_time'] = pd.to_numeric(df['response_time'], errors='coerce').fillna(0).astype('int64')
    df['http_status'] = pd.to_numeric(df['http_status'], errors='coerce').fillna(200).astype('int32')
    df['request_bytes'] = pd.to_numeric(df['request_bytes'], errors='coerce').fillna(0).astype('int64')
    df['response_bytes'] = pd.to_numeric(df['response_bytes'], errors='coerce').fillna(0).astype('int64')
    
    table = pa.Table.from_pandas(df)
    
    # Create chunk filename
    base_filename = key.split("/")[-1].replace(".gz", "")
    parquet_key = f'alibaba-cdn/alibaba-cdn_parquet/year={year}/month={month}/day={day}/{base_filename}_chunk_{chunk_num:04d}.parquet'
    
    # Write parquet
    parquet_buffer = pa.BufferOutputStream()
    pq.write_table(table, parquet_buffer, compression='gzip', compression_level=9)
    
    s3_client.put_object(
        Bucket=bucket,
        Key=parquet_key,
        Body=parquet_buffer.getvalue().to_pybytes(),
        ContentType='application/octet-stream'
    )
    
    # Clear memory
    del df, table, parquet_buffer
    
    return len(parsed_logs)

def parse_log_line(line):
    pattern = r'\[([^\s]+)\s+([^\]]+)\]\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"([^"]*)"\s+"([^\s]+)\s+([^"]*?)"\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"([^"]*)"\s+"([^"]*)"\s+([^\s]+)'
    
    match = re.match(pattern, line)
    if not match:
        return None
    
    groups = match.groups()
    
    return {
        'date_time': groups[0],
        'timezone': groups[1],
        'client_ip': groups[2],
        'proxy_ip': groups[3],
        'response_time': groups[4],
        'referrer': groups[5],
        'http_method': groups[6],
        'request_url': groups[7],
        'http_status': groups[8],
        'request_bytes': groups[9],
        'response_bytes': groups[10],
        'cache_status': groups[11],
        'user_agent': groups[12],
        'file_type': groups[13],
        'access_ip': groups[14]
    }