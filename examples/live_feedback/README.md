# Live Feedback Examples

This directory contains examples demonstrating pause/resume patterns for LLM streams with live user feedback.

## Overview

These examples show how to create interactive LLM applications where users can pause streams, inject feedback, and resume generation - all while maintaining conversation context.

## Examples

### 01: Simple Keyboard Pause
**File**: `01_simple_keyboard_pause.py`

The simplest pause/resume pattern using keyboard controls.

**Features:**
- Press Enter anytime to pause the stream
- When paused: type message and press Enter to add feedback and resume
- Or press Space + Enter to resume without adding message
- Live text streaming with Rich for beautiful output
- Background thread for keyboard input handling

**When to use:**
- Quick interruptions during generation
- Simple feedback injection
- Learning pause/resume basics
- Non-structured feedback (free-form text)

**Complexity:** ~150 lines | Simple

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/01_simple_keyboard_pause.py
```

**Key Concepts:**
- `asyncio.Event` for pause/resume coordination
- Background thread for keyboard input
- Conversation history management
- Simple streaming without block extraction

### 02: Two-Phase Interactive Workflow
**File**: `02_two_phase_interactive.py`

Advanced example demonstrating TWO distinct pause/resume patterns with structured blocks.

**Features:**
- **TYPE 1: Event-Driven Interactive Questions**
  - Direct event processing in the event loop
  - Uses yesno, choice, and input blocks
  - Discussion phase before operations
  - No callbacks - pure event handling

- **TYPE 2: Callback-Based Validation**
  - Callback registry for block type handlers
  - Uses confirm blocks with registered callbacks
  - Per-operation approval workflow
  - Demonstrates callback mechanism pattern

- **Rich UI with colored panels, tables, and syntax highlighting**
- **Questionary integration for beautiful CLI interactions**
- **Full conversation context management**
- **Multiple pause/resume cycles**

**When to use:**
- Complex interactive workflows requiring user approval
- Structured questions with validation
- Per-operation confirmations
- Production-grade interactive applications
- File operations with safety checks

**Complexity:** ~1100 lines | Advanced

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/02_two_phase_interactive.py
```

**Key Concepts:**
- Custom block types (yesno, choice, input, confirm, message, file_content, files_operations)
- Event-driven vs callback-based processing
- Block callback registry pattern
- Rich terminal UI components
- Questionary interactive prompts
- System prompt engineering for block generation
- Two-phase workflow orchestration

### 03: Smooth Typewriter Rendering
**File**: `03_smooth_typewriter_rendering.py`

Advanced example demonstrating smooth character-by-character text rendering with interactive controls.

**Features:**
- **Smooth Typewriter Effect**: Character-by-character rendering with configurable delay
- **Space key**: Pause/Resume stream
- **+/- keys**: Adjust rendering speed in real-time (20% increments)
- **e key**: Toggle native event display on/off
- **q key**: Quit application
- **Protocol-based design**: StreamRenderer protocol for extensibility
- **Live statistics**: Track characters written, rendering speed
- **Rich UI**: Tables, panels, and formatted output

**When to use:**
- When you need smooth visual feedback during streaming
- Applications where rendering speed matters (UX)
- Learning renderer design patterns
- Building production text streaming interfaces
- Testing different rendering speeds

**Complexity:** ~500 lines | Intermediate

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/03_smooth_typewriter_rendering.py
```

**Key Concepts:**
- `StreamRenderer` Protocol for clean interface design
- `TypewriterRenderer` with async character-by-character writes
- Configurable delay between characters (adjustable at runtime)
- Multi-key keyboard controls (Space, +/-, e, q)
- Speed calculation (chars/sec) and statistics tracking
- Separation of concerns: rendering logic vs stream control

**Performance Notes:**
- Default: 15ms delay = ~67 chars/sec
- Faster: 12ms delay = ~83 chars/sec (press +)
- Slower: 18ms delay = ~56 chars/sec (press -)
- Range: 1ms-100ms (clamped for safety)

### 04: Feedback Patterns with Cancellation
**File**: `04_feedback_patterns_with_cancellation.py`

Advanced example demonstrating multiple feedback injection patterns with timeout cancellation.

**Features:**
- **Multiple feedback patterns**:
  - Quick Options: Select from predefined feedback choices
  - Custom Text: Free-form multiline feedback input
  - Structured Forms: Multi-field feedback collection
- **Timeout cancellation**: Hard stop after 5 minutes using `hother-cancelable`
- **Rich keyboard controls**:
  - Space: Quick pause/resume (no feedback)
  - f: Structured feedback with predefined options
  - c: Custom free-form feedback
  - +/-: Adjust rendering speed
  - e: Toggle native events
  - Ctrl+C: Immediate hard cancel
  - q: Graceful quit
- **FeedbackPattern Protocol**: Extensible feedback design
- **Questionary integration**: Beautiful CLI prompts
- **Smooth typewriter rendering**: Character-by-character with instant pause
- **Session statistics**: Track characters, speed, timing

**When to use:**
- Need sophisticated feedback injection during generation
- Want multiple feedback options (quick vs. detailed)
- Require timeout-based cancellation (long operations)
- Building production-ready interactive applications
- Learning protocol-based extensible patterns
- Testing different feedback UX approaches

**Complexity:** ~600 lines | Advanced

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/04_feedback_patterns_with_cancellation.py
```

