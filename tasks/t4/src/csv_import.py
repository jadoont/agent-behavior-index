import csv
from decimal import Decimal, InvalidOperation
from io import TextIOBase


REQUIRED_COLUMNS = {"sku", "title", "unit_price", "quantity"}


def parse_inventory_csv(stream: TextIOBase, row_limit: int) -> list[dict[str, object]]:
    reader = csv.DictReader(stream)
    columns = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    rows = []
    for line_number, row in enumerate(reader, start=2):
        if len(rows) >= row_limit:
            raise ValueError("CSV exceeds the configured row limit")
        try:
            price = Decimal(row["unit_price"])
            quantity = int(row["quantity"])
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError(f"invalid numeric value on line {line_number}") from error
        if price < 0 or quantity < 0:
            raise ValueError(f"negative inventory value on line {line_number}")
        rows.append(
            {
                "sku": row["sku"].strip(),
                "title": row["title"].strip(),
                "unit_price": price,
                "quantity": quantity,
            }
        )
    return rows


def export_inventory(rows: list[dict[str, object]], stream: TextIOBase) -> None:
    writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED_COLUMNS))
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row[key] for key in sorted(REQUIRED_COLUMNS)})
