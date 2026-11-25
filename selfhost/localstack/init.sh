#!/bin/sh
# Recreate the AWS stand-ins document storage, uploads, files, and the
# connection gateway need. LocalStack community edition does not keep this
# across a restart, so the install runs this on every boot. Object bytes are
# not restored; document text lives in Postgres and the sync volume.
set -eu

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ENDPOINT="${AWS_ENDPOINT_URL:-http://localstack:4566}"
ACCOUNT=000000000000

i=0
until command aws --endpoint-url "$ENDPOINT" s3api list-buckets >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 60 ]; then
    echo "localstack did not become ready" >&2
    exit 1
  fi
  sleep 2
done

aws() {
  command aws --endpoint-url "$ENDPOINT" "$@"
}

bucket() {
  aws s3api create-bucket --bucket "$1" >/dev/null 2>&1 || true
}

queue() {
  aws sqs create-queue --queue-name "$1" >/dev/null 2>&1 || true
}

for name in \
  doc-storage \
  static-file-storage \
  docx-upload \
  bulk-upload-staging \
  macro-email-attachments \
  macro-call-recording-local \
  agent-session-changes \
  github-pull-request-patches
do
  bucket "$name"
done

for name in \
  document-upload-finalizer-queue \
  static-file-s3-event-notification-queue \
  notification-queue \
  notification-ingress-queue \
  push-delivery-queue \
  reminder-dispatch-queue \
  search-event-queue \
  slack-import-queue \
  slack-import-dlq \
  delete-document-handler-queue \
  document-text-extractor-lambda-queue
do
  queue "$name"
done

# doc-storage object-created events wake the upload finalizer.
FINALIZER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:${ACCOUNT}:document-upload-finalizer-queue"
FINALIZER_URL="${ENDPOINT}/${ACCOUNT}/document-upload-finalizer-queue"
aws sqs set-queue-attributes \
  --queue-url "$FINALIZER_URL" \
  --attributes "{\"Policy\":\"{\\\"Version\\\":\\\"2012-10-17\\\",\\\"Statement\\\":[{\\\"Effect\\\":\\\"Allow\\\",\\\"Principal\\\":\\\"*\\\",\\\"Action\\\":\\\"sqs:SendMessage\\\",\\\"Resource\\\":\\\"${FINALIZER_ARN}\\\"}]}\"}" \
  >/dev/null 2>&1 || true
aws s3api put-bucket-notification-configuration \
  --bucket doc-storage \
  --notification-configuration "{\"QueueConfigurations\":[{\"Id\":\"document-upload-finalizer\",\"QueueArn\":\"${FINALIZER_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}" \
  >/dev/null 2>&1 || true

if ! aws dynamodb describe-table --table-name connection-gateway-table >/dev/null 2>&1; then
  aws dynamodb create-table \
    --table-name connection-gateway-table \
    --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
    --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes '[{"IndexName":"ConnectionPkIndex","KeySchema":[{"AttributeName":"SK","KeyType":"HASH"},{"AttributeName":"PK","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}]' \
    >/dev/null
fi

if ! aws dynamodb describe-table --table-name static-file-metadata >/dev/null 2>&1; then
  aws dynamodb create-table \
    --table-name static-file-metadata \
    --attribute-definitions AttributeName=file_id,AttributeType=S \
    --key-schema AttributeName=file_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    >/dev/null
fi

if ! aws dynamodb describe-table --table-name bulk-upload >/dev/null 2>&1; then
  aws dynamodb create-table \
    --table-name bulk-upload \
    --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
    --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes '[{"IndexName":"DocumentPkIndex","KeySchema":[{"AttributeName":"SK","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
    >/dev/null
fi

for alias in \
  alias/macro-local-cursor-api-key \
  alias/macro-local-codex-oauth \
  alias/macro-local-mcp-oauth \
  alias/macro-local-microsoft-token
do
  if aws kms describe-key --key-id "$alias" >/dev/null 2>&1; then
    continue
  fi
  key_id="$(aws kms create-key --query KeyMetadata.KeyId --output text)"
  aws kms create-alias --alias-name "$alias" --target-key-id "$key_id" >/dev/null
done

echo "localstack resources ready"
