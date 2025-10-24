# Contributing Guide

[Back to Home](../../README.md) | [中文](../zh/CONTRIBUTING.md)

Thank you for considering contributing to Nmodm!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Standards](#commit-standards)

---

## Code of Conduct

### Our Pledge

To foster an open and welcoming environment, we pledge to:

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Use of sexualized language or imagery
- Trolling, insulting/derogatory comments, personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other unethical or unprofessional conduct

---

## How to Contribute

### Reporting Bugs

**Before Submitting**:
1. Check [Issues](https://github.com/your-repo/Nmodm/issues) to avoid duplicates
2. Confirm using latest version
3. Collect relevant information

**Bug Report Should Include**:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots (if applicable)
- Environment info:
  - OS version
  - Python version (if running from source)
  - Nmodm version

**Example**:
```markdown
**Description**
Program crashes when clicking "Launch Game"

**Steps to Reproduce**
1. Open Nmodm
2. Configure game path
3. Click "Launch Game"
4. Program crashes

**Expected Behavior**
Game should launch normally

**Environment**
- OS: Windows 11 64-bit
- Nmodm: v3.1.2
- Python: 3.11.0 (if applicable)

**Screenshots**
[Attach screenshots]
```

### Feature Suggestions

**Before Suggesting**:
1. Confirm feature doesn't exist
2. Check for similar suggestions
3. Consider feature practicality

**Feature Suggestion Should Include**:
- Clear feature description
- Use cases
- Possible implementation
- Alternatives

### Improving Documentation

Documentation improvements include:
- Fixing errors or outdated info
- Adding missing instructions
- Improving code examples
- Translating documentation

---

## Development Workflow

### 1. Fork Project

Click "Fork" button on GitHub page

### 2. Clone Repository

```bash
git clone https://github.com/your-username/Nmodm.git
cd Nmodm
```

### 3. Create Branch

```bash
# Feature branch
git checkout -b feature/amazing-feature

# Fix branch
git checkout -b fix/bug-description

# Docs branch
git checkout -b docs/improve-readme
```

### 4. Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install dev tools
pip install black flake8 mypy pytest
```

### 5. Develop

- Write code
- Add tests
- Update documentation
- Follow code standards

### 6. Test Code

```bash
# Run tests
pytest tests/

# Format code
black src/

# Check code
flake8 src/

# Type check
mypy src/
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add amazing feature"
```

### 8. Push Branch

```bash
git push origin feature/amazing-feature
```

### 9. Create Pull Request

1. Visit your fork page
2. Click "New Pull Request"
3. Fill PR description
4. Submit PR

---

## Code Standards

### Python Style

Follow [PEP 8](https://pep8.org/):

```python
# Good example
def calculate_total_price(items: list, tax_rate: float) -> float:
    """Calculate total price with tax
    
    Args:
        items: Item list
        tax_rate: Tax rate
        
    Returns:
        Total price
    """
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)


# Bad example
def calc(i,t):
    s=sum(x.p for x in i)
    return s*(1+t)
```

### Naming Conventions

```python
# Class names: PascalCase
class ConfigManager:
    pass

# Function names: snake_case
def get_game_path():
    pass

# Constants: UPPER_CASE
MAX_RETRY_COUNT = 3

# Private methods: prefix underscore
def _internal_method():
    pass
```

### Docstrings

```python
def download_file(url: str, save_path: str, timeout: int = 30) -> bool:
    """Download file to specified path
    
    Args:
        url: File download URL
        save_path: Save path
        timeout: Timeout in seconds, default 30
        
    Returns:
        Whether download succeeded
        
    Raises:
        ValueError: Invalid URL format
        IOError: File write failed
        
    Example:
        >>> download_file("https://example.com/file.zip", "file.zip")
        True
    """
    pass
```

### Type Annotations

```python
from typing import List, Dict, Optional

def process_mods(
    mod_list: List[str],
    config: Dict[str, any],
    output_path: Optional[str] = None
) -> bool:
    pass
```

---

## Commit Standards

### Conventional Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code formatting
- `refactor`: Refactoring
- `perf`: Performance
- `test`: Testing
- `chore`: Build/tools

### Scope

Optional, indicates affected module:

- `mod`: Mod management
- `config`: Configuration
- `ui`: User interface
- `network`: Network features
- `build`: Build system

### Subject

- Use imperative mood
- Don't capitalize first letter
- No period at end
- Limit to 50 characters

### Body

- Explain what and why
- Compare with previous behavior

### Footer

- Reference issues: `Closes #123`
- Breaking changes: `BREAKING CHANGE: ...`

### Examples

```
feat(mod): add mod auto-update feature

Implemented features:
- Detect new mod versions
- Auto-download updates
- Backup old versions

Closes #123
```

```
fix(ui): fix window restore issue after minimize

On Windows 11, clicking taskbar icon doesn't restore window.
Fixed by handling WM_SYSCOMMAND message.

Fixes #456
```

---

## Pull Request Guide

### PR Title

Use same format as commit messages:

```
feat(mod): add mod auto-update feature
```

### PR Description

Include:

```markdown
## Changes
Brief description of what this PR does

## Change Type
- [ ] Bug fix
- [x] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
Describe how to test these changes

## Screenshots
If UI changes, add screenshots

## Related Issues
Closes #123
```

### PR Checklist

Before submitting:

- [ ] Code follows project standards
- [ ] Added necessary tests
- [ ] All tests pass
- [ ] Updated relevant documentation
- [ ] Commit messages follow standards
- [ ] Self-reviewed code

---

## Code Review

### Reviewer Responsibilities

- Check code quality
- Verify functionality
- Provide constructive feedback
- Respond promptly

### Reviewee Responsibilities

- Respond to review comments
- Make necessary changes
- Stay polite and professional

---

## Get Help

If you have questions:

- 📖 See [Developer Guide](DEVELOPER_GUIDE.md)
- 💬 Ask in [Discussions](https://github.com/your-repo/Nmodm/discussions)
- 📧 Contact maintainers

---

## License

Contributed code will use the same [MIT License](../../LICENSE) as the project.

---

**Thank you for contributing!** 🎉

**Last Updated**: 2025-01-20
