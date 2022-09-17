from __future__ import annotations
import enum
from fractions import Fraction
from frozendict import frozendict
import json_utils
from numbers import Number
from typing import Iterable, TypeVar, Generic
from types import UnionType, GenericAlias

import voluptuous as vlps


class _MissedValue:
	pass


# Placeholder
_MISSED_VALUE = _MissedValue()


class StrEnum(str, enum.Enum):
	"""Class with default str conversion to str(member value)."""
	def __str__(self):
		return str(self.value)


class SEnumMeta(enum.EnumMeta):
	def __getitem__(cls, name):
		if name is None:
			return None
		return super().__getitem__(name)


class SEnum(enum.Enum, metaclass=SEnumMeta):
	"""Class with default str conversion to member name.

	Also, because of metaclass, SEnum[None] returns None without raising error.
	"""
	def __str__(self):
		return str(self.name)


def const_dict(schema=None):
	"""Factory for frozendict with optional validation.

	Validator is callable that checks the validity of the dict and raises error
	in case of invalid data.

	NOTE: Signature of const_dict(*args, **kwargs)
	      and _SCHEMA = vlps.Schema(*args, **kwargs)
	      can be useful for decreasing code length of function calls, but
	      it restricts you with only ony type of validators for all instances.

	Args:
	schema - None | Validator
	"""
	class _ConstDict(frozendict):
		_SCHEMA = schema

		def __init__(self, *_, **__):
			# There is no need to call super().__init__, because starting from
			# version 2.2.0 frozendict does not overload object.__init__.
			if self._SCHEMA is not None:
				# dict call is for avoiding endless recursion.
				self._SCHEMA(dict(self))

	return _ConstDict


def any_value(value):
	"""For Voluptuous schemas."""
	return value


def enum_const_dict(enum_: enum.EnumMeta, value_type, strict: bool = True):
	if isinstance(value_type, (GenericAlias, UnionType)):
		if not strict:
			raise ValueError(f"{value_type} can not be used with {strict=}")
		value_type = any_value
	elif strict:
		value_type = vlps.Coerce(value_type)

	return const_dict(vlps.Schema(vlps.All(
		{enum_: value_type},
		vlps.Length(min=len(enum_), max=len(enum_))
	)))


def pretty_print(data):
	print(json_utils.json.dumps(
		data,
		default=str,
		indent=4,
		cls=json_utils.KeysToStrings
	))


def clamp(x, min_=None, max_=None):
	if min_ is not None:
		x = max(min_, x)
	if max_ is not None:
		x = min(x, max_)

	return x


_T = TypeVar('_T', bound=Number)
_T1 = TypeVar('_T1', bound=Number)
_T2 = TypeVar('_T2', bound=Number)
NumRange_T = tuple[_T, _T]
GenNumRange_T = NumRange_T | _T


