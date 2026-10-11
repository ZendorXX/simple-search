import ast
import csv
from dataclasses import dataclass
from datetime import datetime

EXPECTED_HEADERS = ["text", "created_date", "rubrics"]
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CsvValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class PostRow:
    id: int
    text: str
    created_date: datetime
    rubrics: list[str]


def _parse_date(raw: str) -> datetime:
    value = datetime.strptime(raw, DATE_FORMAT)
    if value.strftime(DATE_FORMAT) != raw:
        raise ValueError(f"дата не соответствует формату {DATE_FORMAT!r}")
    return value


def _parse_rubrics(raw: str) -> list[str]:
    value = ast.literal_eval(raw)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("rubrics должны быть списком строк")
    return value


def parse_posts_csv(path: str) -> list[PostRow]:
    rows: list[PostRow] = []
    errors: list[str] = []
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
        except StopIteration:
            raise CsvValidationError(["строка 1: файл пуст"]) from None
        if header != EXPECTED_HEADERS:
            raise CsvValidationError(
                [f"строка 1: ожидался заголовок {','.join(EXPECTED_HEADERS)}, получен {','.join(header)}"]
            )
        last_line = reader.line_num
        for ordinal, raw_row in enumerate(reader, start=1):
            start_line = last_line + 1
            last_line = reader.line_num
            record_id = ordinal
            if len(raw_row) != 3:
                errors.append(f"строка {start_line}: ожидалось 3 поля, получено {len(raw_row)}")
                continue
            text, raw_date, raw_rubrics = raw_row
            try:
                created_date = _parse_date(raw_date)
            except ValueError as exc:
                errors.append(f"строка {start_line}: created_date — {exc}")
                continue
            try:
                rubrics = _parse_rubrics(raw_rubrics)
            except (ValueError, SyntaxError) as exc:
                errors.append(f"строка {start_line}: rubrics — {exc}")
                continue
            rows.append(
                PostRow(id=record_id, text=text, created_date=created_date, rubrics=rubrics)
            )
    if errors:
        raise CsvValidationError(errors)
    return rows
