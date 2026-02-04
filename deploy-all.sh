#!/bin/bash

# Memory Scope - Complete Deployment Script
# This script handles: Git commit/push, website deployment, API deployment, and service restarts
#
# Usage:
#   ./deploy-all.sh                    # Deploy everything with auto-commit message
#   ./deploy-all.sh "Your message"     # Deploy with custom commit message
#   ./deploy-all.sh --no-git           # Skip git operations
#   ./deploy-all.sh --website-only     # Deploy only website
#   ./deploy-all.sh --api-only         # Deploy only API
#   ./deploy-all.sh --no-restart       # Skip service restarts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBSITE_DIR="$PROJECT_ROOT/website"
API_DIR="$PROJECT_ROOT"

# Flags
SKIP_GIT=false
WEBSITE_ONLY=false
API_ONLY=false
SKIP_RESTART=false
COMMIT_MESSAGE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-git)
            SKIP_GIT=true
            shift
            ;;
        --website-only)
            WEBSITE_ONLY=true
            shift
            ;;
        --api-only)
            API_ONLY=true
            shift
            ;;
        --no-restart)
            SKIP_RESTART=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [COMMIT_MESSAGE]"
            echo ""
            echo "Options:"
            echo "  --no-git          Skip git commit and push"
            echo "  --website-only    Deploy only the website"
            echo "  --api-only        Deploy only the API"
            echo "  --no-restart      Skip service restarts"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Deploy everything"
            echo "  $0 \"Update billing page\"            # Deploy with custom message"
            echo "  $0 --website-only                    # Deploy only website"
            echo "  $0 --no-git                          # Deploy without git"
            exit 0
            ;;
        *)
            COMMIT_MESSAGE="$1"
            shift
            ;;
    esac
done

# Function to print colored output
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 not found. Please install it first."
        exit 1
    fi
}

# Function to check git status
check_git_status() {
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        print_warning "Not a git repository. Skipping git operations."
        SKIP_GIT=true
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Check if there are changes
    if [ -z "$(git status --porcelain)" ]; then
        print_warning "No changes to commit. Skipping git operations."
        SKIP_GIT=true
        return
    fi
    
    # Check if we're on a branch
    if ! git rev-parse --abbrev-ref HEAD &> /dev/null; then
        print_warning "Not on a branch. Skipping git operations."
        SKIP_GIT=true
        return
    fi
}

# Function to commit and push to GitHub
git_deploy() {
    if [ "$SKIP_GIT" = true ]; then
        return
    fi
    
    print_step "Git: Checking status..."
    check_git_status
    
    if [ "$SKIP_GIT" = true ]; then
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Get current branch
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    print_step "Git: Current branch is '$BRANCH'"
    
    # Generate commit message if not provided
    if [ -z "$COMMIT_MESSAGE" ]; then
        COMMIT_MESSAGE="Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # Stage all changes
    print_step "Git: Staging changes..."
    git add -A
    
    # Commit
    print_step "Git: Committing changes..."
    git commit -m "$COMMIT_MESSAGE" || {
        print_warning "Nothing to commit or commit failed"
        SKIP_GIT=true
        return
    }
    
    # Push to GitHub
    print_step "Git: Pushing to GitHub..."
    if git push origin "$BRANCH"; then
        print_success "Git: Pushed to GitHub successfully"
    else
        print_error "Git: Push failed. Continuing with deployment..."
    fi
}

# Function to deploy website
deploy_website() {
    if [ "$API_ONLY" = true ]; then
        return
    fi
    
    print_step "Website: Starting deployment..."
    
    cd "$WEBSITE_DIR"
    
    # Check if Firebase CLI is installed
    if ! command -v firebase &> /dev/null; then
        print_warning "Firebase CLI not found. Installing..."
        npm install -g firebase-tools
    fi
    
    # Check if logged in to Firebase
    if ! firebase projects:list &> /dev/null; then
        print_error "Not logged in to Firebase. Please run: firebase login"
        exit 1
    fi
    
    # Set API URL if not set
    if [ -z "$NEXT_PUBLIC_API_URL" ]; then
        export NEXT_PUBLIC_API_URL="https://memory-scope-api-x2luqzah4q-uc.a.run.app"
        print_warning "NEXT_PUBLIC_API_URL not set. Using Cloud Run URL: https://memory-scope-api-x2luqzah4q-uc.a.run.app"
    fi
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_step "Website: Installing dependencies..."
        npm install
    fi
    
    # Build
    print_step "Website: Building Next.js application..."
    npm run build
    
    if [ ! -d "out" ]; then
        print_error "Website: Build failed - 'out' directory not found"
        exit 1
    fi
    
    print_success "Website: Build successful"
    
    # Deploy to Firebase
    print_step "Website: Deploying to Firebase Hosting..."
    if firebase deploy --only hosting; then
        print_success "Website: Deployed successfully to Firebase Hosting"
        echo "   🌐 Live at: https://memoryscope.dev"
    else
        print_error "Website: Deployment failed"
        exit 1
    fi
}

