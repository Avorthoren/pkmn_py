import math
import random

from pkmn_stat import Stat
from pkmn_stat_type import StatType


_TOTAL_STATS = len(StatType)


def _perfect_child_ivs_spread_validate(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
    ignored_stats: int,
) -> None:
    total_stats = _TOTAL_STATS - ignored_stats

    if not (0 <= mother_perfect_ivs <= total_stats):
        raise ValueError(f"perfect IVs count should be in range 0..{total_stats}")
    if not (0 <= father_perfect_ivs <= total_stats):
        raise ValueError(f"perfect IVs count should be in range 0..{total_stats}")

    min_common = max(0, mother_perfect_ivs + father_perfect_ivs - total_stats)
    max_common = min(mother_perfect_ivs, father_perfect_ivs)
    if not (min_common <= common_perfect_ivs <= max_common):
        raise ValueError(
            f"common perfect IVs count should be in range {min_common}..{max_common}"
        )


def _get_parents_perfect_ivs_template(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
    ignored_stats: int,
) -> list[int]:
    total_stats = _TOTAL_STATS - ignored_stats

    # for each stat: how many parents have that stat perfect?
    stat_marks = [
        (2 if i < common_perfect_ivs else int(i < mother_perfect_ivs + father_perfect_ivs - common_perfect_ivs))
        for i in range(total_stats)
    ]
    # Example for common_perfect_ivs=2, mother_perfect_ivs=4, father_perfect_ivs=3, ignored_stats=0:
    # [2, 2, 1, 1, 1, 0]
    return stat_marks


def _get_child_perfect_ivs_count(
    parents_perfect_ivs_template: list[int],
    destiny_knot: bool = True,
) -> int:
    inherited_stats_count = 5 if destiny_knot else 3
    # Of course, ignored stats also can be inherited.
    inherited_stats = random.sample(range(_TOTAL_STATS), k=inherited_stats_count)
    total_perfect_ivs = 0
    for i, mark in enumerate(parents_perfect_ivs_template):
        # `i` here always represents relevant (non-ignored) stat, because
        # that's how `parents_perfect_ivs_template` was built.
        if i not in inherited_stats:
            # random value.
            total_perfect_ivs += random.randint(Stat.IV_RANGE.min, Stat.IV_RANGE.max) == Stat.IV_RANGE.max
        elif mark == 2:
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
    ignored_stats: int,  # it's irrelevant..?
    girls_rate: float = 0.5,
    destiny_knot: bool = True,
    total_rolls: int = 100_000
) -> tuple[float, float, dict[int, float]]:
    """
    Estimates potential perfect IVs count for child for gen VI+.

    Usually, 1 of 6 stats is irrelevant (for example SPATK for physical
    damagers). But other options are possible as well. Use `ignored_stats`
    for that.
    In `mother_perfect_ivs`, `father_perfect_ivs` and `common_perfect_ivs`
    only relevant stats (non-ignored) should be counted.

    `girls_rate` indicates the probability of egg producing a female.

    Child inherits 3 random stats from parents (for each stat parent is chosen
    randomly). If any parent holds Destiny Knot - it inherits 5 random stats
    instead of 3 (still, each stat from random parent).

    Returns:
         probability of child being a girl with more perfect IVs than mother,
         probability of child being a boy with more perfect IVs than father,
         probabilities of child having all possible counts of perfect IVs.
    """
    _perfect_child_ivs_spread_validate(
        mother_perfect_ivs,
        father_perfect_ivs,
        common_perfect_ivs,
        ignored_stats
    )

    parents_perfect_ivs_template = _get_parents_perfect_ivs_template(
        mother_perfect_ivs,
        father_perfect_ivs,
        common_perfect_ivs,
        ignored_stats
    )
    perfect_ivs_count_results: dict[int, int] = {i: 0 for i in range(_TOTAL_STATS - ignored_stats + 1)}
    for _ in range(total_rolls):
        child_perfect_ivs_count = _get_child_perfect_ivs_count(
            parents_perfect_ivs_template,
            destiny_knot
        )
        perfect_ivs_count_results[child_perfect_ivs_count] += 1

    p_girl_better_than_mother = sum(
        count
        for child_perfect_ivs_count, count in perfect_ivs_count_results.items()
        if child_perfect_ivs_count > mother_perfect_ivs
    ) / total_rolls * girls_rate
    p_boy_better_than_father = sum(
        count
        for child_perfect_ivs_count, count in perfect_ivs_count_results.items()
        if child_perfect_ivs_count > father_perfect_ivs
    ) / total_rolls * (1 - girls_rate)
    spread: dict[int, float] = {
        i: count / total_rolls
        for i, count in perfect_ivs_count_results.items()
    }

    return p_girl_better_than_mother, p_boy_better_than_father, spread


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


def _get_percent_str(x: float) -> str:
    precision = _get_percent_precision(x)
    return f"{100 * x:.{precision}f}%"


def pprint_perfect_child_ivs_spread(
    p_girl_better_than_mother: float,
    p_boy_better_than_father: float,
    spread: dict[int, float]
) -> None:
    print(f"{_get_percent_str(p_girl_better_than_mother)} for getting a girl with more perfect IVs than mother")
    print(f"{_get_percent_str(p_boy_better_than_father)} for getting a boy with more perfect IVs than father")
    for i, p in spread.items():
        print(f"{i} perfect IVs: {_get_percent_str(p)}")


def analyze_child_ivs(
    mother_perfect_ivs: int,
    father_perfect_ivs: int,
    common_perfect_ivs: int,
    ignored_stats: int,  # it's irrelevant..?
    girls_rate: float = 0.5,
    destiny_knot: bool = True,
    total_rolls: int = 100_000
) -> None:
    """
    Read `get_perfect_child_ivs_spread` docs for args description.
    """
    p_girl_better_than_mother, p_boy_better_than_father, spread = get_perfect_child_ivs_spread(
        mother_perfect_ivs,
        father_perfect_ivs,
        common_perfect_ivs,
        ignored_stats,
        girls_rate,
        destiny_knot,
        total_rolls
    )
    print(girls_rate, 'girls. Perfect IVs template')
    print(
        '-' * (mother_perfect_ivs - common_perfect_ivs)
        + '+' * common_perfect_ivs
        + '-' * (father_perfect_ivs - common_perfect_ivs)
        + '.' * ignored_stats
    )
    print()
    print("Spread:")
    pprint_perfect_child_ivs_spread(p_girl_better_than_mother, p_boy_better_than_father, spread)


def main():
    ...
    analyze_child_ivs(
        mother_perfect_ivs=3,
        father_perfect_ivs=5,
        common_perfect_ivs=3,
        ignored_stats=1,
        girls_rate=0.5,
    )

    # for x in (1, 0.11, 0.1, 0.011, 0.01):
    #     print(x, _get_percent_precision(x), _get_percent_str(x))


if __name__ == "__main__":
    main()
