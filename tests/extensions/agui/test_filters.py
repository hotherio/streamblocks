"""Tests for AG-UI event filters."""

from __future__ import annotations

from hother.streamblocks.extensions.agui.filters import AGUIEventFilter


class TestAGUIEventFilterBasics:
    """Tests for basic AGUIEventFilter functionality."""

    def test_none_filter_is_zero(self) -> None:
        """Test that NONE filter has value 0."""
        assert AGUIEventFilter.NONE.value == 0
        assert not AGUIEventFilter.NONE

    def test_individual_flags_are_distinct(self) -> None:
        """Test that each individual flag has a unique value."""
        individual_flags = [
            AGUIEventFilter.RAW_TEXT,
            AGUIEventFilter.TEXT_DELTA,
            AGUIEventFilter.BLOCK_OPENED,
            AGUIEventFilter.BLOCK_DELTA,
            AGUIEventFilter.BLOCK_EXTRACTED,
            AGUIEventFilter.BLOCK_REJECTED,
        ]

        # Each flag should have a unique value
        values = [flag.value for flag in individual_flags]
        assert len(values) == len(set(values))

        # Each flag should be non-zero
        for flag in individual_flags:
            assert flag.value > 0

    def test_flag_combination_with_or(self) -> None:
        """Test combining flags with OR operator."""
        combined = AGUIEventFilter.RAW_TEXT | AGUIEventFilter.TEXT_DELTA

        # Combined flag should contain both
        assert AGUIEventFilter.RAW_TEXT in combined
        assert AGUIEventFilter.TEXT_DELTA in combined
        # But not others
        assert AGUIEventFilter.BLOCK_OPENED not in combined

    def test_flag_membership_check(self) -> None:
        """Test checking if a flag is in a combined flag."""
        combined = AGUIEventFilter.BLOCK_OPENED | AGUIEventFilter.BLOCK_EXTRACTED

        assert AGUIEventFilter.BLOCK_OPENED in combined
        assert AGUIEventFilter.BLOCK_EXTRACTED in combined
        assert AGUIEventFilter.TEXT_DELTA not in combined
        assert AGUIEventFilter.BLOCK_DELTA not in combined


class TestAGUIEventFilterPresets:
    """Tests for predefined filter presets."""

    def test_all_preset_contains_all_individual_flags(self) -> None:
        """Test that ALL preset contains all individual event flags."""
        all_filter = AGUIEventFilter.ALL

        individual_flags = [
            AGUIEventFilter.RAW_TEXT,
            AGUIEventFilter.TEXT_DELTA,
            AGUIEventFilter.BLOCK_OPENED,
            AGUIEventFilter.BLOCK_DELTA,
            AGUIEventFilter.BLOCK_EXTRACTED,
            AGUIEventFilter.BLOCK_REJECTED,
        ]

        for flag in individual_flags:
            assert flag in all_filter, f"{flag} should be in ALL"

    def test_blocks_only_preset(self) -> None:
        """Test BLOCKS_ONLY preset contains only block lifecycle events."""
        blocks_only = AGUIEventFilter.BLOCKS_ONLY

        # Should include
        assert AGUIEventFilter.BLOCK_OPENED in blocks_only
        assert AGUIEventFilter.BLOCK_EXTRACTED in blocks_only
        assert AGUIEventFilter.BLOCK_REJECTED in blocks_only

        # Should NOT include
        assert AGUIEventFilter.RAW_TEXT not in blocks_only
        assert AGUIEventFilter.TEXT_DELTA not in blocks_only
        assert AGUIEventFilter.BLOCK_DELTA not in blocks_only

    def test_blocks_with_progress_preset(self) -> None:
        """Test BLOCKS_WITH_PROGRESS preset includes block lifecycle and deltas."""
        blocks_progress = AGUIEventFilter.BLOCKS_WITH_PROGRESS

        # Should include
        assert AGUIEventFilter.BLOCK_OPENED in blocks_progress
        assert AGUIEventFilter.BLOCK_DELTA in blocks_progress
        assert AGUIEventFilter.BLOCK_EXTRACTED in blocks_progress
        assert AGUIEventFilter.BLOCK_REJECTED in blocks_progress

        # Should NOT include
        assert AGUIEventFilter.RAW_TEXT not in blocks_progress
        assert AGUIEventFilter.TEXT_DELTA not in blocks_progress

    def test_text_and_final_preset(self) -> None:
        """Test TEXT_AND_FINAL preset includes text and final block events."""
        text_final = AGUIEventFilter.TEXT_AND_FINAL

        # Should include
        assert AGUIEventFilter.TEXT_DELTA in text_final
        assert AGUIEventFilter.BLOCK_EXTRACTED in text_final
        assert AGUIEventFilter.BLOCK_REJECTED in text_final

        # Should NOT include
        assert AGUIEventFilter.RAW_TEXT not in text_final
        assert AGUIEventFilter.BLOCK_OPENED not in text_final
        assert AGUIEventFilter.BLOCK_DELTA not in text_final


