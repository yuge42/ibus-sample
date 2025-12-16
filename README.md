# IBus Voiceinput Engine

A minimal IBus input method engine implementation for learning and experimentation purposes.

## About

This project provides a simple IBus engine that demonstrates the basic structure and setup process for creating custom input method engines on Linux. The engine currently replaces the Return key with the text "HELLO" as a proof of concept.

> **Important**: This project was developed and tested on **Debian Trixie**. Setup procedures and file paths may vary significantly depending on your Linux distribution. The instructions below are specific to Debian-based systems with GNOME desktop environment.

## Prerequisites

- IBus framework installed (`ibus` package)
- Python 3 with GObject introspection bindings (`python3-gi` package)
- GNOME desktop environment (or compatible)

## Installation

Follow these steps to install the voiceinput engine system-wide. **Do not use user-level component directories** as they can cause conflicts with system-managed IBus instances.

### Step 1: Install the Engine Binary

```bash
sudo install -m 755 \
  ibus-engine-voiceinput.py \
  /usr/libexec/ibus-engine-voiceinput
```

For reinstallation, you may need to kill any running instances first:

```bash
pkill -f ibus-engine-voiceinput
```

Verify installation:

```bash
ls -l /usr/libexec/ibus-engine-voiceinput
```

### Step 2: Install the Component XML

The component XML file must specify the absolute path to the engine executable.

```bash
sudo install -m 644 \
  voiceinput.xml \
  /usr/share/ibus/component/voiceinput.xml
```

### Step 3: Update IBus Cache

Rebuild the IBus cache to register the new engine:

```bash
sudo ibus write-cache
```

**Important**: Do **not** restart IBus manually at this step.

### Step 4: Logout and Login

Log out of your session and log back in. This is the proper way to apply IBus changes on GNOME without conflicting with the desktop environment's session management.

### Step 5: Verify Registration

Check if the engine is registered:

```bash
ibus list-engine | grep voiceinput
```

If the output shows `voiceinput`, the installation was successful.

You can also verify the cache directly:

```bash
ibus read-cache | grep -A5 voiceinput
```

## Usage

To activate the voiceinput engine:

```bash
ibus engine voiceinput
```

The engine will intercept all keyboard input. Only pressing the Return key will produce output: the text "HELLO". All other keys will be suppressed.

Check the log file for debugging:

```bash
tail -f /tmp/ibus-voiceinput.log
```

## Important Restrictions

On Debian with GNOME, avoid the following operations to prevent breaking your IBus setup:

| Operation | Why to Avoid |
|-----------|-------------|
| `ibus restart` | Conflicts with GNOME's session management |
| `ibus-daemon -drx` | Manual daemon startup can break the system configuration |
| `IBUS_COMPONENT_PATH` environment variable | Corrupts the registry cache |
| User-level component directory (`~/.local/share/ibus/component`) | Not recommended on Debian |

## Troubleshooting

If IBus becomes unresponsive or broken, reset it with:

```bash
im-config -n ibus
logout
```

Then log back in.

## Key Points Summary

- Engine binary location: `/usr/libexec/ibus-engine-voiceinput`
- Component XML location: `/usr/share/ibus/component/voiceinput.xml`
- Always run `sudo ibus write-cache` after changes
- Always logout/login to apply changes properly

## License

MIT

## Author

Your Name