**Key Concepts:**
- `FeedbackPattern` Protocol for extensible feedback designs
- `QuickFeedbackPattern`, `CustomFeedbackPattern`, `StructuredFeedbackPattern`
- `hother-cancelable` integration for timeout management
- Multi-key keyboard controls (Space, f, c, +/-, e, q)
- Feedback injection with `inject_feedback()` method
- Questionary for beautiful interactive prompts
- Async/await coordination between feedback and streaming
- Thread-safe keyboard handling

**Feedback Pattern Examples:**

1. **Quick Options** (f key):
   ```
   How should I continue?
   > Continue in more detail
     Summarize briefly
     Give concrete examples
     Provide step-by-step instructions
     Skip to next topic
     Resume without changes
   ```

2. **Custom Text** (c key):
   ```
   Your feedback: (multiline)
   > Focus more on practical applications
   > and less on theory. Give 3 real examples
   > from industry use cases.
   ```

3. **Structured Form** (future extension):
   ```
   Change direction?
   > More technical depth

   Additional details:
   > Explain backpropagation mathematics
   ```

### 05: Textual Chat Interface (Seamless Transitions)
**File**: `05_textual_chat_interface.py`

Textual-based TUI chat interface demonstrating **seamless stream transitions** where interruptions are invisible to the user.

**Features:**
- **Textual TUI**: Production-ready terminal user interface
- **Auto-scrolling chat**: RichLog widget with Rich formatting
- **Enter**: Send message in input field
- **Seamless transitions**: Interrupting mid-stream smoothly transitions to new instruction
- **No visible cancellation**: Stream appears to naturally evolve without restart
- **Character-by-character streaming**: Smooth real-time text updates
- **Multi-turn conversation**: Full context preservation
- **Status indicator**: Shows stream state (Streaming/Ready)
- **Simple architecture**: Single async event loop (no threading)
- **Rich formatting**: Colored user vs assistant messages
- **q key**: Quit application

**Seamless Transition Example:**
```
User: "Write a long essay about AI in English"
Assistant: "...neural networks have revolutionized AI..."
[User sends mid-stream: "Change to French"]
Assistant: "...Les réseaux de neurones ont également transformé..."
```
No "cancelled" message, no visible interruption - just smooth continuation!

**When to use:**
- Want ChatGPT/Claude-like seamless interruptions
- Building production chat interfaces where UX matters
- Need invisible cancellation with smooth transitions
- Want TUI instead of CLI interface
- Learning worker cancellation patterns in Textual

**Complexity:** ~280 lines | Intermediate

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/05_textual_chat_interface.py
```

**Key Concepts:**
- `textual.app.App` for TUI application
- `RichLog` widget for auto-scrolling chat display
- `Input` widget with `on_input_submitted()` handler
- Worker pattern with `run_worker()` for async LLM streaming
- **Silent worker cancellation** with `worker.cancel()` and `WorkerCancelled` exception
- **Transition prompt engineering** for smooth continuity
- **Partial response preservation** before interruption
- Status bar with reactive state updates
- CSS styling for chat interface
- Direct widget updates from async workers

**Transition Prompt Pattern:**
```python
if partial_response_before_interrupt:
    prompt = f"""You were responding and said:

{partial_response_before_interrupt}

The user now wants: {user_message}

IMPORTANT: Continue NATURALLY and SMOOTHLY.
Don't say "Let me start over" or acknowledge the interruption.
Just continue your response, transitioning organically to fulfill
the new requirement.

Example of GOOD transition (English→French):
"...neural networks have revolutionized AI. Les réseaux de neurones..."

Continue now:"""
```

**Architecture:**
```
┌─────────────────────────────────┐
│ Status: [Streaming/Ready]       │  ← Static header
├─────────────────────────────────┤
│ You: Hello                      │
│ Assistant: Hi! How can I...     │  ← RichLog (auto-scroll)
│ [streaming text appears here▊]  │
│                                  │
├─────────────────────────────────┤
│ Type message...                  │  ← Input widget
└─────────────────────────────────┘
```

**Comparison to Example 01:**
- TUI vs CLI interface
- Seamless transitions vs visible pause/resume
- Silent cancellation vs explicit cancellation messages
- Transition prompt engineering for continuity
- Single async loop vs threading
- Auto-scrolling vs manual scrolling
- Status bar vs console prints

### 06: Multi-Threaded Conversation Management
**File**: `06_multi_threaded_conversation.py`

Advanced Textual TUI demonstrating **single LLM managing multiple conversation threads** with semantic routing.

**Features:**
- **Single LLM**: One Gemini Chat API managing all threads
- **Semantic routing**: LLM decides thread assignment based on message content
- **Structured blocks**: YAML frontmatter with thread metadata
- **Dual-view UI**:
  - "All Messages" tab: Chronological chat view (real "chat vibe")
  - Per-thread tabs: Filtered conversations by topic
- **Dynamic tab creation**: Tabs created as threads discovered
- **Sequential processing**: Messages processed in order with context isolation
- **Thread metadata**: thread_id, message_id, topic, reasoning
- **Rich formatting**: Thread badges `[T1]`, `[T2]` in chronological view
- **Auto-scrolling**: Smooth message display
- **q key**: Quit application

**LLM-as-Router Pattern:**
```
User: "Write an essay about AI"
→ LLM: thread_id=1, topic="AI Essay"

