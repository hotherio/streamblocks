# StreamBlocks Implementation Tasks

## Core Foundation
1. Define core types and enums (EventType, BlockState, StreamEvent)
2. Create BlockCandidate class for tracking potential blocks
3. Define BlockSyntax protocol interface
4. Create Block model with metadata and content
5. Implement DetectionResult and ParseResult dataclasses

## Stream Processor
6. Implement StreamBlockProcessor class
7. Add async stream processing with line accumulation
8. Implement candidate tracking and state management
9. Add event emission for all processing stages
10. Implement size limit enforcement

## Built-in Syntaxes
11. Implement DelimiterPreambleSyntax (!! delimiter with inline metadata)
12. Implement MarkdownFrontmatterSyntax (markdown fence with YAML frontmatter)
13. Implement DelimiterFrontmatterSyntax (delimiter markers with YAML frontmatter)

## Block Registry
14. Create BlockRegistry class with syntax registration
15. Add priority-based syntax ordering
16. Implement block type to syntax mapping
17. Add validator registration and execution

## Content Models
18. Create base content model classes
19. Implement FileOperationsContent and FileOperationsMetadata
20. Implement PatchContent and PatchMetadata

## Testing
21. Write tests for core types and models
22. Write tests for StreamBlockProcessor
23. Write tests for each built-in syntax
24. Write tests for BlockRegistry
25. Write edge case tests

## Integration
26. Create AG-UI encoder (optional - mentioned in examples)
27. Add performance monitoring utilities (optional - in examples)
28. Create usage examples