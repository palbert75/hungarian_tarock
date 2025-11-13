#!/bin/bash

# Docker Build and Publish Script for Hungarian Tarokk Server
# Usage: ./docker-publish.sh [version]
# Example: ./docker-publish.sh 1.0.0
# If no version is provided, only 'latest' tag is used

set -e  # Exit on any error

# Configuration
DOCKER_USERNAME="palbert75"
IMAGE_NAME="hungarian-tarokk-server"
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME"
DOCKERFILE_PATH="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_info "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if logged in to Docker Hub
check_docker_login() {
    print_info "Checking Docker Hub authentication..."
    if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
        print_warning "Not logged in to Docker Hub as $DOCKER_USERNAME"
        print_info "Attempting to login..."
        docker login
    fi
    print_success "Authenticated with Docker Hub"
}

# Build the Docker image
build_image() {
    local version=$1

    print_info "Building Docker image..."
    print_info "Image: $FULL_IMAGE_NAME:latest"

    if ! docker build -t "$FULL_IMAGE_NAME:latest" "$DOCKERFILE_PATH"; then
        print_error "Docker build failed"
        exit 1
    fi

    print_success "Image built successfully"

    # Tag with version if provided
    if [ -n "$version" ]; then
        print_info "Tagging image with version: $version"
        docker tag "$FULL_IMAGE_NAME:latest" "$FULL_IMAGE_NAME:$version"
        docker tag "$FULL_IMAGE_NAME:latest" "$FULL_IMAGE_NAME:v$version"
        print_success "Tagged with versions: $version, v$version"
    fi
}

# Test the image
test_image() {
    print_info "Testing the image..."

    # Start test container
    local container_id=$(docker run -d -p 8001:8000 "$FULL_IMAGE_NAME:latest")

    # Wait for container to start
    sleep 5

    # Check if container is running
    if ! docker ps | grep -q "$container_id"; then
        print_error "Container failed to start"
        docker logs "$container_id"
        docker rm -f "$container_id" 2>/dev/null || true
        exit 1
    fi

    # Test health endpoint
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        docker logs "$container_id"
        docker rm -f "$container_id" 2>/dev/null || true
        exit 1
    fi

    # Cleanup
    docker stop "$container_id" > /dev/null
    docker rm "$container_id" > /dev/null
    print_success "Test completed successfully"
}

# Push to Docker Hub
push_image() {
    local version=$1

    print_info "Pushing image to Docker Hub..."

    # Push latest
    print_info "Pushing $FULL_IMAGE_NAME:latest"
    if ! docker push "$FULL_IMAGE_NAME:latest"; then
        print_error "Failed to push latest tag"
        exit 1
    fi
    print_success "Pushed latest tag"

    # Push version tags if provided
    if [ -n "$version" ]; then
        print_info "Pushing $FULL_IMAGE_NAME:$version"
        docker push "$FULL_IMAGE_NAME:$version"
        print_success "Pushed version $version"

        print_info "Pushing $FULL_IMAGE_NAME:v$version"
        docker push "$FULL_IMAGE_NAME:v$version"
        print_success "Pushed version v$version"
    fi
}

# Display image info
show_image_info() {
    local version=$1

    echo ""
    print_success "=== Docker Image Published Successfully ==="
    echo ""
    echo "Image: $FULL_IMAGE_NAME"
    echo "Tags pushed:"
    echo "  - latest"
    if [ -n "$version" ]; then
        echo "  - $version"
        echo "  - v$version"
    fi
    echo ""
    echo "Pull command:"
    echo "  docker pull $FULL_IMAGE_NAME:latest"
    echo ""
    echo "Run command:"
    echo "  docker run -d -p 8000:8000 -v tarokk-data:/app/data $FULL_IMAGE_NAME:latest"
    echo ""
    echo "Docker Hub URL:"
    echo "  https://hub.docker.com/r/$FULL_IMAGE_NAME"
    echo ""
}

# Cleanup on error
cleanup_on_error() {
    print_error "Build/push failed. Cleaning up..."
    # Remove any test containers
    docker ps -a | grep "$IMAGE_NAME" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
}

# Main script
main() {
    local version=$1

    echo ""
    print_info "=== Docker Build and Publish Script ==="
    print_info "Image: $FULL_IMAGE_NAME"
    if [ -n "$version" ]; then
        print_info "Version: $version"
    else
        print_warning "No version specified, will only tag as 'latest'"
        print_info "Usage: $0 <version> (e.g., $0 1.0.0)"
    fi
    echo ""

    # Trap errors
    trap cleanup_on_error ERR

    # Run checks and build
    check_docker
    check_docker_login
    build_image "$version"
    test_image

    # Confirm before pushing
    echo ""
    read -p "$(echo -e ${YELLOW}Push to Docker Hub? [y/N]:${NC} )" -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        push_image "$version"
        show_image_info "$version"
    else
        print_warning "Push cancelled by user"
        print_info "Image built locally: $FULL_IMAGE_NAME:latest"
        exit 0
    fi
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
