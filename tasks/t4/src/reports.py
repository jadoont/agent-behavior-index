from collections import defaultdict
from decimal import Decimal
from typing import Iterable


def revenue_by_day(rows: Iterable[dict[str, object]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in rows:
        day = str(row["placed_at"])[:10]
        totals[day] += Decimal(str(row["total"]))
    return dict(sorted(totals.items()))


def low_stock_rows(
    rows: Iterable[dict[str, object]],
    minimum: int,
) -> list[dict[str, object]]:
    selected = [row for row in rows if int(row["quantity"]) <= minimum]
    return sorted(selected, key=lambda row: (int(row["quantity"]), str(row["sku"])))


def report_totals(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "row_count": len(rows),
        "distinct_skus": len({str(row["sku"]) for row in rows}),
        "total_units": sum(int(row["quantity"]) for row in rows),
    }


def csv_safe(value: object) -> str:
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
