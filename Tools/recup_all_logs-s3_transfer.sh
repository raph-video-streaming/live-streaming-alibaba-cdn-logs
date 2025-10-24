#!/bin/bash

DOMAIN="alibaba-live.servers8.com"
#DOMAIN="alibaba.servers8.com"
START="2025-10-18T20:00:00Z"
END="2025-10-24T23:59:59Z"

# S3 Configuration
S3_BUCKET="spl-live-cdn-logs"
S3_PREFIX="alibaba-cdn/alibaba-cdn_partitioned"
#S3_PREFIX="logs/alibaba-live-cdn"
AWS_PROFILE="spl"

# Convert dates to epoch for iteration
START_EPOCH=$(date -d "${START%T*}" +%s)
END_EPOCH=$(date -d "${END%T*}" +%s)

# Iterate through each day
for ((current_epoch=START_EPOCH; current_epoch<=END_EPOCH; current_epoch+=86400)); do
    current_date=$(date -d "@$current_epoch" -u +"%Y-%m-%d")
    
    # Process in 4-hour blocks
    for hour_start in 00 02 04 06 08 10 12 14 16 18 20 22; do
        case $hour_start in
            00) hour_end="01:59:59" ;;
            02) hour_end="03:59:59" ;;
            04) hour_end="05:59:59" ;;
            06) hour_end="07:59:59" ;;
            08) hour_end="09:59:59" ;;
            10) hour_end="11:59:59" ;;
            12) hour_end="13:59:59" ;;
            14) hour_end="15:59:59" ;;
            16) hour_end="17:59:59" ;;
            18) hour_end="19:59:59" ;;
            20) hour_end="21:59:59" ;;
            22) hour_end="23:59:59" ;;
        esac
        
        START_BLOCK="${current_date}T${hour_start}:00:00Z"
        END_BLOCK="${current_date}T${hour_end}Z"
        
        echo "Processing logs for: $START_BLOCK to $END_BLOCK"
        
        # Get log metadata from API for current 2-hour block
        LOGS=$(aliyun cdn DescribeCdnDomainLogs \
          --DomainName "$DOMAIN" \
          --StartTime "$START_BLOCK" \
          --EndTime "$END_BLOCK")
        
        # Display total number of log files
        LOG_COUNT=$(echo "$LOGS" | jq -r '.DomainLogDetails.DomainLogDetail[].LogInfos.LogInfoDetail[].LogPath' | wc -l)
        echo "📤📤📤📤Total log files found: $LOG_COUNT 📤📤📤📤"

        # Output directory for logs
        OUTPUT_DIR="cdn-logs-alibaba"
        mkdir -p "$OUTPUT_DIR"
        
        # Create date-based directory
        DATE_DIR="$OUTPUT_DIR/$current_date"
        mkdir -p "$DATE_DIR"
    
        # Extract and download each LogPath
        echo "$LOGS" | jq -r '.DomainLogDetails.DomainLogDetail[].LogInfos.LogInfoDetail[].LogPath' | while read -r url; do
            # Extract filename from URL (everything after last slash before the query string)
            filename=$(basename "${url%%\?*}")
            
            echo "Downloading: $filename"
            curl -s -o "$DATE_DIR/$filename" "$url"

            if [[ $? -eq 0 ]]; then
                echo "✅ Downloaded: $filename"
                echo "📤 Uploading to S3..."

                # Upload to S3 with partitioned structure

                # Extract date from filename: alibaba-live.servers8.com_2025_10_06_170000_180000.gz
                if [[ $filename =~ ([0-9]{4})_([0-9]{2})_([0-9]{2})_ ]]; then
                    year="${BASH_REMATCH[1]}"
                    month="${BASH_REMATCH[2]}"
                    day="${BASH_REMATCH[3]}"
                else
                    echo "⚠️  Could not extract date from $filename, skipping..."
                    continue
                fi
                
                # Create partitioned S3 path
                dest_key="${S3_PREFIX}/year=${year}/month=${month}/day=${day}/${filename}"
                echo $dest_key
                echo "📁 Uploading: $filename -> year=$year/month=$month/day=$day/"
                aws s3 cp "$DATE_DIR/$filename" "s3://$S3_BUCKET/$dest_key" --profile "$AWS_PROFILE"
                echo "✅ Upload completed"

            else
                echo "❌ Failed: $filename"
            fi
        done
    done
done

echo "🗑️  Cleaning up local files..."
rm -rf "$OUTPUT_DIR"
echo "✅ Cleanup complete"

echo "🎉 Process complete!"
