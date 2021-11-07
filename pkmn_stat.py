from dataclasses import dataclass
from fractions import Fraction
from typing import Union

import voluptuous as vlps

import pokemon
from utils import const_dict, pretty_print, SEnum, multiplier_range_frac, summand_range, IntRange_T


class StatType(SEnum):
	HP = 1
	ATK = 2
	DEF = 3
	SPATK = 4
	SPDEF = 5
	SPEED = 6


@dataclass
class StatData:
	value: int = None
	iv: int = None
	ev: int = None


class StatsData(const_dict(vlps.Schema({
	StatType: StatData
	for stat_type in StatType
}))):
	...


NatureMult_T = Union[int, Fraction]


class Stat:
	BASE_RANGE = 0, 256
	IV_RANGE = 0, 31
	EV_RANGE = 0, 252

	INCREASED_MULT = Fraction(11, 10)
	DECREASED_MULT = Fraction(9, 10)
	POSSIBLE_NATURE_MULTS = 1, INCREASED_MULT, DECREASED_MULT

	def __init__(
		self,
		type_: StatType,
		base: int,
		lvl: int = None,
		val: int = None,
		iv: int = None,
		ev: int = 0,
		mult: Union[NatureMult_T, None] = 1  # nature multiplier with convenient default value
	):
		self._type = vlps.Schema(StatType)(type_)
		self._base = vlps.Schema(vlps.All(int, vlps.Range(*self.BASE_RANGE)))(base)
		self._lvl = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*pokemon.LVL_RANGE))))(lvl)
		self._iv = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*self.IV_RANGE))))(iv)
		self._ev = vlps.Schema(vlps.All(int, vlps.Range(*self.EV_RANGE)))(ev)

		if type_ == StatType.HP:
			if mult is not None and mult != 1:
				raise ValueError(f"{StatType.HP} can not have nature multiplier")
			# If mult=1 will be provided it will still be explicitly ignored.
			self._mult = None
		else:
			self._mult = vlps.Schema(vlps.In(self.POSSIBLE_NATURE_MULTS))(mult)

		self._val = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*self.get_val_range(
			self._type,
			self._base,
			self._iv,
			self._ev,
			self._lvl,
			self._mult
		)))))(val)

	@classmethod
	def _get_hp_val(
		cls,
		base: int,
		iv: int,
		ev: int,
		lvl: int
	) -> int:
		return (2*base + iv + ev//4) * lvl//pokemon.LVL_RANGE[1] + lvl + 10

	@classmethod
	def _get_non_hp_val(
		cls,
		base: int,
		iv: int,
		ev: int,
		lvl: int,
		mult: NatureMult_T
	) -> int:
		val = (2*base + iv + ev//4) * lvl//pokemon.LVL_RANGE[1] + 5
		if mult != 1:
			val = val * mult.numerator // mult.denominator

		return val

	@classmethod
	def _get_val(
		cls,
		type_: StatType,
		base: int,
		iv: int,
		ev: int,
		lvl: int,
		mult: Union[NatureMult_T, None] = None
	) -> int:
		if type_ == StatType.HP:
			return cls._get_hp_val(base, iv, ev, lvl)
		else:
			return cls._get_non_hp_val(base, iv, ev, lvl, mult)

	@classmethod
	def get_val_range(
		cls,
		type_: StatType,
		base: int,
		iv: Union[int, None],
		ev: int,
		lvl: Union[int, None],
		mult: Union[NatureMult_T, None] = None
	) -> IntRange_T:
		iv_range = cls.IV_RANGE if iv is None else (iv, iv)
		lvl_range = pokemon.LVL_RANGE if lvl is None else (lvl, lvl)

		return (
			cls._get_val(type_, base, iv_range[0], ev, lvl_range[0], mult),
			cls._get_val(type_, base, iv_range[1], ev, lvl_range[1], mult)
		)

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

		return self._get_val(self._type, self._base, self._iv, self._ev, lvl, self._mult)

	def get_iv_range(self) -> IntRange_T:
		if self._lvl is None:
			raise ValueError("Lvl must be specified")
		if self._val is None:
			raise ValueError("Stat value must be specified")

		if self._type == StatType.HP:
			left = self._val - 10 - self._lvl
			range_ = left, left
		elif self._mult != 1:
			range_ = multiplier_range_frac(self._mult, self._val)
			range_ = summand_range(5, range_)
		else:
			left = self._val - 5
			range_ = left, left

		range_ = multiplier_range_frac(Fraction(self._lvl, 100), range_)

		base_and_ev = 2*self._base + self._ev//4
		try:
			range_ = summand_range(base_and_ev, range_, *self.IV_RANGE)
		except ValueError as e:
			raise ValueError(f"Calculated {self._type.name} IVs are impossible: {e}") from e

		return range_


def main():
	lvl = 78

	stats = [
		Stat(StatType.HP,    base=108, iv=24, lvl=lvl, ev=74),
		Stat(StatType.ATK,   base=130, iv=12, lvl=lvl, ev=190, mult=Stat.INCREASED_MULT),
		Stat(StatType.DEF,   base=95,  iv=30, lvl=lvl, ev=91),
		Stat(StatType.SPATK, base=80,  iv=16, lvl=lvl, ev=48,  mult=Stat.DECREASED_MULT),
		Stat(StatType.SPDEF, base=85,  iv=23, lvl=lvl, ev=84),
		Stat(StatType.SPEED, base=102, iv=5,  lvl=lvl, ev=23)
	]
	for stat in stats:
		print(f"{stat._type.name}: {stat.get_val(lvl)}")

	stats = [
		Stat(StatType.HP,    base=108, val=289, lvl=lvl, ev=74),              # 24
		Stat(StatType.ATK,   base=130, val=278, lvl=lvl, ev=190, mult=Stat.INCREASED_MULT),   # 12
		Stat(StatType.DEF,   base=95,  val=193, lvl=lvl, ev=91),              # 30
		Stat(StatType.SPATK, base=80,  val=135, lvl=lvl, ev=48,  mult=Stat.DECREASED_MULT),   # 16
		Stat(StatType.SPDEF, base=85,  val=171, lvl=lvl, ev=84),              # 23
		Stat(StatType.SPEED, base=102, val=171, lvl=lvl, ev=23)               # 5
	]

	for stat in stats:
		print(f"{stat._type.name}: {stat.get_iv_range()}")

	sd = StatsData({
		StatType.HP: StatData(51),
		StatType.ATK: StatData(17),
		StatType.DEF: StatData(39),
		StatType.SPATK: StatData(15),
		StatType.SPDEF: StatData(18),
		StatType.SPEED: StatData(51)
	})
	pretty_print(sd)

	print(multiplier_range_frac(Fraction(76, 100), 200))
	print()
	print(multiplier_range_frac(Fraction(13, 100), 51))


if __name__ == "__main__":
	main()
