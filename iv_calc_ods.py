import operator
from collections.abc import Container
from enum import Enum
from pathlib import Path
from typing import Optional, Iterable, TypedDict, NoReturn, Generator, Callable

import ezodf
from characteristic import Characteristic
import iv_calc
from iv_calc import CalcedIVSets_T
from nature import Nature
from pkmn_stat import StatType, Stat, InputStatsData_T
from pokemon import Species_T, Sample, Pokemon, NatureIVSets_T

BLOCK_HEIGHT = 8


class ObsSample(TypedDict):
    label: Optional[str]
    spec: Species_T
    obs_stats: Iterable[iv_calc.ObsStat]
    nature: Optional[Nature]
    characteristic: Optional[Characteristic]


class OdsFormatError(ValueError):
    pass


def _fail(sheet: ezodf.Sheet, row: int, col: int, message: str) -> NoReturn:
    raise OdsFormatError(
        f"${sheet.name!r}.{_cell_name(row, col)}: {message}"
    )


def _cell_name(row: int, col: int) -> str:
    """
    Convert zero-based row/column indices into A1 notation.

    Examples:
        (0, 0)   -> A1
        (0, 25)  -> Z1
        (0, 26)  -> AA1
        (4, 27)  -> AB5
        (9, 701) -> ZZ10
        (0, 702) -> AAA1
    """
    if row < 0:
        raise ValueError(f"row must be non-negative, got {row}")

    if col < 0:
        raise ValueError(f"column must be non-negative, got {col}")

    letters = []

    while True:
        col, remainder = divmod(col, 26)
        letters.append(chr(ord("A") + remainder))

        if col == 0:
            break

        col -= 1

    return "".join(reversed(letters)) + str(row + 1)


def _parse_sheet(sheet: ezodf.Sheet) -> list[ObsSample]:
    """
    Parse all data blocks from a single worksheet.

    Empty sheet is valid and produces an empty list.

    Raises:
        OdsFormatError:
            Sheet structure is invalid.
    """
    samples: list[ObsSample] = []

    row = 0
    while True:
        block_row = _find_next_block(sheet, row)
        if block_row is None:
            break

        _validate_empty_gap(sheet, row, block_row)

        samples.append(_parse_block(sheet, block_row))

        row = block_row + BLOCK_HEIGHT

    return samples


def _cell_is_empty(cell: ezodf.Cell) -> bool:
    return cell.value in (None, "")


def _row_is_empty(sheet: ezodf.Sheet, row: int) -> bool:
    """Return True iff every cell in the row is empty."""
    return all(
        _cell_is_empty(sheet[row, col])
        for col in range(sheet.ncols())
    )


def _find_next_block(
    sheet: ezodf.Sheet,
    start_row: int,
) -> int | None:
    """
    Return the first non-empty row at or after ``start_row``.

    Returns:
        Row index of the next candidate block,
        or None if there are no more blocks.
    """
    for row in range(start_row, sheet.nrows()):
        if not _row_is_empty(sheet, row):
            return row

    return None


def _validate_empty_gap(
    sheet: ezodf.Sheet,
    start_row: int,
    end_row: int,
) -> None:
    """
    Verify that all rows in [start_row, end_row) are completely empty.

    Raises:
        OdsFormatError:
            If any cell contains data.
    """
    for row in range(start_row, end_row):
        for col in range(sheet.ncols()):
            value = sheet[row, col].value
            if value not in (None, ""):
                _fail(sheet, row, col, message="only completely empty rows are allowed between data blocks")


def _parse_block(
    sheet: ezodf.Sheet,
    block_row: int,
) -> ObsSample:
    """
    Parse a single 8-row data block.

    Args:
        sheet:
            Worksheet containing the block.

        block_row:
            Zero-based row index of the first row of the block.

    Returns:
        Parsed observation sample.

    Raises:
        OdsFormatError:
            Block structure is invalid.
    """
    if block_row + BLOCK_HEIGHT > sheet.nrows():
        _fail(sheet, block_row, col=0, message=f"data block must occupy exactly {BLOCK_HEIGHT} rows")

    meta_col = 1
    label, spec, nature, characteristic, header_col = _parse_meta(sheet, block_row, meta_col)

    stat_order, first_level_col = _parse_header(sheet, block_row, header_col)

    obs_stats = _parse_levels(sheet, block_row, first_level_col, stat_order)

    return {
        "label": label,
        "spec": spec,
        "nature": nature,
        "characteristic": characteristic,
        "obs_stats": obs_stats,
    }


