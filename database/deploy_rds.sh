#!/bin/bash
# Deploy RDS PostgreSQL for Medicare API
# Using AWS profile: silverman

export AWS_PROFILE=silverman

DB_NAME="medicare_plans"
DB_USERNAME="medicare_admin"
DB_INSTANCE_ID="medicare-plans-db"
REGION="us-east-1"

echo "=========================================="
echo "DEPLOYING RDS POSTGRESQL DATABASE"
echo "=========================================="
echo ""

# Generate random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "Generated database password (save this!)"
echo "Password: $DB_PASSWORD"
echo ""

# Create standard RDS PostgreSQL instance (simpler than Aurora for small datasets)
echo "Creating RDS PostgreSQL instance (db.t3.micro)..."
aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_ID \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.8 \
    --master-username $DB_USERNAME \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --db-name $DB_NAME \
    --publicly-accessible \
    --backup-retention-period 7 \
    --region $REGION

echo ""
echo "Waiting for database to become available (this takes ~5 minutes)..."
aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $REGION

# Get endpoint
ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo ""
echo "=========================================="
echo "✅ DATABASE CREATED"
echo "=========================================="
echo "Endpoint: $ENDPOINT"
echo "Database: $DB_NAME"
echo "Username: $DB_USERNAME"
echo "Password: $DB_PASSWORD"
echo ""
echo "Connection string:"
echo "postgresql://$DB_USERNAME:$DB_PASSWORD@$ENDPOINT:5432/$DB_NAME"
echo ""
echo "SAVE THESE CREDENTIALS!"
echo "=========================================="

# Save credentials to file
cat > database/db_credentials.json << EOF
{
  "endpoint": "$ENDPOINT",
  "port": 5432,
  "database": "$DB_NAME",
  "username": "$DB_USERNAME",
  "password": "$DB_PASSWORD",
  "connection_string": "postgresql://$DB_USERNAME:$DB_PASSWORD@$ENDPOINT:5432/$DB_NAME"
}
EOF

echo ""
echo "✅ Credentials saved to database/db_credentials.json"
