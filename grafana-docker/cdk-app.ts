#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { GrafanaEcsStack } from './grafana-ecs-stack';

const app = new cdk.App();
new GrafanaEcsStack(app, 'GrafanaEcsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});

