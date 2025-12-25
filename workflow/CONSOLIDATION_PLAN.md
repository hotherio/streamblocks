# StreamBlocks Consolidation Plan

This document outlines the gaps between the `cancelable` library (reference) and `streamblocks`, with a plan to align streamblocks with the same mature project structure.

## Executive Summary

The `cancelable` library represents a mature, production-ready Python project. StreamBlocks needs to be consolidated to match this standard across CI/CD, documentation, examples, and configuration.

---

## 1. CI/CD Configuration

### Current State (streamblocks)

| Workflow | Status |
|----------|--------|
| `pull_request.yaml` | Exists but tests use `|| exit 0` (never fails) |
| `docs.yaml` | Exists |
| `release.yml` | Exists |
| `bump.yml` | Exists |
| `stale.yml` | Exists |
| `test.yaml` | **MISSING** |
| Codecov integration | **MISSING** |

### Gap Analysis

1. **Missing `test.yaml` workflow**
   - Cancelable runs tests on push to main with coverage upload
   - Tests Python 3.12, 3.13, 3.14
   - Uploads coverage to Codecov
   - Stores coverage artifacts

2. **Missing `.codecov.yml`**
   - Cancelable has threshold configuration (1% patch/project)
   - Coverage range: 70-100%

3. **pull_request.yaml issues**
   - `|| exit 0` on tests means failures are silently ignored
   - Should fail on test/lint failures

### Actions Required

- [ ] Create `.github/workflows/test.yaml` workflow (copy from cancelable, adapt package name)
- [ ] Create `.github/.codecov.yml` configuration
- [ ] Fix `pull_request.yaml` to remove `|| exit 0` from test/lint commands
- [ ] Add Python 3.14 to test matrix

---

## 2. Examples Restructuring

### Current State (streamblocks)

```
examples/
├── adapters/          # 13 examples
├── integrations/      # 1 example
├── logging/           # 3 examples
├── syntaxes/          # 2 examples
├── ui/                # 2 examples
├── *.py               # ~10 root examples
├── run_examples.py    # Example runner
└── README.md          # Comprehensive guide
```

### Target State (aligned with cancelable)

```
examples/
├── 00_basics/                                # Foundational examples
│   ├── 01_basic_usage.py                     # Basic StreamBlocks usage
│   ├── 02_minimal_api.py                     # Minimal API example
│   ├── 03_error_handling.py                  # Error handling patterns
│   └── 04_structured_output.py               # Structured output handling
├── 01_syntaxes/                              # Syntax-related examples
│   ├── 01_markdown_frontmatter.py            # Markdown frontmatter syntax
│   ├── 02_delimiter_frontmatter.py           # Delimiter with frontmatter
│   └── 03_parsing_decorators.py              # Using parsing decorators
├── 02_adapters/                              # Stream adapter examples
│   ├── 01_identity_adapter_plain_text.py     # Plain text (no adapter)
│   ├── 02_gemini_auto_detect.py              # Gemini with auto-detection
│   ├── 03_openai_explicit_adapter.py         # OpenAI explicit adapter
│   ├── 04_anthropic_adapter.py               # Anthropic event streams
│   ├── 05_mixed_event_stream.py              # Mixed event streams
│   ├── 06_text_delta_streaming.py            # Real-time text delta events
│   ├── 07_block_opened_event.py              # Block opening detection
│   ├── 08_configuration_flags.py             # Processor configuration
│   ├── 09_custom_adapter.py                  # Custom adapter creation
│   ├── 10_callable_adapter.py                # Callable adapters
│   ├── 11_attribute_adapter_generic.py       # Generic attribute adapters
│   ├── 12_disable_original_events.py         # Event emission control
│   └── 13_manual_chunk_processing.py         # Manual chunk processing
├── 03_content/                               # Content processing
│   └── 01_patch_content.py                   # Patch content operations
├── 04_logging/                               # Logging examples
│   ├── 01_stdlib_logging.py                  # Python stdlib logging
│   ├── 02_structlog.py                       # Structured logging
│   └── 03_custom_logger.py                   # Custom logger implementation
├── 05_integrations/                          # Framework integrations
│   └── 01_pydantic_ai_integration.py         # PydanticAI integration
├── 06_providers/                             # AI Provider demos
│   ├── 01_gemini_simple_demo.py              # Simple Gemini demo
│   └── 02_gemini_architect.py                # Complex Gemini example
├── 07_ui/                                    # User interface examples
│   ├── 01_interactive_blocks.py              # Interactive block types (CLI)
│   └── 02_interactive_ui_demo.py             # Full Textual UI demo (TUI)
├── run_examples.py                           # Example runner
└── README.md                                 # Comprehensive guide
```