User: "Tell me a joke"
→ LLM: thread_id=2, topic="Jokes" (unrelated, new thread)

User: "Make that joke funnier"
→ LLM: thread_id=2, topic="Jokes" (related, same thread)

User: "Back to AI, explain neural networks"
→ LLM: thread_id=1, topic="AI Essay" (related to T1, same thread)
```

**When to use:**
- Need LLM to manage multiple conversation topics
- Want semantic routing without manual thread selection
- Building production multi-topic chat interfaces
- Learning LLM-as-coordinator patterns
- Need both chronological and filtered views
- Want structured block-based routing

**Complexity:** ~635 lines | Advanced

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/06_multi_threaded_conversation.py
```

**Key Concepts:**
- **Single LLM coordination**: One Gemini Chat API routing messages
- **Semantic similarity analysis**: LLM decides thread assignment
- **Structured blocks**: `ThreadedAnswer` with YAML frontmatter
- **Thread metadata**: thread_id, message_id, topic, reasoning
- **Sequential message processing**: Queue-based with asyncio
- **ThreadManager**: Tracks threads, messages, responses
- **Dual-view architecture**: Chronological + per-thread filtered
- **Dynamic UI updates**: Tab creation on thread discovery
- **Textual TabbedContent**: TabPane widgets
- **Block extraction**: BlockExtractedEvent processing
- **Context isolation**: Per-thread conversation history

**Block Structure:**
```yaml
!!start
---
block_type: threaded_answer
thread_id: 1
message_id: 1
topic: "AI Essay"
reasoning: "New topic about artificial intelligence"
---
Artificial intelligence is transforming our world...
!!end
```

**System Prompt Pattern:**
```python
SYSTEM_PROMPT = """You are a multi-threaded conversation manager.

## THREAD MANAGEMENT RULES:
- RELATED messages stay in SAME thread
- UNRELATED messages get NEW thread IDs
- Examples:
  * "write an essay on AI" → thread_id=1 (new)
  * "tell me a joke" → thread_id=2 (unrelated, new)
  * "make that joke funnier" → thread_id=2 (related, same)

### Response Format:
!!start
---
block_type: threaded_answer
thread_id: 1
message_id: 1
topic: "AI Essay"
reasoning: "New topic about AI"
---
[Response content]
!!end
"""
```

**Architecture:**
```
┌──────────────────────────────────────────────────┐
│ Multi-Threaded Chat - Thread 1: AI Essay        │
├──────────────────────────────────────────────────┤
│ [All Messages] [Thread 1: AI] [Thread 2: Jokes] │  ← TabbedContent
├──────────────────────────────────────────────────┤
│ All Messages Tab (Chronological):               │
│   You: Write essay about AI                     │
│   Assistant [T1]: AI is transforming...         │
│   You: Tell me a joke                           │
│   Assistant [T2]: Why did the chicken...        │
│   You: Make it funnier                          │
│   Assistant [T2]: Why did the quantum...        │
│                                                  │
│ Thread 1 Tab (Filtered):                        │
│   You: Write essay about AI                     │
│   Assistant: AI is transforming...              │
│                                                  │
│ Thread 2 Tab (Filtered):                        │
│   You: Tell me a joke                           │
│   Assistant: Why did the chicken...             │
│   You: Make it funnier                          │
│   Assistant: Why did the quantum...             │
├──────────────────────────────────────────────────┤
│ Type message...                                  │  ← Input widget
└──────────────────────────────────────────────────┘
```

**Data Flow:**
```
User Input
    ↓
Message Queue (Sequential)
    ↓
Build Prompt (with thread context)
    ↓
Single Gemini LLM
    ↓
Block Extraction (thread_id, message_id, topic)
    ↓
ThreadManager (assign to thread)
    ↓
UI Updates (All Messages + Thread Tab)
```

**Comparison to Example 05:**
- Multi-threaded vs single conversation
- LLM-based routing vs user control
- Structured blocks vs plain text
- Dual-view (chronological + filtered) vs single view
- Thread context isolation vs full history
- Per-thread tabs vs single chat log
- Sequential processing queue vs direct streaming
- More complex (~635 lines vs ~280 lines)

### 07: Minimal Chat
**File**: `07_minimal_chat.py`

Clean, minimal chat interface demonstrating basic block extraction with StreamBlocks.

