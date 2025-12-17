#!/bin/bash
# LABBAIK.AI WhatsApp Bot - Deployment Script
# Run: chmod +x deploy.sh && ./deploy.sh

set -e

echo "🕌 LABBAIK.AI WhatsApp Bot - Deployment Script"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit .env file with your credentials before continuing.${NC}"
    echo ""
    echo "Required variables:"
    echo "  - WAHA_API_URL"
    echo "  - WAHA_SESSION"
    echo "  - GROQ_API_KEY"
    echo "  - DATABASE_URL"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Load environment variables
source .env

# Validate required variables
echo "🔍 Validating configuration..."

if [ -z "$WAHA_API_URL" ]; then
    echo -e "${RED}❌ WAHA_API_URL is not set${NC}"
    exit 1
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo -e "${RED}❌ GROQ_API_KEY is not set${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration validated${NC}"

# Check deployment method
echo ""
echo "Select deployment method:"
echo "1) Docker Compose (recommended)"
echo "2) Local Python (development)"
echo "3) Docker only"
read -p "Enter choice [1-3]: " DEPLOY_METHOD

case $DEPLOY_METHOD in
    1)
        echo ""
        echo "🐳 Deploying with Docker Compose..."
        
        # Check if Docker is installed
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
            exit 1
        fi
        
        # Check if Docker Compose is installed
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
            exit 1
        fi
        
        # Build and start
        docker-compose down 2>/dev/null || true
        docker-compose build
        docker-compose up -d
        
        echo ""
        echo -e "${GREEN}✅ Bot deployed successfully!${NC}"
        echo ""
        echo "📊 View logs: docker-compose logs -f"
        echo "🛑 Stop: docker-compose down"
        ;;
        
    2)
        echo ""
        echo "🐍 Setting up local Python environment..."
        
        # Check Python version
        if ! command -v python3 &> /dev/null; then
            echo -e "${RED}❌ Python 3 is not installed${NC}"
            exit 1
        fi
        
        # Create virtual environment if not exists
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Install dependencies
        echo "Installing dependencies..."
        pip install -r requirements.txt
        
        echo ""
        echo -e "${GREEN}✅ Setup complete!${NC}"
        echo ""
        echo "To start the bot:"
        echo "  source venv/bin/activate"
        echo "  uvicorn app.main:app --reload --port 8000"
        ;;
        
    3)
        echo ""
        echo "🐳 Building Docker image..."
        
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker is not installed${NC}"
            exit 1
        fi
        
        docker build -t labbaik-wa-bot .
        
        echo ""
        echo -e "${GREEN}✅ Image built successfully!${NC}"
        echo ""
        echo "To run:"
        echo "  docker run -d --name labbaik-wa-bot -p 8000:8000 --env-file .env labbaik-wa-bot"
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "🎉 Deployment script completed!"
echo ""
echo "Next steps:"
echo "1. Configure WAHA webhook URL: https://your-domain/webhook/waha"
echo "2. Test with: curl http://localhost:8000/health"
echo "3. Send a WhatsApp message to your bot!"
echo ""
echo "🌐 Website: labbaik-umrahplanner.streamlit.app"
echo "=============================================="
