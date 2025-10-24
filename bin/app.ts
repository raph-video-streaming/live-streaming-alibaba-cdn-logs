#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AlibabaCdnLogsStack } from '../lib/stack';
import { AlibabaCdnAthenaStack } from '../lib/athena-stack';
import { ParquetConversionStack } from '../lib/parquet-conversion-stack';

const app = new cdk.App();

// Original Lambda-based stack
new AlibabaCdnLogsStack(app, 'AlibabaCdnLogsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'me-central-1',
  },
  description: 'Download logs from Aliyun to store them in S3 - event bridge to download logs automatically',
});


// Parquet conversion stack
new ParquetConversionStack(app, 'ParquetConversionStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'me-central-1',
  },
  description: 'Automatic conversion of GZ logs to Parquet format',
});


//  Athena-based stack (DO NOT USER IT)
new AlibabaCdnAthenaStack(app, 'AlibabaCdnAthenaStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'me-central-1',
  },
  description: 'Alibaba CDN Logs Athena Stack - transferring raw logs to S3 and converting to parquet format with Athena',
});

