# Nmodm User Guide

[Back to Home](../../README.md) | [中文](../zh/USER_GUIDE.md)

## 📺 Video Tutorial

**Complete Tutorial**: [Bilibili Video Tutorial](https://www.bilibili.com/video/BV1LK3CztE54) (Chinese)

We recommend watching the video tutorial first to quickly understand Nmodm's core features and usage.

---

## Table of Contents

- [Installation & Configuration](#installation--configuration)
- [Basic Features](#basic-features)
- [Advanced Features](#advanced-features)
- [FAQ](#faq)

---

## Installation & Configuration

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Memory**: 4GB RAM (8GB recommended)
- **Storage**: 500MB available space
- **Dependencies**:
  - Visual C++ Redistributable 2015-2022 (x64)
  - .NET Framework 4.7.2+

### Installation Steps

1. **Download**
   - Visit [Releases](https://github.com/your-repo/Nmodm/releases)
   - Download the latest version

2. **Installation Methods**
   
   **Method 1: Portable (Recommended)**
   ```
   1. Extract to any directory (English path recommended)
   2. Double-click Nmodm.exe to launch
   ```

   **Method 2: Installer**
   ```
   1. Run Nmodm_Setup.exe
   2. Follow the installation wizard
   3. Launch from Start Menu or desktop shortcut
   ```

### Initial Configuration

#### 1. Configure Game Path

1. Launch Nmodm and go to "Basic Configuration"
2. Click "Browse" button
3. Locate and select `nightreign.exe`
4. Click "Save" to confirm

**Tip**: Game path is usually at:
- Steam: `C:\Program Files (x86)\Steam\steamapps\common\ELDEN RING\Game\`
- Other: Check your installation location

#### 2. Download ME3 Tools

1. Go to "Tool Download" page
2. Select download mirror (default recommended)
3. Click "Download ME3 Tools"
4. Wait for download and extraction

**Mirror Options**:
- Default: GitHub official source
- Alternative: Domestic mirrors (for poor network)

#### 3. Enable Online Fix

1. Return to "Basic Configuration"
2. Check "Enable Online Fix"
3. Program will auto-download necessary files

---

## Basic Features

### Quick Launch

**Quick Launch Page** provides one-stop game launching:

1. **View Status Overview**
   - Game path status
   - ME3 tools status
   - Mod configuration status
   - Network connection status

2. **Launch Game**
   - Click "Launch Game" button
   - Program applies all configurations
   - Game launches with configured parameters

### Mod Management

#### Adding Mods

**Internal Mods (Recommended)**:
1. Copy mod folder to `Mods/` directory
2. Refresh list in "Mod Configuration" page
3. Check mods to enable
4. Click "Generate Config"

**External Mods**:
1. Click "Add External Mod"
2. Browse and select mod file/folder
3. Configure mod parameters
4. Click "Generate Config"

#### Mod Types

Nmodm auto-identifies two mod types:

- **Folder Mods**: Mod directories with multiple files
- **DLL Mods**: Single .dll file mods

#### Configuring Mods

1. Select mod from list
2. Configure in right panel:
   - **Enable/Disable**: Checkbox control
   - **Load Order**: Drag to adjust
   - **Parameters**: Enter custom parameters
   - **Comments**: Add notes

3. Click "Generate Config" to save

### Basic Configuration

#### Game Path Management

- **Change Path**: Click "Browse" to reselect
- **Validate Path**: Auto-validates path
- **Path Check**: Detects Chinese characters warning

#### Online Fix

- **Enable**: Check "Enable Online Fix"
- **Disable**: Uncheck
- **Status**: View fix file status

#### Launch Parameters

Customize game launch parameters:
```
-windowed          # Windowed mode
-borderless        # Borderless window
-width 1920        # Window width
-height 1080       # Window height
```

---

## Advanced Features

### LAN Multiplayer

#### Creating Room

1. Go to "Virtual LAN" page
2. Click "Create Room"
3. Configure room parameters:
   - **Room Name**: Custom name
   - **Network ID**: Auto-generated or manual
   - **Password**: Optional, for room protection
   - **Port**: Default or custom

4. Click "Start Network"
5. Share room info with other players

#### Joining Room

1. Go to "Virtual LAN" page
2. Click "Join Room"
3. Enter room information:
   - **Network ID**: Provided by host
   - **Password**: If room has password

4. Click "Connect"
5. Wait for connection success

#### Network Optimization

**Basic Optimization**:
- Auto-enable network acceleration
- Optimize latency and packet loss
- Smart routing selection

**Advanced Settings**:
- **Compression**: LZ4 (fast) / ZSTD (high compression)
- **Encryption**: Enable/disable end-to-end encryption
- **MTU**: Adjust maximum transmission unit

### Tool Management

#### ME3 Tools

**Version Management**:
- View current version
- Check for updates
- One-click update to latest

**Installation Types**:
- **Portable**: Built-in, no system installation
- **Full**: System-level, supports command line

#### EasyTier Management

**Version Selection**:
- Release: Stable version
- Pre-release: Latest features

**Configuration Management**:
- View config files
- Export configuration
- Import configuration

---

## FAQ

### Installation Issues

**Q: Program won't start, missing DLL**

A: Install these components:
1. Visual C++ Redistributable 2015-2022 (x64)
   - Download: [Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. .NET Framework 4.7.2+
   - Download: [Microsoft](https://dotnet.microsoft.com/download/dotnet-framework)

**Q: Antivirus reports virus**

A: This is a false positive. Solutions:
1. Add Nmodm.exe to whitelist
2. Or temporarily disable antivirus
3. Download from official Releases for safety

**Q: Interface displays abnormally**

A: Check these:
1. Update graphics drivers
2. Ensure DirectX 11 support
3. Try running as administrator

### Feature Issues

**Q: Cannot detect game path**

A: Manual configuration:
1. Open "Basic Configuration"
2. Click "Browse"
3. Find nightreign.exe
4. Ensure path has no Chinese characters

**Q: ME3 tools download fails**

A: Try these:
1. Switch download mirror
2. Check network connection
3. Disable firewall/proxy
4. Manual download to me3p directory

**Q: Mods not working**

A: Check steps:
1. Confirm ME3 tools installed
2. Check mod file integrity
3. Regenerate config file
4. Restart game to test

**Q: LAN connection fails**

A: Troubleshoot:
1. Check firewall settings
2. Confirm correct network ID
3. Verify port not in use
4. Try disabling VPN

### Performance Issues

**Q: Program runs slowly**

A: Optimization tips:
1. Close unnecessary background programs
2. Ensure sufficient memory
3. Check disk space
4. Update to latest version

**Q: Game launches slowly**

A: Optimization methods:
1. Reduce enabled mods
2. Optimize launch parameters
3. Use SSD for game storage
4. Disable unnecessary startup items

---

## Get Help

If this guide doesn't solve your problem:

- 📺 Watch [Video Tutorial](https://www.bilibili.com/video/BV1LK3CztE54) (Chinese)
- 📖 See [Developer Guide](DEVELOPER_GUIDE.md)
- 🐛 Submit [Issue](https://github.com/your-repo/Nmodm/issues)
- 💬 Join [Discussions](https://github.com/your-repo/Nmodm/discussions)
- 📧 Contact developers

---

**Last Updated**: 2025-01-20