def _parse_meta(
    sheet: ezodf.Sheet,
    block_row: int,
    meta_col: int,
) -> tuple[Optional[str], Pokemon, Nature, Characteristic, int]:
    """
    Parse and validate the metadata section of a block.

    Returns:
        (label, pokemon, nature, characteristic, header_column)
    """
    label_cell = sheet[block_row, 0]
    merged = label_cell.span
    if merged != (1, BLOCK_HEIGHT):
        _fail(sheet, block_row, col=0, message=f"expected a merged cell spanning 1×{BLOCK_HEIGHT}")
    # noinspection PyStringConversionWithoutDunderMethod
    label_value = None if label_cell.value is None else str(label_cell.value)

    pkmn_label_row = block_row
    pkmn, nature_label_row = _parse_required_meta_node(
        sheet, pkmn_label_row, meta_col,
        Pokemon, expected_label="POKEMON"
    )
    nature, characteristic_label_row = _parse_required_meta_node(
        sheet, nature_label_row, meta_col,
        Nature, expected_label="NATURE"
    )
    characteristic, next_label_row = _parse_required_meta_node(
        sheet, characteristic_label_row, meta_col,
        Characteristic, expected_label="CHARACTERISTIC"
    )
    # Other cells in the column are ignored.
    # for row in range(next_label_row, block_row + BLOCK_HEIGHT):
    #     if not _cell_is_empty(sheet[row, meta_col]):
    #         _fail(sheet, row, meta_col, message="expected an empty cell")

    header_col = meta_col + 1

    return label_value, pkmn, nature, characteristic, header_col


def _parse_required_meta_node[T: Enum](
    sheet: ezodf.Sheet,
    label_row: int,
    col: int,
    enum_: type[T],
    expected_label: str,
) -> tuple[T, int]:
    """
    Parse a meta node of a block.
    Expects two adjacent cells in one column (`col`). First cell should
    contain a label text (`expected_label`) and the second should contain
    valid name from `enum_`.

    Returns parsed value and index of the row for the next node.
    """
    label = sheet[label_row, col].value
    if not isinstance(label, str) or label.strip().casefold() != expected_label.casefold():
        _fail(sheet, label_row, col, message=f'expected "{expected_label}"')

    value_row = label_row + 1
    value = sheet[value_row, col].value
    if not isinstance(value, str):
        _fail(sheet, value_row, col, message=f"expected a valid {expected_label.upper()} name")

    try:
        return enum_[value.strip()], value_row + 1
    except KeyError:
        _fail(sheet, value_row, col, message=f"unknown {expected_label.upper()}: {value!r}")


def _parse_header(
    sheet: ezodf.Sheet,
    block_row: int,
    header_col: int,
) -> tuple[list[StatType], int]:
    """
    Parse and validate the header column.

    Returns:
        (stat_order, first_level_col)
    """
    value = sheet[block_row, header_col].value
    if not isinstance(value, str):
        _fail(sheet, block_row, header_col, message='expected "LEVEL"')

    normalized = value.strip().removesuffix(":").casefold()
    if normalized not in ("level", "lvl"):
        _fail(sheet, block_row, header_col, message='expected "LEVEL" or "LVL"')

    sep_row = block_row + 1
    if not _cell_is_empty(sheet[sep_row, header_col]):
        _fail(sheet, sep_row, header_col, message="expected an empty cell")

    # Other rows should represent each `StatType`.
    stats_row = sep_row + 1
    assert block_row + BLOCK_HEIGHT - stats_row == len(StatType)

    stat_order: list[StatType] = []
    seen: set[StatType] = set()
    for row in range(stats_row, block_row + BLOCK_HEIGHT):
        value = sheet[row, header_col].value
        if not isinstance(value, str):
            _fail(sheet, row, header_col, message="expected a stat name")

        try:
            stat = StatType[value.strip()]
        except KeyError:
            _fail(sheet, row, header_col, message=f"unknown stat type: {value!r}")

        if stat in seen:
            _fail(sheet, row, header_col, message=f"duplicate stat type: {stat.name}")

        seen.add(stat)
        stat_order.append(stat)

    if len(seen) != len(StatType):
        missing = ", ".join(
            stat.name
            for stat in StatType
            if stat not in seen
        )
        _fail(sheet, stats_row, header_col, message=f"missing stat types: {missing}")

    first_level_col = header_col + 1

    return stat_order, first_level_col


