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
from datetime import datetime, timedelta
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
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')
            end_date = yesterday.strftime('%Y-%m-%d')  # Same day for scheduled
            print(f"Scheduled execution: collecting logs for {start_date}")
        else:
            start_date = event.get('start_date')
            end_date = event.get('end_date')
            if not start_date or not end_date:
                raise ValueError("start_date and end_date are required")
            print(f"Manual execution: collecting logs from {start_date} to {end_date}")
        
        configure_aliyun_cli()
        
        # Process each date in 2-hour windows
        all_uploaded_files = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"Processing date: {date_str}")
            
            # Process in 2-hour blocks
            hour_blocks = [
                ('00', '01:59:59'), ('02', '03:59:59'), ('04', '05:59:59'),
                ('06', '07:59:59'), ('08', '09:59:59'), ('10', '11:59:59'),
                ('12', '13:59:59'), ('14', '15:59:59'), ('16', '17:59:59'),
                ('18', '19:59:59'), ('20', '21:59:59'), ('22', '23:59:59')
            ]
            
            for hour_start, hour_end in hour_blocks:
                start_time = f"{date_str}T{hour_start}:00:00Z"
                end_time = f"{date_str}T{hour_end}Z"
                
                print(f"Processing 2-hour block: {start_time} to {end_time}")
                
                try:
                    log_urls = get_cdn_log_urls(domain, start_time, end_time)
                    print(f"Found {len(log_urls)} log files for this 2-hour block")
                    
                    if log_urls:
                        for i, url in enumerate(log_urls, 1):
                            try:
                                print(f"Processing file {i}/{len(log_urls)}: {os.path.basename(url)}")
                                s3_key = upload_log_file(url)
                                all_uploaded_files.append(s3_key)
                            except Exception as e:
                                print(f"Error processing {url}: {str(e)}")
                                continue
                    
                except Exception as e:
                    print(f"Error processing 2-hour block {start_time}-{end_time}: {str(e)}")
                    continue
            
            current_date += timedelta(days=1)
        
        print(f"Processing complete: {len(all_uploaded_files)} files uploaded successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Uploaded {len(all_uploaded_files)} files',
                'uploaded_files': all_uploaded_files
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


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
    
    env = os.environ.copy()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"stderr: {result.stderr}")
        raise Exception(f"Failed to get CDN logs: {result.stderr}")
    
    logs_data = json.loads(result.stdout)
    urls = []
    
    total_logs = 0
    for domain_detail in logs_data.get('DomainLogDetails', {}).get('DomainLogDetail', []):
        domain_name = domain_detail.get('DomainName', 'Unknown')
        log_count = domain_detail.get('LogCount', 0)
        total_logs += log_count
        print(f"Domain: {domain_name}, Log Count: {log_count}")
        
        for log_info in domain_detail.get('LogInfos', {}).get('LogInfoDetail', []):
            if 'LogPath' in log_info:
                urls.append(log_info['LogPath'])
    
    print(f"Total logs found: {total_logs}")
    return urls

def upload_log_file(log_url):
    if not log_url.startswith('http'):
        log_url = f'https://{log_url}'
    
    print(f"📥 Downloading file from: {log_url}")
    response = requests.get(log_url, timeout=300)
    response.raise_for_status()
    
    filename = os.path.basename(urlparse(log_url).path.split('?')[0])
    print(f"📁 Processing file: {filename}")
    
    # Extract date from filename
    match = re.search(r'([0-9]{4})_([0-9]{2})_([0-9]{2})_', filename)
    if match:
        year, month, day = match.groups()
        print(f"📅 Extracted date: year={year}/month={month}/day={day}")
    else:
        print(f"⚠️  Could not extract date from {filename}, using current date")
        now = datetime.utcnow()
        year, month, day = str(now.year), f"{now.month:02d}", f"{now.day:02d}"
    
    # Create partitioned S3 path
    s3_bucket = 'spl-live-cdn-logs'
    s3_prefix = 'alibaba-cdn/alibaba-cdn_partitioned'
    dest_key = f"{s3_prefix}/year={year}/month={month}/day={day}/{filename}"
    
    print(f"📤 Uploading to S3: s3://{s3_bucket}/{dest_key}")
    
    # Upload to S3
    s3_client = boto3.client('s3')
    s3_client.upload_fileobj(
        io.BytesIO(response.content),
        s3_bucket,
        dest_key,
        ExtraArgs={'ContentType': 'application/gzip'}
    )
    
    print(f"✅ Successfully uploaded: {filename}")
    return dest_key