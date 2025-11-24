# Installation Guide - Abode Security Integration

Complete step-by-step instructions for installing the Abode Security integration for Home Assistant.

## Table of Contents

- [HACS Installation](#hacs-installation-recommended)
- [Manual Installation](#manual-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Upgrading](#upgrading)

## HACS Installation (Recommended)

HACS (Home Assistant Community Store) is the easiest way to install the integration.

### Prerequisites

- Home Assistant 2024.1 or later
- HACS installed and configured
- Abode account credentials

### Installation Steps

1. **Open HACS**
   - In Home Assistant, go to **Settings** → **Devices & Services** → **HACS**
   - Or click the HACS icon in the sidebar

2. **Search for Abode Security**
   - Click the **+** button in the bottom right corner
   - Search for "Abode Security"
   - Select the integration from the results

3. **Download the Integration**
   - Click **Download**
   - Wait for the download to complete
   - A dialog will appear asking to reload Home Assistant
   - Click **Reload** (or manually restart if preferred)

4. **Add the Integration**
   - Go to **Settings** → **Devices & Services** → **Create Integration**
   - Search for "Abode Security"
   - Click the integration card
   - Enter your Abode credentials:
     - **Email**: Your Abode account email
     - **Password**: Your Abode account password
   - Click **Next**

5. **Configure Options** (Optional)
   - Choose polling settings (optional)
   - Click **Create**

6. **Wait for Setup**
   - Home Assistant will initialize the integration
   - Devices will appear in Home Assistant within a few seconds
   - Check notifications for any errors

### What Gets Installed

The HACS installation includes:
- Integration code (`custom_components/abode_security/`)
- Configuration files
- Service definitions
- Diagnostic tools
- Localization support

## Manual Installation

Use manual installation if:
- You prefer to manage the integration directly
- HACS is not available in your environment
- You want to use development versions

### Prerequisites

- Home Assistant 2024.1 or later
- SSH or file access to Home Assistant
- Abode account credentials

### Installation Steps

1. **Clone or Download the Repository**

   Using git:
   ```bash
   git clone https://github.com/molant/abode-security.git ~/abode-security
   cd ~/abode-security
   ```

   Or download the ZIP file:
   - Visit https://github.com/molant/abode-security
   - Click **Code** → **Download ZIP**
   - Extract to a temporary directory

2. **Copy the Integration Files**

   Find your Home Assistant `custom_components` directory:
   - For Docker: `/config/custom_components/`
   - For standalone: `~/.homeassistant/custom_components/`
   - For add-on: `/homeassistant/custom_components/`

   Copy the integration:
   ```bash
   cp -r custom_components/abode_security /path/to/custom_components/
   ```

   You should have:
   ```
   custom_components/
   ├── abode_security/
   │   ├── __init__.py
   │   ├── manifest.json
   │   ├── config_flow.py
   │   ├── const.py
   │   └── ... (other files)
   ```

3. **Restart Home Assistant**

   - Go to **Settings** → **System** → **Restart**
   - Or via command line: `systemctl restart home-assistant`
   - Or via SSH: `docker restart homeassistant`

4. **Add the Integration**

   - Go to **Settings** → **Devices & Services** → **Create Integration**
   - Search for "Abode Security"
   - Click the integration card
   - Enter your credentials as described in [HACS Installation](#hacs-installation-recommended) steps 4-6

## Verification

After installation, verify everything is working correctly:

### 1. Check Integration Status

- Go to **Settings** → **Devices & Services** → **Abode Security**
- You should see the integration listed
- Status should show as "configured"

### 2. Verify Entities

- Go to **Settings** → **Devices & Services** → **Devices**
- Search for "Abode Security"
- You should see your Abode devices listed
- Click on any device to see entity details

### 3. Check Diagnostics

- Go to **Settings** → **Devices & Services** → **Abode Security**
- Click the three-dot menu
- Select **Download Diagnostics**
- The diagnostic file should contain system information

### 4. Test a Service Call

- Go to **Developer Tools** → **Services**
- Search for "abode_security"
- Available services should appear

## Troubleshooting

### Integration Not Appearing After Installation

**Problem:** The integration doesn't show up in Home Assistant.

**Solutions:**
1. **Verify file location**
   - Check that `manifest.json` exists in `custom_components/abode_security/`
   - Verify the folder is named exactly `abode_security`

2. **Check for syntax errors**
   ```bash
   python3 -m py_compile custom_components/abode_security/__init__.py
   ```

3. **Restart Home Assistant completely**
   - Go to **Settings** → **System** → **Restart**
   - Wait for the system to fully restart

4. **Check Home Assistant logs**
   - Go to **Settings** → **System** → **Logs**
   - Search for "abode_security" or error messages
   - Share any errors found

### Authentication Failures

**Problem:** "Invalid credentials" or authentication errors.

**Solutions:**
1. **Verify your credentials**
   - Test your email and password on the Abode website
   - Ensure you can log in directly

2. **Check for special characters**
   - If your password contains special characters, ensure they're entered correctly
   - Try without special characters if possible

3. **Verify account status**
   - Ensure your Abode account is not locked or disabled
   - Check if you have multi-factor authentication enabled (currently not supported)

### Devices Not Appearing

**Problem:** No devices show up after configuration.

**Solutions:**
1. **Check your Abode account**
   - Log into the Abode app or website
   - Verify you have devices assigned to your account
   - Ensure devices are online and responding

2. **Check Home Assistant logs**
   - Go to **Settings** → **System** → **Logs**
   - Look for device-related errors
   - Check network connectivity

3. **Download diagnostics**
   - Follow [Verification](#verification) step 3
   - Check the diagnostic file for device information

### Slow Performance

**Problem:** Device updates are slow or integration is unresponsive.

**Solutions:**
1. **Adjust polling interval**
   - Go to **Settings** → **Devices & Services** → **Abode Security**
   - Click **Options**
   - Increase the polling interval (60-120 seconds)
   - Click **Submit**

2. **Check network connectivity**
   - Verify Home Assistant can reach the Abode API
   - Check for firewall or network issues

3. **Check system resources**
   - Monitor Home Assistant CPU and memory usage
   - Stop other resource-intensive processes

### SSL/TLS Errors

**Problem:** "SSL: CERTIFICATE_VERIFY_FAILED" or similar errors.

**Solutions:**
1. **Update certificates**
   ```bash
   pip install --upgrade certifi
   ```

2. **Check system time**
   - Ensure Home Assistant server time is correct
   - Incorrect time can cause certificate validation failures

3. **Check firewall/proxy**
   - Ensure no firewall is blocking the connection
   - If behind a proxy, configure it properly

## Upgrading

### HACS Installation

1. Go to HACS → **Integrations** → **Abode Security**
2. Click the three-dot menu
3. Click **Download**
4. Select the latest version
5. Click **Install**
6. Restart Home Assistant

### Manual Installation

1. Download the latest version:
   ```bash
   cd ~/abode-security
   git pull origin main
   ```

2. Copy updated files:
   ```bash
   cp -r custom_components/abode_security /path/to/custom_components/
   ```

3. Restart Home Assistant:
   - Go to **Settings** → **System** → **Restart**

## Uninstallation

### HACS Installation

1. Go to HACS → **Integrations** → **Abode Security**
2. Click the three-dot menu
3. Click **Uninstall**
4. Remove the integration from Home Assistant:
   - Go to **Settings** → **Devices & Services** → **Abode Security**
   - Click the three-dot menu
   - Click **Delete**
5. Restart Home Assistant

### Manual Installation

1. Remove the integration folder:
   ```bash
   rm -rf custom_components/abode_security/
   ```

2. Remove the integration from Home Assistant:
   - Go to **Settings** → **Devices & Services** → **Abode Security**
   - Click the three-dot menu
   - Click **Delete**

3. Restart Home Assistant

## Next Steps

- Read [CONFIGURATION.md](CONFIGURATION.md) to learn about configuration options
- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting
- Check [README.md](README.md) for available services and features
- Visit [DEVELOPMENT.md](DEVELOPMENT.md) for development information

## Getting Help

If you encounter issues:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review Home Assistant logs
3. Download and share diagnostics
4. [Open an issue](https://github.com/molant/abode-security/issues) with:
   - Home Assistant version
   - Integration version
   - Error messages from logs
   - Relevant sections of diagnostics

---

**Back to:** [README.md](README.md)