**Features:**
- **Simple chat UI**: Clean interface with boxed messages
- **Block-based extraction**: Assistant messages extracted via blocks
- **Fence syntax**: Uses `!!start`/`!!end` delimiters with DelimiterFrontmatterSyntax
- **Minimal code**: ~220 lines of clean, understandable code
- **Textual TUI**: Production-ready terminal interface
- **Real-time streaming**: Messages appear immediately
- **No complexity**: Single conversation, no threading, no tabs
- **q key**: Quit application

**When to use:**
- Learning StreamBlocks + Textual basics
- Need a simple working chat example
- Want clean code to study and modify
- Building a basic chat interface
- Understanding block extraction fundamentals

**Complexity:** ~220 lines | Simple

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/07_minimal_chat.py
```

**Key Concepts:**
- `DelimiterFrontmatterSyntax` with fence delimiters
- Simple block definition (just id and block_type)
- `VerticalScroll` + `RichLog` pattern for proper display
- `Panel` boxes for clean message UI
- Worker pattern for async streaming
- `BlockExtractedEvent` for message display
- System prompt engineering for block format

**Block Format:**
```yaml
!!start
---
id: msg_001
block_type: message
---
Hello! How can I help you?
!!end
```

**Architecture:**
```
┌─────────────────────────────────────┐
│ Minimal Chat with StreamBlocks      │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ You                       [cyan]│ │
│ │ Hello!                          │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Assistant                [green]│ │
│ │ Hi! How can I help you?         │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ Type message...                     │
└─────────────────────────────────────┘
```

**Comparison to Other Examples:**
- **vs Example 05**: Simpler (~220 vs ~280 lines), uses blocks for extraction
- **vs Example 06**: Much simpler (~220 vs ~720 lines), no multi-threading
- **vs Examples 01-04**: TUI instead of CLI, cleaner message display

### 08: Language Switching
**File**: `08_language_switching.py`

Seamless language switching mid-stream demonstrating invisible stream cancellation and continuation.

**Features:**
- **Language buttons**: English 🇬🇧, French 🇫🇷, Spanish 🇪🇸
- **Long-form streaming**: LLM writes comprehensive AI essay (8-10 paragraphs)
- **Mid-stream switching**: Click language button while streaming
- **Seamless transitions**: No "cancelled" or "restarting" messages
- **Smart prompting**: Essay continues naturally in new language
- **Worker cancellation**: Silent stream interruption using Textual Workers
- **Visual feedback**: Active language button highlighted
- **Status tracking**: Shows current streaming state
- **q key**: Quit application

**When to use:**
- Learning silent stream cancellation patterns
- Implementing language switching features
- Understanding Worker cancellation in Textual
- Building ChatGPT/Claude-like seamless transitions
- Studying prompt engineering for continuity

**Complexity:** ~320 lines | Intermediate

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/live_feedback/08_language_switching.py
```

**Key Concepts:**
- `Worker.cancel()` for silent stream interruption
- `WorkerCancelled` exception handling without UI feedback
- Partial response preservation before language switch
- Transition prompt engineering for natural continuity
- Button state management with variant updates
- Horizontal button layout with Textual
- Real-time streaming with `TextDeltaEvent`

**Interactive Controls:**
1. Click **English** → Essay starts in English
2. Mid-stream, click **French** → Seamless transition to French
3. Essay continues from same point in French
4. Click **Spanish** → Another seamless transition
5. **q** → Quit

**Expected Behavior:**
```
English: "...neural networks revolutionized the field of AI."
[Click French]
French: "Les réseaux de neurones profonds ont également transformé..."
[Click Spanish]
Spanish: "Las redes neuronales profundas también han revolucionado..."
```

**Worker Cancellation Pattern:**
```python
if self.is_streaming:
    # Save partial essay
    self.partial_essay_before_switch = self.current_essay

    # Cancel silently
    self.current_worker.cancel()
    await self.current_worker.wait()  # Catch WorkerCancelled

    # Build transition prompt
    prompt = f"You wrote: {partial}. Continue in {new_language}."

    # Start new worker
    self.current_worker = self.run_worker(self.stream_essay())
```

**Transition Prompt Template:**
```
You were writing: {partial_essay}

Continue THE SAME ESSAY in {new_language}.

CRITICAL: DO NOT restart. Seamlessly continue.

GOOD: "...revolutionized AI. Les réseaux de neurones..."
BAD: "...AI. Now in French: Les réseaux..."
```

**Architecture:**
```
┌──────────────────────────────────────┐
│ 🇬🇧 English  🇫🇷 French  🇪🇸 Spanish │ ← Buttons
├──────────────────────────────────────┤
│ The history of Artificial Intelligence│
│ began in the 1950s when pioneers like│
│ Alan Turing and John McCarthy...     │
│                                      │
│ [Click French mid-stream]            │
│                                      │
│ Les réseaux de neurones profonds ont │
│ révolutionné le domaine de l'IA...  │
└──────────────────────────────────────┘
```

**Comparison to Other Examples:**
- **vs Example 05**: Similar cancellation pattern (~320 vs ~280 lines), button trigger instead of input
- **vs Example 07**: More complex (~320 vs ~450 lines), adds cancellation pattern
- **vs Examples 01-04**: TUI instead of CLI, demonstrates seamless transitions

