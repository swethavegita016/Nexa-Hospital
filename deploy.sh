#!/bin/bash
# ════════════════════════════════════════════
# Deploy Productivity Agent to Google Cloud Run
# Usage: bash deploy.sh
# ════════════════════════════════════════════
set -e

PROJECT_ID="swetha-vegita"
SERVICE_NAME="productivity-agent"
REGION="us-central1"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying Multi-Agent Productivity Assistant..."
echo "   Project : $PROJECT_ID"
echo "   Service : $SERVICE_NAME"
echo "   Region  : $REGION"
echo ""

# Load API key from .env
GENAI_KEY=$(grep GOOGLE_GENAI_API_KEY .env | cut -d= -f2)
MODEL=$(grep "^MODEL=" .env | cut -d= -f2)
MODEL=${MODEL:-gemini-2.0-flash}

echo "📦 Building and pushing image..."
gcloud builds submit --tag $IMAGE --project $PROJECT_ID

echo "☁️  Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --project $PROJECT_ID \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120 \
  --concurrency 80 \
  --set-env-vars "MODEL=$MODEL,GOOGLE_GENAI_API_KEY=$GENAI_KEY"

echo ""
echo "✅ Deployment complete!"
echo ""
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format 'value(status.url)')
echo "🌐 Your API is live at: $SERVICE_URL"
echo "📖 API Docs:            $SERVICE_URL/docs"
echo "📊 Dashboard:           $SERVICE_URL/dashboard"
echo "💬 Chat:                POST $SERVICE_URL/chat"
