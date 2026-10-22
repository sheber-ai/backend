from sqlalchemy import Enum

from models import Base, import_all_models


def test_no_enum_columns() -> None:
    """Code enums are validated in schemas; the database stores plain strings, so new values need no migration."""
    import_all_models()
    enum_columns = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, Enum)
    ]
    assert not enum_columns, f"Use String columns for enums: {enum_columns}"
