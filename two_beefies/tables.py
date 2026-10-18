"""Open embedding tables, including the additive Britannica match-link migration."""

import pyarrow as pa

from two_beefies.schema import BritannicaChunk, CHUNK_MATCH_DEFAULTS


def vector_table(db, name, schema, model):
    # create_table(exist_ok=True, schema=...) validates before returning, which
    # would reject a legacy table before its nullable columns can be migrated.
    table = (db.open_table(name) if name in db.list_tables().tables
             else db.create_table(name, schema=schema))
    expected, actual = schema.to_arrow_schema(), table.schema
    missing = [field for field in expected if field.name not in actual.names]
    # Only the new nullable match columns may be added to an existing table.
    # Check all existing fields before changing anything; never rebuild the table.
    if (any(name not in expected.names for name in actual.names)
            or any(not field.equals(expected.field(field.name), check_metadata=False) for field in actual)
            or (missing and (schema is not BritannicaChunk
                             or any(field.name not in CHUNK_MATCH_DEFAULTS for field in missing)))):
        raise ValueError(f"Incompatible schema in {name}")
    quoted = "'" + model.replace("'", "''") + "'"
    if table.count_rows(f"embed_model IS NULL OR embed_model != {quoted}"):
        raise ValueError(f"Table {name} contains another/unknown embedding model")
    if missing:
        table.add_columns(pa.schema(missing))
    return table