### Mapping Table

| Old Location | New Location |
|--------------|--------------|
| `basic_usage.py` | `00_basics/01_basic_usage.py` |
| `minimal_api_example.py` | `00_basics/02_minimal_api.py` |
| `error_handling_example.py` | `00_basics/03_error_handling.py` |
| `structured_output_example.py` | `00_basics/04_structured_output.py` |
| `syntaxes/markdown_frontmatter_example.py` | `01_syntaxes/01_markdown_frontmatter.py` |
| `syntaxes/delimiter_frontmatter_example.py` | `01_syntaxes/02_delimiter_frontmatter.py` |
| `parsing_decorators_example.py` | `01_syntaxes/03_parsing_decorators.py` |
| `adapters/01_*.py` → `adapters/13_*.py` | `02_adapters/01_*.py` → `02_adapters/13_*.py` |
| `patch_content_example.py` | `03_content/01_patch_content.py` |
| `logging/stdlib_logging_example.py` | `04_logging/01_stdlib_logging.py` |
| `logging/structlog_example.py` | `04_logging/02_structlog.py` |
| `logging/custom_logger_example.py` | `04_logging/03_custom_logger.py` |
| `integrations/pydantic_ai_integration.py` | `05_integrations/01_pydantic_ai_integration.py` |
| `gemini_simple_demo.py` | `06_providers/01_gemini_simple_demo.py` |
| `gemini_architect_example.py` | `06_providers/02_gemini_architect.py` |
| `ui/interactive_blocks_example.py` | `07_ui/01_interactive_blocks.py` |
| `ui/interactive_ui_demo.py` | `07_ui/02_interactive_ui_demo.py` |

### Actions Required

- [ ] Create new numbered directory structure
- [ ] Move and rename all example files with numbered prefixes
- [ ] Update `run_examples.py` to work with new structure
- [ ] Update `.examples.yaml` configuration for new paths
- [ ] Update `examples/README.md` with new structure
- [ ] Update any imports or references in documentation

---

## 3. Documentation Structure

### Current State (streamblocks)

```
docs/
├── index.md
├── about.md
├── assets/
│   └── logo.png
└── stylesheets/
    └── extra.css
```

### Target State (aligned with cancelable)

```
docs/
├── .hooks/
│   └── main.py                   # Custom mkdocs hooks
├── javascripts/
│   ├── tablesort.js              # Table sorting
│   ├── mathjax.js                # Math rendering
│   └── mermaid.js                # Diagram support
├── stylesheets/
│   └── extra.css                 # Custom styles
├── assets/
│   └── logo.png                  # Logo
├── index.md                      # Landing page
├── installation.md               # Installation guide
├── getting_started.md            # Quick start guide
├── basics.md                     # Core concepts
├── advanced.md                   # Advanced usage
├── streaming.md                  # Stream processing (domain-specific)
├── patterns.md                   # Common patterns
├── performance.md                # Performance considerations
├── troubleshooting.md            # Common issues
├── community.md                  # Support & community
├── contributing.md               # Contribution guide
├── examples/
│   ├── index.md                  # Examples overview
│   ├── setup.md                  # Running examples
│   ├── basic.md                  # Basic examples walkthrough
│   ├── syntaxes.md               # Syntax examples
│   ├── adapters.md               # Adapter examples
│   ├── logging.md                # Logging examples
│   └── integrations.md           # Integration examples
├── integrations/
│   ├── index.md                  # Integrations overview
│   └── pydantic_ai.md            # PydanticAI integration guide
└── reference/
    ├── index.md                  # API reference overview
    ├── core.md                   # Core components API
    ├── syntaxes.md               # Syntaxes API
    ├── adapters.md               # Adapters API
    └── blocks.md                 # Blocks API
```

