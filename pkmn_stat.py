import math
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
	_MIN_VALUE = 0
	_MAX_VALUE = 31

	@classmethod
	def clamp(cls, val):
		return clamp(val, cls._MIN_VALUE, cls._MAX_VALUE)

	def __init__(self, type_, base, lvl=None, val=None, iv=None, ev=0, mult=1.0):
		self._type = type_
		self._base = base
		self._lvl = lvl
		self._val = val
		self._iv = iv
		self._ev = ev
		self._mult = mult

	def getVal(self, lvl=None):
		if lvl is None:
			if self._lvl is None:
				raise ValueError("Lvl must be specified")

			if self._val is not None:
				return self._val

			lvl = self._lvl

		if self._iv is None:
			raise ValueError("IV must be specified")

		if self._type == StatType.HP:
			return (2*self._base + self._iv + self._ev//4) * lvl // 100 + lvl + 10
		else:
			return math.floor(((2 * self._base + self._iv + self._ev // 4) * lvl // 100 + 5) * self._mult)

	@classmethod
	def min_(cls, left, mult):
		res = int(left / mult)
		if int(res * mult) == left:
			return res
		elif int((res + 1) * mult) == left:
			return res + 1
		else:
			raise Exception("min_() implementation error")

	@classmethod
	def max_(cls, left, mult):
		res = int((left + 1) / mult)
		if int(res * mult) == left:
			return res
		elif int((res - 1) * mult) == left:
			return res - 1
		else:
			raise Exception("max_() implementation error")

	@classmethod
	def range_(cls, left, mult):
		return cls.min_(left, mult), cls.max_(left, mult)

	@staticmethod
	def rangeMerge(r1, r2):
		return min(r1[0], r2[0]), max(r1[1], r2[1])

	def getIVRange(self):
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

		range_ = self.rangeMerge(
			self.range_(range_[0], self._lvl/100),
			self.range_(range_[1], self._lvl/100)
		)

		baseAndEV = 2*self._base + self._ev//4
		range_ = range_[0] - baseAndEV, range_[1] - baseAndEV

		if range_[0] > self._MAX_VALUE or range_[1] < self._MIN_VALUE:
			raise ValueError(f"Calculated {self._type.name} IVs are impossible: [{range_[0]}, {range_[1]}]")

		return self.clamp(range_[0]), self.clamp(range_[1])
