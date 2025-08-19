# 📱 VLESS Tester - Social Media Testing

## 🔄 **New Testing Flow Added**

The VLESS Tester now includes comprehensive testing for social media access, following the same pattern as the VMESS Tester.

### **📋 Testing Phases:**

1. **Phase 1: Connection Test**
   - Tests basic VLESS connection (TCP, HTTP, Protocol)
   - Filters working configurations

2. **Phase 2: Iran Access Test**
   - Tests access to Iranian websites
   - Only configs that pass this test proceed

3. **Phase 3: Social Media Access Test** ⭐ **NEW**
   - Tests access to YouTube, Instagram, and Telegram
   - Only configs that pass this test proceed

4. **Phase 4: Download Speed Test**
   - Tests download speed
   - Only configs that pass all previous tests reach this phase

## 🚀 **New Functions Added:**

### **`test_social_media_access_via_xray(link: str)`**
```python
async def test_social_media_access_via_xray(self, link: str) -> Dict[str, bool]:
    """Tests access to social media platforms using Xray"""
    # Returns: {"youtube": bool, "instagram": bool, "telegram": False}
```

**Features:**
- Uses Xray to create HTTP proxy
- Tests YouTube, Instagram, and Telegram access
- Returns detailed results for each platform
- Automatic cleanup of temporary files

### **`filter_configs_by_social_media_access(configs: List[str])`**
```python
async def filter_configs_by_social_media_access(self, configs: List[str]) -> List[str]:
    """Filters configs based on social media access test"""
    # Returns list of configs that pass social media test
```

**Features:**
- Sequential testing to avoid overload
- Detailed logging for each test
- Stores partial results for timeout handling
- Configs must pass at least one social media platform

## 📊 **Enhanced Partial Progress Saving:**

The tester now tracks social media test results:
```python
self.partial_social_ok: List[str] = []  # Configs that pass social media test
```

**Priority Order for Partial Saving:**
1. **Speed OK** - Configs that pass download speed test
2. **Social Media OK** ⭐ **NEW** - Configs that pass social media test
3. **Iran Access OK** - Configs that pass Iran access test
4. **Connection OK** - Configs that pass basic connection test

## 🔧 **Configuration Requirements:**

### **Xray Binary:**
- Must be available in `../Files/xray-bin/`
- Supports both Windows (`xray.exe`) and Linux (`xray`)

### **Test URLs:**
- **YouTube**: `https://www.youtube.com`
- **Instagram**: `https://www.instagram.com`
- **Telegram**: `https://web.telegram.org`

### **Timeout Settings:**
- Social media test timeout: 10 seconds per platform
- Xray startup delay: 0.5 seconds
- Process cleanup timeout: 2 seconds

## 📈 **Benefits:**

- **Comprehensive Testing**: Ensures configs work with blocked social media
- **Quality Filter**: Only high-quality configs proceed to speed testing
- **Real-World Validation**: Tests actual access to commonly blocked services
- **Efficient Processing**: Sequential testing prevents system overload
- **Partial Results**: Saves progress even if testing is interrupted

## 🚨 **Error Handling:**

- **Xray Not Found**: Returns all platforms as inaccessible
- **Connection Failures**: Gracefully handles network errors
- **Timeout Handling**: Continues with next config on timeout
- **Process Cleanup**: Ensures Xray processes are properly terminated

## 📝 **Usage Example:**

```python
# Test social media access for a single config
results = await manager.test_social_media_access_via_xray(vless_link)

# Filter multiple configs by social media access
social_ok_configs = await manager.filter_configs_by_social_media_access(configs)

# Check individual platform results
if results["youtube"]:
    print("YouTube access: ✅")
if results["instagram"]:
    print("Instagram access: ✅")
if results["telegram"]:
    print("Telegram access: ✅")
```

## 🔄 **Integration with Existing Flow:**

The social media testing is seamlessly integrated into the existing VLESS testing pipeline:

1. **Connection Test** → **Iran Access Test** → **Social Media Test** → **Speed Test**
2. Each phase filters configs for the next phase
3. Partial results are saved at each stage
4. Comprehensive logging shows progress through all phases

## 📊 **Logging Output:**

```
📱 شروع تست شبکه‌های اجتماعی برای 150 کانفیگ با دسترسی ایرانی
[1/150] ✅ شبکه‌های اجتماعی قابل دسترسی - پذیرفته شد
  YouTube: True, Instagram: False, Telegram: True
[2/150] ❌ شبکه‌های اجتماعی غیرقابل دسترسی - رد شد
...
نتیجه تست شبکه‌های اجتماعی: 89 از 150 پذیرفته شدند
```

This enhancement ensures that VLESS configurations are thoroughly tested for real-world usability, particularly for accessing commonly blocked social media platforms.
