# Logging

Integrate StreamBlocks with stdlib logging, structlog, loguru, or a custom logger.

## How loggers are injected

Both `Registry` and `StreamBlockProcessor` accept an optional `logger` argument:

```python
registry = Registry(syntax=syntax, logger=logger)
processor = StreamBlockProcessor(registry, logger=logger)
```

Anything that implements the `Logger` protocol works: an object with `debug`, `info`, `warning`, `error`, and `exception` methods. StreamBlocks passes structured data as **direct keyword arguments** — the native pattern of structlog and loguru:

```python
logger.info("block_extracted", block_type="files", block_id="abc123")
```

If you pass nothing, both components default to a wrapped `logging.getLogger(__name__)`, so log output integrates with your existing stdlib configuration out of the box.

## Stdlib logging

Stdlib loggers don't accept arbitrary kwargs, so wrap them in `StdlibLoggerAdapter`. The adapter appends structured fields to the message (`msg | key=value …`) and also stores them in the `extra` dict for handlers and filters:

```python
--8<-- "src/hother/streamblocks_examples/05_logging/01_stdlib_logging.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/05_logging/01_stdlib_logging.py)

## Structlog

Structlog loggers support direct kwargs natively, so no adapter is needed — configure structlog and pass the bound logger straight in. Install with the `structlog` extra (`pip install streamblocks[structlog]`):

```python
--8<-- "src/hother/streamblocks_examples/05_logging/02_structlog.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/05_logging/02_structlog.py)

## Loguru

Loguru also supports direct kwargs natively. Install with the `loguru` extra (`pip install streamblocks[loguru]`) and pass the global logger directly:

```python
from loguru import logger

registry = Registry(syntax=syntax, logger=logger)
processor = StreamBlockProcessor(registry, logger=logger)
```

## Custom logger

Any object with the five methods satisfies the protocol — no base class required. Accept `**kwargs` to receive the structured fields:

```python
--8<-- "src/hother/streamblocks_examples/05_logging/03_custom_logger.py:logger"
```

Then inject it like any other logger:

```python
--8<-- "src/hother/streamblocks_examples/05_logging/03_custom_logger.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/05_logging/03_custom_logger.py)

## What gets logged

The registry logs block-type registration and block parsing/validation steps at `DEBUG`. The processor logs stream start at `DEBUG` and input adapter auto-detection at `INFO`. Run any example with level `DEBUG` to see the full trace, then raise the level in production.

## Next steps

- [Error Handling](error-handling.md) — turn block errors into events you can act on, not just log lines.
- [Performance Tuning](performance.md) — processor configuration knobs.
- [Validation](validation.md) — where validation failures surface.
