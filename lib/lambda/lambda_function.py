import json
import os
import subprocess
import boto3
import re
import gzip
import io
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from urllib.parse import urlparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import partial


def lambda_handler(event, context):
    try:
        domain = event.get('domain', 'alibaba-live.servers8.com')
        
        # Handle scheduled execution
        if event.get('scheduled'):
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            print(f"Scheduled execution: collecting logs from {start_date} to {end_date}")
        else:
            start_date = event.get('start_date')
            end_date = event.get('end_date')
            if not start_date or not end_date:
                raise ValueError("start_date and end_date are required")
            print(f"Manual execution: collecting logs from {start_date} to {end_date}")
        
        # Use exact same format as manual command
        start_time = f"{start_date}T00:00:00Z"
        end_time = f"{end_date}T23:59:59Z"
        
        print(f"Requesting logs from: {start_time} to {end_time}")
        print(f"Using domain: {domain}")
        
        configure_aliyun_cli()
        log_urls = get_cdn_log_urls(domain, start_time, end_time)
        print(f"Found {len(log_urls)} log files to process")
        
        # Debug: Print first few URLs to see the time ranges
        if log_urls:
            print("Sample log URLs:")
            for i, url in enumerate(log_urls[:5]):
                print(f"  {i+1}: {url}")
        
        if not log_urls:
            print("No logs found for the specified date range")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No logs found'})
            }
        
        # Process files sequentially to avoid memory issues with large files
        uploaded_files = []
        
        print(f"Processing {len(log_urls)} files sequentially to avoid memory issues...")
        
        for i, url in enumerate(log_urls, 1):
            try:
                print(f"Processing file {i}/{len(log_urls)}: {os.path.basename(url)}")
                result = upload_log_file(url)
                
                # Handle both single file and multiple files (for large files)
                if isinstance(result, list):
                    uploaded_files.extend(result)
                    print(f"Successfully uploaded {len(result)} files for large dataset")
                else:
                    uploaded_files.append(result)
                    print(f"Successfully uploaded: {result}")
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue
        
        print(f"Processing complete: {len(uploaded_files)}/{len(log_urls)} files uploaded successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Uploaded {len(uploaded_files)} files',
                'uploaded_files': uploaded_files,
                'total_found': len(log_urls)
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def extract_file_type_from_url(url):
    """Extract file type from URL"""
    try:
        if not url or url == '/':
            return '-'
        # Extract file extension from URL
        if '.' in url:
            return url.split('.')[-1].split('?')[0].split('#')[0]
        return '-'
    except:
        return '-'

def parse_nginx_log_line(line):
    """Parse CDN log line using the same regex that was working before"""
    try:
        # Skip empty lines
        if not line.strip():
            return None
        
        # Use the correct regex pattern for the actual log format
        import re
        # Pattern: [datetime timezone] IP - response_time "referrer" "method url" status request_size response_size cache_status "user_agent" "content_type" access_ip
        pattern = r'\[([^\s]+)\s+([^\]]+)\]\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"([^"]*)"\s+"([^\s]+)\s+([^"]*)"\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+"([^"]*)"\s+"([^"]*)"\s+([^\s]+)'
        
        match = re.match(pattern, line)
        if not match:
            return None
        
        # Extract matched groups
        groups = match.groups()
        
        # Helper functions
        def safe_int(value, default=0):
            try:
                return int(value) if str(value).isdigit() else default
            except:
                return default
        
        def safe_strip(value, default='-'):
            try:
                return value.strip('"\'') if value else default
            except:
                return default
        
        # Map groups to fields based on actual log format
        # Format: [datetime timezone] IP - response_time "referrer" "method url" status request_size response_size cache_status "user_agent" "content_type" access_ip
        # Groups: 0=datetime, 1=timezone, 2=IP, 3=dash, 4=response_time, 5=referrer, 6=method, 7=url, 8=status, 9=request_size, 10=response_size, 11=cache_status, 12=user_agent, 13=content_type, 14=access_ip
        return {
            'client_ip': groups[2] if len(groups) > 2 else '-',           # IP
            'proxy_ip': groups[3] if len(groups) > 3 else '-',            # - (dash)
            'response_time': safe_int(groups[4] if len(groups) > 4 else '0'),  # response_time
            'referrer': safe_strip(groups[5] if len(groups) > 5 else '-'),     # referrer
            'http_method': safe_strip(groups[6] if len(groups) > 6 else 'GET'), # method
            'request_url': safe_strip(groups[7] if len(groups) > 7 else '/'),  # url
            'http_status': safe_int(groups[8] if len(groups) > 8 else '200'),  # status
            'request_bytes': safe_int(groups[9] if len(groups) > 9 else '0'), # request_size
            'response_bytes': safe_int(groups[10] if len(groups) > 10 else '0'), # response_size
            'cache_status': groups[11] if len(groups) > 11 else '-',      # cache_status
            'user_agent': safe_strip(groups[12] if len(groups) > 12 else '-'), # user_agent
            'access_ip': groups[14] if len(groups) > 14 else groups[2] if len(groups) > 2 else '-' # access_ip (group 14)
        }
        
    except Exception as e:
        return None


def configure_aliyun_cli():
    client = boto3.client('secretsmanager')
    secret = json.loads(client.get_secret_value(SecretId='aliyun-credentials')['SecretString'])
    
    os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'] = secret['access_key_id']
    os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'] = secret['access_key_secret']
    os.environ['ALIBABA_CLOUD_REGION_ID'] = secret.get('region', 'cn-hangzhou')
    
    print(f"Configured Aliyun CLI with region: {os.environ['ALIBABA_CLOUD_REGION_ID']}")
    print(f"Access Key ID: {os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'][:8]}...")

def get_cdn_log_urls(domain, start_time, end_time):
    cmd = ['/opt/aliyun/aliyun', 'cdn', 'DescribeCdnDomainLogs',
           '--DomainName', domain, '--StartTime', start_time, '--EndTime', end_time]
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Add environment variables to the subprocess
    env = os.environ.copy()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    
    print(f"Command stdout: {result.stdout[:200]}...")
    if result.stderr:
        print(f"Command stderr: {result.stderr}")
    
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"stderr: {result.stderr}")
        raise Exception(f"Failed to get CDN logs: {result.stderr}")
    
    logs_data = json.loads(result.stdout)
    urls = []
    
    print(f"API Response: {json.dumps(logs_data, indent=2)[:500]}...")
    
    # Debug: Print total count and domain info
    total_logs = 0
    for domain_detail in logs_data.get('DomainLogDetails', {}).get('DomainLogDetail', []):
        domain_name = domain_detail.get('DomainName', 'Unknown')
        log_count = domain_detail.get('LogCount', 0)
        total_logs += log_count
        print(f"Domain: {domain_name}, Log Count: {log_count}")
        
        for log_info in domain_detail.get('LogInfos', {}).get('LogInfoDetail', []):
            if 'LogPath' in log_info:
                urls.append(log_info['LogPath'])
                log_name = log_info.get('LogName', 'Unknown')
                start_time = log_info.get('StartTime', 'Unknown')
                end_time = log_info.get('EndTime', 'Unknown')
                print(f"Found log: {log_name} ({start_time} to {end_time})")
    
    print(f"Total logs found across all domains: {total_logs}")
    
    return urls

