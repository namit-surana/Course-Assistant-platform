#!/bin/sh
set -eu

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
BUCKET="${S3_BUCKET_NAME:-prod-bucket-uploads}"
QUEUE="${SQS_QUEUE_NAME:-prod-queue-analysis}"

awslocal s3api create-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null || true

cat <<'JSON' >/tmp/bucket-cors.json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["PUT", "POST", "GET", "HEAD"],
      "AllowedOrigins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
      ],
      "ExposeHeaders": ["ETag", "x-amz-request-id", "x-amz-id-2"],
      "MaxAgeSeconds": 3000
    }
  ]
}
JSON

awslocal s3api put-bucket-cors \
  --bucket "$BUCKET" \
  --cors-configuration file:///tmp/bucket-cors.json

awslocal sqs create-queue \
  --queue-name "$QUEUE" \
  --attributes VisibilityTimeout=1800,MessageRetentionPeriod=345600

echo "LocalStack resources ready: s3://$BUCKET (CORS configured), queue=$QUEUE"
