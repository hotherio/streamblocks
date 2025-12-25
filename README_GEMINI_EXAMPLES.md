# Gemini + Streamblocks Examples

This directory contains examples showing how to use Streamblocks with Google's Gemini AI.

## Prerequisites

1. Install the Google AI SDK:
   ```bash
   pip install google-genai
   ```

2. Get a Gemini API key from https://makersuite.google.com/app/apikey

3. Set the environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here" # pragma: allowlist secret
   ```

## Available Examples

### 1. Simple Demo (`gemini_simple_demo.py`)

The simplest example showing file operations with Gemini:

```bash
# Run with default prompt
python examples/gemini_simple_demo.py

# Or provide your own prompt
python examples/gemini_simple_demo.py "Create a Flask web server"
```

Features:
- File operations (create/edit/delete)
- Real-time streaming from Gemini
- Progress tracking

### 2. Complete Demo (`gemini_complete_demo.py`)

More comprehensive example with multiple block types:

```bash
python examples/gemini_complete_demo.py
```

Features:
- File operations
- Tool calls (calculations, text analysis)
- Code patches
- Colored output

### 3. Multi-Block Demo (`multi_block_demo.py`)

Demonstrates all block types without requiring Gemini API:

```bash
python examples/multi_block_demo.py
```

Features:
- Pre-defined scenarios
- All block types (files, tools, patches, visualizations, memory)
- No API key required

### 4. Test Scripts

Quick test scripts to verify setup:

```bash
# Test Gemini API connection
python examples/test_gemini_api.py

# Debug raw Gemini responses
python examples/debug_gemini_response.py
```

## Example Prompts

Try these prompts with the demos:

1. **Basic File Creation**
   - "Create a Python hello world script"
   - "Create a README file for my project"
   - "Create a basic web server with Flask"

2. **Project Setup**
   - "Create a Python package structure with tests"
   - "Set up a Django project structure"
   - "Create a CLI tool with argparse"

3. **Code Generation**
   - "Create a calculator that supports basic operations"
   - "Build a simple todo list manager"
   - "Create a file organizer script"

## How It Works

1. **System Prompt**: The examples teach Gemini about available block syntaxes
2. **Streaming**: Responses are streamed in real-time from Gemini
3. **Block Extraction**: Streamblocks processes the stream and extracts structured blocks
4. **Execution**: Extracted blocks are processed (files listed, tools executed, etc.)

## Block Syntax Reference

### File Operations
```
!!files:operation_name
path/to/file.py:C
another/file.md:E
old/file.txt:D
!!end
```

### Tool Calls
```yaml
```toolcall
---
block_type: tool_call
tool_name: calculate
description: What this does
---
expression: "2 + 2"
```

### Patches
```yaml
```patch
---
block_type: patch
file_path: src/main.py
description: Adding feature
---
@@ -1,3 +1,5 @@
 def main():
+    # New code here
     pass
```

## Troubleshooting

1. **API Key Issues**
   - Verify your API key is set: `echo $GEMINI_API_KEY`
   - Check the key is valid at https://makersuite.google.com

2. **Import Errors**
   - Ensure Streamblocks is installed: `pip install -e .` from project root
   - Check you have google-genai installed: `pip install google-genai`

3. **Block Parsing Issues**
   - Gemini may wrap blocks in code fences - this is expected
   - The examples handle common formatting variations

4. **Rate Limits**
   - Free tier has rate limits
   - Add delays between requests if needed
