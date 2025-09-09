# Contributing to PalletDataGenerator

Thank you for your interest in contributing to the PalletDataGenerator library! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Submitting Changes](#submitting-changes)
8. [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Blender 4.5+ (for development and testing)
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
   cd PalletDataGenerator
   ```

## Development Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

4. **Verify setup:**
   ```bash
   python -m pytest tests/
   ruff check src/
   black --check src/
   mypy src/
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-exporter` - for new features
- `fix/bbox-calculation-bug` - for bug fixes
- `docs/update-readme` - for documentation updates
- `refactor/generator-structure` - for refactoring

### Commit Messages

Follow the conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation changes
- `style`: formatting changes
- `refactor`: code refactoring
- `test`: adding or modifying tests
- `chore`: maintenance tasks

Examples:
```
feat(exporters): add COCO format support

Add COCO annotation format exporter with support for
bounding boxes and dataset splitting.

Closes #123
```

```
fix(generator): correct bbox calculation for rotated objects

The bounding box calculation was incorrect when objects
were rotated. This fix ensures proper 2D projection.
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src/palletdatagenerator

# Run specific test file
python -m pytest tests/test_generator.py

# Run with verbose output
python -m pytest -v
```

### Writing Tests

- Write tests for all new functionality
- Maintain at least 90% test coverage
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies (especially Blender API)

Example test structure:
```python
class TestGeneratorFeature:
    """Test generator feature functionality."""

    def test_feature_success_case(self, mock_fixture):
        """Test that feature works correctly with valid input."""
        # Arrange
        config = GenerationConfig(...)

        # Act
        result = generator.feature_method(config)

        # Assert
        assert result.success
        assert result.data == expected_data

    def test_feature_error_handling(self):
        """Test that feature handles errors gracefully."""
        with pytest.raises(ValueError, match="Expected error message"):
            generator.feature_method(invalid_config)
```

## Code Style

### Formatting and Linting

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Bandit**: Security linting

### Style Guidelines

1. **Type Hints**: Use type hints for all public functions and methods
   ```python
   def generate_dataset(self, config: GenerationConfig) -> Dict[str, Any]:
       """Generate synthetic dataset."""
       pass
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def export_annotations(self, data: List[Detection]) -> str:
       """Export annotations to file.

       Args:
           data: List of detection objects to export

       Returns:
           Path to exported annotation file

       Raises:
           ValueError: If data is empty or invalid
       """
       pass
   ```

3. **Error Handling**: Use specific exception types
   ```python
   if not output_dir.exists():
       raise FileNotFoundError(f"Output directory not found: {output_dir}")
   ```

4. **Imports**: Organize imports using isort standards
   ```python
   # Standard library
   import os
   from pathlib import Path
   from typing import Dict, List, Optional

   # Third-party
   import numpy as np

   # Local imports
   from palletdatagenerator.core import Generator
   ```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
```

## Submitting Changes

### Pull Request Process

1. **Update your branch:**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run all checks:**
   ```bash
   python -m pytest
   ruff check src/
   black --check src/
   mypy src/
   bandit -r src/
   ```

3. **Push your changes:**
   ```bash
   git push origin your-feature-branch
   ```

4. **Create Pull Request:**
   - Use a descriptive title
   - Fill out the PR template
   - Link related issues
   - Add screenshots if applicable

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Coverage maintained above 90%

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

## Release Process

### Versioning

The project follows [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Steps

1. **Update version:**
   ```bash
   # Update version in src/palletdatagenerator/__init__.py
   __version__ = "1.2.0"
   ```

2. **Update CHANGELOG.md:**
   ```markdown
   ## [1.2.0] - 2024-01-15

   ### Added
   - New COCO exporter functionality
   - GPU rendering support

   ### Fixed
   - Bbox calculation for rotated objects

   ### Changed
   - Improved error handling in generators
   ```

3. **Create release PR:**
   - Title: "Release v1.2.0"
   - Include all changes since last release

4. **Tag and release:**
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin v1.2.0
   ```

5. **GitHub Actions will:**
   - Run all tests
   - Build distribution packages
   - Publish to PyPI
   - Create GitHub release

## Development Tips

### Working with Blender

- Use mocks for Blender API during testing
- Test with actual Blender when possible
- Handle Blender API changes gracefully

### Performance Considerations

- Profile code for performance bottlenecks
- Use efficient data structures
- Consider memory usage for large datasets

### Documentation

- Update docstrings for all changes
- Include examples in documentation
- Test code examples in documentation

## Getting Help

- **Issues**: Search existing issues or create new ones
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check the project documentation

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- README.md contributors section
- GitHub releases

Thank you for contributing to PalletDataGenerator! 🚀
