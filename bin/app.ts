#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AlibabaCdnLogsStack } from '../lib/stack';

const app = new cdk.App();
new AlibabaCdnLogsStack(app, 'AlibabaCdnLogsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'me-central-1',
  },
});