def _parse_levels(
    sheet: ezodf.Sheet,
    block_row: int,
    first_level_col: int,
    stat_order: list[StatType],
) -> list[iv_calc.ObsStat]:
    """
    Parse all level blocks belonging to a data block.
    Blocks with empty level value are ignored: it's convenient to add
    next block in which one keeps track of EVs, but it's not clear, what
    final values of stats will be, and at which level it will happen.
    """
    obs_stats: list[iv_calc.ObsStat] = []
    col = first_level_col
    while col + 1 < sheet.ncols():
        lvl_cell = sheet[block_row, col]
        if _cell_is_empty(lvl_cell):
            col += 2
            continue

        left_empty = True
        right_empty = True
        for row in range(block_row, block_row + BLOCK_HEIGHT):
            if not _cell_is_empty(sheet[row, col]):
                left_empty = False
            if not _cell_is_empty(sheet[row, col + 1]):
                right_empty = False
        if left_empty and right_empty:
            break
        if left_empty != right_empty:
            _fail(sheet, block_row, col, "each level must occupy exactly two columns")

        obs_stats.append(_parse_level(sheet, block_row, col, stat_order))
        col += 2

    if not obs_stats:
        _fail(sheet, block_row, first_level_col, "data block must contain at least one level")

    return obs_stats


def _parse_level(
    sheet: ezodf.Sheet,
    block_row: int,
    first_col: int,
    stat_order: list[StatType],
) -> iv_calc.ObsStat:
    """
    Parse a single level block.
    """
    lvl_cell = sheet[block_row, first_col]
    if lvl_cell.span != (2, 1):
        _fail(sheet, block_row, first_col, "level value must be in a cell merged across two columns")

    lvl = lvl_cell.value
    if not isinstance(lvl, int):
        _fail(sheet, block_row, first_col, "expected an integer level")

    # These labels should be case folded.
    total_label = "total".casefold()
    ev_label = "ev".casefold()

    left_header = sheet[block_row + 1, first_col].value
    right_header = sheet[block_row + 1, first_col + 1].value
    if not isinstance(left_header, str):
        _fail(sheet, block_row + 1, first_col, message=f'expected {total_label!r} or {ev_label!r}')
    if not isinstance(right_header, str):
        _fail(sheet, block_row + 1, first_col + 1, message=f'expected {total_label!r} or {ev_label!r}')

    left_header = left_header.strip().casefold()
    right_header = right_header.strip().casefold()
    if {left_header, right_header} != {total_label, ev_label}:
        _fail(sheet, block_row + 1, first_col, message=f'expected one {total_label!r} column and one {ev_label!r} column')

    total_col = first_col if left_header == total_label else first_col + 1
    ev_col = first_col if left_header == ev_label else first_col + 1
    stats: InputStatsData_T = {}
    for row_offset, stat_type in enumerate(stat_order, start=2):
        row = block_row + row_offset
        total_cell = sheet[row, total_col]
        ev_cell = sheet[row, ev_col]

        total = total_cell.value
        if not isinstance(total, int):
            _fail(sheet, row, total_col, message=f"expected an integer {total_label} value")

        if _cell_is_empty(ev_cell):
            ev = 0
        else:
            ev = ev_cell.value
            if not isinstance(ev, int):
                _fail(sheet, row, ev_col, message=f"expected an integer {ev_label} value")

        stats[stat_type] = {
            "value": total,
            "ev": ev,
        }

    return {
        "lvl": lvl,
        "stats": stats,
    }


