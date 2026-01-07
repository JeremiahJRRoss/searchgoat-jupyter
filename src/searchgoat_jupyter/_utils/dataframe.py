"""DataFrame conversion utilities."""

from typing import Iterable

import pandas as pd


def records_to_dataframe(
    records: Iterable[dict],
    parse_timestamps: bool = True,
) -> pd.DataFrame:
    """
    Convert iterable of record dicts to pandas DataFrame.
    
    Args:
        records: Iterable of dictionaries (e.g., from pagination generator)
        parse_timestamps: If True, convert '_time' field to datetime
        
    Returns:
        pandas DataFrame with all records
        
    Example:
        records = [{"_time": 1704067200, "msg": "hello"}]
        df = records_to_dataframe(records)
        print(df.dtypes)  # _time is datetime64[ns, UTC]
    """
    df = pd.DataFrame(list(records))
    
    if df.empty:
        return df
    
    if parse_timestamps and "_time" in df.columns:
        # Cribl uses Unix timestamps
        df["_time"] = pd.to_datetime(df["_time"], unit="s", utc=True)
    
    return df
