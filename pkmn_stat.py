from dataclasses import dataclass
from fractions import Fraction
from typing import Union

import voluptuous as vlps

from pkmn_stat_type import StatType, GenStatType
from utils import enum_const_dict, multiplier_range_frac, NumRange_T, IntRange,\
	IntOrRange_T, FracRange, IntOrFracOrRange_T
from nature import Nature


LVL_RANGE = IntRange(1, 100)
# Used in formulas
LVL_NORM = 100


class BaseStats(enum_const_dict(StatType, int)):
	...


class IVRanges(enum_const_dict(StatType, IntOrRange_T)):
	...


class GenStats(enum_const_dict(GenStatType, int)):
	...


@dataclass(slots=True)
class StatData:
	value: int = None
	iv: IntOrRange_T = None
	ev: IntOrRange_T = 0


class StatsData(enum_const_dict(StatType, StatData)):
	...


NatureMult_T = int | Fraction


class Stat:
	BASE_RANGE = IntRange(0, 256)
	IV_RANGE = IntRange(0, 31)
	EV_RANGE = IntRange(0, 252)

	DEFAULT_MULT = 1
	INCREASED_MULT = Fraction(11, 10)
	DECREASED_MULT = Fraction(9, 10)
	MULT_RANGE = FracRange(DECREASED_MULT, INCREASED_MULT)
	POSSIBLE_MULTS = DEFAULT_MULT, INCREASED_MULT, DECREASED_MULT

	@classmethod
	def get_mult(cls, stat_type: StatType, nature: Nature):
		if stat_type == StatType.HP:
			return None
		elif nature.is_simple():
			return cls.DEFAULT_MULT
		elif stat_type == nature.increased:
			return cls.INCREASED_MULT
		elif stat_type == nature.decreased:
			return cls.DECREASED_MULT
		else:
			return cls.DEFAULT_MULT

	def __init__(
		self,
		type_: StatType,
		base: int,
		lvl: int = None,
		val: int = None,
		iv: IntOrRange_T = None,
		ev: int = None,
		mult: NatureMult_T = None
	):
		self._type = vlps.Schema(StatType)(type_)
		self._base = vlps.Schema(vlps.All(int, vlps.Range(*self.BASE_RANGE)))(base)
		self._lvl = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*LVL_RANGE))))(lvl)
		self._iv = vlps.Schema(vlps.Maybe(
			vlps.All(
				vlps.Any(IntRange, vlps.All(int, vlps.Coerce(IntRange))),
				vlps.Range(*self.IV_RANGE),
				IntRange.is_straight_validator
			)
		))(iv)
		self._ev = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*self.EV_RANGE))))(ev)

		if type_ == StatType.HP:
			# For HP multiplier always is None (not used), but for protection
			# against gross typos:
			if mult is not None and mult != self.DEFAULT_MULT:
				raise ValueError(f"{StatType.HP} can not have nature multiplier")
			self._mult = None
		elif mult is None:
			self._mult = None
		else:
			self._mult = vlps.Schema(vlps.In(self.POSSIBLE_MULTS))(mult)

		if val is None:
			self._val = None
			try:
				self._val = self.get_val()
			except ValueError:
				pass
		else:
			try:
				self._val = vlps.Schema(vlps.All(int, vlps.Range(*self.calc_val(
					self._type,
					self._base,
					self._iv,
					self._ev,
					self._lvl,
					self._mult
				))))(val)
			except vlps.Error as e:
				raise ValueError(f"{self._type} {e}")

	@property
	def type(self) -> StatType:
		return self._type

	@property
	def base(self) -> int:
		return self._base

	@classmethod
	def _calc_hp_val(
		cls,
		base: IntOrRange_T,
		lvl: IntOrRange_T,
		iv: IntOrRange_T,
		ev: IntOrRange_T
	) -> IntOrRange_T:
		return (2*base + iv + ev//4) * lvl // LVL_NORM + lvl + 10

	@classmethod
	def _calc_non_hp_val(
		cls,
		base: IntOrRange_T,
		lvl: IntOrRange_T,
		iv: IntOrRange_T,
		ev: IntOrRange_T,
		mult: IntOrFracOrRange_T
	) -> IntOrRange_T:
		val = (2*base + iv + ev//4) * lvl // LVL_NORM + 5
		if mult != cls.DEFAULT_MULT:
			val = val * mult.numerator // mult.denominator

		return val

	@classmethod
	def _calc_val(
		cls,
		type_: StatType,
		base: IntOrRange_T,
		lvl: IntOrRange_T,
		iv: IntOrRange_T,
		ev: IntOrRange_T,
		mult: IntOrFracOrRange_T | None  # None for HP.
	) -> IntOrRange_T:
		if type_ == StatType.HP:
			return cls._calc_hp_val(base, lvl, iv, ev)
		else:
			return cls._calc_non_hp_val(base, lvl, iv, ev, mult)

	@classmethod
	def calc_val(
		cls,
		type_: StatType,
		base: IntOrRange_T,
		lvl: IntOrRange_T = None,
		iv: IntOrRange_T = None,
		ev: IntOrRange_T = None,
		mult: NatureMult_T = None
	) -> IntOrRange_T:
		if lvl is None:
			lvl = LVL_RANGE

		if iv is None:
			iv = cls.IV_RANGE

		if ev is None:
			ev = cls.EV_RANGE

		if type_ == StatType.HP:
			if mult is not None:
				raise ValueError(f"{StatType.HP} can not have nature multiplier")
		elif mult is None:
			mult = cls.MULT_RANGE

		return cls._calc_val(type_, base, iv, ev, lvl, mult)

	def get_val(
		self,
		lvl: IntOrRange_T = None,
		iv: IntOrRange_T = None,
		ev: IntOrRange_T = None,
		mult: NatureMult_T = None
	) -> IntOrRange_T:
		"""Get stat value."""
		if lvl is None:
			lvl = self._lvl

		if iv is None:
			iv = self._iv

		if ev is None:
			ev = self._ev

		if mult is None:
			mult = self._mult

		return self.calc_val(self._type, self._base, lvl, iv, ev, mult)

	def get_iv(
		self,
		lvl: int = None,
		val: int = None,
		ev: IntOrRange_T = None,
		mult: NatureMult_T = None  # None for self value
	) -> IntRange:
		if lvl is None:
			if self._lvl is None:
				raise ValueError("Lvl must be specified")
			lvl = self._lvl

		if val is None:
			if self._val is None:
				raise ValueError("Stat value must be specified")
			val = self._val

		if ev is None:
			ev = self._ev

		if mult is None:
			if self._mult is None and self._type != StatType.HP:
				raise ValueError("Nature multiplier must be specified")
			mult = self._mult

		#     HP =  (2*base + iv + ev//4) * lvl // LVL_NORM + lvl + 10
		# NON_HP = ((2*base + iv + ev//4) * lvl // LVL_NORM + 5) * mult

		if self._type == StatType.HP:
			range_ = val - 10 - lvl
		elif mult != self.DEFAULT_MULT:
			range_ = multiplier_range_frac(mult, val) - 5
		else:
			range_ = val - 5

		range_ = multiplier_range_frac(Fraction(lvl, LVL_NORM), range_)
		range_ -= 2*self._base + ev//4
		try:
			range_.clamp(self.IV_RANGE)
		except ValueError as e:
			raise ValueError(f"Calculated {self._type.name} IVs are impossible: {e}") from e

		return range_


def main():
	lvl = 78

	# stats = [
	# 	Stat(StatType.HP,    base=108, iv=24, lvl=lvl, ev=74),
	# 	Stat(StatType.ATK,   base=130, iv=12, lvl=lvl, ev=190, mult=Stat.INCREASED_MULT),
	# 	Stat(StatType.DEF,   base=95,  iv=30, lvl=lvl, ev=91),
	# 	Stat(StatType.SPATK, base=80,  iv=16, lvl=lvl, ev=48,  mult=Stat.DECREASED_MULT),
	# 	Stat(StatType.SPDEF, base=85,  iv=23, lvl=lvl, ev=84),
	# 	Stat(StatType.SPEED, base=102, iv=5,  lvl=lvl, ev=23)
	# ]
	# for stat in stats:
	# 	print(f"{stat._type.name}: {stat.get_val(lvl)}")

	stats = [
		Stat(StatType.HP,    base=108, val=289, lvl=lvl, ev=74),              # 24
		Stat(StatType.ATK,   base=130, val=278, lvl=lvl, ev=190, mult=Stat.INCREASED_MULT),   # 12
		Stat(StatType.DEF,   base=95,  val=193, lvl=lvl, ev=91),              # 30
		Stat(StatType.SPATK, base=80,  val=135, lvl=lvl, ev=48,  mult=Stat.DECREASED_MULT),   # 16
		Stat(StatType.SPDEF, base=85,  val=171, lvl=lvl, ev=84),              # 23
		Stat(StatType.SPEED, base=102, val=171, lvl=lvl, ev=23)               # 5
	]

	for stat in stats:
		print(f"{stat.type.name}: {stat.get_iv()}")
	print()

	stats = [
		Stat(StatType.HP,    base=70, val=54, lvl=17),              # 24
		Stat(StatType.ATK,   base=110, val=45, lvl=17),   # 12
		Stat(StatType.DEF,   base=180,  val=60, lvl=17, mult=Stat.DECREASED_MULT),              # 30
		Stat(StatType.SPATK, base=60,  val=28, lvl=17),   # 16
		Stat(StatType.SPDEF, base=60,  val=30, lvl=17, mult=Stat.INCREASED_MULT),              # 23
		Stat(StatType.SPEED, base=50, val=22, lvl=17)               # 5
	]

	for stat in stats:
		print(f"{stat.type.name}: {stat.get_iv()}")
	print()

	lvl = 50
	print(Stat.calc_val(type_=StatType.HP, base=70, lvl=lvl))
	print(Stat.calc_val(type_=StatType.ATK, base=110, lvl=lvl))
	print(Stat.calc_val(type_=StatType.DEF, base=180, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPATK, base=60, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPDEF, base=60, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPEED, base=50, lvl=lvl))
	print()

	lvl = 100
	print(Stat.calc_val(type_=StatType.HP, base=70, lvl=lvl))
	print(Stat.calc_val(type_=StatType.ATK, base=110, lvl=lvl))
	print(Stat.calc_val(type_=StatType.DEF, base=180, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPATK, base=60, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPDEF, base=60, lvl=lvl))
	print(Stat.calc_val(type_=StatType.SPEED, base=50, lvl=lvl))
	print()


	# sd = StatsData({
	# 	StatType.HP: StatData(51),
	# 	StatType.ATK: StatData(17),
	# 	StatType.DEF: StatData(39),
	# 	StatType.SPATK: StatData(15),
	# 	StatType.SPDEF: StatData(18),
	# 	StatType.SPEED: StatData(51)
	# })
	# pretty_print(sd)

	# print(multiplier_range_frac(Fraction(76, 100), 200))
	# print()
	# print(multiplier_range_frac(Fraction(13, 100), 51))
	#
	# sd = StatsData({
	# 	st: StatData()
	# 	for st in StatType
	# })
	# pretty_print(sd)


if __name__ == "__main__":
	main()
