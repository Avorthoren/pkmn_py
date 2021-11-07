import enum
from fractions import Fraction
from frozendict import frozendict
import json
from typing import Tuple, Union, Type


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

	Also because of metaclass, SEnum[None] returns None without raising error.
	"""
	def __str__(self):
		return str(self.name)


def const_dict(schema=None):
	"""Factory for frozendict with optional validation.

	Validator is callable that checks the validity of the dict and raises error
	in case of invalid data.

	Args:
	schema - None | Validator
	"""
	class _ConstDict(frozendict):
		_SCHEMA = schema

		def __init__(self, *args, **kwargs):
			super().__init__(*args, *kwargs)
			if self._SCHEMA is not None:
				# dict call is for avoiding endless recursion.
				self._SCHEMA(dict(self))

	return _ConstDict


class KeysToStrings(json.JSONEncoder):
	def _keys_to_string_encode(self, obj):
		if isinstance(obj, dict):
			def cast_keys(o):
				return self._keys_to_string_encode(
					o if isinstance(o, (str, int, float, bool)) or o is None
					else str(o)
				)
			return {cast_keys(k): cast_keys(v) for k, v in obj.items()}
		else:
			return obj

	def encode(self, obj):
		return super(KeysToStrings, self).encode(self._keys_to_string_encode(obj))


def pretty_print(data):
	print(json.dumps(data, default=str, indent=4, cls=KeysToStrings))


def clamp(x, min_=None, max_=None):
	if min_ is not None:
		x = max(min_, x)
	if max_ is not None:
		x = min(x, max_)

	return x


IntRange_T = Tuple[int, int]


def summand_range(
	summ: int,
	sum_: IntRange_T,
	min_: Union[int, None] = 0,
	max_: int = None
) -> IntRange_T:
	"""Find summand range for given summand and sum range."""
	range_min = sum_[0] - summ
	range_max = sum_[1] - summ

	if min_ is not None:
		range_min = clamp(range_min, min_=min_)
		if range_max < min_:
			raise ValueError(f"range_max < min value: {range_max} < {min_}")

	if max_ is not None:
		range_max = clamp(range_max, max_=max_)
		if range_min > max_:
			raise ValueError(f"range_min > max value: {range_min} < {max_}")

	return range_min, range_max


def numerator_range(den: int, quot: Union[int, IntRange_T]) -> IntRange_T:
	"""Find numerator range for given positive denominator and positive quotient."""
	if isinstance(quot, int):
		return den * quot, den * (quot + 1) - 1
	else:
		return den * quot[0], den * (quot[1] + 1) - 1


def multiplier_range(mult: int, prod_range: IntRange_T) -> IntRange_T:
	"""Find multiplier range for given positive multiplicand and positive product range."""
	return (prod_range[0] + mult - 1) // mult, prod_range[1] // mult


def multiplier_range_frac(mult: Fraction, prod: Union[int, IntRange_T]) -> IntRange_T:
	"""Find multiplier range for given positive fraction multiplicand and positive product."""
	return multiplier_range(mult.numerator, numerator_range(mult.denominator, prod))


def validator(value, name: str, type_: Union[Type, Tuple[Type]] = None, int_range: IntRange_T = None):
	if not isinstance(value, type_):
		types_str = f"one of {'|'.join(t.__name__ for t in type_)}" if isinstance(type_, tuple) else type_.__name__
		raise TypeError(f"{name} should be {types_str}, not {type(value).__name__}")


def main():
	validator(5, "value", tuple)


if __name__ == "__main__":
	main()
