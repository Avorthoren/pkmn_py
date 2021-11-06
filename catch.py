MAX_CATCH_RATE = 255
TRASH_HOLD_RANGE = 256**2
CRITICAL_CAPTURE_TRASH_HOLD_RANGE = 256
SHAKES = 4


def _critical_capture_mult(pokedex_caught: int) -> float:
	if pokedex_caught <= 30:
		return 0
	elif pokedex_caught <= 150:
		return 0.5
	elif pokedex_caught <= 300:
		return 1
	elif pokedex_caught <= 450:
		return 1.5
	elif pokedex_caught <= 600:
		return 2
	else:
		return 2.5


def prob(
	catch_rate: int,            # species catch rate
	hp_rate: float = 1.0,       # current hp rate
	ball_bonus: float = 1.0,    # pokeball multiplier
	status_bonus: float = 1.0,  # non-volatile status condition bonus
	pokedex_caught: int = 0     # total different 'caught' species in pokedex
) -> float:
	modified_catch_rate = catch_rate * (1 - 2 / 3 * hp_rate) * ball_bonus * status_bonus
	trash_hold = int(TRASH_HOLD_RANGE / (MAX_CATCH_RATE / modified_catch_rate) ** 0.1875)
	shake_succ_prob = min(trash_hold / TRASH_HOLD_RANGE, 1.0)
	capture_prob = shake_succ_prob ** SHAKES

	crit_capture_trashHold = int(modified_catch_rate * _critical_capture_mult(pokedex_caught) / 6)
	crit_capture_prob = min(crit_capture_trashHold / CRITICAL_CAPTURE_TRASH_HOLD_RANGE, 1.0)

	return (1 - crit_capture_prob) * capture_prob + crit_capture_prob * shake_succ_prob


def main():
	print(prob(
		catch_rate=255,
		hp_rate=1 / 48,
		# ballBonus=1.5,
		# statusBonus=2,
		pokedex_caught=100
	))


if __name__ == "__main__":
	main()
