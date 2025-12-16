# Testing Whisper

```bash
# ffmpeg might be required for some use cases
# sudo apt install ffmpeg

uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
# you might want to install dependencies globally when you register the programs to systemd/ibus

source .venv/bin/activate
python ./ibus-voiceinputd.py
```
