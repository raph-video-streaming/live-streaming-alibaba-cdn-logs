#!/bin/bash

set -e

echo "🔨 Building Aliyun CLI layer..."

# Build Aliyun CLI layer
echo "📦 Building Aliyun CLI layer..."
mkdir -p layers/aliyun-cli/aliyun
mkdir -p layers/aliyun-cli/python

# Add Aliyun CLI binary
cd layers/aliyun-cli/aliyun
wget -O aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar -xzf aliyun-cli.tgz
chmod 755 aliyun
rm aliyun-cli.tgz
cd ..

# Add requests library
pip install requests -t python/
cd ..

echo "✅ Aliyun CLI layer built successfully!"