### 09: Language Switching with Local LLM (KV Cache Optimized)
**File**: `09_language_switching_local_llm.py`

Same seamless language switching as Example 08, but using **local LLM Studio** with **KV cache optimization** for immediate reactions.

**Features:**
- **Local LLM endpoint**: Works with LM Studio, LocalAI, vLLM, Text Generation WebUI
- **KV cache optimization**: Full message history enables server-side attention caching
- **Immediate reactions**: Fast continuation without recomputing previous tokens
- **OpenAI-compatible API**: Uses AsyncOpenAI client with custom base_url
- **Manual history management**: Explicit message tracking for KV cache
- **No API costs**: Runs completely offline
- **Full privacy**: Data never leaves your machine
- **Same UX as Example 08**: Language buttons, seamless transitions, silent cancellation
- **q key**: Quit application

**KV Cache Benefits:**
```
Traditional (no cache):
User: "Write essay in English"
→ LLM computes all tokens [slow]

User clicks French:
→ LLM recomputes from scratch [slow]

With KV Cache (Example 09):
User: "Write essay in English"
→ LLM computes + caches attention keys/values [initial compute]

User clicks French:
→ LLM reuses cached keys/values [instant continuation]
```

**When to use:**
- Want language switching with local LLMs
- Need immediate stream transitions (KV cache)
- Want full privacy and offline capability
- Learning local LLM integration patterns
- Testing local models (Mistral, Llama, Qwen, etc.)
- No API costs - unlimited experimentation
- Understanding OpenAI adapter usage

**Complexity:** ~380 lines | Intermediate

```bash
# 1. Start LM Studio and load a model
# 2. Enable server in LM Studio (default: localhost:1234)

# 3. Set environment variables
export LLM_STUDIO_URL="http://localhost:1234/v1"
export LLM_STUDIO_MODEL="mistral-7b-instruct"  # Your loaded model

# 4. Run example
uv run python examples/live_feedback/09_language_switching_local_llm.py
```

**Key Concepts:**
- `AsyncOpenAI` with custom `base_url` for local endpoints
- `OpenAIAdapter` for chunk format handling (explicit, not auto-detect)
- Manual message history management for KV cache optimization
- Response accumulation for history preservation
- `max_tokens=-1` for unlimited generation (LM Studio)
- Same Worker cancellation pattern as Example 08
- Same seamless transition prompts as Example 08

**LocalLLMController Pattern:**
```python
class LocalLLMController:
    def __init__(self, base_url: str, model: str):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed"  # Local servers don't validate
        )
        self.messages: list[dict[str, str]] = []  # Manual history for KV cache

    async def stream(self, message: str):
        # Add to history (enables KV cache)
        self.messages.append({"role": "user", "content": message})

        # Stream with full history (server caches keys/values)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,  # Full history
            stream=True,
            max_tokens=-1
        )

        # Collect response for next KV cache
        async for chunk in stream:
            yield chunk
            # Accumulate for history

        # Save to history
        self.messages.append({"role": "assistant", "content": response})
```

**OpenAI Adapter Usage:**
```python
# In __init__
self.adapter = OpenAIAdapter()  # Explicit adapter

# In stream processing
async for event in self.processor.process_stream(
    self.controller.stream(prompt),
    adapter=self.adapter  # Required for OpenAI format
):
    if isinstance(event, TextDeltaEvent):
        display.write(event.delta)
```

**Supported Endpoints:**
- **LM Studio**: http://localhost:1234/v1 (default)
- **LocalAI**: http://localhost:8080/v1
- **vLLM**: http://localhost:8000/v1
- **Text Generation WebUI**: http://localhost:5000/v1
- **Any OpenAI-compatible endpoint**

**Architecture:**
```
┌──────────────────────────────────────┐
│ 🇬🇧 English  🇫🇷 French  🇪🇸 Spanish │ ← Buttons
├──────────────────────────────────────┤
│ Status: Streaming in English...     │
│ Endpoint: http://localhost:1234/v1  │
│ Model: mistral-7b-instruct           │
├──────────────────────────────────────┤
│ The history of AI began...          │
│ [Click French mid-stream]            │
│ Les réseaux neuronaux ont...         │
└──────────────────────────────────────┘

KV Cache:
┌─────────────────────────────────────┐
│ Server-side attention cache         │
│ ✓ Cached: User prompts + responses  │
│ ✓ Reused: Attention keys/values     │
│ → Fast continuation on language     │
│   switch (no recomputation)         │
└─────────────────────────────────────┘
```

**Comparison to Example 08:**
- **Same UX**: Identical user experience and UI
- **Same cancellation**: Worker.cancel() pattern
- **Same prompts**: Identical transition prompts
- **Different backend**: Local LLM vs Gemini API
- **Different adapter**: OpenAIAdapter (explicit) vs auto-detect
- **Different history**: Manual management vs Chat API auto-management
- **KV cache optimization**: Explicit message history for server caching
- **No API costs**: Free unlimited usage
- **Full privacy**: Offline, local execution

