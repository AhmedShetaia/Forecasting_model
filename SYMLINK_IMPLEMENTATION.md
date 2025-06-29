# Selective Symlinks Implementation Guide

## Overview

This implementation uses **selective symlinks** to persist only data directories to Azure File Share while keeping source code in the container for optimal performance.

## Architecture

### Container Structure
```
/app/ (container working directory)
├── forecasting/ (actual directory - code in container)
│   ├── src/ (actual directory)
│   ├── config/ (actual directory)
│   └── data/ (symlink → /mnt/fileshare/forecasting/data/)
├── modelling/ (actual directory - code in container)
│   ├── src/ (actual directory)
│   ├── cache/ (symlink → /mnt/fileshare/modelling/cache/)
│   └── predictions/ (symlink → /mnt/fileshare/modelling/predictions/)
└── scraping/ (actual directory - code in container)
    ├── src/ (actual directory)
    └── scraped_data/ (symlink → /mnt/fileshare/scraping/scraped_data/)
```

### Azure File Share Structure
```
/mnt/fileshare/
├── forecasting/
│   └── data/
│       ├── input/
│       └── output/
├── modelling/
│   ├── cache/
│   │   ├── sarima_params/
│   │   └── time_moe_cache/
│   └── predictions/
└── scraping/
    └── scraped_data/
```

## Benefits

1. **Performance**: Source code executes from container (fast local access)
2. **Persistence**: Data survives container restarts
3. **Cost Efficiency**: Minimal Azure File Share usage
4. **Simplicity**: Clean separation of code vs data concerns

## Development Workflow

### Local Development
```bash
# Use local file share simulation
docker-compose up --build
```

### Production Deployment
```bash
# Use Azure File Share
docker-compose -f docker-compose.prod.yml up --build
```

## Key Files

- `scripts/init_data_symlinks.sh` - Creates selective symlinks on container startup
- `run_pipeline.py` - Simplified pipeline orchestrator (no AFS-specific code)
- `docker-compose.yml` - Local development with `local_fileshare/`
- `docker-compose.prod.yml` - Production with Azure File Share

## Automatic Initialization

The Dockerfile automatically:
1. Copies source code to container
2. Sets up symlink initialization script
3. Creates entrypoint that initializes symlinks before running pipeline
4. Preserves all existing constants and import paths

## No Code Changes Required

- All existing constants files remain unchanged
- Import paths stay the same
- Module structure preserved
- Data operations transparently use symlinks

## Troubleshooting

### Check Symlinks
```bash
# Inside container
ls -la forecasting/data        # Should show symlink
ls -la modelling/cache         # Should show symlink
ls -la modelling/predictions   # Should show symlink
ls -la scraping/scraped_data   # Should show symlink
```

### Verify Data Persistence
```bash
# Create test file
echo "test" > forecasting/data/test.txt

# Restart container
docker-compose restart

# Check file still exists
cat forecasting/data/test.txt
```

### Manual Symlink Setup
If symlinks fail, run manually:
```bash
/usr/local/bin/init_data_symlinks.sh
```

## Migration from Previous Implementation

1. **No changes needed** in source code
2. **Data automatically persists** via symlinks
3. **Performance improved** (code execution faster)
4. **Costs reduced** (less file share usage)

This implementation provides the best of both worlds: fast code execution with persistent data storage.