class TestAGUIEventFilterOperations:
    """Tests for Flag operations on AGUIEventFilter."""

    def test_combining_presets(self) -> None:
        """Test combining multiple presets."""
        combined = AGUIEventFilter.BLOCKS_ONLY | AGUIEventFilter.TEXT_DELTA

        # Should have both blocks and text_delta
        assert AGUIEventFilter.BLOCK_OPENED in combined
        assert AGUIEventFilter.BLOCK_EXTRACTED in combined
        assert AGUIEventFilter.TEXT_DELTA in combined

    def test_subtracting_flags(self) -> None:
        """Test removing flags from a preset."""
        # Start with ALL and remove text events
        filtered = AGUIEventFilter.ALL & ~AGUIEventFilter.RAW_TEXT

        assert AGUIEventFilter.RAW_TEXT not in filtered
        assert AGUIEventFilter.TEXT_DELTA in filtered
        assert AGUIEventFilter.BLOCK_EXTRACTED in filtered

    def test_intersection_of_presets(self) -> None:
        """Test intersection of two presets."""
        intersection = AGUIEventFilter.BLOCKS_WITH_PROGRESS & AGUIEventFilter.TEXT_AND_FINAL

        # Only common elements should remain
        assert AGUIEventFilter.BLOCK_EXTRACTED in intersection
        assert AGUIEventFilter.BLOCK_REJECTED in intersection

        # Elements unique to each should be gone
        assert AGUIEventFilter.BLOCK_OPENED not in intersection
        assert AGUIEventFilter.BLOCK_DELTA not in intersection
        assert AGUIEventFilter.TEXT_DELTA not in intersection

    def test_none_filter_combination(self) -> None:
        """Test that NONE combined with anything equals that thing."""
        result = AGUIEventFilter.NONE | AGUIEventFilter.TEXT_DELTA
        assert result == AGUIEventFilter.TEXT_DELTA

    def test_filter_equality(self) -> None:
        """Test filter equality comparisons."""
        # Manual combination equals preset
        manual = (
            AGUIEventFilter.RAW_TEXT
            | AGUIEventFilter.TEXT_DELTA
            | AGUIEventFilter.BLOCK_OPENED
            | AGUIEventFilter.BLOCK_DELTA
            | AGUIEventFilter.BLOCK_EXTRACTED
            | AGUIEventFilter.BLOCK_REJECTED
        )
        assert manual == AGUIEventFilter.ALL

    def test_custom_filter_creation(self) -> None:
        """Test creating custom filter combinations."""
        # Create a custom filter for streaming UIs
        streaming_ui = AGUIEventFilter.TEXT_DELTA | AGUIEventFilter.BLOCK_DELTA | AGUIEventFilter.BLOCK_EXTRACTED

        assert AGUIEventFilter.TEXT_DELTA in streaming_ui
        assert AGUIEventFilter.BLOCK_DELTA in streaming_ui
        assert AGUIEventFilter.BLOCK_EXTRACTED in streaming_ui
        assert AGUIEventFilter.BLOCK_OPENED not in streaming_ui
        assert AGUIEventFilter.RAW_TEXT not in streaming_ui

    def test_bool_evaluation(self) -> None:
        """Test boolean evaluation of filters."""
        assert not AGUIEventFilter.NONE
        assert AGUIEventFilter.RAW_TEXT
        assert AGUIEventFilter.ALL
        assert AGUIEventFilter.TEXT_DELTA | AGUIEventFilter.BLOCK_EXTRACTED


class TestAGUIEventFilterEnumProperties:
    """Tests for enum-specific properties."""

    def test_filter_name_access(self) -> None:
        """Test accessing filter names."""
        assert AGUIEventFilter.RAW_TEXT.name == "RAW_TEXT"
        assert AGUIEventFilter.BLOCK_EXTRACTED.name == "BLOCK_EXTRACTED"
        assert AGUIEventFilter.BLOCKS_ONLY.name == "BLOCKS_ONLY"

    def test_filter_value_access(self) -> None:
        """Test that filter values are integers."""
        for filter_item in AGUIEventFilter:
            assert isinstance(filter_item.value, int)

    def test_iteration_over_filters(self) -> None:
        """Test iterating over all canonical (non-composite) filter values.

        Note: Flag enum iteration only yields canonical members (individual flags),
        not composite values like NONE (0) or presets (ALL, BLOCKS_ONLY, etc.).
        """
        all_filters = list(AGUIEventFilter)

        # Should include individual flags
        assert AGUIEventFilter.RAW_TEXT in all_filters
        assert AGUIEventFilter.TEXT_DELTA in all_filters
        assert AGUIEventFilter.BLOCK_OPENED in all_filters
        assert AGUIEventFilter.BLOCK_DELTA in all_filters
        assert AGUIEventFilter.BLOCK_EXTRACTED in all_filters
        assert AGUIEventFilter.BLOCK_REJECTED in all_filters

        # Count should be 6 individual flags
        individual_flag_count = 6
        assert len(all_filters) == individual_flag_count

    def test_preset_values_are_combinations(self) -> None:
        """Test that preset values equal the sum of their components."""
        # BLOCKS_ONLY should equal BLOCK_OPENED | BLOCK_EXTRACTED | BLOCK_REJECTED
        expected_blocks_only = (
            AGUIEventFilter.BLOCK_OPENED | AGUIEventFilter.BLOCK_EXTRACTED | AGUIEventFilter.BLOCK_REJECTED
        )
        assert expected_blocks_only == AGUIEventFilter.BLOCKS_ONLY

        # TEXT_AND_FINAL should equal TEXT_DELTA | BLOCK_EXTRACTED | BLOCK_REJECTED
        expected_text_final = (
            AGUIEventFilter.TEXT_DELTA | AGUIEventFilter.BLOCK_EXTRACTED | AGUIEventFilter.BLOCK_REJECTED
        )
        assert expected_text_final == AGUIEventFilter.TEXT_AND_FINAL