**Comparison to Other Examples:**
- **vs Example 08**: Same UX, local LLM instead of Gemini (~380 vs ~320 lines)
- **vs Example 05**: Button trigger instead of text input, local LLM
- **vs Examples 01-04**: TUI instead of CLI, local LLM integration

## Comparison

| Feature | 01 Simple | 02 Two-Phase | 03 Typewriter | 04 Feedback+Cancel | 05 Textual Chat | 06 Multi-Threaded | 07 Minimal Chat | 08 Language Switch | 09 Local LLM |
|---------|-----------|--------------|---------------|--------------------|--------------------|-------------------|-----------------|-------------------|--------------|
| **Lines of Code** | ~300 | ~1100 | ~500 | ~600 | ~280 | ~720 | ~450 | ~320 | ~380 |
| **Complexity** | Simple | Advanced | Intermediate | Advanced | Intermediate | Advanced | Simple | Intermediate | Intermediate |
| **Interface** | CLI | CLI | CLI | CLI | TUI (Textual) | TUI (Textual) | TUI (Textual) | TUI (Textual) | TUI (Textual) |
| **LLM Backend** | Gemini API | Gemini API | Gemini API | Gemini API | Gemini API | Gemini API | Gemini API | Gemini API | Local LLM Studio |
| **Adapter** | Auto-detect | Auto-detect | Auto-detect | Auto-detect | Auto-detect | Auto-detect | Auto-detect | Auto-detect | OpenAI (explicit) |
| **Pause Pattern** | Space key | Block-triggered | Space key | Space/f/c keys | Seamless cancel | N/A (sequential) | N/A | Button trigger | Button trigger |
| **Rendering** | Instant chunks | Instant chunks | Smooth char-by-char | Smooth char-by-char | Smooth char-by-char | Instant blocks | Instant blocks | Smooth char-by-char | Smooth char-by-char |
| **Speed Control** | No | No | Yes (+/- keys) | Yes (+/- keys) | No | No | No | No | No |
| **Feedback Type** | None | Structured blocks | None | Multiple patterns | Seamless transition | Thread routing | Thread tracking | Language switch | Language switch |
| **Feedback Options** | None | Block-based | None | Quick/Custom/Structured | Message input | Message + routing | Message IDs | Button selection | Button selection |
| **Cancellation** | No | No | No | Yes (timeout) | Yes (silent) | No | No | Yes (silent) | Yes (silent) |
| **UI** | Basic Rich | Rich panels/tables | Rich + Statistics | Rich + Questionary | Textual TUI | Textual TUI + Tabs | Textual TUI Split | Textual TUI + Buttons | Textual TUI + Buttons |
| **User Input** | Pynput | Questionary | Pynput (multi-key) | Pynput + Questionary | Textual Input | Textual Input | Textual Input | Textual Buttons | Textual Buttons |
| **Block Types** | None | 7 custom types | None | None | None | 1 (answer) | 1 (message) | None | None |
| **Callbacks** | No | Yes (Type 2) | No | No | No | No | No | No | No |
| **Validation** | No | Yes | No | No | No | No | No | No | No |
| **Renderer Design** | No | No | Yes (Protocol) | Yes (Protocol) | No | No | No | No | No |
| **Pattern Design** | No | No | No | Yes (Protocol) | No | No | No | No | No |
| **Auto-scroll** | No | No | No | No | Yes (RichLog) | Yes (RichLog) | Yes (RichLog) | Yes (RichLog) | Yes (RichLog) |
| **Threading** | Yes | Yes | Yes | Yes | No (pure async) | No (pure async) | No (pure async) | No (pure async) | No (pure async) |
| **Multi-Threading** | No | No | No | No | No | Yes (LLM-routed) | No | No | No |
| **Dual View** | No | No | No | No | No | Yes (tabs) | Yes (split) | No | No |
| **Boxed Messages** | No | No | No | No | No | Yes (Panel) | Yes (Panel) | No | No |
| **KV Cache** | No | No | No | No | No | No | No | No | Yes (optimized) |
| **Offline** | No | No | No | No | No | No | No | No | Yes |
| **API Costs** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No (free) |
| **Best For** | Quick pause/resume | Complex workflows | Smooth UX | Feedback injection | Seamless chat | Multi-topic chat | Learning basics | Language switching | Local LLM switching |

## API Requirements

**Examples 01-08** require a Gemini API key:

```bash
# Get your key at: https://aistudio.google.com/apikey
export GEMINI_API_KEY="your-key-here"
# or
export GOOGLE_API_KEY="your-key-here"
```

**Example 09** requires a local LLM server (no API key):

```bash
# 1. Install LM Studio: https://lmstudio.ai
# 2. Load a model (e.g., Mistral, Llama, Qwen)
# 3. Start server (default: localhost:1234)

# 4. Set endpoint and model
export LLM_STUDIO_URL="http://localhost:1234/v1"
export LLM_STUDIO_MODEL="mistral-7b-instruct"  # Your loaded model name

# Also compatible with:
# - LocalAI: http://localhost:8080/v1
# - vLLM: http://localhost:8000/v1
# - Text Generation WebUI: http://localhost:5000/v1
```

