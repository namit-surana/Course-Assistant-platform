#!/bin/sh
set -eu

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
BUCKET="${S3_BUCKET_NAME:-prod-bucket-uploads}"
QUEUE="${SQS_QUEUE_NAME:-prod-queue-analysis}"

awslocal s3api create-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null || true
awslocal sqs create-queue \
  --queue-name "$QUEUE" \
  --attributes VisibilityTimeout=1800,MessageRetentionPeriod=345600

echo "LocalStack resources ready: s3://$BUCKET, queue=$QUEUE"