def _parse_ods(path: str | Path, sheet_name: Optional[str] = None) -> list[ObsSample]:
    """
    Parse an observation workbook.

    The workbook is an OpenDocument Spreadsheet (.ods) consisting of one or more
    worksheets. Every worksheet contains zero or more independent data blocks.

    A data block:

    * always starts in the first column of a worksheet;
    * occupies exactly 8 rows;
    * may be immediately followed by another data block or separated from it
      by any number of completely empty rows;
    * describes one Pokémon together with observations made at one
      or more levels.

    Block layout
    ============

    The first column should have all 8 rows merged into one cell and contain
    human-readable label. It can be empty.

    The second ("meta") column contains:
        row 1:  "POKEMON"
        row 2:  Pokémon name (`Pokemon` enum)
        row 3:  "NATURE"
        row 4:  Nature (`Nature` enum)
        row 5:  "CHARACTERISTIC"
        row 6:  Characteristic (`Characteristic` enum)
        row 7:  ignored
        row 8:  ignored

    The third ("header") column contains:
        row 1:  LEVEL or LVL (case-insensitive, optional trailing ':')
        row 2:  empty
        rows 3-8: all `StatType names`, each appearing exactly once
                  in arbitrary order.

    Every following pair of columns represents one level data.

    Level block
    ===========

    The first row contains the level value in a cell merged across both columns.
    If the level cell is empty, the whole level block is ignored. This allows
    preparing future observations before the final level or TOTAL stats are known.

    The second row contains the headers:
        TOTAL    EV
    or
        EV       TOTAL
    The order is arbitrary.

    Rows 3-8 contain values for the stat whose name is given in the header column.
    TOTAL values are mandatory integers.
    EV values are integers; an empty EV cell is treated as 0.

    Example
    =======

    +==========+================+=======+=======+=======+=======+=======+=======+=======+
    |          | POKEMON        | LEVEL |       5       |               |       7       |
    +          +----------------+-------+-------+-------+-------+-------+-------+-------+
    |          | PIKACHU        |       | TOTAL |  EV   | TOTAL |  EV   | TOTAL |  EV   |
    +          +----------------+-------+-------+-------+-------+-------+-------+-------+
    |          | NATURE         | HP    |  35   |       |  37   |       |  39   |   4   |
    + label    +----------------+-------+-------+-------+-------+-------+-------+-------+
    | merged   | JOLLY          | ATK   |  20   |       |  23   |       |  26   |   0   |
    | over     +----------------+-------+-------+-------+-------+-------+-------+-------+
    | all      | CHARACTERISTIC | DEF   |  11   |       |  12   |       |  13   |       |
    + rows     +----------------+-------+-------+-------+-------+-------+-------+-------+
    |          | LIKES_TO_RUN   | SPATK |  14   |       |  16   |       |  18   |       |
    +          +----------------+-------+-------+-------+-------+-------+-------+-------+
    |          | ignored        | SPDEF |  10   |       |  11   |       |  12   |       |
    +          +----------------+-------+-------+-------+-------+-------+-------+-------+
    |          | ignored        | SPEED |  18   |       |  21   |       |  24   |  20   |
    +----------+----------------+-------+-------+-------+-------+-------+-------+-------+

    Args:
        path:
            Path to an .ods file.
        sheet_name:
            Specific sheet to parse. `None` for "all sheets"

    Returns:
        Parsed observation samples from all sheets.

    Raises:
        OSError:
            The file cannot be opened.

        OdsFormatError:
            Workbook structure is invalid.
    """
    path = Path(path)
    try:
        document = ezodf.opendoc(str(path))
    except Exception as exc:
        raise OSError(f"Unable to open ODS file {path!s}") from exc

    if sheet_name is not None:
        try:
            sheet = document.sheets[sheet_name]
        except KeyError:
            raise KeyError(f"No sheet named {sheet_name!r} in ODS file")
        return _parse_sheet(sheet)

    samples: list[ObsSample] = []
    for sheet in document.sheets.values():
        samples.extend(_parse_sheet(sheet))

    return samples