## Common Patterns

### Pattern 1: Simple Pause/Resume (Example 01)
```python
class SimpleKeyboardPause:
    def __init__(self):
        self._paused = asyncio.Event()
        self._feedback: str | None = None

    def pause_with_feedback(self, message: str):
        self._feedback = message
        self._paused.set()

    async def stream(self, prompt: str):
        while True:
            async for chunk in llm_stream():
                if self._paused.is_set():
                    # Save progress
                    # Add feedback
                    # Break to restart
                    break
                yield chunk
```

### Pattern 2: Event-Driven Block Processing (Example 02, Type 1)
```python
async for event in processor.process_stream(stream):
    if isinstance(event, BlockExtractedEvent):
        block = event.block

        if block.metadata.block_type == "yesno":
            # Process directly in event loop
            answer = questionary.confirm(block.content.prompt).ask()
            feedback = f"Answer: {answer}"

            # Pause stream and inject feedback
            stream.pause_and_wait_for_feedback(feedback)
            stream.resume()
```

### Pattern 3: Callback-Based Validation (Example 02, Type 2)
```python
# Register callback
callback_registry = BlockCallbackRegistry()
callback_registry.register("confirm", validate_operation)

# Callback function
def validate_operation(block: ExtractedBlock) -> tuple[bool, str]:
    approved = questionary.select(
        "Approve?",
        choices=["Yes", "No"]
    ).ask()

    feedback = "Approved!" if approved == "Yes" else "Rejected"
    return (approved == "Yes", feedback)

# Event processing
async for event in processor.process_stream(stream):
    if isinstance(event, BlockExtractedEvent):
        if callback := callback_registry.get(block.metadata.block_type):
            approved, feedback = callback(block)
            stream.pause_and_wait_for_feedback(feedback)
            stream.resume()
```

## Architecture

### Simple Pause (Example 01)

```
┌─────────────┐
│   User      │ Press Enter
│   Input     │ ───────────┐
└─────────────┘            │
                           ▼
┌─────────────┐      ┌──────────┐      ┌─────────────┐
│   Gemini    │      │  Pause   │      │  Feedback   │
│   Stream    │─────▶│  Event   │─────▶│  Injection  │
└─────────────┘      └──────────┘      └─────────────┘
                           │
                           ▼
                     ┌──────────┐
                     │  Resume  │
                     └──────────┘
```

### Two-Phase Interactive (Example 02)

```
┌──────────────────────────────────────────┐
│          PHASE 1: DISCUSSION             │
│      (Type 1: Event-Driven)              │
├──────────────────────────────────────────┤
│  1. LLM emits yesno/choice/input block   │
│  2. Event loop detects block             │
│  3. Questionary prompts user             │
│  4. Feedback injected into conversation  │
│  5. Stream resumes with feedback         │
│  6. Repeat for next question             │
└──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│          PHASE 2: OPERATIONS             │
│      (Type 2: Callback-Based)            │
├──────────────────────────────────────────┤
│  1. LLM emits confirm block              │
│  2. Event loop detects block             │
│  3. Callback registry finds validator    │
│  4. Validator prompts user for approval  │
│  5. Feedback injected into conversation  │
│  6. Stream resumes with decision         │
│  7. Repeat for next operation            │
└──────────────────────────────────────────┘
```

## Key Differences

### When to Use Example 01
- ✅ Simple pause/resume functionality
- ✅ Learning the basics of stream control
- ✅ Quick prototyping
- ✅ No rendering customization needed
- ✅ Minimal code complexity

### When to Use Example 02
- ✅ Complex workflows with multiple steps
- ✅ Structured user input with validation
- ✅ Per-operation approval workflows
- ✅ Production applications
- ✅ Safety-critical operations (file changes, deletions)
- ✅ Two-phase workflows (discussion + execution)
- ✅ Need beautiful CLI with Rich and Questionary

### When to Use Example 03
- ✅ Need smooth visual rendering (UX-focused)
- ✅ Want adjustable rendering speed
- ✅ Building production streaming interfaces
- ✅ Learning renderer design patterns
- ✅ Testing different rendering speeds for optimal UX
- ✅ Want protocol-based extensible architecture

### When to Use Example 04
- ✅ Need sophisticated feedback injection during generation
- ✅ Want multiple feedback options (quick select vs. detailed text)
- ✅ Require timeout-based cancellation for long operations
- ✅ Building production applications with rich interactions
- ✅ Learning protocol-based extensible feedback patterns
- ✅ Testing different feedback UX approaches
- ✅ Need questionary integration for beautiful prompts

### When to Use Example 05
- ✅ Want ChatGPT/Claude-like seamless interruptions
- ✅ Building production chat interfaces where UX matters
- ✅ Need invisible cancellation with smooth transitions
- ✅ Want TUI instead of CLI interface
- ✅ Learning worker cancellation patterns in Textual
- ✅ Want simpler async architecture (no threading)
- ✅ Need visual chat history with Rich formatting