def upload_log_file(log_url):
    # Add https:// scheme if missing
    if not log_url.startswith('http'):
        log_url = f'https://{log_url}'
    
    response = requests.get(log_url, timeout=300)
    response.raise_for_status()
    
    filename = os.path.basename(urlparse(log_url).path.split('?')[0])
    
    # Extract date from filename using regex: domain_2025_10_13_HHMMSS_HHMMSS.gz
    match = re.search(r'([0-9]{4})_([0-9]{2})_([0-9]{2})_', filename)
    if match:
        year, month, day = match.groups()
    else:
        now = datetime.utcnow()
        year, month, day = str(now.year), f"{now.month:02d}", f"{now.day:02d}"
    
    # Decompress and parse log data
    print(f"Downloaded file size: {len(response.content)} bytes")
    with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz_file:
        log_content = gz_file.read().decode('utf-8')
    print(f"Decompressed content size: {len(log_content)} characters")
    
    # Parse log lines using optimized approach
    lines = [line.strip() for line in log_content.strip().split('\n') if line.strip()]
    total_lines = len(lines)
    
    print(f"Processing {total_lines} log lines...")
    
    # Debug: Show sample log lines to understand format
    if lines:
        print(f"Sample log line 1: {lines[0][:200]}...")
        if len(lines) > 1:
            print(f"Sample log line 2: {lines[1][:200]}...")
    
    # Use optimized parsing
    records = parse_log_lines_vectorized(lines)
    parsed_lines = len(records)
    
    print(f"Total log lines: {total_lines}, Successfully parsed: {parsed_lines}")
    
    # Debug: Show sample parsed record
    if records:
        print(f"Sample parsed record: {records[0]}")
    
    if not records:
        raise Exception("No valid log records found")
    
    # For very large files, split into multiple parquet files to avoid memory issues
    max_records_per_file = 100000  # Maximum records per parquet file
    
    if len(records) <= max_records_per_file:
        # Small file - process normally
        return process_single_parquet_file(records, filename, year, month, day)
    else:
        # Large file - split into multiple parquet files
        print(f"Large file detected ({len(records)} records). Splitting into multiple parquet files...")
        return process_large_file_in_chunks(records, filename, year, month, day, max_records_per_file)