def get_samples_iv_sets(
    path: str | Path,
    sheet_name: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
) -> Generator[tuple[ObsSample, iv_calc.CalcedIVSets_T]]:
    """
    Parse an observation workbook.

    Args:
        path:
            Path to an .ods file.
        sheet_name:
            Specific sheet to parse. `None` for "all sheets"
        skip:
            Number of first records to skip
        limit:
            Max number of records to return

    Returns:
        Parsed observation samples from all sheets with their iv sets

    Raises:
        OSError:
            The file cannot be opened.

        OdsFormatError:
            Workbook structure is invalid.
    """
    parsed = _parse_ods(path, sheet_name)

    if limit is None:
        limit = len(parsed)

    for i in range(skip, min(skip + limit, len(parsed))):
        obs_sample = parsed[i]
        try:
            yield obs_sample, iv_calc.get_iv_sets(**obs_sample)
        except Exception as e:
            raise type(e)(f"Problem with sample {obs_sample['label']!r}: {e}")


def minmax_filter_samples_iv_sets(
    samples_iv_sets: Iterable[tuple[ObsSample, CalcedIVSets_T]],
    important_stat_types: Optional[dict[StatType, bool]] = None,
) -> tuple[
    Iterable[tuple[ObsSample, CalcedIVSets_T]],
    list[tuple[Optional[str], Optional[str]]]
]:
    """
    Filter obs_samples by their IV sets.
    Suppose we want all IVs to be as high as possible. Then if ALL maximal IVs
    of some sample A are not higher than ALL minimal IVs of some sample B, then
    sample A should be filtered out, because it's can NOT be better than B.

    Every stat we care about should be in `important_stat_types`. Respective
    value should be `True` if we want that stat as high as possible.
    Sometimes we want some IV be as low as possible (SPEED for trick-room
    Pokémon, for example), in which case respective value should be `False`.

    By default, if `None` was passed in `important_stat_types`, all stats
    will be considered as important and needed to be high.

    Returns "good" elements of `samples_iv_sets`, labels of filtered elements
    together with respective labels
    """
    if important_stat_types is None:
        important_stat_types = {stat_type: True for stat_type in StatType}

    if not isinstance(samples_iv_sets, list):
        # Normalize to list, consume possible iterators.
        samples_iv_sets = list(samples_iv_sets)
    if len(samples_iv_sets) < 2 or not important_stat_types:
        return iter(samples_iv_sets), []

    # Let's save filtered indices and reference indices they were filtered by.
    filtered_indices: dict[int, int] = dict()
    for i, (obs_sample, calced_iv_sets) in enumerate(samples_iv_sets):
        # Check if i-th element can be filtered.
        best_ivs: dict[StatType, int] = dict()
        for stat_type, asc in important_stat_types.items():
            fetcher: Callable = max if asc else min
            best_ivs[stat_type] = fetcher(calced_iv_sets[stat_type].values)

        for ref_i, (ref_obs_sample, ref_calced_iv_sets) in enumerate(samples_iv_sets):
            if i == ref_i:
                continue

            for stat_type, asc in important_stat_types.items():
                fetcher: Callable = min if asc else max
                worst_ref_iv = fetcher(ref_calced_iv_sets[stat_type].values)
                if best_ivs[stat_type] > worst_ref_iv:
                    # i-th element can NOT be filtered by current reference.
                    # Go to the next reference candidate.
                    break
            else:
                # We didn't break. I.e. `obs_sample` can NOT be better than
                # `ref_obs_sample` and should be filtered out.
                filtered_indices[i] = ref_i
                break

    good_sample_iv_sets = (
        element
        for (i, element) in enumerate(samples_iv_sets)
        if (i not in filtered_indices)
    )
    filtered_labels = list(
        (samples_iv_sets[i][0]['label'], samples_iv_sets[ref_i][0]['label'])
        for (i, ref_i) in filtered_indices.items()
    )

    return good_sample_iv_sets, filtered_labels


