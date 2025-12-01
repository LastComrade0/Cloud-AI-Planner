# Cloud AI Planner - Lambda Deployment Guide

## Prerequisites
- AWS CLI configured
- AWS Lambda, API Gateway, and RDS access
- Python 3.11+ installed locally

## Step 1: Package the Application

Run the packaging script:
.\package-lambda.ps1 This creates `lambda-deployment.zip` ready for upload.

## Step 2: Create Lambda Layer (Dependencies)

The Lambda function requires a layer containing Python dependencies. 

### Option A: Build Layer in AWS CloudShell

1. Upload `build-layer.sh` and `requirements-lambda.txt` to CloudShell
2. Run: `bash build-layer.sh`
3. Download `layer.zip`
4. In Lambda Console → Layers → Create layer
5. Upload `layer.zip` and select compatible runtime (Python 3.11 or 3.12)

### Option B: Use Existing Layer

If you already have a layer, note its ARN (e.g., `arn:aws:lambda:us-west-1:504998239826:layer:cloud-ai-planner-dependencies:3`)

**Important:** The layer must include `mangum`, `fastapi`, `python-jose[cryptography]`, `requests`, and all other dependencies from `requirements-lambda.txt`.

## Step 3: Create Lambda Function

1. Go to AWS Lambda Console
2. Create function: `cloud-ai-planner-api`
3. Runtime: Python 3.11 or 3.12
4. Upload `lambda-deployment.zip`
5. Set Handler: `lambda_handler.handler`
6. **Attach the Lambda Layer** (from Step 2) to the function

## Step 4: Configure Environment Variables

Add these in Lambda → Configuration → Environment variables:

### Required Environment Variables

```bash
# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://www.simpleaiplanner.com,https://simpleaiplanner.com

# Cognito Authentication
COGNITO_REGION=us-west-1
COGNITO_USER_POOL_ID=us-west-1_SsXJndL6f
COGNITO_APP_CLIENT_ID=34ec70utdus79c7l9ru3frmf40

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# OpenAI
OPENAI_API_KEY=sk-...
```

### Optional Environment Variables (with defaults)

```bash
# AWS Region (defaults to us-west-1)
AWS_REGION=us-west-1

# Textract Configuration (for async document processing)
TEXTRACT_S3_BUCKET=your-textract-bucket
TEXTRACT_SNS_TOPIC_ARN=arn:aws:sns:us-west-1:account:topic-name
TEXTRACT_SQS_QUEUE_URL=https://sqs.us-west-1.amazonaws.com/account/queue-name
TEXTRACT_ROLE_ARN=arn:aws:iam::account:role/textract-role
```

**Note:** See `env.example` for a template of all environment variables.

## Step 5: Configure API Gateway

1. Create or configure an HTTP API in API Gateway
2. Create a route: `ANY /{proxy+}` pointing to your Lambda function
3. Deploy the API
4. Note the API endpoint URL (e.g., `https://api.simpleaiplanner.com`)

## Step 6: Update Frontend Environment Variables

Update `frontend/.env.production` with your production URLs:

```env
VITE_COGNITO_USER_POOL_ID=us-west-1_SsXJndL6f
VITE_COGNITO_APP_CLIENT_ID=34ec70utdus79c7l9ru3frmf40
VITE_COGNITO_REGION=us-west-1
VITE_COGNITO_DOMAIN=us-west-1ssxjndl6f
VITE_APP_URL=https://www.simpleaiplanner.com
VITE_API_URL=https://api.simpleaiplanner.com
```

## Troubleshooting

### Error: "Unable to import module 'lambda_handler': No module named 'mangum'"
- **Solution:** Rebuild the Lambda Layer to include `mangum` and all dependencies from `requirements-lambda.txt`

### Error: "Cognito configuration missing"
- **Solution:** Ensure `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, and `COGNITO_APP_CLIENT_ID` are set in Lambda environment variables

### Error: CORS errors
- **Solution:** Ensure `ALLOWED_ORIGINS` includes your frontend domain (e.g., `https://www.simpleaiplanner.com`)
- Also verify API Gateway CORS settings allow credentials and your frontend origin


upload frontend:Access to XMLHttpRequest at 'https://api.simpleaiplanner.com/api/v1/planner/c791d81b-0b83-4092-a374-0068c28b8e00' from origin 'https://www.simpleaiplanner.com' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
index-BEfUJi-F.js:42  PATCH https://api.simpleaiplanner.com/api/v1/planner/c791d81b-0b83-4092-a374-0068c28b8e00 net::ERR_FAILED   aws s3 sync frontend/dist/ s3://cloud-ai-planner-frontend --delete