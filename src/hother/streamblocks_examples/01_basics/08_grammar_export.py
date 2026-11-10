#!/usr/bin/env python3
"""Export a grammar from the registry for constrained decoding on local models."""

# --8<-- [start:imports]
from random import Random

from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent
from hother.streamblocks.grammar import build_grammar, sample

# --8<-- [end:imports]

SAMPLES = 50
SEED = 7


def main() -> None:
    """Build a grammar, then check that what it allows always parses."""
    # --8<-- [start:grammar]
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)

    # GBNF text for llama.cpp, LM Studio and other compatible servers.
    # With the OpenAI client and LM Studio:
    #   client.chat.completions.create(..., extra_body={"grammar": grammar})
    grammar = registry.to_grammar()
    # --8<-- [end:grammar]
    print("\n".join(line[:110] for line in grammar.splitlines()))

    # --8<-- [start:round_trip]
    # Anything the grammar can produce is extracted with no malformed block
    rng = Random(SEED)
    blocks = errors = 0
    for _ in range(SAMPLES):
        processor = StreamBlockProcessor(registry)
        text = sample(build_grammar(registry), rng)
        events = [*processor.process_chunk(text), *processor.finalize()]
        blocks += sum(isinstance(event, BlockEndEvent) for event in events)
        errors += sum(isinstance(event, BlockErrorEvent) for event in events)
    # --8<-- [end:round_trip]

    print(f"\n{SAMPLES} random strings from the grammar: {blocks} blocks extracted, {errors} malformed")
    if errors or not blocks:
        msg = "the grammar produced text the parser rejects"
        raise RuntimeError(msg)


if __name__ == "__main__":
    main()
