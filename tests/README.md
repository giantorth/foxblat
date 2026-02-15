# Foxblat Tests

This directory contains unit tests for the Foxblat application.

## Running Tests

### On Linux

Run all tests:
```bash
python3 -m pytest tests/
```

Or run specific test file:
```bash
python3 -m unittest tests/test_process_handler.py
```

Or with verbose output:
```bash
python3 tests/test_process_handler.py
```

### Requirements

Install test dependencies:
```bash
pip install pytest
```

## Test Coverage

### Plugin System & Controls
- **test_subscription.py**: Event system (Subscription, SubscriptionList, EventDispatcher, SimpleEventDispatcher, Observable, BlockingValue)
- **test_plugin_base.py**: Plugin infrastructure (PluginContext, PluginDeviceInfo, PluginPanel)
- **test_plugin_manager.py**: Plugin discovery, loading, device matching, presets, and event forwarding
- **test_widgets.py**: GTK widget wrappers (FoxblatRow, SliderRow, SwitchRow, ButtonRow, LabelRow, ToggleButtonRow, ComboRow, LevelRow)

### Core Logic
- **test_bitwise.py**: Bit manipulation utilities (test_bit, modify_bit, set_bit, unset_bit, toggle_bit, swap_nibbles)
- **test_moza_command.py**: Serial protocol command construction, payload encoding/decoding, checksum, message framing, response parsing
- **test_settings_handler.py**: YAML settings persistence (read, write, remove, path management)
- **test_pithouse_converter.py**: Pithouse preset import validation, conversion, and FFB curve decoding
- **test_preset_handler.py**: Preset save/load, linked processes/vehicles, device settings

### I/O & Communication
- **test_process_handler.py**: Process discovery, command-line pattern matching
- **test_connection_manager.py**: Device handler resolution, serial device management, wheel ID cycling
- **test_serial_handler.py**: Serial write queueing, shutdown lifecycle, subscription dispatching
- **test_hid_handler.py**: HID device detection, axis values, blip data, compatibility modes
- **test_ipc_handler.py**: JSON-RPC command processing (ping, set/get angle, status, list/load presets)

## Notes
- Tests requiring GTK/Adwaita will be skipped if the libraries are not available
- The `FOXBLAT_FLATPAK_EDITION` environment variable is set automatically by tests that need it

## Adding New Tests

1. Create a new file `test_<module>.py` in this directory
2. Import `unittest` and the module you want to test
3. Create test classes that inherit from `unittest.TestCase`
4. Name test methods starting with `test_`
5. Run tests to verify they work
