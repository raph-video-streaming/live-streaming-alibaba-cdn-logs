import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export class ParquetConversionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Reference existing S3 buckets
    const logsBucket = s3.Bucket.fromBucketName(this, 'LogsBucket', 'spl-live-cdn-logs');
    const targetBucket = s3.Bucket.fromBucketName(this, 'TargetBucket', 'spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf');

    // AWS managed pandas layer
    const pandasLayer = lambda.LayerVersion.fromLayerVersionArn(
      this,
      'PandasLayer',
      'arn:aws:lambda:me-central-1:593833071574:layer:AWSSDKPandas-Python312-Arm64:19'
    );

    // Lambda function for Parquet conversion
    const parquetConverter = new lambda.Function(this, 'ParquetConverter', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('lib/lambda/parquet_converter'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 8096,
      architecture: lambda.Architecture.ARM_64,
      layers: [pandasLayer]
    });

    // Grant permissions
    logsBucket.grantReadWrite(parquetConverter);
    targetBucket.grantReadWrite(parquetConverter);
    
    parquetConverter.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'athena:StartQueryExecution',
        'athena:GetQueryExecution',
        'glue:*',
        's3:PutObject',
        's3:PutObjectAcl'
      ],
      resources: [
        'arn:aws:s3:::spl-live-cdn-logs/*',
        'arn:aws:s3:::spl-live-foundationstack-hostingvideofilebucketc54-s8wpjvayhncf/*',
        '*'
      ]
    }));

    // S3 event notification for new gz files
    logsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(parquetConverter),
      { 
        prefix: 'alibaba-cdn/alibaba-cdn_partitioned/',
        suffix: '.gz'
      }
    );
  }
}