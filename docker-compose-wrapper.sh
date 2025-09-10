#!/bin/bash
# Enhanced docker-compose wrapper for cuti containers
# This script ensures docker-compose works properly in the container environment

# Function to check if Docker is accessible
check_docker() {
    if ! docker version &>/dev/null; then
        echo "Error: Docker is not accessible. Checking permissions..." >&2
        
        # Check if docker socket exists
        if [ ! -e /var/run/docker.sock ]; then
            echo "Error: Docker socket not found at /var/run/docker.sock" >&2
            echo "Make sure the container was started with -v /var/run/docker.sock:/var/run/docker.sock" >&2
            exit 1
        fi
        
        # Check socket permissions
        echo "Docker socket permissions:" >&2
        ls -la /var/run/docker.sock >&2
        
        # Try to fix permissions
        if [ -n "$SUDO_USER" ] || [ "$EUID" -eq 0 ]; then
            echo "Attempting to fix Docker permissions..." >&2
            DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
            groupmod -g $DOCKER_GID docker 2>/dev/null || true
            usermod -aG docker $USER 2>/dev/null || true
            echo "Please restart your shell or run 'newgrp docker'" >&2
        else
            echo "Try running: sudo usermod -aG docker $USER" >&2
            echo "Then restart your shell or run: newgrp docker" >&2
        fi
        exit 1
    fi
}

# Check Docker access first
check_docker

# Handle version flag specially
if [ "$1" = "--version" ] || [ "$1" = "-v" ] || [ "$1" = "version" ]; then
    docker compose version
    exit $?
fi

# Use docker compose plugin (v2) with full argument passthrough
exec docker compose "$@"