from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


@dataclass(frozen=True)
class Cell:
    value: object
    span: tuple[int, int]  # (columns, rows)


@dataclass
class Sheet:
    name: str
    _cells: list[list[Cell]]

    def nrows(self) -> int:
        return len(self._cells)

    def ncols(self) -> int:
        if not self._cells:
            return 0
        return len(self._cells[0])

    def __getitem__(self, pos: tuple[int, int]) -> Cell:
        row, col = pos
        if row < 0 or col < 0:
            raise IndexError(f"negative indices are not supported: ({row}, {col})")

        return self._cells[row][col]


@dataclass
class Document:
    sheets: list[Sheet]


def _parse_cell_element(cell_element: ElementTree.Element) -> Cell:
    """
    Parse a <table:table-cell> element.
    """
    value_type = cell_element.get(f"{{{_NS['office']}}}value-type")

    if value_type is None:
        value = None

    elif value_type == "string":
        paragraphs = cell_element.findall("text:p", _NS)
        value = "\n".join(
            "".join(paragraph.itertext())
            for paragraph in paragraphs
        )

    elif value_type == "float":
        float_value = cell_element.get(f"{{{_NS['office']}}}value")
        if float_value is None:
            raise ValueError("float cell without office:value")

        value = float(float_value)
        if value.is_integer():
            value = int(value)

    elif value_type == "boolean":
        boolean_value = cell_element.get(f"{{{_NS['office']}}}boolean-value")
        if boolean_value is None:
            raise ValueError("boolean cell without office:boolean-value")

        value = boolean_value == "true"

    else:
        raise ValueError(f"unsupported cell value type: {value_type!r}")

    col_span = int(
        cell_element.get(
            f"{{{_NS['table']}}}number-columns-spanned",
            "1",
        )
    )

    row_span = int(
        cell_element.get(
            f"{{{_NS['table']}}}number-rows-spanned",
            "1",
        )
    )

    return Cell(
        value=value,
        span=(col_span, row_span),
    )


def _parse_row_element(row_element: ElementTree.Element) -> list[Cell]:
    """
    Parse a <table:table-row> element.
    """
    row: list[Cell] = []

    for cell_element in row_element:
        if cell_element.tag not in {
            f"{{{_NS['table']}}}table-cell",
            f"{{{_NS['table']}}}covered-table-cell",
        }:
            continue

        if cell_element.tag == f"{{{_NS['table']}}}covered-table-cell":
            cell = Cell(None, (1, 1))
        else:
            cell = _parse_cell_element(cell_element)

        repeat = int(
            cell_element.get(
                f"{{{_NS['table']}}}number-columns-repeated",
                "1",
            )
        )

        row.extend(cell for _ in range(repeat))

    return row


def _parse_sheet_element(table: ElementTree.Element) -> Sheet:
    """
    Parse a <table:table> element.
    """
    name = table.get(f"{{{_NS['table']}}}name")
    if not name:
        raise ValueError("table without a name")

    rows: list[list[Cell]] = []

    for row_element in table.findall("table:table-row", _NS):
        row = _parse_row_element(row_element)

        repeat = int(
            row_element.get(
                f"{{{_NS['table']}}}number-rows-repeated",
                "1",
            )
        )

        for _ in range(repeat):
            rows.append(list(row))

    width = max((len(row) for row in rows), default=0)

    for row in rows:
        if len(row) < width:
            row.extend(
                Cell(None, (1, 1))
                for _ in range(width - len(row))
            )

    return Sheet(
        name=name,
        _cells=rows,
    )


def opendoc(path: str | Path) -> Document:
    """
    Open an ODS document.

    Args:
        path:
            Path to an .ods file.

    Returns:
        Parsed document.

    Raises:
        OSError:
            Unable to read the file.

        ValueError:
            The file is not a valid ODS document.
    """
    path = Path(path).expanduser()

    try:
        with ZipFile(path) as archive:
            try:
                content = archive.read("content.xml")
            except KeyError as exc:
                raise ValueError("ODS archive does not contain content.xml") from exc
    except BadZipFile as exc:
        raise ValueError(f"{path!s} is not a valid ODS file") from exc

    root = ElementTree.fromstring(content)

    body = root.find("office:body", _NS)
    if body is None:
        raise ValueError("content.xml does not contain office:body")

    spreadsheet = body.find("office:spreadsheet", _NS)
    if spreadsheet is None:
        raise ValueError("content.xml does not contain office:spreadsheet")

    sheets = [
        _parse_sheet_element(table)
        for table in spreadsheet.findall("table:table", _NS)
    ]

    return Document(sheets)


def main():
    doc = opendoc('~/Documents/pkmn/samples/test.ods')


if __name__ == '__main__':
    main()

