# 🚀 GitHub Actions - Persistent Healthy Configs System

## 📋 Overview

This document explains how the Persistent Healthy Configs system works specifically in the GitHub Actions environment.

## 🔄 How It Works in GitHub Actions

### 1. **Commit-Based Cleanup**
- **Local Development**: Cleanup happens every 10 days
- **GitHub Actions**: Cleanup happens on every new commit
- **Reason**: GitHub Actions runners don't persist files between runs, so we use commit SHA to detect changes

### 2. **Automatic Detection**
- The system automatically detects if it's running in GitHub Actions
- Uses environment variables: `GITHUB_ACTIONS`, `GITHUB_SHA`, `GITHUB_RUN_ID`
- Compares current commit SHA with the last stored SHA

### 3. **Cleanup Triggers**
```python
# GitHub Actions: Cleanup on new commit
if GITHUB_ACTIONS:
    if last_commit_sha != current_commit_sha:
        cleanup_persistent_healthy()
        # Reset metadata with new commit info
```

## 📁 Files Created

### **Persistent Configs File**
- **Path**: `configs/PersistentHealthy.txt`
- **Content**: All tested and healthy configurations
- **Format**: One config per line

### **Metadata File**
- **Path**: `configs/.persistent_healthy_metadata.json`
- **Content**: Cleanup history and commit information
- **Example**:
```json
{
  "last_cleanup": "2024-01-15T10:30:00",
  "total_cleanups": 5,
  "github_actions": true,
  "last_commit_sha": "a1b2c3d4",
  "last_run_id": "1234567890"
}
```

## 🚦 Workflow

### **Step 1: Environment Detection**
```python
GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
GITHUB_SHA = os.getenv('GITHUB_SHA', '')
GITHUB_RUN_ID = os.getenv('GITHUB_RUN_ID', '')
```

### **Step 2: Cleanup Decision**
```python
def should_cleanup_persistent_healthy():
    if GITHUB_ACTIONS:
        # Check if new commit
        if last_commit_sha != current_commit_sha:
            return True
        return False
    else:
        # Local: time-based cleanup
        return days_since_cleanup >= 10
```

### **Step 3: Health Check Integration**
```python
# After health checks complete
if ENABLE_HEALTH_CHECK and healthy_union:
    merge_and_update_persistent_healthy(healthy_union)
```

## 📊 Benefits in GitHub Actions

### **1. Automatic Fresh Start**
- Each new commit gets a clean slate
- Prevents accumulation of stale configurations
- Ensures quality maintenance

### **2. Commit Tracking**
- Know exactly when cleanup happened
- Track which commit triggered cleanup
- Maintain audit trail

### **3. Environment Awareness**
- Different behavior for local vs. CI
- Optimized for GitHub Actions constraints
- Maintains local development experience

## 🔧 Configuration

### **Environment Variables**
```bash
# Automatically set by GitHub Actions
GITHUB_ACTIONS=true
GITHUB_SHA=a1b2c3d4e5f6...
GITHUB_RUN_ID=1234567890

# Customizable
CLEANUP_INTERVAL_DAYS=10  # Only used locally
```

### **File Paths**
```python
PERSISTENT_HEALTHY_FILE = 'configs/PersistentHealthy.txt'
PERSISTENT_HEALTHY_METADATA_FILE = 'configs/.persistent_healthy_metadata.json'
```

## 📝 Logging Examples

### **New Commit Detected**
```
INFO - Running in GitHub Actions environment (Commit: a1b2c3d4, Run: 1234567890)
INFO - New commit detected - will cleanup persistent healthy configs
INFO - GitHub Actions cleanup completed. Commit SHA: a1b2c3d4, Run ID: 1234567890
```

### **Same Commit**
```
INFO - Running in GitHub Actions environment (Commit: a1b2c3d4, Run: 1234567890)
INFO - Same commit - no cleanup needed
```

## 🚨 Important Notes

### **1. File Persistence**
- Files are only available during the GitHub Actions run
- Must be committed to repository to persist between runs
- Consider using artifacts or releases for long-term storage

### **2. Cleanup Frequency**
- **Local**: Every 10 days
- **GitHub Actions**: Every new commit
- This ensures fresh start on each deployment

### **3. Performance**
- Cleanup is fast and efficient
- Only processes new healthy configs
- Minimal impact on overall execution time

## 🔍 Troubleshooting

### **Common Issues**

#### **1. Cleanup Not Happening**
- Check if `GITHUB_ACTIONS` environment variable is set
- Verify commit SHA comparison logic
- Check metadata file permissions

#### **2. Configs Not Accumulating**
- Ensure health checks are enabled
- Check if `healthy_union` contains configs
- Verify file write permissions

#### **3. Metadata File Issues**
- Check JSON format validity
- Verify file encoding (UTF-8)
- Ensure directory exists before writing

### **Debug Commands**
```bash
# Check environment variables
echo "GITHUB_ACTIONS: $GITHUB_ACTIONS"
echo "GITHUB_SHA: $GITHUB_SHA"
echo "GITHUB_RUN_ID: $GITHUB_RUN_ID"

# Check file contents
cat configs/.persistent_healthy_metadata.json
wc -l configs/PersistentHealthy.txt
```

## 📈 Future Enhancements

### **1. Artifact Storage**
- Store persistent configs as GitHub artifacts
- Download previous configs at start of run
- Merge with new configs before cleanup

### **2. Smart Cleanup**
- Keep some percentage of old configs
- Age-based filtering
- Quality scoring system

### **3. Cross-Run Persistence**
- Use GitHub API to store configs
- Database integration
- Cloud storage options

---

## 🤝 Contributing

When modifying the persistent healthy configs system:

1. **Test locally first** - Ensure local behavior unchanged
2. **Test in GitHub Actions** - Verify CI behavior
3. **Update documentation** - Keep this README current
4. **Consider backward compatibility** - Don't break existing functionality

## 📞 Support

For issues or questions about the persistent healthy configs system:

1. Check the logs for error messages
2. Verify environment variables are set correctly
3. Review the metadata file for corruption
4. Create an issue with detailed error information
