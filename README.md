# Mocha

A smart home assistant that uses a locally-hosted LLM (via [Ollama](https://ollama.com)) to control [TP-Link Kasa](https://www.tp-link.com/us/smart-home/) smart lights through natural language. Talk to it like you would a person — it figures out which devices you mean, what you want done, and executes the commands.

## How It Works

Mocha connects three things together:

1. **Ollama** runs a local LLM with tool-calling support (e.g. `qwen2.5:14b`)
2. **python-kasa** discovers and controls TP-Link Kasa devices on your local network
3. **Streamlit** provides a chat UI accessible from any device on your LAN

When you send a message like *"turn off the bedroom lights"*, here's what happens:

```
User message
  -> Ollama LLM (decides which tools to call)
    -> search_devices("bedroom")        # fuzzy match to find device IPs
    -> power_light("10.0.0.90", "off")  # control the matched device
  -> LLM generates a natural language response
```

The LLM doesn't just relay commands — it reasons about multi-step operations. For example, *"turn on all lights that are currently off"* triggers the model to list all devices, check each one's status, then power on only the ones that are off.

## Project Structure

```
mocha/
├── app.py                          # Streamlit chat UI
├── config.yaml                     # App configuration (gitignored)
├── requirements.txt                # Python dependencies
└── utilities/
    ├── OllamaChat.py               # LLM orchestration and tool definitions
    ├── SmartDevice.py              # Kasa device discovery and control
    └── FuzzyMatching.py            # Device name resolution
```

### `app.py`

The Streamlit frontend. Initializes services on first load (cached via `@st.cache_resource` so device discovery only happens once), generates a time-aware greeting from the LLM, and renders a standard chat interface.

### `utilities/OllamaChat.py`

The core orchestration layer. Defines 7 tools as JSON schemas that are passed to Ollama's `/api/chat` endpoint:

| Tool | Purpose |
|------|---------|
| `list_devices` | Get all discovered devices (IP -> name mapping) |
| `search_devices` | Fuzzy search for devices by name |
| `power_light` | Turn a light on or off |
| `light_status` | Check if a light is on or off |
| `adjust_brightness` | Set brightness (0-100) |
| `adjust_hue` | Set color via HSV values |
| `blink_effect` | Blink a light for N seconds |

The `chat()` method runs a loop: send messages to Ollama, execute any tool calls the model returns, feed results back, and repeat until the model responds with plain text. When the model returns multiple tool calls in a single response, they are executed concurrently via `asyncio.gather`.

A system prompt guides the model's behavior — how to chain tools together, how to handle groups of devices, and how to convert color names to HSV tuples.

### `utilities/SmartDevice.py`

A synchronous wrapper around the async `python-kasa` library. On initialization, it runs `Discover.discover()` to find all Kasa devices on the network. Each method (power, brightness, hue, blink, status) has a sync public interface and an async private implementation that operates on the discovered device objects.

Color and brightness controls use the Kasa `Light` module (`device.modules[Module.Light]`) rather than direct device attributes.

### `utilities/FuzzyMatching.py`

Uses [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) (`fuzz.partial_ratio`) to match user input like *"bedroom"* against device names. Works with both dicts (IP -> name) and flat lists. The match threshold is configurable — a lower value catches more matches but risks false positives.

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- TP-Link Kasa smart lights on the same network

### Installation

```bash
git clone <repo-url> && cd mocha
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Pull an Ollama model with tool-calling support:

```bash
ollama pull qwen2.5:14b
```

### Configuration

Create a `config.yaml` in the project root:

```yaml
FUZZY_MATCH_THRESHOLD: 50
TITLE: "Mocha"
CAPTION: "Smart Home Assistant"
MODEL: "qwen2.5:14b"
```

| Key | Description |
|-----|-------------|
| `FUZZY_MATCH_THRESHOLD` | Minimum fuzzy match score (0-100) for device name resolution. Lower = more permissive. |
| `TITLE` | App title displayed in the UI |
| `CAPTION` | Subtitle displayed below the title |
| `MODEL` | Ollama model to use. Must support tool calling. |

If Ollama is running on a different host, set the `OLLAMA_HOST` environment variable:

```bash
export OLLAMA_HOST=http://192.168.1.100:11434
```

### Running

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`. To access it from other devices on your network, Streamlit exposes the network URL automatically (shown in the terminal output).

## Example Interactions

| You say | What happens |
|---------|-------------|
| *"Turn off the bedroom lights"* | Searches for "bedroom", powers off matched devices |
| *"Turn on all the lights"* | Lists all devices, powers on each one |
| *"Which lights are on?"* | Lists all devices, checks status of each, reports back |
| *"Make the living room lights purple"* | Searches for "living room", sets HSV to (270, 100, 100) |
| *"Dim the kitchen lights to 30%"* | Searches for "kitchen", sets brightness to 30 |
| *"Blink the bedroom lights for 10 seconds"* | Searches for "bedroom", blinks on/off for 10s |
| *"Turn off all lights that are on"* | Lists devices, checks each status, powers off only the ones that are on |

## Model Selection

The LLM needs reliable tool-calling support. Smaller models (7-8B) tend to output raw JSON or call tools with wrong arguments. From testing:

- **`qwen2.5:14b`** — Reliable tool calling, good conversational quality. Recommended.
- **`qwen2.5:7b`** — Works but less reliable with complex tool chains.
- **`llama3.1:8b`** — Inconsistent tool use, often outputs JSON as text instead of using the tool mechanism.

The model needs to fit in your system's RAM. 14B models require ~16GB.

## Future Goals

### Voice Input via ESP32 Microphones

The current interface is text-based through a browser. The goal is to place ESP32-based microphones throughout the home so users can speak commands from any room without needing a phone or computer.

The intended flow:

```
ESP32 microphone (wake word detection)
  -> streams audio to a central server
  -> speech-to-text (e.g. Whisper) transcribes the audio
  -> transcribed text is sent to Ollama for tool calling
  -> Mocha executes the device commands
  -> text-to-speech response played back through the ESP32's speaker
```

This would make Mocha a fully local, privacy-respecting voice assistant — no cloud services involved at any step.
