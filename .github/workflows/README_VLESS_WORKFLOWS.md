# VLESS Tester Workflows - Complete Guide

## Overview
This repository contains multiple GitHub Actions workflows for the VLESS tester, each designed for different execution frequencies and use cases.

## Available Workflows

### 1. VLESS Tester - 6 Hourly Execution
**File**: `vless-tester-6hourly.yml`

**Schedule**: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
**Purpose**: Frequent updates for fresh configurations
**Best For**: Active environments requiring regular updates

**Features**:
- ✅ Automatic execution every 6 hours
- ✅ 90-minute timeout
- ✅ Manual trigger with test mode selection
- ✅ Comprehensive logging and artifacts
- ✅ Automatic commit and push

### 2. VLESS Tester - Hourly Execution
**File**: `vless-tester-hourly.yml`

**Schedule**: Every hour (currently disabled)
**Purpose**: Very frequent updates (disabled by default)
**Best For**: Development and testing (manual execution)

**Features**:
- ⚠️ Hourly execution (currently commented out)
- ✅ Manual trigger available
- ✅ Push trigger on main/master
- ✅ Test mode selection
- ✅ Comprehensive error handling

### 3. VLESS Tester - Weekly Execution
**File**: `vless-tester-weekly.yml`

**Schedule**: Every Sunday at 03:00 UTC (06:30 Tehran)
**Purpose**: Weekly maintenance and updates
**Best For**: Stable environments with weekly updates

**Features**:
- ✅ Weekly execution (Sundays)
- ✅ 120-minute timeout for comprehensive testing
- ✅ Manual trigger with test mode selection
- ✅ Push trigger on VLESS-related changes
- ✅ Detailed execution summaries

## Workflow Comparison

| Feature | 6-Hourly | Hourly | Weekly |
|---------|----------|---------|---------|
| **Schedule** | Every 6 hours | Every hour | Weekly (Sunday) |
| **Auto-run** | ✅ Enabled | ⚠️ Disabled | ✅ Enabled |
| **Timeout** | 90 min | Default | 120 min |
| **Frequency** | High | Very High | Low |
| **Resource Usage** | Medium | High | Low |
| **Best Use Case** | Active updates | Development | Maintenance |

## Recommended Usage

### For Production (Active Updates)
**Use**: `vless-tester-6hourly.yml`
- Provides fresh configurations every 6 hours
- Balanced resource usage
- Regular updates without overwhelming the system

### For Development (Testing)
**Use**: `vless-tester-hourly.yml`
- Manual execution when needed
- Quick testing and validation
- No automatic resource consumption

### For Maintenance (Weekly Updates)
**Use**: `vless-tester-weekly.yml`
- Comprehensive weekly updates
- Longer execution time for thorough testing
- Stable, predictable schedule

## Configuration Details

### Cron Expressions

#### 6-Hourly
```yaml
cron: "0 */6 * * *"
# Runs at: 00:00, 06:00, 12:00, 18:00 UTC daily
```

#### Hourly (Disabled)
```yaml
# cron: "0 * * * *"
# Runs at: Every hour (currently commented out)
```

#### Weekly
```yaml
cron: "0 3 * * 0"
# Runs at: 03:00 UTC every Sunday
```

### Time Zones
- **UTC**: All cron schedules are in UTC
- **Tehran**: UTC +3:30 (Iran Standard Time)
- **Conversion**: Add 3:30 to UTC times for Tehran time

## Execution Triggers

### Automatic Schedule
- **6-Hourly**: Every 6 hours automatically
- **Weekly**: Every Sunday at 03:00 UTC automatically
- **Hourly**: Currently disabled

### Manual Trigger
All workflows support manual execution via:
1. GitHub Actions tab
2. Workflow selection
3. "Run workflow" button
4. Test mode selection (سریع/کامل)

### Push Trigger
- **6-Hourly**: Triggers on any push to main/master
- **Weekly**: Triggers only on VLESS-related changes
- **Hourly**: Triggers on any push to main/master

## Test Modes

### سریع (Fast Mode)
- Quick execution
- Basic testing
- Suitable for development
- Faster completion

### کامل (Complete Mode)
- Comprehensive testing
- Full validation
- Production-ready
- Longer execution time

## Output and Results

### Generated Files
All workflows generate the same output structure:
```
trustlink/
├── trustlink_vless.txt          # Updated VLESS configurations
└── .trustlink_vless_metadata.json  # Execution metadata

logs/
└── vless_tester.log            # Detailed execution logs
```

### Artifacts
- **6-Hourly**: 7-day retention
- **Weekly**: 7-day retention
- **Hourly**: 7-day retention

### Git Integration
- Automatic commits on success
- Metadata tracking
- Log preservation
- Branch protection compatible

## Monitoring and Debugging

### GitHub Actions Tab
- Real-time execution status
- Step-by-step logs
- Artifact downloads
- Manual trigger options

### Log Analysis
1. **Execution Logs**: Check `logs/vless_tester.log`
2. **Artifacts**: Download from Actions tab
3. **Metadata**: Review `.trustlink_vless_metadata.json`
4. **Git History**: Check commit messages

### Common Issues
1. **Source File Missing**: Verify `configs/raw/Vless.txt`
2. **Dependencies**: Check `vless/requirements.txt`
3. **Permissions**: Ensure workflow has write access
4. **Timeout**: Review execution logs for hanging processes

## Performance Optimization

### Resource Management
- **6-Hourly**: 90-minute timeout (balanced)
- **Weekly**: 120-minute timeout (comprehensive)
- **Hourly**: Default timeout (flexible)

### Concurrency Control
- Branch-specific concurrency groups
- Prevents multiple instances
- Stable execution environment

### Error Handling
- Comprehensive error logging
- Graceful failure handling
- Artifact preservation
- Status reporting

## Best Practices

### For Active Environments
1. Use **6-Hourly** workflow for regular updates
2. Monitor execution success rates
3. Review logs for performance issues
4. Adjust timeout if needed

### For Development
1. Use **Hourly** workflow for testing
2. Manual execution when needed
3. Quick validation of changes
4. No automatic resource consumption

### For Maintenance
1. Use **Weekly** workflow for comprehensive updates
2. Longer execution time for thorough testing
3. Stable, predictable schedule
4. Detailed execution summaries

## Future Enhancements

### Planned Improvements
1. **Email Notifications**: Success/failure alerts
2. **Slack Integration**: Team notifications
3. **Performance Metrics**: Execution time tracking
4. **Health Checks**: Configuration validation
5. **Rollback Capability**: Previous version restoration

### Monitoring Features
1. **Execution History**: Track success rates
2. **Performance Trends**: Monitor execution times
3. **Error Patterns**: Identify common issues
4. **Resource Usage**: Optimize resource allocation

## Support and Maintenance

### Documentation
- This README file
- Individual workflow documentation
- GitHub Actions documentation
- Python script documentation

### Regular Maintenance
- Workflow updates
- Dependency updates
- Performance optimization
- Error handling improvements

### Troubleshooting
- Common issue resolution
- Debug procedures
- Performance optimization
- Error analysis

## Conclusion

The VLESS tester workflows provide flexible automation options for different use cases:

- **6-Hourly**: Best for active production environments
- **Weekly**: Best for maintenance and comprehensive updates
- **Hourly**: Best for development and testing

Choose the workflow that best fits your requirements and resource constraints. All workflows maintain the same high-quality output and comprehensive logging capabilities.
