#!/bin/bash

# Selective Symlink Initialization Script
# This script creates symlinks ONLY for data directories while keeping source code local

set -e  # Exit on any error

# Configuration
AFS_BASE="/mnt/fileshare"
APP_BASE="/app"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting selective data symlink initialization..."

# Verify Azure File Share mount exists
if [ ! -d "$AFS_BASE" ]; then
    log "ERROR: Azure File Share not mounted at $AFS_BASE"
    exit 1
fi

log "✓ Azure File Share detected at $AFS_BASE"

# Function to create directory in file share if it doesn't exist
ensure_afs_dir() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        log "Creating directory: $dir_path"
        mkdir -p "$dir_path"
        chmod 755 "$dir_path"
    else
        log "✓ Directory exists: $dir_path"
    fi
}

# Function to create selective symlink
create_data_symlink() {
    local container_path="$1"
    local afs_path="$2"
    local description="$3"
    
    log "Setting up $description..."
    
    # Ensure target directory exists in file share
    ensure_afs_dir "$afs_path"
    
    # Remove existing directory/symlink in container if it exists
    if [ -e "$container_path" ]; then
        log "Removing existing: $container_path"
        rm -rf "$container_path"
    fi
    
    # Create parent directory if needed
    mkdir -p "$(dirname "$container_path")"
    
    # Create symlink
    log "Creating symlink: $container_path -> $afs_path"
    ln -s "$afs_path" "$container_path"
    
    # Verify symlink works
    if [ -L "$container_path" ] && [ -d "$container_path" ]; then
        log "✓ $description symlink created successfully"
        # Test write access
        if touch "$container_path/.write_test" 2>/dev/null; then
            rm -f "$container_path/.write_test"
            log "✓ $description has write access"
        else
            log "⚠️  $description symlink created but no write access"
        fi
    else
        log "❌ Failed to create $description symlink"
        return 1
    fi
}

# Create data directory structure in Azure File Share
log "Creating data directory structure in Azure File Share..."

ensure_afs_dir "$AFS_BASE/forecasting/data/input"
ensure_afs_dir "$AFS_BASE/forecasting/data/output"
ensure_afs_dir "$AFS_BASE/modelling/cache/sarima_params"
ensure_afs_dir "$AFS_BASE/modelling/cache/time_moe_cache"
ensure_afs_dir "$AFS_BASE/modelling/predictions"
ensure_afs_dir "$AFS_BASE/scraping/scraped_data"
ensure_afs_dir "$AFS_BASE/logs"

# Create selective symlinks for data directories ONLY
log "Creating selective symlinks for data directories..."

# Forecasting data symlink
create_data_symlink \
    "$APP_BASE/forecasting/data" \
    "$AFS_BASE/forecasting/data" \
    "Forecasting Data"

# Modelling cache symlink
create_data_symlink \
    "$APP_BASE/modelling/cache" \
    "$AFS_BASE/modelling/cache" \
    "Modelling Cache"

# Modelling predictions symlink
create_data_symlink \
    "$APP_BASE/modelling/predictions" \
    "$AFS_BASE/modelling/predictions" \
    "Modelling Predictions"

# Scraping data symlink
create_data_symlink \
    "$APP_BASE/scraping/scraped_data" \
    "$AFS_BASE/scraping/scraped_data" \
    "Scraping Data"

# Logs symlink
create_data_symlink \
    "$APP_BASE/logs" \
    "$AFS_BASE/logs" \
    "Logs"

# Validation summary
log "Symlink validation summary:"
log "=========================="

symlinks=(
    "$APP_BASE/forecasting/data"
    "$APP_BASE/modelling/cache"
    "$APP_BASE/modelling/predictions"
    "$APP_BASE/scraping/scraped_data"
    "$APP_BASE/logs"
)

all_good=true
for link in "${symlinks[@]}"; do
    if [ -L "$link" ] && [ -d "$link" ]; then
        target=$(readlink "$link")
        log "✓ $link -> $target"
    else
        log "❌ $link (FAILED)"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    log "🎉 All data symlinks created successfully!"
    log "Source code remains in container for optimal performance."
    log "Data directories persisted to Azure File Share."
else
    log "❌ Some symlinks failed to create. Check logs above."
    exit 1
fi

log "Selective symlink initialization completed."
