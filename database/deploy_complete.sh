#!/bin/bash
# Complete deployment script for Medicare API
# 1. Create RDS database
# 2. Load data
# 3. Deploy Lambda + API Gateway

export AWS_PROFILE=silverman
export AWS_REGION=us-east-1

echo "=========================================="
echo "MEDICARE API - COMPLETE DEPLOYMENT"
echo "=========================================="
echo ""

# Step 1: Deploy RDS
echo "Step 1: Deploying RDS PostgreSQL..."
echo "Press ENTER to continue or Ctrl+C to cancel"
read

./database/deploy_rds.sh

# Wait for credentials
if [ ! -f database/db_credentials.json ]; then
    echo "❌ Database credentials not found. Deploy failed."
    exit 1
fi

# Step 2: Create database schema
echo ""
echo "Step 2: Creating database schema..."
echo "Press ENTER to continue"
read

# Extract connection details
DB_HOST=$(jq -r '.endpoint' database/db_credentials.json)
DB_NAME=$(jq -r '.database' database/db_credentials.json)
DB_USER=$(jq -r '.username' database/db_credentials.json)
DB_PASSWORD=$(jq -r '.password' database/db_credentials.json)

export PGPASSWORD="$DB_PASSWORD"
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f database/schema.sql

if [ $? -ne 0 ]; then
    echo "❌ Schema creation failed"
    exit 1
fi

echo "✅ Schema created"

# Step 3: Load data
echo ""
echo "Step 3: Loading Medicare data into database..."
echo "This will load 6,402 plans + geographic data"
echo "Press ENTER to continue"
read

python3 database/load_data.py "host=$DB_HOST dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD"

if [ $? -ne 0 ]; then
    echo "❌ Data load failed"
    exit 1
fi

echo "✅ Data loaded"

# Step 4: Create Lambda deployment package
echo ""
echo "Step 4: Creating Lambda deployment package..."

cd lambda
rm -rf package medicare-api.zip
mkdir package
pip3 install -r requirements.txt -t package/
cp medicare_api.py package/
cd package
zip -r ../medicare-api.zip .
cd ../..

echo "✅ Lambda package created: lambda/medicare-api.zip"

# Step 5: Deploy Lambda function
echo ""
echo "Step 5: Deploying Lambda function..."

# Create IAM role for Lambda
ROLE_NAME="MedicareAPILambdaRole"
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null)

if [ -z "$ROLE_ARN" ]; then
    echo "Creating IAM role..."
    
    cat > /tmp/lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
    
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
    
    sleep 10  # Wait for role to propagate
    
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
fi

echo "Role ARN: $ROLE_ARN"

# Create or update Lambda function
FUNCTION_NAME="MedicareAPI"

aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda/medicare-api.zip
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler medicare_api.lambda_handler \
        --zip-file fileb://lambda/medicare-api.zip \
        --timeout 30 \
        --memory-size 512 \
        --environment Variables="{DB_HOST=$DB_HOST,DB_PORT=5432,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD}"
fi

echo "✅ Lambda deployed"

# Step 6: Create API Gateway
echo ""
echo "Step 6: Setting up API Gateway..."

API_NAME="MedicareAPI"
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='$API_NAME'].ApiId" --output text)

if [ -z "$API_ID" ]; then
    echo "Creating new API Gateway..."
    API_ID=$(aws apigatewayv2 create-api \
        --name $API_NAME \
        --protocol-type HTTP \
        --query 'ApiId' \
        --output text)
fi

echo "API ID: $API_ID"

# Create integration
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)

INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri $LAMBDA_ARN \
    --payload-format-version 2.0 \
    --query 'IntegrationId' \
    --output text)

# Create route
aws apigatewayv2 create-route \
    --api-id $API_ID \
    --route-key 'GET /medicare/{proxy+}' \
    --target integrations/$INTEGRATION_ID

# Create stage
aws apigatewayv2 create-stage \
    --api-id $API_ID \
    --stage-name prod \
    --auto-deploy

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$AWS_REGION:*:$API_ID/*/*" \
    2>/dev/null

# Get API endpoint
API_ENDPOINT="https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "API Endpoint: $API_ENDPOINT"
echo ""
echo "Test endpoints:"
echo "  $API_ENDPOINT/medicare/states.json"
echo "  $API_ENDPOINT/medicare/zip/10001.json"
echo "  $API_ENDPOINT/medicare/state/NY/info.json"
echo ""
echo "Database: $DB_HOST"
echo "Lambda: $FUNCTION_NAME"
echo "API Gateway: $API_ID"
echo ""
echo "=========================================="

# Save deployment info
cat > database/deployment_info.json << EOF
{
  "api_endpoint": "$API_ENDPOINT",
  "api_id": "$API_ID",
  "lambda_function": "$FUNCTION_NAME",
  "database_host": "$DB_HOST",
  "region": "$AWS_REGION",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Deployment info saved to database/deployment_info.json"
