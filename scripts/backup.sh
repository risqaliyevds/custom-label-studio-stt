#!/bin/sh
#
# Automated Backup Script for Label Studio + Audio Analysis System
# 
# This script backs up ALL critical data:
# - Label Studio data (annotations, projects, tasks)
# - PostgreSQL database (all Label Studio metadata)
# - Uploaded audio files
# - ML Backend data
# - Logs
#
# Schedule: Daily at 00:00 UTC (5:00 AM UTC+5)
# Retention: 3 days rolling window

set -e

# Configuration
BACKUP_DIR="/backups"
DATA_DIR="/data"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-3}"
TIMESTAMP=$(date +%Y-%m-%d)
BACKUP_NAME="${TIMESTAMP}.zip"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
TEMP_BACKUP_DIR="${BACKUP_DIR}/temp_${TIMESTAMP}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}" || error_exit "Failed to create backup directory"

log "========================================="
log "Starting FULL backup process: ${TIMESTAMP}"
log "========================================="

# Check if backup already exists for today
if [ -f "${BACKUP_PATH}" ]; then
    log "Backup for ${TIMESTAMP} already exists. Removing old backup..."
    rm -f "${BACKUP_PATH}"
fi

# Create temporary directory for staging backup
log "Creating temporary backup directory..."
mkdir -p "${TEMP_BACKUP_DIR}" || error_exit "Failed to create temporary directory"

# ==========================================================================
# CRITICAL DATA - Label Studio & PostgreSQL
# ==========================================================================

# Backup Label Studio data (annotations, projects, settings)
if [ -d "${DATA_DIR}/labelstudio_data" ]; then
    log "Backing up Label Studio data (annotations, projects)..."
    cp -r "${DATA_DIR}/labelstudio_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup labelstudio_data"
else
    log "WARNING: labelstudio_data directory not found"
fi

# Backup Label Studio files (uploaded audio, images, etc.)
if [ -d "${DATA_DIR}/labelstudio_files" ]; then
    log "Backing up Label Studio files (audio, uploads)..."
    cp -r "${DATA_DIR}/labelstudio_files" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup labelstudio_files"
else
    log "WARNING: labelstudio_files directory not found"
fi

# Backup PostgreSQL data (database files)
if [ -d "${DATA_DIR}/postgres_data" ]; then
    log "Backing up PostgreSQL database..."
    cp -r "${DATA_DIR}/postgres_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup postgres_data"
else
    log "WARNING: postgres_data directory not found"
fi

# ==========================================================================
# ML BACKEND DATA
# ==========================================================================

# Backup audio data
if [ -d "${DATA_DIR}/audio_data" ]; then
    log "Backing up ML Backend audio data..."
    cp -r "${DATA_DIR}/audio_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup audio_data"
else
    log "WARNING: audio_data directory not found"
fi

# Backup Redis data
if [ -d "${DATA_DIR}/redis_data" ]; then
    log "Backing up Redis data..."
    cp -r "${DATA_DIR}/redis_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup redis_data"
else
    log "WARNING: redis_data directory not found"
fi

# Backup Prometheus data
if [ -d "${DATA_DIR}/prometheus_data" ]; then
    log "Backing up Prometheus data..."
    cp -r "${DATA_DIR}/prometheus_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup prometheus_data"
else
    log "WARNING: prometheus_data directory not found"
fi

# Backup Grafana data
if [ -d "${DATA_DIR}/grafana_data" ]; then
    log "Backing up Grafana data..."
    cp -r "${DATA_DIR}/grafana_data" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup grafana_data"
else
    log "WARNING: grafana_data directory not found"
fi

# Backup logs
if [ -d "${DATA_DIR}/logs" ]; then
    log "Backing up logs..."
    cp -r "${DATA_DIR}/logs" "${TEMP_BACKUP_DIR}/" || log "WARNING: Failed to backup logs"
else
    log "WARNING: logs directory not found"
fi

# Create metadata file
log "Creating backup metadata..."
cat > "${TEMP_BACKUP_DIR}/backup_metadata.txt" << EOF
===============================================
LABEL STUDIO FULL BACKUP
===============================================
Backup Date: ${TIMESTAMP}
Backup Time: $(date '+%Y-%m-%d %H:%M:%S %Z')
Hostname: $(hostname)

Backup Contents:
$(du -sh ${TEMP_BACKUP_DIR}/* 2>/dev/null || echo "N/A")

CRITICAL DATA INCLUDED:
- labelstudio_data: All annotations, projects, tasks
- labelstudio_files: All uploaded audio/media files
- postgres_data: PostgreSQL database (all metadata)
- audio_data: ML Backend processed data
- logs: Application logs

System Information:
$(uname -a)

Disk Space:
$(df -h ${BACKUP_DIR})

RESTORE INSTRUCTIONS:
1. Stop all services: docker compose down
2. Run restore script: ./scripts/restore_backup.sh ${TIMESTAMP}
3. Start services: ./start.sh
===============================================
EOF

# Create ZIP archive
log "Creating ZIP archive..."
cd "${BACKUP_DIR}"
zip -r "${BACKUP_NAME}" "temp_${TIMESTAMP}" > /dev/null 2>&1 || error_exit "Failed to create ZIP archive"

# Remove temporary directory
log "Cleaning up temporary files..."
rm -rf "${TEMP_BACKUP_DIR}"

# Calculate backup size
BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
log "Backup created successfully: ${BACKUP_NAME} (${BACKUP_SIZE})"

# Remove old backups (keep only last N days)
log "========================================="
log "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."
log "========================================="

DELETED_COUNT=0
for backup_file in ${BACKUP_DIR}/*.zip; do
    if [ -f "$backup_file" ]; then
        backup_date=$(basename "$backup_file" .zip)
        
        # Calculate age in days
        if [ -n "$backup_date" ] && [ "$backup_date" != "*" ]; then
            # Convert date to seconds since epoch for comparison
            backup_epoch=$(date -d "$backup_date" +%s 2>/dev/null || echo 0)
            current_epoch=$(date +%s)
            age_days=$(( (current_epoch - backup_epoch) / 86400 ))
            
            if [ $age_days -gt $RETENTION_DAYS ]; then
                log "Deleting old backup: $(basename $backup_file) (${age_days} days old)"
                rm -f "$backup_file"
                DELETED_COUNT=$((DELETED_COUNT + 1))
            else
                log "Keeping backup: $(basename $backup_file) (${age_days} days old)"
            fi
        fi
    fi
done

log "Deleted ${DELETED_COUNT} old backup(s)"

# List current backups
log "========================================="
log "Current backups in ${BACKUP_DIR}:"
log "========================================="
ls -lh ${BACKUP_DIR}/*.zip 2>/dev/null || log "No backups found"

# Calculate total backup size
TOTAL_SIZE=$(du -sh ${BACKUP_DIR} | cut -f1)
log "========================================="
log "Total backup storage used: ${TOTAL_SIZE}"
log "FULL BACKUP COMPLETED SUCCESSFULLY!"
log "========================================="

exit 0
