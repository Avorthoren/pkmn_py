import math
import random

from pkmn_stat import Stat
from pkmn_stat_type import StatType


_TOTAL_STATS = len(StatType)


def _perfect_child_ivs_spread_validate(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
) -> None:
    if not (0 <= mother_perfect_ivs <= _TOTAL_STATS):
        raise ValueError(f"perfect IVs count should be in range 0..{_TOTAL_STATS}")
    if not (0 <= father_perfect_ivs <= _TOTAL_STATS):
        raise ValueError(f"perfect IVs count should be in range 0..{_TOTAL_STATS}")

    min_common = max(0, mother_perfect_ivs + father_perfect_ivs - _TOTAL_STATS)
    max_common = min(mother_perfect_ivs, father_perfect_ivs)
    if not (min_common <= common_perfect_ivs <= max_common):
        raise ValueError(
            f"common perfect IVs count should be in range {min_common}..{max_common}"
        )


def _get_parents_perfect_ivs_template(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
) -> list[int]:
    # for each stat: how many parents have that stat perfect?
    stat_marks = [0] * _TOTAL_STATS
    i = 0
    while i < common_perfect_ivs:
        stat_marks[i] = 2
        i += 1
    one_parent_ivs = mother_perfect_ivs + father_perfect_ivs - 2 * common_perfect_ivs
    while i < common_perfect_ivs + one_parent_ivs:
        stat_marks[i] = 1
        i += 1

    return stat_marks


def _get_child_perfect_ivs_count(
    parents_perfect_ivs_template: list[int],
    destiny_knot: bool = True,
) -> int:
    inherited_stats_count = 5 if destiny_knot else 3
    inherited_stats = random.sample(range(_TOTAL_STATS), k=inherited_stats_count)
    total_perfect_ivs = 0
    for i, mark in enumerate(parents_perfect_ivs_template):
        if i not in inherited_stats:
            # random value.
            total_perfect_ivs += random.randint(Stat.IV_RANGE.min, Stat.IV_RANGE.max) == Stat.IV_RANGE.max
            continue
        if mark == 2:
            # Both parents have perfect IV: inherits perfect.
            total_perfect_ivs += 1
        elif mark == 1:
            # One of parents has perfect IV: inherits it half of the time.
            total_perfect_ivs += random.randint(0, 1) == 1
        # mark == 0: both parents have non-perfect: inherits non-perfect.

    return total_perfect_ivs


def get_perfect_child_ivs_spread(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
    destiny_knot: bool = True,
    total_rolls: int = 100_000
) -> tuple[float, float, dict[int, float]]:
    """
    Estimates potential perfect IVs count for child for gen VI+.

    Child inherits 3 random stats from parents (for each stat parent is chosen
    randomly). If any parent holds Destiny Knot - it inherits 5 random stats
    instead of 3 (still, each stat from random parent).

    Returns:
         probability of child having higher count of perfect IVs than at least
         one of parents,
         probability of child having higher count of perfect IVs than both
         parents,
         probabilities of child having all possible counts of perfect IVs.
    """
    _perfect_child_ivs_spread_validate(
        mother_perfect_ivs,
        father_perfect_ivs,
        common_perfect_ivs,
    )

    parents_perfect_ivs_template = _get_parents_perfect_ivs_template(
        mother_perfect_ivs,
        father_perfect_ivs,
        common_perfect_ivs,
    )
    perfect_ivs_count_results: dict[int, int] = {i: 0 for i in range(_TOTAL_STATS + 1)}
    for _ in range(total_rolls):
        child_perfect_ivs_count = _get_child_perfect_ivs_count(
            parents_perfect_ivs_template,
            destiny_knot
        )
        perfect_ivs_count_results[child_perfect_ivs_count] += 1

    p1 = sum(
        count
        for i, count in perfect_ivs_count_results.items()
        if i > min(mother_perfect_ivs, father_perfect_ivs)
    ) / total_rolls
    p2 = sum(
        count
        for i, count in perfect_ivs_count_results.items()
        if i > max(mother_perfect_ivs, father_perfect_ivs)
    ) / total_rolls
    spread: dict[int, float] = {
        i: count / total_rolls
        for i, count in perfect_ivs_count_results.items()
    }

    return p1, p2, spread


def _get_percent_precision(x: float) -> int:
    """
    10+ -> 1
    1+ -> 2
    0.1+ -> 3
    """
    if x <= 0:
        return 0

    p = math.log10(100 * x)
    return max(1, 2 - math.floor(p))


def pprint_perfect_child_ivs_spread(p1: float, p2: float, spread: dict[int, float]) -> None:
    print(f"{p1 * 100:.{_get_percent_precision(p1)}f}% for having more perfect IVs than worse parent")
    print(f"{p2 * 100:.{_get_percent_precision(p2)}f}% for having more perfect IVs than best parent")
    for i, p in spread.items():
        print(f"{p * 100:.{_get_percent_precision(p)}f}% for having {i} perfect IVs")


def main():
    ...
    p1, p2, spread = get_perfect_child_ivs_spread(3, 3, 2)
    pprint_perfect_child_ivs_spread(p1, p2, spread)

    # for x in (1, 0.11, 0.1, 0.011, 0.01):
    #     print(x, _get_percent_precision(x), f"{100 * x:.{_get_percent_precision(x)}f}%}}")


if __name__ == "__main__":
    main()
