#!/bin/bash

# ============================================================================
# Label Studio + Audio ML Backend - Smart Startup Script
# ============================================================================
# This script handles:
# 1. Check if Docker volumes exist with data
# 2. If no volume data but backups exist → restore from latest backup
# 3. If restore fails → try previous backups (up to 3 days)
# 4. Start ALL services: PostgreSQL, Label Studio, ML Backend, Backup
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Volume names - CRITICAL DATA
LABELSTUDIO_DATA_VOLUME="labelstudio-data"
POSTGRES_DATA_VOLUME="labelstudio-postgres-data"
DATA_VOLUME="audio-analysis-data"
BACKUP_VOLUME="audio-analysis-backups"

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

header() {
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================${NC}"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Check if Docker is running
check_docker() {
    if ! docker version > /dev/null 2>&1; then
        error "Docker is not running or not accessible!"
        echo ""
        echo "Possible solutions:"
        echo "  1. Start Docker: sudo systemctl start docker"
        echo "  2. Add user to docker group: sudo usermod -aG docker \$USER"
        echo "  3. Run with sudo: sudo ./start.sh"
        exit 1
    fi
    success "Docker is running ($(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'version unknown'))"
}

# Check if volume exists and has data
check_volume_has_data() {
    local volume_name="$1"
    
    # Check if volume exists
    if ! docker volume inspect "$volume_name" > /dev/null 2>&1; then
        return 1
    fi
    
    # Check if volume has data (more than just empty directory)
    local file_count=$(docker run --rm -v ${volume_name}:/data alpine sh -c "find /data -type f 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    
    if [ "$file_count" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Get list of available backups sorted by date (newest first)
get_available_backups() {
    # Check if backup volume exists
    if ! docker volume inspect "$BACKUP_VOLUME" > /dev/null 2>&1; then
        echo ""
        return
    fi
    
    # List backup files sorted by date (newest first)
    docker run --rm -v ${BACKUP_VOLUME}:/backups alpine sh -c \
        "ls -1 /backups/*.zip 2>/dev/null | sort -r | xargs -I{} basename {} .zip" 2>/dev/null || echo ""
}

# Restore from a specific backup
restore_from_backup() {
    local backup_date="$1"
    local backup_file="${backup_date}.zip"
    
    info "Attempting to restore from backup: ${backup_date}"
    
    # Create temp restore directory
    local restore_dir="/tmp/restore_${backup_date}_$$"
    mkdir -p "$restore_dir"
    
    # Extract backup
    if ! docker run --rm \
        -v ${BACKUP_VOLUME}:/backups:ro \
        -v ${restore_dir}:/restore \
        alpine sh -c "apk add --no-cache unzip > /dev/null 2>&1 && cd /restore && unzip -q /backups/${backup_file}" 2>/dev/null; then
        warn "Failed to extract backup ${backup_date}"
        rm -rf "$restore_dir"
        return 1
    fi
    
    # Find the temp directory in extracted backup
    local temp_dir=$(ls -d ${restore_dir}/temp_* 2>/dev/null | head -n 1)
    if [ -z "$temp_dir" ]; then
        warn "Invalid backup structure in ${backup_date}"
        rm -rf "$restore_dir"
        return 1
    fi
    
    # Restore Label Studio data
    if [ -d "${temp_dir}/labelstudio_data" ]; then
        info "Restoring Label Studio data..."
        docker run --rm \
            -v labelstudio-data:/data \
            -v ${temp_dir}/labelstudio_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore Label Studio files
    if [ -d "${temp_dir}/labelstudio_files" ]; then
        info "Restoring Label Studio files..."
        docker run --rm \
            -v labelstudio-files:/data \
            -v ${temp_dir}/labelstudio_files:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore PostgreSQL data
    if [ -d "${temp_dir}/postgres_data" ]; then
        info "Restoring PostgreSQL database..."
        docker run --rm \
            -v labelstudio-postgres-data:/data \
            -v ${temp_dir}/postgres_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore audio data
    if [ -d "${temp_dir}/audio_data" ]; then
        info "Restoring audio data..."
        docker run --rm \
            -v ${DATA_VOLUME}:/data \
            -v ${temp_dir}/audio_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore Redis data
    if [ -d "${temp_dir}/redis_data" ]; then
        info "Restoring Redis data..."
        docker run --rm \
            -v audio-analysis-redis:/data \
            -v ${temp_dir}/redis_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore Prometheus data
    if [ -d "${temp_dir}/prometheus_data" ]; then
        info "Restoring Prometheus data..."
        docker run --rm \
            -v audio-analysis-prometheus:/data \
            -v ${temp_dir}/prometheus_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Restore Grafana data
    if [ -d "${temp_dir}/grafana_data" ]; then
        info "Restoring Grafana data..."
        docker run --rm \
            -v audio-analysis-grafana:/data \
            -v ${temp_dir}/grafana_data:/backup:ro \
            alpine sh -c "cp -r /backup/* /data/ 2>/dev/null || true" || true
    fi
    
    # Cleanup
    rm -rf "$restore_dir"
    
    success "Restored from backup: ${backup_date}"
    return 0
}

# Smart restore - try backups in order until one works
smart_restore() {
    header "Smart Backup Restore"
    
    local backups=$(get_available_backups)
    
    if [ -z "$backups" ]; then
        warn "No backups found. Starting with fresh data."
        return 1
    fi
    
    info "Available backups:"
    echo "$backups" | while read backup; do
        echo "  - ${backup}"
    done
    echo ""
    
    # Try each backup in order (newest first)
    local restored=false
    for backup_date in $backups; do
        if [ -n "$backup_date" ]; then
            info "Trying backup: ${backup_date}"
            if restore_from_backup "$backup_date"; then
                success "Successfully restored from ${backup_date}"
                restored=true
                break
            else
                warn "Failed to restore from ${backup_date}, trying next..."
            fi
        fi
    done
    
    if [ "$restored" = true ]; then
        return 0
    else
        warn "All backup restore attempts failed. Starting with fresh data."
        return 1
    fi
}

# ============================================================================
# MAIN STARTUP LOGIC
# ============================================================================

main() {
    header "🚀 Label Studio + Audio ML Backend - Starting"
    
    log "Working directory: $SCRIPT_DIR"
    echo ""
    
    # Step 1: Check Docker
    header "Step 1: Checking Prerequisites"
    check_docker
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        error ".env file not found!"
        echo "Please create a .env file with your configuration (GEMINI_API_KEY, etc.)"
        exit 1
    fi
    success ".env file found"
    
    # Step 2: Check existing data
    header "Step 2: Checking Data State"
    
    local has_volume_data=false
    local has_backups=false
    
    # Check if Label Studio data volume has data (most important)
    if check_volume_has_data "$LABELSTUDIO_DATA_VOLUME"; then
        success "Label Studio data volume exists with data"
        has_volume_data=true
    elif check_volume_has_data "$POSTGRES_DATA_VOLUME"; then
        success "PostgreSQL data volume exists with data"
        has_volume_data=true
    elif check_volume_has_data "$DATA_VOLUME"; then
        success "ML Backend data volume exists with data"
        has_volume_data=true
    else
        warn "No existing data volumes found"
    fi
    
    # Check if backups exist
    local backups=$(get_available_backups)
    if [ -n "$backups" ]; then
        local backup_count=$(echo "$backups" | wc -l)
        success "Found ${backup_count} backup(s) available"
        has_backups=true
    else
        warn "No backups found"
    fi
    
    # Step 3: Decide whether to restore
    header "Step 3: Data Recovery Decision"
    
    if [ "$has_volume_data" = true ]; then
        success "Volume has existing data - using current data"
        info "Skipping backup restore (data already exists)"
    elif [ "$has_backups" = true ]; then
        info "No volume data found, but backups are available"
        info "Attempting smart restore from backups..."
        smart_restore
    else
        warn "No existing data and no backups found"
        info "Starting with fresh empty volumes"
    fi
    
    # Step 4: Stop any existing services
    header "Step 4: Stopping Existing Services"
    
    info "Stopping any running containers..."
    docker compose down 2>/dev/null || true
    
    # Also stop any local processes
    pkill -f enhanced_api.py 2>/dev/null || true
    pkill -f simple_api.py 2>/dev/null || true
    
    success "Existing services stopped"
    
    # Step 5: Build if needed
    header "Step 5: Building Docker Image"

    if docker images | grep -q "labelstudio-audio-api"; then
        info "Docker image exists"
        read -t 5 -p "Rebuild image? (y/N, 5s timeout): " rebuild || rebuild="n"
        echo ""
        if [[ "$rebuild" =~ ^[Yy]$ ]]; then
            info "Building Docker image..."
            docker build -t labelstudio-audio-api:latest .
            success "Docker image built"
        else
            info "Using existing image"
        fi
    else
        info "Building Docker image for first time..."
        docker build -t labelstudio-audio-api:latest .
        success "Docker image built"
    fi
    
    # Step 6: Start all services
    header "Step 6: Starting All Services"
    
    info "Starting PostgreSQL database..."
    docker compose up -d postgres
    
    # Wait for PostgreSQL to be healthy
    info "Waiting for PostgreSQL to be ready..."
    local pg_attempts=0
    while [ $pg_attempts -lt 30 ]; do
        if docker compose exec -T postgres pg_isready -U labelstudio > /dev/null 2>&1; then
            success "PostgreSQL is ready!"
            break
        fi
        echo -n "."
        sleep 2
        pg_attempts=$((pg_attempts + 1))
    done
    echo ""
    
    info "Starting Label Studio..."
    docker compose up -d label-studio
    
    info "Starting ML Backend API..."
    docker compose up -d labelstudio-audio-api
    
    info "Starting backup service..."
    docker compose up -d backup-service
    
    # Wait for services to be ready
    info "Waiting for all services to start..."
    sleep 10
    
    # Step 7: Health check
    header "Step 7: Health Check"
    
    local max_attempts=30
    local attempt=1
    local api_healthy=false
    local ls_healthy=false
    
    info "Checking ML Backend API..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:9090/health > /dev/null 2>&1; then
            api_healthy=true
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    
    if [ "$api_healthy" = true ]; then
        success "ML Backend API is healthy!"
    else
        warn "ML Backend API health check timeout"
    fi
    
    info "Checking Label Studio..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
            ls_healthy=true
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    
    if [ "$ls_healthy" = true ]; then
        success "Label Studio is healthy!"
    else
        warn "Label Studio may still be starting (this is normal on first run)"
    fi
    
    # Step 8: Display status
    header "🎉 Startup Complete!"
    
    echo ""
    echo -e "${GREEN}Services Status:${NC}"
    docker compose ps
    echo ""
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}       ACCESS YOUR SERVICES            ${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "  🏷️  ${GREEN}Label Studio:${NC}     http://localhost:8080"
    echo -e "      Default login:  admin@admin.com / admin123"
    echo ""
    echo -e "  🤖 ${GREEN}ML Backend API:${NC}   http://localhost:9090"
    echo -e "  ❤️  Health Check:    http://localhost:9090/health"
    echo -e "  📊 API Docs:        http://localhost:9090/docs"
    echo ""
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}       DATA SAFETY INFORMATION         ${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "  💾 ${GREEN}All data is stored in Docker volumes:${NC}"
    echo "     - labelstudio-data (annotations, projects)"
    echo "     - labelstudio-postgres-data (database)"
    echo "     - labelstudio-files (uploaded audio files)"
    echo ""
    echo -e "  🔄 ${GREEN}Automated Backups:${NC}"
    echo "     - Schedule: Daily at 00:00 UTC (5:00 AM UTC+5)"
    echo "     - Retention: 3 days rolling window"
    echo "     - Includes: ALL annotations, audio files, database"
    echo ""
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}       USEFUL COMMANDS                 ${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo "  View all logs:       docker compose logs -f"
    echo "  View Label Studio:   docker compose logs -f label-studio"
    echo "  View ML Backend:     docker compose logs -f labelstudio-audio-api"
    echo "  Manual backup:       docker exec labelstudio-backup /backup.sh"
    echo "  Stop all:            docker compose down"
    echo "  Restore backup:      ./scripts/restore_backup.sh YYYY-MM-DD"
    echo ""
    
    success "All services are running! 🚀"
    echo ""
    echo -e "${GREEN}Open Label Studio at: ${CYAN}http://localhost:8080${NC}"
}

# Run main function
main "$@"