### Actions Required

- [ ] Create `docs/.hooks/main.py` for custom mkdocs hooks
- [ ] Create `docs/javascripts/` with tablesort.js, mathjax.js, mermaid.js
- [ ] Create `docs/installation.md`
- [ ] Create `docs/getting_started.md`
- [ ] Create `docs/basics.md` (core concepts: syntaxes, blocks, events)
- [ ] Create `docs/advanced.md` (adapters, custom syntaxes, custom blocks)
- [ ] Create `docs/streaming.md` (stream processing patterns)
- [ ] Create `docs/patterns.md` (common usage patterns)
- [ ] Create `docs/performance.md`
- [ ] Create `docs/troubleshooting.md`
- [ ] Create `docs/community.md`
- [ ] Create `docs/contributing.md`
- [ ] Create `docs/examples/` directory with walkthrough docs
- [ ] Create `docs/integrations/` with PydanticAI guide
- [ ] Create `docs/reference/` with API documentation

---

## 4. mkdocs.yml Configuration

### Gap Analysis

| Feature | Cancelable | StreamBlocks |
|---------|------------|--------------|
| Navigation structure | Comprehensive | Minimal (2 pages) |
| Snippets with base_path | Yes | No |
| Social plugin | Yes | No |
| Glightbox plugin | Yes | No |
| Validation block | Yes | No |
| Custom hooks | Yes | No |
| Mermaid diagrams | Yes | Partial (format string issue) |
| Watch paths | Includes examples | Only src |
| Search features | highlight, suggest, share | Basic |
| mkdocstrings options | Comprehensive | Basic |

### Actions Required

- [ ] Update `mkdocs.yml` navigation structure to match new docs
- [ ] Add snippets base_path configuration for examples
- [ ] Add social plugin for social cards
- [ ] Add glightbox plugin for image galleries
- [ ] Add validation block for warnings
- [ ] Add hooks configuration
- [ ] Fix mermaid fence format (remove quotes)
- [ ] Add search.suggest, search.highlight, search.share
- [ ] Enhance mkdocstrings options
- [ ] Update watch paths to include examples
- [ ] Add external imports (pydantic, anyio)

---

## 5. pyproject.toml Configuration

### Gap Analysis

| Feature | Cancelable | StreamBlocks |
|---------|------------|--------------|
| Versioning | hatch-vcs (dynamic) | Static (0.1.0) |
| Build backend | hatchling | uv_build |
| Line length | 128 | 120 |
| Coverage fail_under | 100 | None |
| pytest-xdist | Yes | No |
| pytest-mock | Yes | No |
| dirty-equals | Yes | No |
| inline-snapshot | Yes | No |

### Actions Required

- [ ] Consider switching to hatch-vcs for dynamic versioning
- [ ] Add coverage `fail_under` threshold (suggest starting at 80%)
- [ ] Add `pytest-xdist` for parallel test execution
- [ ] Add `pytest-mock` for mocking support
- [ ] Consider `dirty-equals` and `inline-snapshot` for better assertions
- [ ] Align line length to 128 (optional)

---

## 6. Lefthook Configuration

The lefthook configurations are already quite similar. Minor alignment:

### Actions Required

- [ ] Align hook naming conventions (minor, optional)

---

## 7. Testing Structure

### Current State (streamblocks)

```
tests/
├── adapters/
├── conftest.py
├── test_*.py
```

### Target State (aligned with cancelable)

```
tests/
├── unit/                         # Unit tests
│   ├── test_types.py
│   ├── test_models.py
│   ├── test_registry.py
│   ├── test_processor.py
│   └── test_syntaxes/            # Syntax tests
├── integration/                  # Integration tests
│   └── test_adapters/            # Adapter integration tests
├── performance/                  # Performance benchmarks
└── conftest.py
```

