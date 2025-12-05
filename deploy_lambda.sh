#!/bin/bash
# Deploy Medicare Plan API to AWS Lambda

set -e

echo "================================"
echo "Lambda Deployment Script"
echo "================================"

# Configuration
FUNCTION_NAME="medicare-plan-api"
REGION="us-east-1"
RUNTIME="python3.12"
HANDLER="lambda_function.lambda_handler"
MEMORY_SIZE=512
TIMEOUT=30

# Create deployment package
echo ""
echo "Step 1: Creating deployment package..."
rm -rf lambda_package lambda_package.zip
mkdir -p lambda_package

# Copy Lambda function
cp lambda_function.py lambda_package/

# Copy all state data
echo "  Copying state data..."
cp -r mock_api lambda_package/

# Calculate package size
cd lambda_package
PACKAGE_SIZE=$(du -sh . | awk '{print $1}')
echo "  Package size: $PACKAGE_SIZE"

# Create ZIP
echo ""
echo "Step 2: Creating ZIP file..."
zip -r ../lambda_package.zip . -q
cd ..

ZIP_SIZE=$(du -sh lambda_package.zip | awk '{print $1}')
echo "  ZIP size: $ZIP_SIZE"

# Check if function exists
echo ""
echo "Step 3: Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "  Function exists - updating code..."

    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_package.zip \
        --region $REGION

    echo "  ✓ Function code updated"

else
    echo "  Function does not exist - creating new function..."
    echo ""
    echo "  NOTE: You need to create an IAM role first!"
    echo "  Run this command to create a basic Lambda execution role:"
    echo ""
    echo "  aws iam create-role --role-name lambda-medicare-api-role \\"
    echo "    --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}'"
    echo ""
    echo "  aws iam attach-role-policy --role-name lambda-medicare-api-role \\"
    echo "    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    echo ""
    echo "  Then get the role ARN with:"
    echo "  aws iam get-role --role-name lambda-medicare-api-role --query 'Role.Arn' --output text"
    echo ""
    read -p "Enter the Lambda execution role ARN: " ROLE_ARN

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://lambda_package.zip \
        --memory-size $MEMORY_SIZE \
        --timeout $TIMEOUT \
        --region $REGION

    echo "  ✓ Function created"
fi

# Configure Function URL with CORS from permanent config file
echo ""
echo "Step 4: Configuring Function URL with CORS..."
echo "  Using CORS config from: cors-config.json"

# Create/update function URL with CORS
FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name $FUNCTION_NAME \
    --auth-type NONE \
    --cors file://cors-config.json \
    --region $REGION \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || \
    aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --query 'FunctionUrl' \
        --output text)

# Add public access permission
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --region $REGION 2>/dev/null || echo "  Permission already exists"

echo ""
echo "================================"
echo "✓ Deployment Complete!"
echo "================================"
echo ""
echo "Function URL: $FUNCTION_URL"
echo ""
echo "Test it:"
echo "  curl ${FUNCTION_URL}health"
echo "  curl ${FUNCTION_URL}nh/03462"
echo "  curl ${FUNCTION_URL}nh/03602"
echo "  curl ${FUNCTION_URL}vt/05401"
echo "  curl ${FUNCTION_URL}wy/82001"
echo "  curl ${FUNCTION_URL}ak/99501"
echo ""
echo "Cleanup:"
echo "  rm -rf lambda_package lambda_package.zip"
echo ""
