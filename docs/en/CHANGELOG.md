# Changelog

[Back to Home](../../README.md) | [中文](../zh/CHANGELOG.md)

All notable changes to Nmodm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Mod auto-update feature
- Cloud configuration sync
- More language support (Japanese, Korean, etc.)

---

## [3.1.4] - 2025-12-31

### Added
- ✨ nrsc.dll preload feature
  - Support early loading for SeamlessCoop's nrsc.dll
  - When preload is enabled, no longer enforces nighter.dll → nrsc.dll load order
  - Persisted in config file as `load_early = true`
  - Right-click menu support in both Mod Config and Quick Launch pages
  - Display preload status in list: 🚀 nrsc.dll [Preload]
- 🎨 Preset editor dialog status label
  - Added status notification label at bottom-left (auto-dismiss after 3 seconds)
  - Replaced popup dialogs for better user experience
- 📝 Dynamic tab title updates
  - Shows "✏️ Edit Preset" when editing
  - Shows "Create Preset" when creating

### Changed
- 🎨 Preview config layout optimization
  - Preview info and config content now displayed horizontally (side-by-side)
  - Improved readability and space utilization
- 🔧 Close button visibility optimization
  - Font size adjusted to 20px
  - Color changed to pink (#FF69B4) for better visibility
- 🌐 Complete internationalization for context menus
  - "Preload", "Force Load Last", "Force Load First" support Chinese/English switching
  - Real-time response to language changes

### Fixed
- 🐛 Fixed checkbox hover effect issue (2 places)
  - Added `QCheckBox::indicator:checked:hover` style
  - Ensures checked state remains visible when hovering
- 🐛 Fixed empty description display issue
  - When description is empty, skip writing description line or use default
  - Ensures proper parsing of empty descriptions
- 🐛 Fixed filename retention issue
  - Auto-clear filename input after updating preset
  - Prevents confusion from residual filenames
- 🐛 Fixed preload status display issue
  - Fixed filename matching logic (extract pure filename for comparison)
  - Correctly displays preload status indicator
- 🐛 Fixed preload status restoration issue
  - Clear temporary state (`self.preload_dlls`) after saving preset
  - Correctly restore preload status when editing preset
- 🐛 Fixed DLL name matching issue
  - Handle DLL filenames with paths (e.g., `SeamlessCoop/nrsc.dll`)
  - Extract pure filename for comparison
- 🐛 Fixed unchecked mod setting issue
  - "Preload", "Force Load Last", "Force Load First" show "Setting Error" when mod is unchecked
  - Unified error handling logic

---

## [3.1.3] - 2025-01-20

### Fixed
- 🐛 Fixed missing text in "Edit Preset" dialog on Quick Launch page
  - Fixed duplicate `label` key in translation files causing text loss
  - Affected labels: preset name, filename, description, icon, mod packages, DLL files, etc.
- 🐛 Fixed Chinese filename garbled text after extracting OnlineFix package
  - Added ZIP file Chinese encoding fix (CP437 -> GBK)
  - Fixed display issues for files like "无缝手柄问题解决方案.png"

### Changed
- 📝 Improved translation file structure to avoid duplicate keys
- 🔧 Enhanced ZIP extraction encoding compatibility

---

## [3.1.2] - 2025-01-20

### Added
- 🌍 Complete internationalization support
  - Fully translated virtual LAN page (17 new translation keys)
  - All log messages and error prompts support Chinese and English
- 📦 Multi-language installer support
  - Inno Setup installer supports English and Chinese interfaces
  - Auto-detect system language (`ShowLanguageDialog=auto`)
  - Fully internationalized installer UI (Tasks, Run, CustomMessages)
- 📚 Complete documentation system (Chinese & English)
  - User guide, developer guide, contribution guide
  - Detailed changelog
  - Version summary documents
- 🔧 GitHub Actions auto-release workflow
- 📝 Unified version management (`src/version.json`)

### Changed
- 🎨 Optimized README structure for clarity
- 📋 Improved `.gitignore` configuration
- 📦 Enhanced dependency management (`requirements.txt`)
- 🌐 Improved translation system with no missing text

### Fixed
- 🐛 Fixed Chinese hardcoded text in `virtual_lan_page.py`
- 🐛 Fixed untranslated default `error_msg` values
- 🐛 Fixed version number inconsistency
- 🐛 Fixed documentation link errors

---

## [3.1.1] - 2025-01-15

### Added
- Version loader module (`version_loader.py`)
- Dynamic version display feature

### Changed
- Optimized build scripts
- Improved error handling

### Fixed
- Fixed version display after packaging
- Fixed resource file path issues

---

## [3.1.0] - 2025-01-10

### Added
- Internationalization (i18n) support
- Language switching feature
- Translation file system

### Changed
- Refactored UI components
- Optimized startup speed
- Improved memory usage

### Fixed
- Fixed UI text display issues
- Fixed language preference saving

---

## [3.0.7] - 2025-01-06

### Added
- Published on Nexus Mods

### Changed
- Optimized user experience
- Improved documentation

---

## [3.0.5] - 2025-01-06

### Fixed
- 🐛 Fixed Mod configuration page display issue
- 🐛 Fixed virtual LAN advanced settings save issue
- 🐛 Fixed TOML config file sync issue
- 🐛 Fixed process management and network stop lag

### Changed
- 🔧 Unified version number to 3.0.5

---

## [3.0.3] - 2024-12-20

### Added
- ✨ New modern frameless interface design
- ✨ Integrated EasyTier virtual LAN
- ✨ Added smart mod management system

### Changed
- 🔧 Optimized packaging and deployment
- 🎨 Improved UI design and UX

---

## [3.0.0] - 2024-12-01

### Added
- 🎉 New 3.0 version release
- 🎮 Auto game path detection
- 🔧 ME3 tool integration
- 🌐 LAN multiplayer support
- 🎨 Modern interface design

### Changed
- Complete code architecture rewrite
- Adopted PySide6 framework
- Modular design

---

## [2.x] - Legacy Versions

Changelog for early versions not detailed.

---

## Version Format

### Version Number

`MAJOR.MINOR.PATCH`

- **MAJOR**: Major architecture changes or incompatible API changes
- **MINOR**: Backward-compatible feature additions
- **PATCH**: Backward-compatible bug fixes

### Change Types

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Fixed**: Bug fixes
- **Removed**: Removed features
- **Deprecated**: Soon-to-be removed features
- **Security**: Security-related fixes

---

**Last Updated**: 2025-10-20
