import * as cdk from 'aws-cdk-lib';
import { Token } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as athena from 'aws-cdk-lib/aws-athena';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class AlibabaCdnAthenaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Reference existing S3 bucket for raw gz files (partitioned)
    const rawLogsBucket = s3.Bucket.fromBucketName(this, 'AlibabaCdnRawLogs', 'spl-live-cdn-logs');

    // Reference existing S3 bucket for parquet files
    const parquetBucket = s3.Bucket.fromBucketName(this, 'AlibabaCdnParquetLogs', 'spl-live-cdn-logs');

    // Glue Database for raw logs
    const rawLogsDatabase = new glue.CfnDatabase(this, 'AlibabaCdnRawLogsDatabase', {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseInput: {
        name: 'alibaba_cdn_raw_logs',
        description: 'Database for Alibaba CDN raw log files'
      }
    });

    // Glue Database for parquet logs
    const parquetDatabase = new glue.CfnDatabase(this, 'AlibabaCdnParquetLogsDatabase', {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseInput: {
        name: 'cdn_logs_parquet',
        description: 'Database for Alibaba CDN parquet log files'
      }
    });

    // Glue Table for raw logs (partitioned by year/month/day)
    const rawLogsTable = new glue.CfnTable(this, 'AlibabaCdnRawLogsTable', {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseName: rawLogsDatabase.ref,
      tableInput: {
        name: 'alibaba_cdn_logs',
        description: 'Alibaba CDN raw log files',
        tableType: 'EXTERNAL_TABLE',
        parameters: {
          'classification': 'json',
          'compressionType': 'gzip',
          'typeOfData': 'file'
        },
        storageDescriptor: {
          location: `s3://${rawLogsBucket.bucketName}/alibaba-cdn/alibaba-cdn_partitioned/`,
          inputFormat: 'org.apache.hadoop.mapred.TextInputFormat',
          outputFormat: 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
          serdeInfo: {
            serializationLibrary: 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
            parameters: {
              'field.delim': ' ',
              'serialization.format': ' '
            }
          },
          columns: [
            { name: 'date_time', type: 'string' },
            { name: 'timezone', type: 'string' },
            { name: 'client_ip', type: 'string' },
            { name: 'proxy_ip', type: 'string' },
            { name: 'response_time', type: 'string' },
            { name: 'referrer', type: 'string' },
            { name: 'http_method', type: 'string' },
            { name: 'request_url', type: 'string' },
            { name: 'http_status', type: 'string' },
            { name: 'request_bytes', type: 'string' },
            { name: 'response_bytes', type: 'string' },
            { name: 'cache_status', type: 'string' },
            { name: 'user_agent', type: 'string' },
            { name: 'file_type', type: 'string' },
            { name: 'access_ip', type: 'string' }
          ]
        },
        partitionKeys: [
          { name: 'year', type: 'string' },
          { name: 'month', type: 'string' },
          { name: 'day', type: 'string' }
        ]
      }
    });

    // Glue Table for parquet logs
    const parquetLogsTable = new glue.CfnTable(this, 'AlibabaCdnParquetLogsTable', {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseName: parquetDatabase.ref,
      tableInput: {
        name: 'cdn_logs',
        description: 'Alibaba CDN parquet log files',
        tableType: 'EXTERNAL_TABLE',
        parameters: {
          'classification': 'parquet'
        },
        storageDescriptor: {
          location: `s3://${parquetBucket.bucketName}/alibaba-cdn/alibaba-cdn_parquet/`,
          inputFormat: 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
          outputFormat: 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
          serdeInfo: {
            serializationLibrary: 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
          },
          columns: [
            { name: 'date_time', type: 'string' },
            { name: 'timezone', type: 'string' },
            { name: 'client_ip', type: 'string' },
            { name: 'proxy_ip', type: 'string' },
            { name: 'response_time', type: 'bigint' },
            { name: 'referrer', type: 'string' },
            { name: 'http_method', type: 'string' },
            { name: 'request_url', type: 'string' },
            { name: 'http_status', type: 'int' },
            { name: 'request_bytes', type: 'bigint' },
            { name: 'response_bytes', type: 'bigint' },
            { name: 'cache_status', type: 'string' },
            { name: 'user_agent', type: 'string' },
            { name: 'file_type', type: 'string' },
            { name: 'access_ip', type: 'string' },
            { name: 'year', type: 'string' },
            { name: 'month', type: 'string' },
            { name: 'day', type: 'string' }
          ]
        }
      }
    });

    // Optional parameter to attach an Aliyun CLI Lambda Layer (so the same CLI used by the working function can run here)
    const aliyunCliLayerArnParam = new cdk.CfnParameter(this, 'AliyunCliLayerArn', {
      type: 'String',
      default: '',
      description: 'Optional: ARN of a Lambda Layer that contains the Aliyun CLI binary. If not set, a local layer asset at layers/aliyun-cli will be deployed and attached.',
    });
    // Managed Pandas layer (Python 3.12, Arm64)
    const pandasLayerArn = 'arn:aws:lambda:me-central-1:593833071574:layer:AWSSDKPandas-Python312-Arm64:19';
    const pandasLayer = lambda.LayerVersion.fromLayerVersionArn(this, 'PandasLayerManaged', pandasLayerArn);

    // Lambda function to download and organize raw logs
    const downloadLogsFunction = new lambda.Function(this, 'DownloadAlibabaLogs', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'download_logs.lambda_handler',
      code: lambda.Code.fromAsset('lib/lambda'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        'RAW_LOGS_BUCKET': rawLogsBucket.bucketName,
        'PARQUET_BUCKET': parquetBucket.bucketName,
        'RAW_DATABASE': rawLogsDatabase.ref,
        'PARQUET_DATABASE': parquetDatabase.ref,
        'RAW_TABLE': rawLogsTable.ref,
        'PARQUET_TABLE': parquetLogsTable.ref,
        'DOMAIN': 'alibaba-live.servers8.com',
        'DELETE_RAW_AFTER_CONVERT': 'false'
      }
    });
    // Always attach pandas layer
    downloadLogsFunction.addLayers(pandasLayer);

    // Attach Aliyun CLI layer: prefer provided ARN, otherwise deploy local layer asset
    const aliyunLayerArn = aliyunCliLayerArnParam.valueAsString;
    const looksLikeLayerArn = !Token.isUnresolved(aliyunLayerArn) && typeof aliyunLayerArn === 'string' && aliyunLayerArn.includes(':layer:');
    if (looksLikeLayerArn) {
      const aliyunCliLayer = lambda.LayerVersion.fromLayerVersionArn(this, 'AliyunCliLayer', aliyunLayerArn);
      downloadLogsFunction.addLayers(aliyunCliLayer);
    } else {
      // Deploy local layer from asset folder layers/aliyun-cli (must contain the aliyun binary under /bin or /opt/bin)
      const aliyunCliLocalLayer = new lambda.LayerVersion(this, 'AliyunCliLocalLayer', {
        code: lambda.Code.fromAsset('layers/aliyun-cli'),
        compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
        compatibleArchitectures: [lambda.Architecture.ARM_64],
        description: 'Aliyun CLI binary layer (local asset)'
      });
      downloadLogsFunction.addLayers(aliyunCliLocalLayer);
    }

    // Grant permissions to Lambda
    rawLogsBucket.grantReadWrite(downloadLogsFunction);
    parquetBucket.grantReadWrite(downloadLogsFunction);
    
    // Grant Glue permissions
    downloadLogsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'glue:GetTable',
        'glue:GetPartitions',
        'glue:CreatePartition',
        'glue:UpdatePartition',
        'glue:BatchCreatePartition',
        'glue:GetDatabase'
      ],
      resources: [
        `arn:aws:glue:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:catalog`,
        `arn:aws:glue:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:database/${rawLogsDatabase.ref}`,
        `arn:aws:glue:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:database/${parquetDatabase.ref}`,
        `arn:aws:glue:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${rawLogsDatabase.ref}/${rawLogsTable.ref}`,
        `arn:aws:glue:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${parquetDatabase.ref}/${parquetLogsTable.ref}`
      ]
    }));

    // Grant Athena permissions
    downloadLogsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'athena:StartQueryExecution',
        'athena:GetQueryExecution',
        'athena:GetQueryResults',
        'athena:StopQueryExecution'
      ],
      resources: ['*']
    }));

    // Grant Secrets Manager permissions
    downloadLogsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue'
      ],
      resources: [
        `arn:aws:secretsmanager:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:secret:aliyun-credentials*`
      ]
    }));

    // Reference existing Athena results bucket or create if it doesn't exist
    const athenaResultsBucketName = `athena-results-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`;
    const athenaResultsBucket = s3.Bucket.fromBucketName(this, 'AthenaResultsBucket', athenaResultsBucketName);

    // Grant permissions to the existing bucket
    athenaResultsBucket.grantReadWrite(downloadLogsFunction);

    // EventBridge rule for scheduled execution
    const scheduleRule = new events.Rule(this, 'AlibabaLogsSchedule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '2', // 2 AM UTC daily
        day: '*',
        month: '*',
        year: '*'
      })
    });

    scheduleRule.addTarget(new targets.LambdaFunction(downloadLogsFunction));

    // Outputs
    new cdk.CfnOutput(this, 'RawLogsBucket', {
      value: rawLogsBucket.bucketName,
      description: 'S3 bucket for raw log files'
    });

    new cdk.CfnOutput(this, 'ParquetBucket', {
      value: parquetBucket.bucketName,
      description: 'S3 bucket for parquet files'
    });

    new cdk.CfnOutput(this, 'RawLogsDatabase', {
      value: rawLogsDatabase.ref,
      description: 'Glue database for raw logs'
    });

    new cdk.CfnOutput(this, 'ParquetDatabase', {
      value: parquetDatabase.ref,
      description: 'Glue database for parquet logs'
    });
  }
}
