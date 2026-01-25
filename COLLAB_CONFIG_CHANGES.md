# Collaboration Configuration Changes

## Summary

Made `max_iterations` configurable via `squad.yaml` instead of hardcoded default.

## Changes Made

### 1. Configuration Files

#### `ai_squad/core/config.py`
- Added `collaboration` section to `DEFAULT_CONFIG`:
  ```python
  "collaboration": {
      "max_iterations": 3,
      "default_mode": "iterative",
  }
  ```

#### `squad.yaml` & `squad.yaml.example`
- Added collaboration configuration section:
  ```yaml
  collaboration:
    max_iterations: 3
    default_mode: iterative
  ```

### 2. Collaboration Module

#### `ai_squad/core/collaboration.py`
- Added `Config` import
- Changed `max_iterations` parameter from `int = 3` to `Optional[int] = None`
- Added config loading when `max_iterations` not specified:
  ```python
  if max_iterations is None:
      config = Config.load()
      max_iterations = config.get("collaboration", {}).get("max_iterations", 3)
  ```

### 3. CLI

#### `ai_squad/cli.py`
- Updated `--max-iterations` flag from `default=3` to `default=None`
- Help text updated: `"Max iteration rounds (default: from config or 3)"`
- Allows config-based default while supporting CLI override

### 4. Tests

#### `tests/test_collaboration.py`
- Added `TestConfigBasedIterationLimit` class with 3 new tests:
  1. `test_max_iterations_from_config` - Verifies config is read
  2. `test_max_iterations_explicit_overrides_config` - Verifies CLI override works
  3. `test_max_iterations_defaults_when_config_missing` - Verifies fallback to 3

**Test Results:** 23/23 passing ✅

### 5. Documentation

#### `docs/configuration.md`
- Added "Collaboration Configuration" section
- Documented `max_iterations` setting with recommendations
- Documented `default_mode` setting
- Added examples for different iteration limits
- Explained CLI override behavior

## Usage Examples

### Using Config Default
```yaml
# squad.yaml
collaboration:
  max_iterations: 5
```

```bash
squad joint-op 123 pm architect
# Uses max_iterations: 5 from config
```

### CLI Override
```bash
squad joint-op 123 pm architect --max-iterations 10
# Overrides config, uses 10 iterations
```

### Fallback to Default
```yaml
# squad.yaml (no collaboration section)
```

```bash
squad joint-op 123 pm architect
# Falls back to default: 3 iterations
```

## Benefits

1. **Project-Specific Settings** - Different projects can have different iteration limits
2. **Team Standards** - Consistent iteration limits across team via committed config
3. **Flexibility** - CLI override available when needed
4. **Backward Compatible** - Defaults to 3 if config missing
5. **Production Ready** - Fully tested with comprehensive test suite

## Configuration Hierarchy

1. **CLI Flag** (`--max-iterations`) - Highest priority
2. **Config File** (`squad.yaml` → `collaboration.max_iterations`)
3. **Hardcoded Default** (3) - Fallback

## Test Coverage

- **Collaboration Module:** 88% coverage (up from 21%)
- **All Tests:** 23/23 passing
- **New Tests:** 3 config-based tests added

## Recommendations

### For Most Projects
```yaml
collaboration:
  max_iterations: 3
  default_mode: iterative
```

### For Critical Features
```yaml
collaboration:
  max_iterations: 5
  default_mode: iterative
```

### For Fast Prototyping
```yaml
collaboration:
  max_iterations: 2
  default_mode: iterative
```

---

**Next Steps:**
- Run `squad sitrep` to validate configuration
- Update your `squad.yaml` with desired iteration limits
- Test with `squad joint-op <issue> <agent1> <agent2>`
