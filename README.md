# IBus Voiceinput Engine

A minimal IBus input method engine implementation for learning and experimentation purposes.

## About

This project provides an IBus engine that enables voice input using OpenAI Whisper for speech recognition. It allows you to dictate text directly into any application that supports IBus input methods.

> **Important**: This project was developed and tested on **Debian Trixie**. Setup procedures and file paths may vary significantly depending on your Linux distribution. The instructions below are specific to Debian-based systems with GNOME desktop environment.

## Prerequisites

- IBus framework installed (`ibus` package)
- Python 3 with GObject introspection bindings (`python3-gi` package)
- GNOME desktop environment (or compatible)
- Python packages for voice input: `openai-whisper`, `sounddevice`, `numpy` (see `requirements.txt`)
- systemd (for running the voice input daemon)

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

### Step 6: Install Voice Input Daemon (Optional)

The voice input daemon (`ibus-voiceinputd`) provides Whisper-based voice recognition. To install it as a systemd user service:

#### Install Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv ~/.local/share/ibus-voiceinputd-venv
source ~/.local/share/ibus-voiceinputd-venv/bin/activate
pip install -r requirements.txt
deactivate
```

#### Install the Daemon Binary

```bash
install -m 755 \
  ibus-voiceinputd.py \
  ~/.local/bin/ibus-voiceinputd
```

Make sure `~/.local/bin` is in your PATH (most distributions include this by default).

#### Install the systemd Service

```bash
# Install for current user
mkdir -p ~/.config/systemd/user
mkdir -p ~/.local/bin

# Create service file from template
envsubst < ibus-voiceinputd.service.in > ~/.config/systemd/user/ibus-voiceinputd.service

# Reload systemd configuration
systemctl --user daemon-reload

# Enable and start the service
systemctl --user enable ibus-voiceinputd.service
systemctl --user start ibus-voiceinputd.service
```

#### Verify the Service

```bash
# Check service status
systemctl --user status ibus-voiceinputd.service

# View logs
journalctl --user -u ibus-voiceinputd.service -f
```

The daemon will create a Unix socket at `$XDG_RUNTIME_DIR/ibus-voiceinput.sock` for communication with the IBus engine.

## Usage

To activate the voiceinput engine:

```bash
ibus engine voiceinput
```

### Voice Input Controls

If you have installed the voice input daemon (`ibus-voiceinputd`), you can use the following controls:

- **Ctrl+Space**: Start/stop voice recording
- **Esc**: Abort current recording

When recording, you'll see 🎤 音声入力中… in the preedit text. After stopping, the engine will show 🧠 認識中… while Whisper processes the audio. The recognized text will be automatically inserted.

### Debugging

Check the IBus engine log (from ibus-engine-voiceinput):

```bash
tail -f ~/.local/state/ibus-voiceinput/daemon.log
```

Check the voice input daemon (ibus-voiceinputd) status and logs:

```bash
systemctl --user status ibus-voiceinputd.service
journalctl --user -u ibus-voiceinputd.service -f
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
