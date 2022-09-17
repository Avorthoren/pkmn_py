from collections.abc import Collection
from typing import Iterable

from pkmn_stat import IVRanges
from pokemon import Species, Pokemon, Sample
from utils import NumRange_T


class PokemonComparator:
	def __init__(
		self,
		samples: dict[Species | Pokemon, IVRanges],
		ref_sample: Sample = None
	):
		# Save initial samples order to fast retrieval.
		self._samples = samples
		self._initial_order = {
			s: i
			for i, s in enumerate(self._samples)
		}
		self._ref_sample = ref_sample

	def get_initial_position(self, sample: Species | Pokemon) -> int:
		return self._initial_order[sample]

	def get_comparison(self, lvl: int = None) -> dict[Sample, ...]:
		...


def main():
	...


if __name__ == "__main__":
	main()
