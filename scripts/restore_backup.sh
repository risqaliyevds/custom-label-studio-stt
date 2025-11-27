#!/bin/bash
#
# Restore Script for Label Studio + Audio Analysis System
# 
# This script restores ALL data from backup:
# - Label Studio data (annotations, projects, tasks)
# - PostgreSQL database
# - Uploaded files (audio, images)
# - ML Backend data
#
# Usage: ./restore_backup.sh <backup-date>
# Example: ./restore_backup.sh 2025-11-27

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DATE="$1"
BACKUP_VOLUME="audio-analysis-backups"
RESTORE_DIR="/tmp/restore_${BACKUP_DATE}"

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if date provided
if [ -z "$BACKUP_DATE" ]; then
    error "Please provide a backup date. Usage: $0 <YYYY-MM-DD>"
fi

# Validate date format
if ! [[ "$BACKUP_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    error "Invalid date format. Use YYYY-MM-DD"
fi

log "========================================="
log "Label Studio FULL Restore"
log "========================================="
log "Backup Date: $BACKUP_DATE"
log "Restore Directory: $RESTORE_DIR"
log ""

# Check if backup exists
log "Checking if backup exists..."
docker run --rm -v ${BACKUP_VOLUME}:/backups alpine ls /backups/${BACKUP_DATE}.zip > /dev/null 2>&1 || \
    error "Backup file ${BACKUP_DATE}.zip not found!"

log "✓ Backup file found!"
log ""

# Confirm with user
echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}WARNING: FULL DATA RESTORE${NC}"
echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}This will STOP all services and restore:${NC}"
echo -e "${YELLOW}  - Label Studio annotations & projects${NC}"
echo -e "${YELLOW}  - PostgreSQL database${NC}"
echo -e "${YELLOW}  - All uploaded files (audio, etc.)${NC}"
echo -e "${YELLOW}  - ML Backend data${NC}"
echo -e "${YELLOW}Current data will be REPLACED!${NC}"
echo -e "${YELLOW}=========================================${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log "Restore cancelled by user"
    exit 0
fi

# Stop services
log "Stopping Docker services..."
docker compose down || warning "Failed to stop services (they might not be running)"
log "✓ Services stopped"
log ""

# Create restore directory
log "Creating restore directory..."
mkdir -p "$RESTORE_DIR"
log "✓ Restore directory created"
log ""

# Extract backup
log "Extracting backup..."
docker run --rm \
    -v ${BACKUP_VOLUME}:/backups \
    -v ${RESTORE_DIR}:/restore \
    alpine sh -c "apk add --no-cache unzip > /dev/null 2>&1 && cd /restore && unzip -q /backups/${BACKUP_DATE}.zip" || \
    error "Failed to extract backup!"
log "✓ Backup extracted"
log ""

# Find the temp directory name
TEMP_DIR=$(ls -d ${RESTORE_DIR}/temp_* 2>/dev/null | head -n 1)
if [ -z "$TEMP_DIR" ]; then
    error "Could not find backup data in extracted files"
fi

log "Backup contents found at: $(basename $TEMP_DIR)"
log ""

# ==========================================================================
# RESTORE CRITICAL DATA - Label Studio & PostgreSQL
# ==========================================================================

# Restore Label Studio data
if [ -d "${TEMP_DIR}/labelstudio_data" ]; then
    log "Restoring Label Studio data (annotations, projects)..."
    docker run --rm \
        -v labelstudio-data:/data \
        -v ${TEMP_DIR}/labelstudio_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore labelstudio_data"
    log "✓ Label Studio data restored"
else
    warning "No labelstudio_data found in backup"
fi

# Restore Label Studio files
if [ -d "${TEMP_DIR}/labelstudio_files" ]; then
    log "Restoring Label Studio files (audio, uploads)..."
    docker run --rm \
        -v labelstudio-files:/data \
        -v ${TEMP_DIR}/labelstudio_files:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore labelstudio_files"
    log "✓ Label Studio files restored"
else
    warning "No labelstudio_files found in backup"
fi

# Restore PostgreSQL data
if [ -d "${TEMP_DIR}/postgres_data" ]; then
    log "Restoring PostgreSQL database..."
    docker run --rm \
        -v labelstudio-postgres-data:/data \
        -v ${TEMP_DIR}/postgres_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore postgres_data"
    log "✓ PostgreSQL data restored"
else
    warning "No postgres_data found in backup"
fi

# ==========================================================================
# RESTORE ML BACKEND DATA
# ==========================================================================

# Restore audio data
if [ -d "${TEMP_DIR}/audio_data" ]; then
    log "Restoring ML Backend audio data..."
    docker run --rm \
        -v audio-analysis-data:/data \
        -v ${TEMP_DIR}/audio_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore audio_data"
    log "✓ Audio data restored"
else
    warning "No audio_data found in backup"
fi

# Restore Redis data
if [ -d "${TEMP_DIR}/redis_data" ]; then
    log "Restoring Redis data..."
    docker run --rm \
        -v audio-analysis-redis:/data \
        -v ${TEMP_DIR}/redis_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore Redis data"
    log "✓ Redis data restored"
else
    warning "No Redis data found in backup"
fi

# Restore Prometheus data
if [ -d "${TEMP_DIR}/prometheus_data" ]; then
    log "Restoring Prometheus data..."
    docker run --rm \
        -v audio-analysis-prometheus:/data \
        -v ${TEMP_DIR}/prometheus_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore Prometheus data"
    log "✓ Prometheus data restored"
else
    warning "No Prometheus data found in backup"
fi

# Restore Grafana data
if [ -d "${TEMP_DIR}/grafana_data" ]; then
    log "Restoring Grafana data..."
    docker run --rm \
        -v audio-analysis-grafana:/data \
        -v ${TEMP_DIR}/grafana_data:/backup:ro \
        alpine sh -c "rm -rf /data/* && cp -r /backup/* /data/" || \
        warning "Failed to restore Grafana data"
    log "✓ Grafana data restored"
else
    warning "No Grafana data found in backup"
fi

# Clean up
log ""
log "Cleaning up temporary files..."
rm -rf "$RESTORE_DIR"
log "✓ Cleanup complete"
log ""

# Start services
log "Starting Docker services..."
docker compose up -d || error "Failed to start services"
log "✓ Services started"
log ""

# Wait for services
log "Waiting for services to become healthy..."
sleep 10

# Display restore summary
log "========================================="
log "FULL RESTORE COMPLETED SUCCESSFULLY!"
log "========================================="
log "Restored from backup: ${BACKUP_DATE}"
log ""
log "Service Status:"
docker compose ps
log ""
log "Access Label Studio at: http://localhost:8080"
log "ML Backend API at: http://localhost:9090"
log ""
log "To view logs: docker compose logs -f"
log "========================================="

exit 0