def process_single_parquet_file(records, filename, year, month, day):
    """Process a single parquet file for small datasets"""
    print(f"Creating DataFrame from {len(records)} records...")
    df = pd.DataFrame(records)
    
    # Optimize data types
    dtype_map = {
        'http_status': 'int32',
        'response_time': 'int64', 
        'request_bytes': 'int64',
        'response_bytes': 'int64',
        'year': 'string',
        'month': 'string', 
        'day': 'string',
        'date_time': 'string',
        'timezone': 'string',
        'client_ip': 'string',
        'proxy_ip': 'string',
        'referrer': 'string',
        'http_method': 'string',
        'request_url': 'string',
        'cache_status': 'string',
        'user_agent': 'string',
        'file_type': 'string',
        'access_ip': 'string'
    }
    
    for col, dtype in dtype_map.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    
    # Create and upload parquet file
    return create_and_upload_parquet(df, filename, year, month, day)

def process_large_file_in_chunks(records, filename, year, month, day, max_records_per_file):
    """Process large files by splitting into multiple parquet files"""
    uploaded_files = []
    num_chunks = (len(records) + max_records_per_file - 1) // max_records_per_file
    
    print(f"Splitting {len(records)} records into {num_chunks} files...")
    
    for i in range(0, len(records), max_records_per_file):
        chunk_records = records[i:i + max_records_per_file]
        chunk_num = i // max_records_per_file + 1
        
        print(f"Processing chunk {chunk_num}/{num_chunks}: {len(chunk_records)} records")
        
        # Create DataFrame for this chunk
        df = pd.DataFrame(chunk_records)
        
        # Optimize data types
        dtype_map = {
            'http_status': 'int32',
            'response_time': 'int64', 
            'request_bytes': 'int64',
            'response_bytes': 'int64',
            'year': 'string',
            'month': 'string', 
            'day': 'string',
            'date_time': 'string',
            'timezone': 'string',
            'client_ip': 'string',
            'proxy_ip': 'string',
            'referrer': 'string',
            'http_method': 'string',
            'request_url': 'string',
            'cache_status': 'string',
            'user_agent': 'string',
            'file_type': 'string',
            'access_ip': 'string'
        }
        
        for col, dtype in dtype_map.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype)
        
        # Create filename for this chunk
        base_filename = filename.replace('.gz', '')
        chunk_filename = f"{base_filename}_part_{chunk_num:03d}.parquet"
        
        # Create and upload parquet file
        s3_key = create_and_upload_parquet(df, chunk_filename, year, month, day)
        uploaded_files.append(s3_key)
        
        # Clear memory
        del df, chunk_records
        import gc
        gc.collect()
    
    return uploaded_files

