# AI Script Agent

An AI-powered script generator for macOS automation using AppleScript.

## Features
- Natural language to AppleScript conversion
- Voice command support
- Learning from successful executions
- Verification of results (v2)

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

## Structure
- `v1/`: Basic version with learning capabilities
- `v2/`: Enhanced version with result verification
