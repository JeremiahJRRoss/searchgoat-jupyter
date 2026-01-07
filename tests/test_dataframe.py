"""Tests for searchgoat._utils.dataframe module."""

import pandas as pd
import pytest

from searchgoat_jupyter._utils.dataframe import records_to_dataframe


class TestRecordsToDataframe:
    """Tests for records_to_dataframe function."""
    
    def test_converts_list_of_dicts_to_dataframe(self):
        """Converts list of dicts to DataFrame."""
        records = [
            {"a": 1, "b": "x"},
            {"a": 2, "b": "y"},
        ]
        
        df = records_to_dataframe(records)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["a", "b"]
    
    def test_parses_time_column(self):
        """Converts _time field to datetime."""
        records = [
            {"_time": 1704067200, "msg": "test"},  # 2024-01-01 00:00:00 UTC
        ]
        
        df = records_to_dataframe(records, parse_timestamps=True)
        
        assert pd.api.types.is_datetime64_any_dtype(df["_time"])
        assert df["_time"].iloc[0].year == 2024
    
    def test_skips_time_parsing_when_disabled(self):
        """Leaves _time as numeric when parse_timestamps=False."""
        records = [
            {"_time": 1704067200, "msg": "test"},
        ]
        
        df = records_to_dataframe(records, parse_timestamps=False)
        
        assert df["_time"].iloc[0] == 1704067200
    
    def test_handles_missing_time_column(self):
        """Works fine when _time column doesn't exist."""
        records = [
            {"a": 1},
            {"a": 2},
        ]
        
        df = records_to_dataframe(records, parse_timestamps=True)
        
        assert len(df) == 2
        assert "_time" not in df.columns
    
    def test_handles_empty_records(self):
        """Returns empty DataFrame for empty input."""
        df = records_to_dataframe([])
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_handles_generator_input(self):
        """Works with generator input."""
        def gen():
            yield {"x": 1}
            yield {"x": 2}
        
        df = records_to_dataframe(gen())
        
        assert len(df) == 2