def _test_filter() -> None:
    important_stat_types = {
        StatType.HP: True,
        StatType.ATK: True,
        StatType.SPEED: False,
    }
    samples = [
        ({"label": "1"}, {  # first ref
            StatType.HP: {10, 12, 14},
            StatType.ATK: {10, 12, 14},
            StatType.DEF: {10, 12, 14},
            StatType.SPATK: {10, 12, 14},
            StatType.SPDEF: {10, 12, 14},
            StatType.SPEED: {20, 22, 24}
        }),
        ({"label": "2"}, {
            StatType.HP: {8, 10, 12, 14},
            StatType.ATK: {20, 22, 24},
            StatType.DEF: {20, 22, 24},
            StatType.SPATK: {20, 22, 24},
            StatType.SPDEF: {20, 22, 24},
            StatType.SPEED: {10, 12}
        }),
        ({"label": "3"}, {  # second and last ref
            StatType.HP: {20},
            StatType.ATK: {20, 22, 24},
            StatType.DEF: {20, 22, 24},
            StatType.SPATK: {20, 22, 24},
            StatType.SPDEF: {20, 22, 24},
            StatType.SPEED: {10, 12}
        }),
        ({"label": "4"}, {
            StatType.HP: {10, 12, 14, 20},
            StatType.ATK: {10, 12, 14},
            StatType.DEF: {10, 12, 14},
            StatType.SPATK: {10, 12, 14},
            StatType.SPDEF: {10, 12, 14},
            StatType.SPEED: {8}
        }),
        ({"label": "5"}, {
            StatType.HP: {10, 12, 14},
            StatType.ATK: {10, 12, 14},
            StatType.DEF: {10, 12, 14},
            StatType.SPATK: {10, 12, 14},
            StatType.SPDEF: {10, 12, 14},
            StatType.SPEED: {12, 14}
        }),
        ({"label": "6"}, {
            StatType.HP: {19},
            StatType.ATK: {19},
            StatType.DEF: {31},
            StatType.SPATK: {31},
            StatType.SPDEF: {31},
            StatType.SPEED: {13}
        }),
    ]

    samples_iv_sets, filtered_labels = minmax_filter_samples_iv_sets(samples, important_stat_types)
    print("Filtered samples:", filtered_labels)


def pprint_sample_iv_sets(
    obs_sample: ObsSample,
    iv_sets: CalcedIVSets_T,
    color_mode: iv_calc.ColorMode = "max",
    important_stat_types: Optional[Container[StatType]] = None,
    print_only_important: bool = True,
) -> None:
    label, name, nature, characteristic = (
        obs_sample["label"], obs_sample['spec'].name, obs_sample["nature"], obs_sample["characteristic"]
    )
    if nature is not None:
        nature = nature.name
    if characteristic is not None:
        characteristic = characteristic.name
    print(f"{label}: {name}({nature=}, {characteristic=})")
    iv_calc.pprint_iv_sets(iv_sets, color_mode, important_stat_types, print_only_important)


def process_ods_with_filter(
    path: Path | str,
    sheet_name: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    important_stat_types: Optional[dict[StatType, bool]] = None,
    minmax_filter: bool = True,
    color_mode: iv_calc.ColorMode = "max",
    print_only_important: bool = True,
) -> None:
    samples_iv_sets = get_samples_iv_sets(path, sheet_name, skip, limit)

    if minmax_filter:
        samples_iv_sets, filtered_labels = minmax_filter_samples_iv_sets(samples_iv_sets, important_stat_types)
        if filtered_labels:
            print("Filtered samples:")
            for label, ref_label in filtered_labels:
                print(f"{label} ≤ {ref_label}")
        print()

    for obs_sample, iv_sets in samples_iv_sets:
        pprint_sample_iv_sets(obs_sample, iv_sets, color_mode, important_stat_types, print_only_important)
        print()


def main():
    ...
    process_ods_with_filter(
        path='~/Documents/pkmn/samples/Aron.ods',
        sheet_name='Initial',
        skip=0,
        limit=None,
        important_stat_types={
            StatType.HP: True,
            StatType.ATK: True,
            StatType.DEF: True,
            StatType.SPDEF: True,
            StatType.SPEED: True
        }
    )

    # _test_filter()


if __name__ == '__main__':
    main()
