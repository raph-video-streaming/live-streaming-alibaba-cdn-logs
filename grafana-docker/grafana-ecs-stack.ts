import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class GrafanaEcsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create VPC
    const vpc = new ec2.Vpc(this, 'GrafanaVPC', {
      maxAzs: 2,
      natGateways: 1,
    });

    // Create ECS Cluster
    const cluster = new ecs.Cluster(this, 'GrafanaCluster', {
      vpc,
      clusterName: 'grafana-cluster',
    });

    // Create CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'GrafanaLogGroup', {
      logGroupName: '/ecs/grafana',
      retention: logs.RetentionDays.ONE_WEEK,
    });

    // Create Task Definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'GrafanaTaskDef', {
      memoryLimitMiB: 1024,
      cpu: 512,
    });

    // Add Grafana Container
    const grafanaContainer = taskDefinition.addContainer('grafana', {
      image: ecs.ContainerImage.fromRegistry('grafana/grafana:latest'),
      memoryLimitMiB: 1024,
      cpu: 512,
      environment: {
        GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS: 'aliyun-log-service-datasource',
        GF_SECURITY_ADMIN_USER: 'admin',
        GF_SECURITY_ADMIN_PASSWORD: 'admin',
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'grafana',
        logGroup,
      }),
    });

    grafanaContainer.addPortMappings({
      containerPort: 3000,
      protocol: ecs.Protocol.TCP,
    });

    // Create ECS Service
    const service = new ecs.FargateService(this, 'GrafanaService', {
      cluster,
      taskDefinition,
      desiredCount: 1,
      serviceName: 'grafana-service',
    });

    // Create Application Load Balancer
    const alb = new elbv2.ApplicationLoadBalancer(this, 'GrafanaALB', {
      vpc,
      internetFacing: true,
    });

    const listener = alb.addListener('GrafanaListener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
    });

    // Add target group
    const targetGroup = listener.addTargets('GrafanaTargets', {
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [service],
      healthCheck: {
        path: '/api/health',
        healthyHttpCodes: '200',
      },
    });

    // Output the ALB URL
    new cdk.CfnOutput(this, 'GrafanaURL', {
      value: `http://${alb.loadBalancerDnsName}`,
      description: 'Grafana URL',
    });

    // Output instructions
    new cdk.CfnOutput(this, 'Instructions', {
      value: 'Access Grafana at the URL above. Default credentials: admin/admin',
      description: 'Setup Instructions',
    });
  }
}

