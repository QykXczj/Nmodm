# Nmodm Developer Guide

[Back to Home](../../README.md) | [中文](../zh/DEVELOPER_GUIDE.md)

## Table of Contents

- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Development Standards](#development-standards)
- [Build & Package](#build--package)
- [Testing](#testing)

---

## Development Setup

### Requirements

- **Python**: 3.8 or higher
- **pip**: Latest version
- **Git**: For version control
- **IDE**: VS Code or PyCharm (recommended)

### Clone Project

```bash
git clone https://github.com/your-repo/Nmodm.git
cd Nmodm
```

### Create Virtual Environment

**Windows**:
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac**:
```bash
python -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development tools (optional)
pip install black flake8 mypy pytest
```

### Run Program

```bash
python main.py
```

---

## Project Architecture

### Directory Structure

```
Nmodm/
├── main.py                 # Application entry
├── src/                    # Source code
│   ├── app.py             # Main app class
│   ├── config/            # Configuration management
│   ├── ui/                # User interface
│   │   ├── main_window.py
│   │   ├── sidebar.py
│   │   ├── components/
│   │   └── pages/
│   ├── utils/             # Utility modules
│   └── i18n/              # Internationalization
├── docs/                   # Documentation
├── .kiro/                  # Kiro configuration
└── requirements.txt        # Dependencies
```

### Core Modules

#### 1. Application Layer (`src/app.py`)

```python
class NmodmApp:
    """Main application class"""
    - Manages app lifecycle
    - Lazy page loading
    - State management
```

#### 2. Configuration Layer (`src/config/`)

- `config_manager.py`: Game path, crack management
- `mod_config_manager.py`: Mod configuration
- `network_optimization_config.py`: Network config

#### 3. UI Layer (`src/ui/`)

- `main_window.py`: Frameless main window
- `sidebar.py`: Sidebar navigation
- `pages/`: Feature pages (lazy-loaded)

#### 4. Utility Layer (`src/utils/`)

- `download_manager.py`: Download management
- `easytier_manager.py`: Virtual LAN
- `tool_manager.py`: Tool management

### Design Patterns

#### Singleton Pattern

Configuration managers use singleton:

```python
class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

#### Signal-Slot Mechanism

Use Qt signals for component communication:

```python
class ModsPage(QWidget):
    config_changed = Signal()  # Config change signal
    
    def save_config(self):
        # Save configuration
        self.config_changed.emit()  # Emit signal
```

#### Lazy Loading

Pages loaded on-demand for faster startup:

```python
def get_or_create_page(self, page_name):
    if page is None:
        page = self._create_page(page_name)
    return page
```

---

## Development Standards

### Code Style

Follow **PEP 8** standards:

```bash
# Format code
black src/

# Check code
flake8 src/

# Type check
mypy src/
```

### Naming Conventions

- **Class names**: PascalCase (`ConfigManager`)
- **Function names**: snake_case (`get_game_path`)
- **Constants**: UPPER_CASE (`DEFAULT_PORT`)
- **Private methods**: `_method_name`

### Docstrings

Use Google-style docstrings:

```python
def download_file(url: str, save_path: str) -> bool:
    """Download file to specified path
    
    Args:
        url: Download URL
        save_path: Save path
        
    Returns:
        bool: Whether download succeeded
        
    Raises:
        ValueError: When URL is invalid
    """
    pass
```

### Commit Standards

Use Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code formatting
- `refactor`: Refactoring
- `test`: Testing
- `chore`: Build/tools

**Example**:
```
feat(mod): add mod auto-update feature

- Implement version detection
- Add auto-download
- Update UI prompts

Closes #123
```

---

## Build & Package

### Using Nuitka

**Directory Mode** (recommended for dev):
```bash
python build_nuitka.py
# Select: 2. Standalone mode
```

**Single-File Mode** (recommended for release):
```bash
python build_nuitka.py
# Select: 1. Onefile mode
```

### Build Configuration

Edit `build_nuitka.py` to modify build options:

```python
class NuitkaBuilder:
    def __init__(self):
        self.version = "3.1.2"  # Version number
        # ... other config
```

### Version Management

Version unified in `src/version.json`:

```json
{
  "version": "3.1.2"
}
```

**Update Version**:
1. Modify `src/version.json`
2. Commit code
3. Create Git Tag
4. Trigger GitHub Actions

---

## Testing

### Unit Tests

Write tests with pytest:

```python
# tests/test_config.py
def test_config_manager():
    manager = ConfigManager()
    assert manager.get_game_path() is not None
```

**Run Tests**:
```bash
pytest tests/
```

### Integration Tests

Test complete workflows:

```python
def test_mod_workflow():
    # 1. Add mod
    # 2. Configure mod
    # 3. Generate config
    # 4. Verify result
    pass
```

### Test Coverage

```bash
pytest --cov=src tests/
```

---

## Debugging Tips

### Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning")
logger.error("Error")
```

### Performance Profiling

```bash
# Use cProfile
python -m cProfile -o profile.stats main.py

# Analyze results
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

### Memory Profiling

```bash
pip install memory_profiler
python -m memory_profiler main.py
```

---

## Contribution Workflow

1. **Fork Project**
2. **Create Branch**: `git checkout -b feature/amazing-feature`
3. **Commit Code**: `git commit -m 'feat: add amazing feature'`
4. **Push Branch**: `git push origin feature/amazing-feature`
5. **Create PR**: Create Pull Request on GitHub

See [Contributing Guide](CONTRIBUTING.md) for details

---

## Common Development Issues

**Q: How to add a new page?**

A: 
1. Create page file in `src/ui/pages/`
2. Add page creation logic in `src/app.py`'s `_create_page()`
3. Add navigation item in `src/ui/sidebar.py`

**Q: How to add new configuration?**

A:
1. Add config methods in corresponding `*_manager.py`
2. Update config file format
3. Add config UI

**Q: How to debug packaged program?**

A:
1. Use directory mode packaging
2. Check log files in `logs/` directory
3. Use `--console` parameter to show console

---

**Last Updated**: 2025-01-20
