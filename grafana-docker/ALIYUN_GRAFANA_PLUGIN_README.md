# Aliyun Log Service Grafana Plugin Installation Guide

This guide will help you install the Aliyun Log Service (SLS) Grafana datasource plugin to connect your Grafana instance with Alibaba Cloud's Log Service.

## Prerequisites

- Docker installed on your system
- Access to Alibaba Cloud Log Service
- Aliyun Access Key ID and Access Key Secret
- SLS Project and Logstore information

## Installation Methods

### Method 1: Docker Container (Recommended)

#### Step 1: Create a new Grafana container with the plugin

```bash
# Create a new Grafana container with Aliyun plugin support
docker run -d \
  --name grafana-aliyun \
  -p 3000:3000 \
  -e "GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=aliyun-log-service-datasource" \
  grafana/grafana:latest
```

#### Step 2: Install the Aliyun Log Service plugin

```bash
# Download and install the plugin
docker exec grafana-aliyun sh -c "
  cd /var/lib/grafana/plugins && \
  wget https://github.com/aliyun/aliyun-log-grafana-datasource-plugin/archive/refs/heads/master.zip -O aliyun-plugin.zip && \
  unzip aliyun-plugin.zip && \
  mv aliyun-log-grafana-datasource-plugin-master aliyun-log-datasource && \
  rm aliyun-plugin.zip
"
```

#### Step 3: Restart Grafana

```bash
docker restart grafana-aliyun
```

### Method 2: Existing Docker Container

If you already have a Grafana container running:

#### Step 1: Stop your current container

```bash
docker stop <your-container-name>
```

#### Step 2: Create a new container with plugin support

```bash
docker run -d \
  --name grafana-aliyun \
  -p 3000:3000 \
  -e "GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=aliyun-log-service-datasource" \
  grafana/grafana:latest
```

#### Step 3: Install the plugin

```bash
# Download and install the plugin
docker exec grafana-aliyun sh -c "
  cd /var/lib/grafana/plugins && \
  wget https://github.com/aliyun/aliyun-log-grafana-datasource-plugin/archive/refs/heads/master.zip -O aliyun-plugin.zip && \
  unzip aliyun-plugin.zip && \
  mv aliyun-log-grafana-datasource-plugin-master aliyun-log-datasource && \
  rm aliyun-plugin.zip
"
```

#### Step 4: Restart Grafana

```bash
docker restart grafana-aliyun
```

## Configuration

### Step 1: Access Grafana

1. Open your browser and navigate to `http://localhost:3000`
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin`

### Step 2: Add Aliyun Log Service Data Source

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Search for **"Aliyun Log Service"** or **"log-service-datasource"**
4. Select **Aliyun Log Service**

### Step 3: Configure the Data Source

Fill in the following information:

#### Basic Configuration
- **Name**: `Aliyun Log Service` (or your preferred name)
- **Access Key ID**: Your Aliyun Access Key ID
- **Access Key Secret**: Your Aliyun Access Key Secret
- **Region**: Your Aliyun region (e.g., `cn-hangzhou`, `us-west-1`, `eu-central-1`)
- **Project**: Your SLS project name
- **Logstore**: Your SLS logstore name

#### Advanced Configuration (Optional)
- **Role ARN**: For STS-based authentication (optional)
- **Custom Headers**: Additional headers if needed
- **Timeout**: Request timeout in seconds (default: 30)

### Step 4: Test the Connection

1. Click **Save & Test**
2. You should see a green success message if the configuration is correct

## Usage Examples

### Basic Log Query

```sql
* | select 
  __time__,
  client_ip,
  method,
  uri,
  return_code,
  request_time
from log 
where return_code != 200
order by __time__ desc
limit 100
```

### Time Series Chart

```sql
* | select 
  __time__ - __time__ % 300 as time,
  count(*) as requests,
  avg(request_time) as avg_response_time
from log 
group by time 
order by time
```

**Chart Type**: Time Series
- **xcol**: `time`
- **ycol**: `requests, avg_response_time`

### Pie Chart

```sql
* | select 
  return_code as status_code,
  count(*) as requests
from log 
group by return_code 
order by requests desc
```

**Chart Type**: Pie Chart
- **xcol**: `pie`
- **ycol**: `status_code, requests`

### Table

```sql
* | select 
  client_ip,
  count(*) as requests,
  avg(request_time) as avg_response_time,
  max(request_time) as max_response_time
from log 
group by client_ip 
order by requests desc 
limit 10
```

**Chart Type**: Table
- **xcol**: (empty)
- **ycol**: `client_ip, requests, avg_response_time, max_response_time`

## Chart Type Configuration

### Time Series
- **xcol**: Time field (e.g., `time`, `__time__`)
- **ycol**: Value fields (e.g., `requests, errors`)

### Pie Chart
- **xcol**: `pie`
- **ycol**: Category field, value field (e.g., `status_code, count`)

### Bar Chart
- **xcol**: `bar`
- **ycol**: Category field, value field (e.g., `method, requests`)

### Table
- **xcol**: (empty)
- **ycol**: Column fields (e.g., `ip, requests, response_time`)

### Stat Panel
- **xcol**: (empty)
- **ycol**: Value fields (e.g., `total_requests, avg_response_time`)

## Troubleshooting

### Plugin Not Loading

1. Check if the plugin is installed:
   ```bash
   docker exec grafana-aliyun ls -la /var/lib/grafana/plugins/
   ```

2. Check Grafana logs:
   ```bash
   docker logs grafana-aliyun | grep -i "aliyun\|plugin"
   ```

3. Ensure the environment variable is set:
   ```bash
   docker exec grafana-aliyun env | grep PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS
   ```

### Authentication Issues

1. Verify your Access Key ID and Secret are correct
2. Check if your Access Key has the necessary permissions:
   - `AliyunLogReadOnlyAccess`
   - `AliyunRAMReadOnlyAccess` (if using STS)

### Query Issues

1. Check your SLS query syntax
2. Verify field names match your log structure
3. Use the SLS console to test queries first

### Performance Issues

1. Use time range filters in your queries
2. Limit result sets with `limit` clause
3. Use appropriate time intervals for time series

## Advanced Features

### STS Authentication (Optional)

For enhanced security, you can use STS (Security Token Service) authentication:

1. Create a RAM role with `AliyunLogReadOnlyAccess` permission
2. Configure the role ARN in the data source settings
3. Ensure your Access Key has `AliyunRAMReadOnlyAccess` and `AliyunSTSAssumeRoleAccess` permissions

### Custom Headers

You can add custom headers for authentication or other purposes:

```json
{
  "X-Custom-Header": "value",
  "Authorization": "Bearer token"
}
```

### One-Click SLS Console

The plugin supports jumping directly to the SLS console for advanced analysis. This feature is available in:
- Explore interface
- Dashboard panels
- Query results

## Support

- **GitHub Repository**: [aliyun-log-grafana-datasource-plugin](https://github.com/aliyun/aliyun-log-grafana-datasource-plugin)
- **Documentation**: [Aliyun Log Service Documentation](https://help.aliyun.com/product/28958.html)
- **Community**: [Aliyun Developer Community](https://developer.aliyun.com/)

## License

This plugin is licensed under the MIT License. See the [LICENSE](https://github.com/aliyun/aliyun-log-grafana-datasource-plugin/blob/master/LICENSE) file for details.

---

**Note**: This plugin requires Grafana 7.0.0 or higher and supports Aliyun Log Service API v0.6.0 or higher.
