#!/bin/bash

# Memory Scope API - Google Cloud Run Deployment Script
# This script deploys the backend API to Google Cloud Run

set -e

PROJECT_ID="scoped-memory-7c9f9"
SERVICE_NAME="memory-scope-api"
REGION="us-central1"
DOMAIN="api.memoryscope.dev"

echo "🚀 Deploying Memory Scope API to Google Cloud Run..."

# Load environment variables from .env.deploy if it exists
if [ -f .env.deploy ]; then
    echo "📂 Loading environment variables from .env.deploy..."
    source .env.deploy
    echo "✅ Environment variables loaded"
    echo ""
fi

# Also load Firebase JSON from file if FIREBASE_SERVICE_ACCOUNT_JSON is not set
if [ -z "$FIREBASE_SERVICE_ACCOUNT_JSON" ] && [ -f "/Users/jonmoore/Downloads/scoped-memory-7c9f9-firebase-adminsdk-fbsvc-03bbb965be.json" ]; then
    echo "📂 Loading Firebase service account JSON from file..."
    export FIREBASE_SERVICE_ACCOUNT_JSON=$(python3 -c "
import json
import sys
with open('/Users/jonmoore/Downloads/scoped-memory-7c9f9-firebase-adminsdk-fbsvc-03bbb965be.json', 'r') as f:
    data = json.load(f)
    print(json.dumps(data))
")
    echo "✅ Firebase JSON loaded"
    echo ""
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK not found."
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged in to Google Cloud. Running: gcloud auth login"
    gcloud auth login
fi

# Set project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Check for required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set. You'll need to set it in Cloud Run console."
    echo "   Or set it now: export DATABASE_URL=postgresql+psycopg://..."
fi

if [ -z "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    echo "⚠️  FIREBASE_SERVICE_ACCOUNT_JSON not set."
    echo "   You can set it later in Cloud Run console or use FIREBASE_SERVICE_ACCOUNT_PATH"
fi

# Build environment variables for deployment
# Use --update-env-vars multiple times to avoid comma/quote issues
# Or use individual --set-env-vars calls

# Build array of environment variable assignments
ENV_VARS_ARGS=()

# Base variables
ENV_VARS_ARGS+=("ENVIRONMENT=production")
ENV_VARS_ARGS+=("LOG_LEVEL=INFO")
ENV_VARS_ARGS+=("LOG_FORMAT=json")
# CORS_ORIGINS needs to be quoted because it contains commas
ENV_VARS_ARGS+=("CORS_ORIGINS=https://memoryscope.dev,https://www.memoryscope.dev")

# Add optional variables
if [ -n "$DATABASE_URL" ]; then
    ENV_VARS_ARGS+=("DATABASE_URL=$DATABASE_URL")
fi

if [ -n "$STRIPE_SECRET_KEY" ]; then
    ENV_VARS_ARGS+=("STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY")
fi

if [ -n "$STRIPE_PUBLISHABLE_KEY" ]; then
    ENV_VARS_ARGS+=("STRIPE_PUBLISHABLE_KEY=$STRIPE_PUBLISHABLE_KEY")
fi

if [ -n "$STRIPE_WEBHOOK_SECRET" ]; then
    ENV_VARS_ARGS+=("STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET")
fi

if [ -n "$SENTRY_DSN" ]; then
    ENV_VARS_ARGS+=("SENTRY_DSN=$SENTRY_DSN")
fi

# Build the --set-env-vars string
# Need to properly quote values with commas
ENV_VARS_STRING=""
for var in "${ENV_VARS_ARGS[@]}"; do
    key="${var%%=*}"
    value="${var#*=}"
    
    # If value contains comma, quote it
    if [[ "$value" == *","* ]]; then
        quoted_var="${key}=\"${value}\""
    else
        quoted_var="$var"
    fi
    
    if [ -z "$ENV_VARS_STRING" ]; then
        ENV_VARS_STRING="$quoted_var"
    else
        ENV_VARS_STRING="$ENV_VARS_STRING,$quoted_var"
    fi
done

# Create YAML file for environment variables (handles commas properly)
echo "📦 Preparing environment variables..."
ENV_VARS_FILE=$(mktemp)
trap "rm -f $ENV_VARS_FILE" EXIT

python3 << PYEOF > "$ENV_VARS_FILE"
import os

env_vars = {
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
    "CORS_ORIGINS": "https://memoryscope.dev,https://www.memoryscope.dev"
}

# Add optional variables
if os.environ.get("DATABASE_URL"):
    env_vars["DATABASE_URL"] = os.environ["DATABASE_URL"]

if os.environ.get("STRIPE_SECRET_KEY"):
    env_vars["STRIPE_SECRET_KEY"] = os.environ["STRIPE_SECRET_KEY"]

if os.environ.get("STRIPE_PUBLISHABLE_KEY"):
    env_vars["STRIPE_PUBLISHABLE_KEY"] = os.environ["STRIPE_PUBLISHABLE_KEY"]

if os.environ.get("STRIPE_WEBHOOK_SECRET"):
    env_vars["STRIPE_WEBHOOK_SECRET"] = os.environ["STRIPE_WEBHOOK_SECRET"]

if os.environ.get("SENTRY_DSN"):
    env_vars["SENTRY_DSN"] = os.environ["SENTRY_DSN"]

# Note: Firebase JSON will be set separately to avoid YAML parsing issues
# We'll set a placeholder first, then update it

# Write as YAML format (gcloud --env-vars-file accepts YAML)
# Format: KEY: "value" (quoted for values with special chars)
for key, value in env_vars.items():
    # Skip Firebase JSON - will be set separately
    if key == "FIREBASE_SERVICE_ACCOUNT_JSON":
        continue
    # Always quote values to handle special characters
    escaped_value = str(value).replace('"', '\\"')
    print(f'{key}: "{escaped_value}"')
PYEOF

echo "✅ Environment variables prepared"
echo ""

# Deploy to Cloud Run WITH environment variables
echo "📦 Building and deploying to Cloud Run..."
echo "   (This may take a few minutes for the first deployment)"

# Build deployment command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --env-vars-file $ENV_VARS_FILE"

# Note: Firebase JSON will be added after initial deployment to avoid YAML parsing issues
# The app will start without it (with a warning) and then Firebase will be added

DEPLOY_CMD="$DEPLOY_CMD --project $PROJECT_ID"

# Execute deployment
eval $DEPLOY_CMD

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo "✅ Initial deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"

# Set Firebase JSON separately to avoid YAML parsing issues
# The app can start without it (startup validation is lenient), then we add it
if [ -n "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    echo ""
    echo "🔧 Setting Firebase service account JSON..."
    
    # Convert to single-line JSON
    FIREBASE_JSON_SINGLE=$(python3 << PYEOF
import os
import json
if os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"):
    json_obj = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
    print(json.dumps(json_obj, separators=(',', ':')))
PYEOF
)
    
    # Update with Firebase JSON using --update-env-vars
    # Use custom delimiter (^##^) to prevent gcloud from splitting on commas in JSON
    # Format: --update-env-vars "^##^KEY=value,with,commas##KEY2=value2"
    gcloud run services update $SERVICE_NAME \
      --region $REGION \
      --update-env-vars "^##^FIREBASE_SERVICE_ACCOUNT_JSON=$FIREBASE_JSON_SINGLE" \
      --project $PROJECT_ID \
      --quiet
    
    echo "✅ Firebase JSON configured (new revision created)"
fi

# Check if custom domain mapping exists
if gcloud run domain-mappings describe --domain $DOMAIN --region $REGION &>/dev/null; then
    echo "✅ Custom domain already configured: https://$DOMAIN"
else
    echo "🔗 Setting up custom domain..."
    echo "   This may take a few minutes..."
    
    gcloud run domain-mappings create \
      --service $SERVICE_NAME \
      --domain $DOMAIN \
      --region $REGION \
      --project $PROJECT_ID || echo "⚠️  Domain mapping may already exist or DNS not configured"
    
    echo ""
    echo "📋 Next steps:"
    echo "   1. Configure DNS: Add CNAME record for $DOMAIN → ghs.googlehosted.com"
    echo "   2. Wait for SSL certificate (can take up to 48 hours)"
    echo "   3. Verify: curl https://$DOMAIN/healthz"
fi

echo ""
echo "🧪 Testing deployment..."
sleep 5
curl -f "$SERVICE_URL/healthz" && echo "✅ Health check passed!" || echo "⚠️  Health check failed - service may still be starting"

echo ""
echo "📝 Run database migrations:"
echo "   gcloud run jobs create migrate-db \\"
echo "     --image gcr.io/$PROJECT_ID/$SERVICE_NAME \\"
echo "     --region $REGION \\"
echo "     --command alembic --args upgrade head"

echo ""
echo "🎉 Deployment complete! Your API is available at:"
echo "   $SERVICE_URL"
if [ -n "$DOMAIN" ]; then
    echo "   https://$DOMAIN (once DNS is configured)"
fi