### When to Use Example 06
- ✅ Need LLM to manage multiple conversation topics
- ✅ Want semantic routing without manual thread selection
- ✅ Building production multi-topic chat interfaces
- ✅ Learning LLM-as-coordinator patterns
- ✅ Need both chronological and filtered views
- ✅ Want structured block-based routing
- ✅ Need per-thread conversation isolation

### When to Use Example 07
- ✅ **Learning StreamBlocks + Textual** - Best starting point!
- ✅ Need a simple, working chat example
- ✅ Want clean, readable code to study and modify
- ✅ Understanding block extraction basics
- ✅ Building your first chat interface
- ✅ Need minimal complexity (~450 lines)
- ✅ Want boxed message UI without complexity

### When to Use Example 08
- ✅ Need seamless language switching mid-stream
- ✅ Learning worker cancellation patterns in Textual
- ✅ Want ChatGPT/Claude-like invisible stream interruption
- ✅ Building applications with dynamic language support
- ✅ Understanding transition prompt engineering
- ✅ Using Gemini API for streaming

### When to Use Example 09
- ✅ **Want local LLM integration** - No API costs, full privacy
- ✅ Need language switching with local models
- ✅ Learning KV cache optimization patterns
- ✅ Want offline capability (no internet required)
- ✅ Understanding OpenAI adapter usage
- ✅ Testing with local models (Mistral, Llama, Qwen, etc.)
- ✅ Unlimited experimentation without API costs
- ✅ Full data privacy - nothing leaves your machine

## Troubleshooting

### Issue: Stream doesn't pause

**Example 01:**
- Check that keyboard listener thread is running
- Verify Enter key is being pressed
- Check terminal supports input()

**Example 02:**
- Verify LLM is emitting blocks correctly
- Check block format matches syntax
- Ensure event loop is processing BlockExtractedEvent

### Issue: Feedback not applied

**Both Examples:**
- Check conversation history is being updated
- Verify pause/resume coordination with asyncio.Event
- Ensure feedback is added before stream restarts

### Issue: Missing API key

```bash
export GEMINI_API_KEY="your-key-here"
```

Get your key at: https://aistudio.google.com/apikey

### Issue: Rich UI not displaying

- Verify Rich is installed: `uv pip list | grep rich`
- Check terminal supports ANSI colors
- Try different terminal emulator

## Further Reading

- [StreamBlocks Documentation](../../README.md)
- [Adapter Examples](../adapters/README.md)
- [Interactive Blocks](../../src/hother/streamblocks/blocks/interactive.py)
- [File Blocks](../../src/hother/streamblocks/blocks/files.py)

## Summary

This directory demonstrates nine complementary approaches to interactive LLM streaming:

1. **Simple Keyboard Pause (01)**: Minimal pause/resume with Space key (CLI)
2. **Two-Phase Interactive (02)**: Advanced workflow with structured blocks and callbacks (CLI)
3. **Smooth Typewriter Rendering (03)**: UX-focused rendering with speed control (CLI)
4. **Feedback Patterns with Cancellation (04)**: Multiple feedback patterns with timeout management (CLI)
5. **Textual Chat Interface (05)**: Seamless stream transitions with invisible cancellation (TUI)
6. **Multi-Threaded Conversation (06)**: Single LLM managing multiple conversation threads (TUI)
7. **Minimal Chat (07)**: Clean, simple chat with block extraction - perfect for learning (TUI)
8. **Language Switching (08)**: Seamless language switching mid-stream with Gemini API (TUI)
9. **Language Switching with Local LLM (09)**: Same as 08 but with local LLM Studio and KV cache optimization (TUI)

**Learning Path:**
- **START HERE:** **Example 07** - Simple, working chat example (~450 lines)
- Then try **Example 01** to understand pause/resume basics (CLI)
- Try **Example 05** for seamless transitions and advanced Textual patterns
- Try **Example 08** for language switching and worker cancellation patterns
- **For local LLMs:** Try **Example 09** to learn local LLM integration with KV cache
- Explore **Example 03** to learn smooth rendering and renderer design patterns
- Try **Example 04** to master feedback injection and cancellation patterns
- Dive into **Example 02** for production-grade interactive workflows with validation
- Master **Example 06** for LLM-as-coordinator patterns with multi-threaded chat

**Feature Matrix:**
- **Pause/Resume**: Examples 01-04
- **Smooth Rendering**: Examples 03, 04, 05, 08, 09
- **Feedback Injection**: Examples 02, 04, 05
- **Cancellation/Timeout**: Examples 04, 05, 08, 09
- **Structured Blocks**: Examples 02, 06, 07
- **TUI Interface**: Examples 05, 06, 07, 08, 09
- **CLI Interface**: Examples 01-04
- **No Threading**: Examples 05, 06, 07, 08, 09 (pure async)
- **Seamless Transitions**: Examples 05, 08, 09
- **Multi-Threading**: Example 06 only (LLM-routed)
- **Language Switching**: Examples 08, 09
- **Local LLM**: Example 09 only
- **KV Cache Optimization**: Example 09 only
- **Boxed Messages**: Examples 06, 07
- **Best for Learning**: Example 07 (simplest)
