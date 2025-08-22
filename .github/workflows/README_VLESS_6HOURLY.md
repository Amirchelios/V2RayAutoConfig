# VLESS Tester - 6 Hourly Execution Workflow

## Overview
This workflow automatically runs the VLESS tester every 6 hours to keep the VLESS configurations updated and fresh.

## Schedule
The workflow runs automatically at the following times (UTC):
- **00:00 UTC** (03:30 Tehran time)
- **06:00 UTC** (09:30 Tehran time)  
- **12:00 UTC** (15:30 Tehran time)
- **18:00 UTC** (21:30 Tehran time)

## Cron Expression
```yaml
cron: "0 */6 * * *"
```
- `0` - At minute 0 (top of the hour)
- `*/6` - Every 6 hours
- `* * *` - Every day, every month, every day of week

## Triggers
1. **Automatic Schedule**: Every 6 hours
2. **Manual Trigger**: Via GitHub Actions UI with test mode selection
3. **Push Trigger**: When changes are pushed to main/master branch

## Features

### Automatic Execution
- Runs every 6 hours without manual intervention
- Updates VLESS configurations automatically
- Commits and pushes results to repository

### Manual Control
- Can be triggered manually anytime
- Test mode selection (سریع/کامل)
- Immediate execution for testing

### Smart Concurrency
- Prevents multiple instances from running simultaneously
- Uses branch-specific concurrency groups
- Ensures stable execution

### Comprehensive Logging
- Detailed execution logs
- Artifact uploads for debugging
- GitHub step summaries
- Error handling and reporting

## Workflow Steps

### 1. Setup
- Repository checkout
- Python 3.11 setup
- Dependencies installation
- Directory creation

### 2. Execution
- Source file validation
- VLESS tester execution
- Result verification
- Error handling

### 3. Results Processing
- Output file validation
- Metadata extraction
- Git commit and push
- Artifact upload

### 4. Reporting
- Execution summary
- Status reporting
- Next run information
- Performance metrics

## Output Files

### Generated Files
- `trustlink/trustlink_vless.txt` - Updated VLESS configurations
- `trustlink/.trustlink_vless_metadata.json` - Execution metadata
- `logs/vless_tester.log` - Detailed execution logs

### Artifacts
- Logs and output files
- 7-day retention period
- Available for download from Actions tab

## Configuration

### Timeout
- **90 minutes** maximum execution time
- Optimized for 6-hourly runs
- Prevents hanging executions

### Permissions
- **Contents write** access for commits
- Repository push permissions
- Artifact upload capabilities

### Concurrency
- **Group**: `vless-tester-6hourly-{branch}`
- **Cancel in progress**: `false`
- **Branch isolation**: Separate groups per branch

## Monitoring

### GitHub Actions Tab
- Real-time execution status
- Detailed step-by-step logs
- Artifact downloads
- Manual trigger options

### Notifications
- Success/failure status
- Execution summaries
- Error notifications
- Schedule information

## Benefits

### Automation
- **24/7 Operation**: Runs automatically every 6 hours
- **No Manual Intervention**: Fully automated execution
- **Consistent Updates**: Regular configuration updates

### Reliability
- **Error Handling**: Comprehensive error handling
- **Logging**: Detailed execution logs
- **Artifacts**: Persistent log storage
- **Status Reporting**: Clear execution summaries

### Performance
- **Optimized Timeout**: 90-minute execution limit
- **Concurrency Control**: Prevents conflicts
- **Resource Management**: Efficient resource usage

## Troubleshooting

### Common Issues
1. **Source File Missing**: Check `configs/raw/Vless.txt`
2. **Dependencies**: Verify `vless/requirements.txt`
3. **Permissions**: Ensure workflow has write access
4. **Timeout**: Check execution logs for hanging processes

### Debug Steps
1. Check GitHub Actions logs
2. Download artifacts for analysis
3. Verify source file existence
4. Check Python dependencies
5. Review error messages

## Manual Execution

### Trigger via GitHub Actions
1. Go to **Actions** tab
2. Select **VLESS Tester - 6 Hourly Execution**
3. Click **Run workflow**
4. Choose test mode (سریع/کامل)
5. Click **Run workflow**

### Test Mode Options
- **سریع (Fast)**: Quick execution for testing
- **کامل (Complete)**: Full execution for production

## Integration

### Repository Integration
- Automatic commits on success
- Metadata tracking
- Log preservation
- Artifact management

### Branch Protection
- Works with protected branches
- Requires appropriate permissions
- Maintains branch integrity

## Future Enhancements

### Potential Improvements
1. **Email Notifications**: Success/failure alerts
2. **Slack Integration**: Team notifications
3. **Performance Metrics**: Execution time tracking
4. **Health Checks**: Configuration validation
5. **Rollback Capability**: Previous version restoration

### Monitoring
1. **Execution History**: Track success rates
2. **Performance Trends**: Monitor execution times
3. **Error Patterns**: Identify common issues
4. **Resource Usage**: Optimize resource allocation

## Support

### Documentation
- This README file
- Workflow configuration
- GitHub Actions documentation
- Python script documentation

### Maintenance
- Regular workflow updates
- Dependency updates
- Performance optimization
- Error handling improvements