def create_and_upload_parquet(df, filename, year, month, day):
    """Create and upload a parquet file to S3"""
    # Create optimized PyArrow table
    table = pa.Table.from_pandas(df, preserve_index=False)
    table = table.replace_schema_metadata({})
    
    # Write with optimized compression and settings
    parquet_buffer = io.BytesIO()
    pq.write_table(
        table, 
        parquet_buffer, 
        compression='snappy',
        use_dictionary=True
    )
    parquet_buffer.seek(0)
    
    file_size = len(parquet_buffer.getvalue())
    print(f"Generated parquet file size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # Upload Parquet to S3
    s3_key = f"alibaba-cdn/alibaba-cdn_parquet/year={year}/month={month}/day={day}/{filename}"
    
    s3_client = boto3.client('s3')
    s3_client.upload_fileobj(
        parquet_buffer,
        'spl-live-cdn-logs',
        s3_key,
        ExtraArgs={'ContentType': 'application/octet-stream'}
    )
    
    return s3_key

def parse_log_lines_vectorized(lines):
    """Parse multiple log lines using optimized approach for better performance and memory usage"""
    records = []
    
    # Pre-compile regex patterns for better performance
    datetime_pattern = re.compile(r'\[([^\]]+)\]')
    
    # Process in smaller chunks to avoid memory issues
    chunk_size = 5000  # Process 5k lines at a time
    
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i + chunk_size]
        print(f"Processing chunk {i//chunk_size + 1}: lines {i+1}-{min(i+chunk_size, len(lines))}")
        
        for line in chunk:
            try:
                # Find datetime bracket
                datetime_match = datetime_pattern.search(line)
                if not datetime_match:
                    continue
                    
                datetime_full = datetime_match.group(1)
                datetime_parts = datetime_full.split(' ', 1)
                date_time_str = datetime_parts[0] if len(datetime_parts) > 0 else ''
                timezone = datetime_parts[1] if len(datetime_parts) > 1 else '+0000'
                
                # Extract year, month, day for partitioning
                year, month, day = extract_partition_columns(date_time_str)
                
                # Parse log line properly handling quoted strings
                parsed = parse_nginx_log_line(line)
                if parsed:
                    records.append({
                        'date_time': date_time_str,
                        'timezone': timezone,
                        'client_ip': parsed.get('client_ip', '-'),
                        'proxy_ip': parsed.get('proxy_ip', '-'),
                        'response_time': parsed.get('response_time', 0),
                        'referrer': parsed.get('referrer', '-'),
                        'http_method': parsed.get('http_method', 'GET'),
                        'request_url': parsed.get('request_url', '/'),
                        'http_status': parsed.get('http_status', 200),
                        'request_bytes': parsed.get('request_bytes', 0),
                        'response_bytes': parsed.get('response_bytes', 0),
                        'cache_status': parsed.get('cache_status', '-'),
                        'user_agent': parsed.get('user_agent', '-'),
                        'file_type': extract_file_type_from_url(parsed.get('request_url', '/')),
                        'access_ip': parsed.get('access_ip', parsed.get('client_ip', '-')),
                        'year': year,
                        'month': month,
                        'day': day
                    })
            except Exception as e:
                # Skip malformed lines silently for better performance
                continue
        
        # Clear chunk from memory and force garbage collection
        del chunk
        import gc
        gc.collect()
    
    return records