# Function to deploy API
deploy_api() {
    if [ "$WEBSITE_ONLY" = true ]; then
        return
    fi
    
    print_step "API: Starting deployment..."
    
    cd "$API_DIR"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if logged in
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not logged in to Google Cloud. Running: gcloud auth login"
        gcloud auth login
    fi
    
    # Load environment variables from .env.deploy
    if [ -f .env.deploy ]; then
        print_step "API: Loading environment variables from .env.deploy..."
        source .env.deploy
        print_success "API: Environment variables loaded"
    else
        print_warning "API: .env.deploy not found. Some environment variables may be missing."
    fi
    
    # Run the deployment script
    print_step "API: Deploying to Google Cloud Run..."
    if [ -f "deploy-backend-cloudrun.sh" ]; then
        bash deploy-backend-cloudrun.sh
        print_success "API: Deployed successfully to Cloud Run"
    else
        print_error "API: deploy-backend-cloudrun.sh not found"
        exit 1
    fi
}

# Function to restart local services (Docker)
restart_services() {
    if [ "$SKIP_RESTART" = true ]; then
        return
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_warning "Docker is not running. Skipping service restart."
        return
    fi
    
    # Check if docker-compose.yml exists
    if [ ! -f "$API_DIR/docker-compose.yml" ]; then
        print_warning "docker-compose.yml not found. Skipping service restart."
        return
    fi
    
    print_step "Services: Restarting local Docker containers..."
    cd "$API_DIR"
    
    if docker-compose ps | grep -q "Up"; then
        docker-compose restart
        print_success "Services: Docker containers restarted"
    else
        print_warning "Services: No running containers to restart"
    fi
}

# Main deployment flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         Memory Scope - Complete Deployment                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Check required commands
    print_step "Checking prerequisites..."
    if [ "$SKIP_GIT" = false ]; then
        check_command "git"
    fi
    if [ "$WEBSITE_ONLY" = false ] && [ "$API_ONLY" = false ]; then
        check_command "firebase"
        check_command "gcloud"
    elif [ "$WEBSITE_ONLY" = true ]; then
        check_command "firebase"
    elif [ "$API_ONLY" = true ]; then
        check_command "gcloud"
    fi
    print_success "Prerequisites check passed"
    echo ""
    
    # Step 1: Git operations
    if [ "$SKIP_GIT" = false ]; then
        git_deploy
        echo ""
    fi
    
    # Step 2: Deploy website
    if [ "$WEBSITE_ONLY" = false ] && [ "$API_ONLY" = false ] || [ "$WEBSITE_ONLY" = true ]; then
        deploy_website
        echo ""
    fi
    
    # Step 3: Deploy API
    if [ "$WEBSITE_ONLY" = false ] && [ "$API_ONLY" = false ] || [ "$API_ONLY" = true ]; then
        deploy_api
        echo ""
    fi
    
    # Step 4: Restart local services
    restart_services
    echo ""
    
    # Summary
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    Deployment Complete! ✅                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ "$SKIP_GIT" = false ]; then
        print_success "Git: Changes committed and pushed"
    fi
    
    if [ "$WEBSITE_ONLY" = false ] && [ "$API_ONLY" = false ] || [ "$WEBSITE_ONLY" = true ]; then
        print_success "Website: Deployed to Firebase Hosting"
        echo "   🌐 https://memoryscope.dev"
    fi
    
    if [ "$WEBSITE_ONLY" = false ] && [ "$API_ONLY" = false ] || [ "$API_ONLY" = true ]; then
        print_success "API: Deployed to Google Cloud Run"
        echo "   🌐 https://api.memoryscope.dev"
    fi
    
    if [ "$SKIP_RESTART" = false ]; then
        print_success "Services: Local containers restarted (if running)"
    fi
    
    echo ""
    print_success "All deployments completed successfully! 🎉"
    echo ""
}

# Run main function
main

