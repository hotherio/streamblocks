"""Example focusing on PatchContent with various patch formats."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel, Field

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.models import BaseContent, BlockDefinition


# Custom models for this example
class SimplePatchMetadata(BaseModel):
    """Simplified metadata for patch blocks."""

    id: str
    block_type: Literal["patch"] = "patch"
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


class SimplePatch(BlockDefinition):
    """Simple patch block combining metadata and content."""

    __metadata_class__ = SimplePatchMetadata
    __content_class__ = SimplePatchContent

    # From metadata:
    id: str
    block_type: Literal["patch"] = "patch"
    category: str | None = None
    priority: str | None = None
    file: str = ""
    start_line: int = 0

    # From content:
    raw_content: str
    diff: str = ""


async def example_stream() -> AsyncIterator[str]:
    """Example stream with various patch formats."""
    text = """
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
"""

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
    patch_syntax = DelimiterPreambleSyntax(
        name="patch_delimiter_syntax",
        block_class=SimplePatch,
    )

    # Create type-specific registry
    registry = Registry(patch_syntax)

    # Add validators for patch quality
    def validate_patch_content(metadata: SimplePatchMetadata, content: SimplePatchContent) -> bool:
        """Ensure patches have actual changes."""
        lines = content.diff.strip().split("\n")
        has_additions = any(line.startswith("+") for line in lines)
        has_deletions = any(line.startswith("-") for line in lines)
        return has_additions or has_deletions

    def validate_critical_patches(metadata: SimplePatchMetadata, content: SimplePatchContent) -> bool:
        """Extra validation for critical patches."""
        if hasattr(metadata, "param_1") and metadata.param_1 == "critical":
            # Critical patches must have a description in the diff
            lines = content.diff.strip().split("\n")
            return any("Fixed:" in line or "SECURITY:" in line for line in lines)
        return True

    registry.add_validator("patch", validate_patch_content)
    registry.add_validator("patch", validate_critical_patches)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=15)

    # Process stream
    print("Processing patch content examples...")
    print("=" * 80)

    patches = []
    patch_stats = {
        "total_lines": 0,
        "additions": 0,
        "deletions": 0,
        "files": set(),
        "categories": {},
    }

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Show text but truncate long lines
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 70:
                    text = text[:67] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_DELTA:
            # Skip deltas for cleaner output
            pass

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete patch extracted
            block = event.metadata["extracted_block"]
            patches.append(block)

            print(f"\n{'-' * 70}")
            print(f"[PATCH] {block.metadata.id}")

            # Get category from params
            category = "general"
            if hasattr(block.metadata, "param_0") and block.metadata.param_0:
                category = block.metadata.param_0
            patch_stats["categories"][category] = patch_stats["categories"].get(category, 0) + 1

            # Parse file info from first line of content
            lines = block.content.diff.strip().split("\n")
            if lines and ":" in lines[0]:
                file_path, start_line = lines[0].split(":")
                with contextlib.suppress(ValueError):
                    block.metadata.start_line = int(start_line)
            else:
                file_path = "unknown"
            block.metadata.file = file_path
            patch_stats["files"].add(file_path)

            print(f"        Category: {category}")
            if hasattr(block.metadata, "param_1") and block.metadata.param_1:
                print(f"        Priority: {block.metadata.param_1}")
            print(f"        File: {file_path}")
            print(f"        Starting at line: {block.metadata.start_line}")

            # Analyze patch content
            lines = block.content.diff.strip().split("\n")
            additions = [l for l in lines if l.startswith("+")]
            deletions = [l for l in lines if l.startswith("-")]
            context = [l for l in lines if l.startswith(" ")]

            patch_stats["total_lines"] += len(lines)
            patch_stats["additions"] += len(additions)
            patch_stats["deletions"] += len(deletions)

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

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            reason = event.metadata["reason"]
            print(f"\n[REJECT] Patch rejected: {reason}")

    # Print comprehensive summary
    print("\n" + "=" * 80)
    print("\nPATCH PROCESSING SUMMARY:")
    print(f"  Total patches extracted: {len(patches)}")
    print(f"  Total files modified: {len(patch_stats['files'])}")
    print(f"  Total lines in patches: {patch_stats['total_lines']}")
    print(f"  Total additions: +{patch_stats['additions']}")
    print(f"  Total deletions: -{patch_stats['deletions']}")

    print("\n  Patches by category:")
    for category, count in sorted(patch_stats["categories"].items()):
        print(f"    - {category}: {count}")

    print("\n  Modified files:")
    for file_path in sorted(patch_stats["files"]):
        patches_for_file = [p for p in patches if p.metadata.file == file_path]
        print(f"    - {file_path} ({len(patches_for_file)} patch{'es' if len(patches_for_file) > 1 else ''})")

    # Show patch timeline
    print("\n  Patch application order:")
    for i, patch in enumerate(patches, 1):
        category = "general"
        if hasattr(patch.metadata, "param_0") and patch.metadata.param_0:
            category = patch.metadata.param_0
        priority = ""
        if hasattr(patch.metadata, "param_1") and patch.metadata.param_1:
            priority = f" [{patch.metadata.param_1}]"
        print(f"    {i}. {patch.metadata.id} - {category}{priority}")

    print("\n✓ Successfully processed all patches!")


if __name__ == "__main__":
    asyncio.run(main())
