# AI Script Agent

An AI-powered script generator for macOS automation using AppleScript.

## Features
- Natural language to AppleScript conversion
- Voice command support
- Learning from successful executions
- Verification of results (v2)
- Voice feedback responses (v3)

## Installation
```bash
pip install -r requirements.txt
```

## Usage
### Basic Version (v1)
```bash
python src/v1/ai_script_agent_learning.py
```

### Version with Result Verification (v2)
```bash
python src/v2/ai_script_agent_learning.py --verify
```

### Version with Voice Feedback (v3)
```bash
python src/v3/ai_script_agent_learning.py --verify --voice
```

## Structure
- `v1/`: Basic version with learning capabilities
- `v2/`: Enhanced version with result verification
- `v3/`: Added voice feedback using macOS text-to-speech

## Changelog

### v3 (Current)
- Added voice feedback using macOS text-to-speech
- System now speaks responses instead of just displaying them
- Added --voice flag to toggle voice feedback

### v2
- Added result verification
- Enhanced feedback collection
- Improved solution learning

### v1
- Initial release
- Basic AppleScript generation
- Voice command support