### Actions Required

- [ ] Reorganize tests into unit/integration/performance directories
- [ ] Add performance benchmarks
- [ ] Add stream-specific integration tests

---

## 8. Additional Files

### Gap Analysis

| File | Cancelable | StreamBlocks |
|------|------------|--------------|
| `.secrets.baseline` | Yes | Yes |
| `.editorconfig` | Yes | Yes |
| `.python-version` | Yes | Yes |
| `Makefile` | Yes | Yes |
| `cliff.toml` | Yes | Yes |
| `renovate.json` | Yes | Yes |
| `.codecov.yml` | Yes | **MISSING** |

### Actions Required

- [ ] Create `.github/.codecov.yml` (or root `.codecov.yml`)

---

## Priority Order

### Phase 1: CI/CD (Critical)

1. Create `test.yaml` workflow
2. Add `.codecov.yml`
3. Fix `pull_request.yaml` to fail on errors

### Phase 2: Examples Restructuring (High)

1. Create new numbered directory structure
2. Move and rename all example files
3. Update runner and configuration
4. Update README.md

### Phase 3: Documentation Structure (High)

1. Create basic doc structure (installation, getting_started, basics)
2. Update mkdocs.yml with proper navigation
3. Add JS files and hooks

### Phase 4: Documentation Content (Medium)

1. Create advanced docs (patterns, performance, troubleshooting)
2. Create integration guides
3. Create example walkthroughs
4. Create API reference documentation

### Phase 5: Configuration & Testing (Low)

1. Consider dynamic versioning
2. Add coverage threshold
3. Add additional test dependencies
4. Reorganize test structure

---

## Implementation Tracks

### Track A: CI/CD

- [ ] A.1: Create `test.yaml` workflow
- [ ] A.2: Create `.codecov.yml`
- [ ] A.3: Fix `pull_request.yaml`

### Track B: Examples

- [ ] B.1: Create numbered directory structure
- [ ] B.2: Move basic examples to `00_basics/`
- [ ] B.3: Move syntax examples to `01_syntaxes/`
- [ ] B.4: Move adapter examples to `02_adapters/`
- [ ] B.5: Move content examples to `03_content/`
- [ ] B.6: Move logging examples to `04_logging/`
- [ ] B.7: Move integration examples to `05_integrations/`
- [ ] B.8: Move provider examples to `06_providers/`
- [ ] B.9: Move UI examples to `07_ui/`
- [ ] B.10: Update `run_examples.py`
- [ ] B.11: Update `.examples.yaml`
- [ ] B.12: Update `examples/README.md`

### Track C: Documentation Infrastructure

- [ ] C.1: Create `docs/.hooks/main.py`
- [ ] C.2: Create `docs/javascripts/` files
- [ ] C.3: Update `mkdocs.yml` configuration
- [ ] C.4: Add required mkdocs plugins to pyproject.toml

### Track D: Documentation Content

- [ ] D.1: Create `docs/installation.md`
- [ ] D.2: Create `docs/getting_started.md`
- [ ] D.3: Create `docs/basics.md`
- [ ] D.4: Create `docs/advanced.md`
- [ ] D.5: Create `docs/streaming.md`
- [ ] D.6: Create `docs/patterns.md`
- [ ] D.7: Create `docs/performance.md`
- [ ] D.8: Create `docs/troubleshooting.md`
- [ ] D.9: Create `docs/community.md`
- [ ] D.10: Create `docs/contributing.md`
- [ ] D.11: Create `docs/examples/` section
- [ ] D.12: Create `docs/integrations/` section
- [ ] D.13: Create `docs/reference/` section

### Track E: Configuration

- [ ] E.1: Add coverage threshold
- [ ] E.2: Add pytest-xdist, pytest-mock
- [ ] E.3: Consider dynamic versioning
- [ ] E.4: Reorganize test structure (optional)

---

## Notes

- The streamblocks example runner is well-designed and should be preserved
- Focus on maintaining backward compatibility during migration
- Documentation can be written incrementally as features mature
- Consider using snippets to embed example code directly in docs
