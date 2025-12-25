"""Example focusing on PatchContent with various patch formats."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Literal

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock


# Custom models for this example
class SimplePatchMetadata(BaseMetadata):
    """Simplified metadata for patch blocks."""

    id: str
    block_type: Literal["patch"] = "patch"  # type: ignore[assignment]
    category: str | None = None
    priority: str | None = None

    # Derived from content
    file: str = ""
    start_line: int = 0


class SimplePatchContent(BaseContent):
    """Content model that parses file info from first line."""

    diff: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> "SimplePatchContent":
        """Parse patch content, extracting file info from first line."""
        lines = raw_text.strip().split("\n")
        if not lines:
            msg = "Empty patch"
            raise ValueError(msg)

        # The content already has the diff, just store it
        return cls(raw_content=raw_text, diff=raw_text.strip())


# Create the block type
SimplePatch = Block[SimplePatchMetadata, SimplePatchContent]


async def example_stream() -> AsyncIterator[str]:
    """Example stream with various patch formats."""
    text = dedent("""
        Let's demonstrate different patch formats that our PatchContent can handle.

        !!patch01:patch
        auth/login.py:45
         def login(username, password):
             # Check credentials
        -    if username == "admin" and password == "admin": # pragma: allowlist secret
        +    user = User.query.filter_by(username=username).first()
        +    if user and user.check_password(password):
                 session['user_id'] = user.id
                 return redirect('/dashboard')
             else:
                 flash('Invalid credentials')
                 return render_template('login.html')
        !!end

        Here's a patch adding a new feature:

        !!patch02:patch:feature
        models/user.py:120
             def get_permissions(self):
                 return self.permissions

        +    def has_permission(self, permission_name):
        +        \"\"\"Check if user has a specific permission.\"\"\"
        +        return permission_name in self.get_permissions()
        +
        +    def add_permission(self, permission):
        +        \"\"\"Add a permission to the user.\"\"\"
        +        if permission not in self.permissions:
        +            self.permissions.append(permission)
        +            self.save()
        +
             def __repr__(self):
                 return f'<User {self.username}>'
        !!end

        Now let's fix a bug in the API:

        !!patch03:patch:bugfix:critical
        api/endpoints.py:200
         @app.route('/api/data/<id>')
         def get_data(id):
        -    # SECURITY: SQL injection vulnerability!
        -    query = f"SELECT * FROM data WHERE id = {id}"
        -    result = db.execute(query)
        +    # Fixed: Use parameterized query
        +    result = db.query(Data).filter_by(id=id).first()
        +    if not result:
        +        return jsonify({'error': 'Not found'}), 404
             return jsonify(result.to_dict())
        !!end

        Let's update configuration handling:

        !!patch04:patch
        config/settings.py:50
         # Database configuration
        -DATABASE_URL = "sqlite:///app.db"
        +DATABASE_URL = os.environ.get(
        +    'DATABASE_URL',
        +    'postgresql://localhost/myapp'
        +)

         # Cache configuration
        -CACHE_TYPE = "simple"
        -CACHE_DEFAULT_TIMEOUT = 300
        +CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')
        +CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '3600'))
        +CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        !!end

        Finally, let's remove deprecated code:

        !!patch05:patch:cleanup
        utils/legacy.py:10
        -# DEPRECATED: Remove in v2.0
        -def old_hash_password(password):
        -    \"\"\"Legacy password hashing - DO NOT USE.\"\"\"
        -    import md5
        -    return md5.new(password).hexdigest()
        -
        -def migrate_password(user, plain_password):
        -    \"\"\"Migrate from old hash to new.\"\"\"
        -    if user.password_hash == old_hash_password(plain_password):
        -        user.set_password(plain_password)
        -        user.save()
        -        return True
        -    return False
        -
         # Modern password utilities
         from werkzeug.security import generate_password_hash, check_password_hash
        !!end

        That's all the patches for this update!
    """)

    # Simulate streaming with realistic network-like behavior
    # Sometimes fast, sometimes slow chunks
    import random

    i = 0
    while i < len(text):
        # Random chunk size between 20-100 chars
        chunk_size = random.randint(20, 100)
        chunk = text[i : i + chunk_size]
        yield chunk
        i += chunk_size

        # Random delay between 5-15ms
        delay = random.uniform(0.005, 0.015)
        await asyncio.sleep(delay)


async def main() -> None:
    """Main example function."""
    # Create delimiter preamble syntax for patches
    patch_syntax = DelimiterPreambleSyntax()

    # Create type-specific registry and register block
    registry = Registry(syntax=patch_syntax)

    # Add validators for patch quality
    def validate_patch_content(block: SimplePatch) -> bool:
        """Ensure patches have actual changes."""
        lines = block.content.diff.strip().split("\n")
        has_additions = any(line.startswith("+") for line in lines)
        has_deletions = any(line.startswith("-") for line in lines)
        return has_additions or has_deletions

    def validate_critical_patches(block: SimplePatch) -> bool:
        """Extra validation for critical patches."""
        if hasattr(block.metadata, "param_1"):
            param_1 = getattr(block.metadata, "param_1", None)
            if param_1 == "critical":
                # Critical patches must have a description in the diff
                lines = block.content.diff.strip().split("\n")
                return any("Fixed:" in line or "SECURITY:" in line for line in lines)
        return True

    registry.register("patch", SimplePatch, validators=[validate_patch_content, validate_critical_patches])

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=15)
    processor = StreamBlockProcessor(registry, config=config)

    # Process stream
    print("Processing patch content examples...")
    print("=" * 80)

    patches: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    patch_stats: dict[str, Any] = {
        "total_lines": 0,
        "additions": 0,
        "deletions": 0,
        "files": set(),
        "categories": {},
    }

    async for event in processor.process_stream(example_stream()):
        if isinstance(event, TextContentEvent):
            # Show text but truncate long lines
            if event.content.strip():
                text = event.content.strip()
                if len(text) > 70:
                    text = text[:67] + "..."
                print(f"[TEXT] {text}")

        elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
            # Skip deltas for cleaner output
            pass

        elif isinstance(event, BlockEndEvent):
            # Complete patch extracted
            block = event.get_block()
            if block is None:
                continue
            patches.append(block)

            # Type narrowing for SimplePatchContent and SimplePatchMetadata
            if not isinstance(block.content, SimplePatchContent):
                continue
            if not isinstance(block.metadata, SimplePatchMetadata):
                continue

            content = block.content
            metadata = block.metadata

            print(f"\n{'-' * 70}")
            print(f"[PATCH] {metadata.id}")

            # Get category from params (dynamic attributes from DelimiterPreambleSyntax)
            category = "general"
            if hasattr(metadata, "param_0"):
                param_0 = getattr(metadata, "param_0", None)
                if param_0:
                    category = str(param_0)
            categories_dict: dict[str, int] = patch_stats["categories"]
            categories_dict[category] = categories_dict.get(category, 0) + 1

            # Parse file info from first line of content
            lines: list[str] = content.diff.strip().split("\n")
            if lines and ":" in lines[0]:
                file_path, start_line_str = lines[0].split(":")
                with contextlib.suppress(ValueError):
                    metadata.start_line = int(start_line_str)
                file_path_final = file_path
            else:
                file_path_final = "unknown"
            metadata.file = file_path_final
            files_set: set[str] = patch_stats["files"]
            files_set.add(file_path_final)

            print(f"        Category: {category}")
            if hasattr(metadata, "param_1"):
                param_1 = getattr(metadata, "param_1", None)
                if param_1:
                    print(f"        Priority: {param_1}")
            print(f"        File: {file_path_final}")
            print(f"        Starting at line: {metadata.start_line}")

            # Analyze patch content
            additions = [l for l in lines if l.startswith("+")]
            deletions = [l for l in lines if l.startswith("-")]
            context = [l for l in lines if l.startswith(" ")]

            patch_stats["total_lines"] = int(patch_stats["total_lines"]) + len(lines)
            patch_stats["additions"] = int(patch_stats["additions"]) + len(additions)
            patch_stats["deletions"] = int(patch_stats["deletions"]) + len(deletions)

            print(f"        Changes: +{len(additions)} -{len(deletions)} ({len(context)} context lines)")

            # Show key changes
            if deletions:
                print("        Removing:")
                for line in deletions[:2]:
                    print(f"          {line[:60]}...")
            if additions:
                print("        Adding:")
                for line in additions[:2]:
                    print(f"          {line[:60]}...")

            # Check for specific patterns
            if any("SECURITY" in line for line in lines):
                print("        ⚠️  SECURITY FIX INCLUDED")
            if any("DEPRECATED" in line for line in lines):
                print("        🗑️  REMOVING DEPRECATED CODE")
            if any("TODO" in line for line in lines):
                print("        📝  CONTAINS TODO ITEMS")

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n[REJECT] Patch rejected: {event.reason}")

    # Print comprehensive summary
    print("\n" + "=" * 80)
    print("\nPATCH PROCESSING SUMMARY:")
    print(f"  Total patches extracted: {len(patches)}")
    print(f"  Total files modified: {len(patch_stats['files'])}")
    print(f"  Total lines in patches: {patch_stats['total_lines']}")
    print(f"  Total additions: +{patch_stats['additions']}")
    print(f"  Total deletions: -{patch_stats['deletions']}")

    print("\n  Patches by category:")
    categories_dict_final: dict[str, int] = patch_stats["categories"]
    for category, count in sorted(categories_dict_final.items()):
        print(f"    - {category}: {count}")

    print("\n  Modified files:")
    files_set_final: set[str] = patch_stats["files"]
    for file_path in sorted(files_set_final):
        # Filter patches by file with type checking
        patches_for_file: list[Any] = []
        for p in patches:
            if isinstance(p.metadata, SimplePatchMetadata) and p.metadata.file == file_path:
                patches_for_file.append(p)
        print(f"    - {file_path} ({len(patches_for_file)} patch{'es' if len(patches_for_file) > 1 else ''})")

    # Show patch timeline
    print("\n  Patch application order:")
    for i, patch in enumerate(patches, 1):
        if not isinstance(patch.metadata, SimplePatchMetadata):
            continue

        category = "general"
        if hasattr(patch.metadata, "param_0"):
            param_0 = getattr(patch.metadata, "param_0", None)
            if param_0:
                category = str(param_0)
        priority = ""
        if hasattr(patch.metadata, "param_1"):
            param_1 = getattr(patch.metadata, "param_1", None)
            if param_1:
                priority = f" [{param_1}]"
        print(f"    {i}. {patch.metadata.id} - {category}{priority}")

    print("\n✓ Successfully processed all patches!")


if __name__ == "__main__":
    asyncio.run(main())
