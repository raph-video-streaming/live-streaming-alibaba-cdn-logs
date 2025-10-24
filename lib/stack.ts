import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class AlibabaCdnLogsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);



    // AWS managed pandas layer
    const pandasLayer = lambda.LayerVersion.fromLayerVersionArn(
      this,
      'PandasLayer',
      'arn:aws:lambda:me-central-1:593833071574:layer:AWSSDKPandas-Python312-Arm64:19'
    );

    // Aliyun CLI layer
    const aliyunLayer = new lambda.LayerVersion(this, 'AliyunCliLayer', {
      code: lambda.Code.fromAsset('layers/aliyun-cli'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      description: 'Aliyun CLI binary',
    });

    // Lambda execution role
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['s3:PutObject', 's3:PutObjectAcl'],
              resources: ['arn:aws:s3:::spl-live-cdn-logs/*'],
            }),
          ],
        }),
        SecretsAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['secretsmanager:GetSecretValue'],
              resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:aliyun-credentials*`],
            }),
          ],
        }),
      },
    });

    // Lambda function
    const cdnLogProcessor = new lambda.Function(this, 'CdnLogProcessor', {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: 'lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('lib/lambda/log_downloader'),
      role: lambdaRole,
      layers: [pandasLayer, aliyunLayer],
      timeout: cdk.Duration.minutes(15),  // Maximum allowed timeout for Lambda
      memorySize: 3008,  // Increased memory for better performance
      environment: {
        ALIYUN_SECRET_NAME: 'aliyun-credentials',
        HOME: '/tmp',
      },
    });

    // EventBridge rules for automated execution
    const noonRule = new events.Rule(this, 'NoonLogCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '12' }),
      description: 'Trigger CDN log collection at noon UTC',
    });

    const midnightRule = new events.Rule(this, 'MidnightLogCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '0' }),
      description: 'Trigger CDN log collection at midnight UTC',
    });

    // Add Lambda targets - dates will be calculated in Lambda function
    noonRule.addTarget(new targets.LambdaFunction(cdnLogProcessor, {
      event: events.RuleTargetInput.fromObject({
        domain: 'alibaba-live.servers8.com',
        scheduled: true
      })
    }));

    midnightRule.addTarget(new targets.LambdaFunction(cdnLogProcessor, {
      event: events.RuleTargetInput.fromObject({
        domain: 'alibaba-live.servers8.com',
        scheduled: true
      })
    }));

    // Output function name
    new cdk.CfnOutput(this, 'FunctionName', {
      value: cdnLogProcessor.functionName,
      description: 'Lambda function name',
    });
  }
}