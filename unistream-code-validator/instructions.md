# Unistream Code Validator Skill

## Purpose

This skill validates the Unistream microscopy automation codebase for common errors, anti-patterns, and violations of project-specific rules. It performs automated checks that are tedious and error-prone when done manually.

## When to Use This Skill

Invoke this skill when:
- User asks to "validate code" or "check for issues"
- User asks about hardcoded values, pixel sizes, or coordinate bugs
- Before committing major changes to coordinate transformation code
- After refactoring hardware configuration code
- User asks "are there any problems in the code?"

## What This Skill Checks

### 1. Hardcoded Pixel Sizes
**Critical Rule:** Never hardcode `pixel_size_um` in production code.

**Valid:**
```python
# Calculated from config
pixel_size_um = camera_sensor_pixel_size_um / objective_magnification

# Test files can hardcode
pixel_size_um = 0.752  # In tests/ directory

# Fallbacks with validation
pixel_size_um = getattr(obj, 'pixel_size_um', None)
if pixel_size_um is None:
    raise ValueError("Missing pixel size")
```

**Invalid:**
```python
# Direct hardcoding in production
pixel_size_um = 0.28
pixel_size_um = 0.752

# Silent fallbacks that hide errors
pixel_size_um = obj.pixel_size_um or 0.1
```

### 2. Unsafe Fallback Values
**Rule:** Fallbacks should fail loudly, not use default values.

**Valid:**
```python
value = config.get('critical_param')
if value is None:
    raise ValueError("critical_param required")
```

**Invalid:**
```python
value = config.get('critical_param', 0.5)  # Silent default
value = config.get('critical_param') or 0.5  # Silent default
```

### 3. Coordinate Transformation Patterns

**Known Bugs to Check:**
- Y-axis inversion in `coordinate_utils.py`
- Stale stage position in `stage_to_live_view()`
- Missing `update_stage_position()` calls before polygon rendering
- Incorrect origin parameters in `transform_polygon_vertices()`

### 4. Configuration Access

**Rule:** Always read from config files, never hardcode hardware parameters.

**Valid:**
```python
laser_power = self.config['laser']['power']
port = hardware_config['devices']['pump']['port']
```

**Invalid:**
```python
laser_power = 50  # Hardcoded
port = '/dev/ttyUSB0'  # Hardcoded
```

## How to Use This Skill

### Basic Validation
```bash
# From the skill directory
python validate_code.py /path/to/unistream
```

### Specific Checks
```bash
# Check only pixel size issues
python validate_code.py /path/to/unistream --check pixel_size

# Check fallbacks
python validate_code.py /path/to/unistream --check fallbacks

# Check coordinate bugs
python validate_code.py /path/to/unistream --check coordinates
```

### Output Format
The validator outputs:
- **ERROR**: Critical issues that will cause bugs
- **WARNING**: Potential issues that need review
- **INFO**: Suggestions for improvement
- **OK**: No issues found

Each finding includes:
- File path and line number
- Description of the issue
- Code snippet
- Suggested fix (when applicable)

## Integration with Claude Code

When this skill is invoked:
1. Claude runs `validate_code.py` on the specified directory
2. Reviews the output
3. Summarizes findings for the user
4. Offers to fix any ERROR-level issues automatically

## Customization

Edit `validation_rules.yaml` to:
- Add new patterns to check
- Adjust severity levels
- Add project-specific rules
- Exclude certain files/patterns

## Maintenance

Update this skill when:
- New coding standards are established
- New bug patterns are discovered
- Hardware configuration changes
- Coordinate transformation logic changes