class NumRange(Generic[_T]):

	__slots__ = "_min", "_max"

	def __init__(self, min_: _T = 0, max_: _T = None):
		self._min = min_
		self._max = min_ if max_ is None else max_

	@property
	def min(self) -> _T:
		return self._min

	@property
	def max(self) -> _T:
		return self._max

	def __getitem__(self, item: int) -> _T:
		if item == 0:
			return self._min
		elif item == 1:
			return self._max
		else:
			raise IndexError

	def __iter__(self) -> range:
		return range(self._min, self._max + 1)

	def __str__(self) -> str:
		if self._min == self._max:
			return str(self._min)
		return f'({self._min}, {self._max})'

	@property
	def is_straight(self) -> bool:
		return self._min <= self._max

	def reverse(self) -> NumRange[_T]:
		self._min, self._max = self._max, self._min
		return self

	def straighten(self) -> NumRange[_T]:
		if not self.is_straight:
			self.reverse()
		return self

	@staticmethod
	def is_straight_validator(r: NumRange) -> NumRange:
		if r.min > r.max:
			raise ValueError(f"Range {r} is not straight")
		return r

	@staticmethod
	def _get_min(r: NumRange[_T1] | _T2) -> _T1 | _T2:
		return r if isinstance(r, Number) else r.min

	@staticmethod
	def _get_max(r: NumRange[_T1] | _T2) -> _T1 | _T2:
		return r if isinstance(r, Number) else r.max

	def __eq__(self, other: NumRange[_T1] | _T2) -> bool:
		if isinstance(other, Number):
			return self._min == other and self._max == other
		elif isinstance(other, NumRange):
			return self._min == other.min and self._max == other.max
		else:
			return False

	def __ne__(self, other: NumRange[_T1] | _T2) -> bool:
		return not (self == other)

	def __lt__(self, other: _T1) -> bool:
		return self._min < other and self._max < other

	def __le__(self, other: _T1) -> bool:
		return self._min <= other and self._max <= other

	def __gt__(self, other: _T1) -> bool:
		return self._min > other and self._max > other

	def __ge__(self, other: _T1) -> bool:
		return self._min >= other and self._max >= other

	def __add__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._min + self._get_min(other),
			self._max + self._get_max(other)
		)

	def __sub__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._min - self._get_min(other),
			self._max - self._get_max(other)
		)

	def __mul__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._min * self._get_min(other),
			self._max * self._get_max(other)
		)

	def __floordiv__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._min // self._get_max(other),
			self._max // self._get_min(other)
		)

	def __radd__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._get_min(other) + self._min,
			self._get_max(other) + self._max
		)

	def __rsub__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._get_min(other) - self._min,
			self._get_max(other) - self._max
		)

	def __rmul__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._get_min(other) * self._min,
			self._get_max(other) * self._max
		)

	def __rfloordiv__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		return self.__class__(
			self._get_min(other) // self._max,
			self._get_max(other) // self._min
		)

	def __iadd__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		self._min += self._get_min(other)
		self._max += self._get_max(other)
		return self

	def __isub__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		self._min -= self._get_min(other)
		self._max -= self._get_max(other)
		return self

	def __imul__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		self._min *= self._get_min(other)
		self._max *= self._get_max(other)
		return self

	def __ifloordiv__(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			return NotImplemented

		self._min //= self._get_max(other)
		self._max //= self._get_min(other)
		return self

	def clamp(self, other: NumRange[_T1]) -> NumRange[_T]:
		if self._min > other.max or self._max < other.min:
			raise ValueError(f"Could not clamp {self} to {other}")

		self._min = clamp(self._min, min_=other.min)
		self._max = clamp(self._max, max_=other.max)
		return self

	def merge_in(self, other: NumRange[_T] | _T) -> NumRange[_T]:
		if not isinstance(other, (self.__class__, self._min.__class__)):
			raise NotImplementedError

		self._min = min(self._min, self._get_min(other))
		self._max = max(self._max, self._get_max(other))
		return self

	@classmethod
	def merge_two(cls, left: NumRange | Number, right: NumRange | Number) -> NumRange:
		left_class = left.__class__ if isinstance(left, Number) else (left.__class__, left.min.__class__)
		right_class = right.__class__ if isinstance(right, Number) else (right.__class__, right.min.__class__)

		if isinstance(right, left_class):
			return left.__class__(
				min(cls._get_min(left), cls._get_min(right)),
				max(cls._get_max(left), cls._get_max(right))
			)
		elif isinstance(left, right_class):
			return right.__class__(
				min(cls._get_min(left), cls._get_min(right)),
				max(cls._get_max(left), cls._get_max(right))
			)
		else:
			raise NotImplementedError

	@property
	def in_validator(self) -> vlps.Range:
		return vlps.Range(self._min, self._max)


class FloatRange(NumRange[float]):
	pass


class FracRange(FloatRange, NumRange[Fraction]):
	@property
	def numerator(self) -> IntRange:
		return IntRange(self.min.numerator, self.max.numerator)

	@property
	def denominator(self) -> IntRange:
		return IntRange(self.max.denominator, self.min.denominator)


class IntRange(FracRange, NumRange[int]):
	pass


IntOrRange_T = int | IntRange
IntOrFracOrRange_T = int | Fraction | FracRange


def numerator_range(den: int, quot: IntOrRange_T) -> IntRange:
	"""Find numerator range for given positive denominator and positive quotient."""
	if isinstance(quot, int):
		return IntRange(
			den * quot,
			den * (quot + 1) - 1
		)
	else:
		return IntRange(
			den * quot.min,
			den * (quot.max + 1) - 1
		)


def multiplier_range(mult: int, prod_range: IntRange) -> IntRange:
	"""Find multiplier range for given positive multiplicand and positive product range."""
	return IntRange(
		(prod_range.min + mult - 1) // mult,
		prod_range.max // mult
	)


def multiplier_range_frac(mult: Fraction, prod: IntOrRange_T) -> IntRange:
	"""Find multiplier range for given positive fraction multiplicand and positive product."""
	return multiplier_range(
		mult.numerator,
		numerator_range(mult.denominator, prod)
	)


def test_floor_div(left: int | IntRange, right: FracRange) -> NumRange[int]:
	return left * right.numerator // right.denominator


def main():
	# float_r = FloatRange(1.1, 3.33)
	# frac_r = FracRange(Fraction(11, 5), Fraction(14, 3))
	# int_r = IntRange(-1, 5) + 2
	# print(float_r)
	# print(frac_r)
	# print(int_r)
	# frac = Fraction(4)
	#
	# frac_r += int_r
	# print(frac_r)
	#
	# n_r = frac_r.numerator
	# d_r = frac_r.denominator
	# print(n_r)
	# print(d_r)
	# int_r = 5 + IntRange(4, -1)
	# print(int_r)
	# float_r = int_r - float_r
	# print(float_r)
	int_r = test_floor_div(17, FracRange(Fraction(6, 5), Fraction(5, 3)))
	print(int_r)
	s = set(int_r)
	print(s)


if __name__ == "__main__":
	main()

