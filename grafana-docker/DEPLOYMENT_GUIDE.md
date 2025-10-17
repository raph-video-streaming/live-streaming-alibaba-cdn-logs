# 🚀 Quick Deployment Guide

## Fastest Deployment Options (Ranked by Speed)

### 1. **Render.com** ⚡ (5 minutes - FASTEST)

**Why it's fastest:** One-click deployment, no configuration needed.

```bash
# 1. Push your code to GitHub
git add .
git commit -m "Add Grafana with Aliyun plugin"
git push

# 2. Go to https://render.com
# 3. Connect GitHub repo
# 4. Select "Web Service"
# 5. Use these settings:
#    - Environment: Docker
#    - Dockerfile Path: ./grafana-docker/Dockerfile
#    - Docker Context: ./grafana-docker
# 6. Deploy!
```

**Cost:** Free tier available, $7/month for production

---

### 2. **Fly.io** ⚡ (10 minutes)

**Why it's fast:** Simple CLI deployment, great for Docker apps.

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
flyctl auth login
flyctl launch --no-deploy
flyctl deploy
```

**Cost:** Free tier available, pay-as-you-go

---

### 3. **AWS ECS with CDK** ⚡ (15 minutes - Using your existing setup)

**Why it's good:** You already have CDK configured, leverages AWS infrastructure.

```bash
cd /home/raf/GITHUB/live-streaming-alibaba-cdn-logs/grafana-docker

# Install dependencies
npm install

# Deploy
cdk deploy --require-approval never
```

**Cost:** ~$20-30/month for Fargate

---

### 4. **AWS EC2** ⚡ (20 minutes)

**Why it's reliable:** Full control, persistent storage, can scale.

```bash
# 1. Launch EC2 instance (t3.small or larger)
# 2. Configure security group (HTTP port 80, SSH port 22)
# 3. SSH and run:
curl -sSL https://raw.githubusercontent.com/your-repo/grafana-docker/main/deploy-aws-ec2.sh | bash
```

**Cost:** ~$15-25/month for t3.small

---

### 5. **Local Development** ⚡ (2 minutes)

**For testing only:**

```bash
cd /home/raf/GITHUB/live-streaming-alibaba-cdn-logs/grafana-docker
./quick-deploy.sh local
```

---

## 🎯 Recommended Approach

### For Production: **Render.com**
- ✅ Fastest setup (5 minutes)
- ✅ Automatic HTTPS
- ✅ Free tier available
- ✅ No server management
- ✅ Built-in monitoring

### For AWS Integration: **AWS ECS**
- ✅ Integrates with your existing AWS setup
- ✅ Uses your existing CDK configuration
- ✅ Can integrate with other AWS services
- ✅ Professional-grade infrastructure

### For Learning/Testing: **Fly.io**
- ✅ Great developer experience
- ✅ Simple CLI
- ✅ Good documentation
- ✅ Free tier

---

## 🚀 One-Command Deployment

```bash
# Navigate to the grafana-docker folder
cd /home/raf/GITHUB/live-streaming-alibaba-cdn-logs/grafana-docker

# Run the quick deploy script
./quick-deploy.sh [platform]

# Examples:
./quick-deploy.sh render    # Deploy to Render.com
./quick-deploy.sh fly       # Deploy to Fly.io
./quick-deploy.sh aws-ecs   # Deploy to AWS ECS
./quick-deploy.sh local     # Run locally
```

---

## 📊 After Deployment

1. **Access Grafana:** Go to the provided URL
2. **Login:** admin / admin
3. **Configure Aliyun:**
   - Go to Configuration → Data Sources
   - Add "Aliyun Log Service"
   - Enter your Aliyun credentials:
     - Access Key ID
     - Access Key Secret
     - Region (e.g., cn-hangzhou, us-west-1)
     - Project name
     - Logstore name

---

## 🔧 Troubleshooting

### Plugin Not Loading
```bash
# Check if plugin is installed
docker exec grafana-aliyun ls -la /var/lib/grafana/plugins/

# Check logs
docker logs grafana-aliyun | grep -i "aliyun\|plugin"
```

### Authentication Issues
1. Verify your Aliyun Access Key ID and Secret
2. Check permissions: `AliyunLogReadOnlyAccess`
3. Test connection in Aliyun console first

### Performance Issues
1. Use time range filters in queries
2. Limit result sets with `limit` clause
3. Use appropriate time intervals

---

## 💰 Cost Comparison

| Platform | Free Tier | Production Cost | Setup Time |
|----------|-----------|-----------------|------------|
| **Render.com** | ✅ Yes | $7/month | 5 min |
| **Fly.io** | ✅ Yes | Pay-as-you-go | 10 min |
| **AWS ECS** | ❌ No | $20-30/month | 15 min |
| **AWS EC2** | ❌ No | $15-25/month | 20 min |
| **Local** | ✅ Free | $0 | 2 min |

---

## 🎉 Success!

Once deployed, you'll have:
- ✅ Grafana with Aliyun Log Service plugin
- ✅ Pre-configured environment
- ✅ Persistent data storage
- ✅ Production-ready setup
- ✅ Easy management scripts

