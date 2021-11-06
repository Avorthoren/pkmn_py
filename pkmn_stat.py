from enum import Enum


def clamp(x, min_=None, max_=None):
	if min_ is not None:
		x = max(min_, x)
	if max_ is not None:
		x = min(x, max_)

	return x


class StatType(Enum):
	HP = 1
	ATK = 2
	DEF = 3
	SPATK = 4
	SPDEF = 5
	SPEED = 6


class Stat:
	_IV_MIN_VALUE = 0
	_IV_MAX_VALUE = 31

	@classmethod
	def _clamp_iv(cls, val: int) -> int:
		return clamp(val, cls._IV_MIN_VALUE, cls._IV_MAX_VALUE)

	def __init__(
		self,
		type_: StatType,
		base: int,
		lvl: int = None,
		val: int = None,
		iv: int = None,
		ev: int = 0,
		mult: float = 1.0  # nature multiplier
	):
		self._type = type_
		self._base = base
		self._lvl = lvl
		self._val = val
		self._iv = iv
		self._ev = ev
		self._mult = mult

	def get_val(self, lvl: int = None) -> int:
		"""Get stat value."""
		if lvl is None:
			if self._lvl is None:
				raise ValueError("Lvl must be specified")

			if self._val is not None:
				return self._val

			lvl = self._lvl

		if self._iv is None:
			raise ValueError("IV must be specified")

		if self._type is StatType.HP:
			return (2*self._base + self._iv + self._ev//4) * lvl // 100 + lvl + 10
		else:
			return int(((2 * self._base + self._iv + self._ev // 4) * lvl // 100 + 5) * self._mult)

	@classmethod
	def min_(cls, left: int, mult: float) -> int:
		"""Get min int x such that left >= x * mult."""
		res = int(left / mult)

		return res if left >= int(res * mult) else res + 1

	@classmethod
	def max_(cls, left: int, mult: float) -> int:
		"""Get max int x such that left <= x * mult."""
		res = int((left + 1) / mult)

		return res if left <= int(res * mult) else res - 1

	@classmethod
	def range_(cls, left, mult):
		min_ = cls.min_(left, mult)
		max_ = cls.max_(left, mult)
		if min_ > max_:
			raise RuntimeError(f"Impossible range: ({min_}, {max_})")

		return min_, max_

	@staticmethod
	def range_merge(r1, r2):
		return min(r1[0], r2[0]), max(r1[1], r2[1])

	def get_iv_range(self):
		if self._lvl is None:
			raise ValueError("Lvl must be specified")
		if self._val is None:
			raise ValueError("Stat value must be specified")

		if self._type == StatType.HP:
			left = self._val - 10 - self._lvl
			range_ = left, left
		else:
			range_ = self.range_(self._val, self._mult)
			range_ = range_[0] - 5, range_[1] - 5

		range_ = self.range_merge(
			self.range_(range_[0], self._lvl/100),
			self.range_(range_[1], self._lvl/100)
		)

		base_and_ev = 2*self._base + self._ev//4
		range_ = range_[0] - base_and_ev, range_[1] - base_and_ev

		if range_[0] > self._IV_MAX_VALUE or range_[1] < self._IV_MIN_VALUE:
			raise ValueError(f"Calculated {self._type.name} IVs are impossible: {range_}")

		return self._clamp_iv(range_[0]), self._clamp_iv(range_[1])


def main():
	left = 4356465
	mult = 5
	min_, max_ = Stat.range_(left, mult)
	print(min_, max_)
	print(f"{int(min_ * mult)} .. {left} .. {int(max_ * mult)}")


if __name__ == "__main__":
	main()
