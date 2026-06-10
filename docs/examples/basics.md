# Basics Examples

Foundational examples covering the core StreamBlocks workflow: setting up a processor, handling events and errors, producing structured output, and validating blocks. All run offline with no API keys.

## Basic Usage

A complete tour of the standard workflow: registry setup, stream processing, and handling the main event types including section delta events. Good reference for the full event vocabulary.

#! src/hother/streamblocks_examples/01_basics/01_basic_usage.py

## Minimal API

Shows the smallest possible setup using default models — no custom metadata or content classes. Useful as a quick-reference template when you just need block extraction without typing.

#! src/hother/streamblocks_examples/01_basics/02_minimal_api.py

## Error Handling

Demonstrates structured error handling: accessing detailed error information from `BlockRejectedEvent`, including the original exception objects, so failures can be diagnosed and recovered from.

#! src/hother/streamblocks_examples/01_basics/03_error_handling.py

## Structured Output

Uses the `create_structured_output_block` factory to build type-safe blocks from any Pydantic model, turning free-form LLM output into validated structured data.

#! src/hother/streamblocks_examples/01_basics/04_structured_output.py

## Metadata Validators

Validates block metadata early — before content streams in — and shows the available `MetadataValidationFailureMode` options for deciding what happens when validation fails.

#! src/hother/streamblocks_examples/01_basics/05_metadata_validators.py

## Validator Composition

Chains multiple validators (metadata, content, and general block validators) on a single block type, showing how validation responsibilities compose.

#! src/hother/streamblocks_examples/01_basics/06_validator_composition.py