def parse_log_line(line):
    """Parse CDN log line - more robust parsing to handle all log formats"""
    try:
        # Skip empty lines
        if not line.strip():
            return None
            
        # Find the bracketed datetime part first
        bracket_start = line.find('[')
        bracket_end = line.find(']')
        if bracket_start == -1 or bracket_end == -1:
            # Try alternative datetime formats
            if ' - ' in line and ' "' in line:
                # Alternative format: IP - - [datetime] "method url" status size
                parts = line.split(' - ', 2)
                if len(parts) >= 3:
                    client_ip = parts[0]
                    rest = parts[2]
                    # Extract datetime from rest
                    datetime_start = rest.find('[')
                    datetime_end = rest.find(']')
                    if datetime_start != -1 and datetime_end != -1:
                        datetime_full = rest[datetime_start+1:datetime_end]
                        datetime_parts = datetime_full.split(' ', 1)
                        date_time_str = datetime_parts[0] if len(datetime_parts) > 0 else ''
                        timezone = datetime_parts[1] if len(datetime_parts) > 1 else '+0000'
                        
                        # Parse the rest of the line
                        after_datetime = rest[datetime_end+1:].strip()
                        if after_datetime.startswith('"'):
                            # Extract method, URL, and status
                            quote_end = after_datetime.find('"', 1)
                            if quote_end != -1:
                                method_url = after_datetime[1:quote_end]
                                method_url_parts = method_url.split(' ', 1)
                                method = method_url_parts[0] if len(method_url_parts) > 0 else 'GET'
                                url = method_url_parts[1] if len(method_url_parts) > 1 else '/'
                                
                                # Extract status and other fields
                                remaining = after_datetime[quote_end+1:].strip().split()
                                status = int(remaining[0]) if len(remaining) > 0 and remaining[0].isdigit() else 200
                                size = int(remaining[1]) if len(remaining) > 1 and remaining[1].isdigit() else 0
                                
                                year, month, day = extract_partition_columns(date_time_str)
                                
                                return {
                                    'date_time': date_time_str,
                                    'timezone': timezone,
                                    'client_ip': client_ip,
                                    'proxy_ip': '-',
                                    'response_time': 0,
                                    'referrer': '-',
                                    'http_method': method,
                                    'request_url': url,
                                    'http_status': status,
                                    'request_bytes': 0,
                                    'response_bytes': size,
                                    'cache_status': '-',
                                    'user_agent': '-',
                                    'file_type': extract_file_type_from_url(url),
                                    'access_ip': client_ip,
                                    'year': year,
                                    'month': month,
                                    'day': day
                                }
            return None
            
        datetime_full = line[bracket_start+1:bracket_end]
        datetime_parts = datetime_full.split(' ', 1)
        
        # Parse the date_time to extract year, month, day for partitioning
        date_time_str = datetime_parts[0] if len(datetime_parts) > 0 else ''
        timezone = datetime_parts[1] if len(datetime_parts) > 1 else '+0000'
        
        # Use the same parsing logic as parse_nginx_log_line
        parsed = parse_nginx_log_line(line)
        if parsed:
            year, month, day = extract_partition_columns(date_time_str)
            
            return {
                'date_time': date_time_str,
                'timezone': timezone,
                'client_ip': parsed.get('client_ip', '-'),
                'proxy_ip': parsed.get('proxy_ip', '-'),
                'response_time': parsed.get('response_time', 0),
                'referrer': parsed.get('referrer', '-'),
                'http_method': parsed.get('http_method', 'GET'),
                'request_url': parsed.get('request_url', '/'),
                'http_status': parsed.get('http_status', 200),
                'request_bytes': parsed.get('request_bytes', 0),
                'response_bytes': parsed.get('response_bytes', 0),
                'cache_status': parsed.get('cache_status', '-'),
                'user_agent': parsed.get('user_agent', '-'),
                'file_type': extract_file_type_from_url(parsed.get('request_url', '/')),
                'access_ip': parsed.get('access_ip', parsed.get('client_ip', '-')),
                'year': year,
                'month': month,
                'day': day
            }
        
        return None
    except Exception as e:
        print(f"Error parsing line: {line[:100]}... Error: {e}")
        return None

def extract_partition_columns(date_time_str):
    """Extract year, month, day from date_time string for partitioning"""
    try:
        from datetime import datetime
        
        # Try multiple date formats that might be in the logs
        formats_to_try = [
            '%d/%b/%Y:%H:%M:%S',  # 10/Oct/2025:16:04:18
            '%d/%m/%Y:%H:%M:%S',  # 10/10/2025:16:04:18
            '%Y-%m-%d %H:%M:%S',  # 2025-10-10 16:04:18
            '%m/%d/%Y %H:%M:%S',  # 10/13/2025 16:04:18
        ]
        
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_time_str, fmt)
                return str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"
            except ValueError:
                continue
        
        # If no format matches, try to extract date parts manually
        print(f"Warning: Could not parse date_time '{date_time_str}' with any known format")
        
        # Try to extract year, month, day from common patterns
        import re
        
        # Pattern for YYYY-MM-DD
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_time_str)
        if match:
            year, month, day = match.groups()
            return year, f"{int(month):02d}", f"{int(day):02d}"
        
        # Pattern for MM/DD/YYYY
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_time_str)
        if match:
            month, day, year = match.groups()
            return year, f"{int(month):02d}", f"{int(day):02d}"
        
        # Pattern for DD/MM/YYYY
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_time_str)
        if match:
            day, month, year = match.groups()
            return year, f"{int(month):02d}", f"{int(day):02d}"
        
        # If all else fails, use current date
        now = datetime.utcnow()
        return str(now.year), f"{now.month:02d}", f"{now.day:02d}"
        
    except Exception as e:
        print(f"Warning: Failed to parse date_time '{date_time_str}': {e}")
        # Fallback to current date if parsing fails
        now = datetime.utcnow()
        return str(now.year), f"{now.month:02d}", f"{now.day:02d}"