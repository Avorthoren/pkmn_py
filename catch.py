MAX_CATCH_RATE = 255
TRASH_HOLD_RANGE = 256**2
CRITICAL_CAPTURE_TRASH_HOLD_RANGE = 256
SHAKES = 4


def prob(catchRate, hpRate=1., ballBonus=1., statusBonus=1., criticalCaptureRate=0.):
	modifiedCatchRate = catchRate * (1 - 2/3 * hpRate) * ballBonus * statusBonus
	trashHold = int(TRASH_HOLD_RANGE / (MAX_CATCH_RATE / modifiedCatchRate) ** 0.1875)
	shakeSuccProb = min(trashHold / TRASH_HOLD_RANGE, 1.0)
	captureProb = shakeSuccProb ** SHAKES

	criticalCaptureTrashHold = int(modifiedCatchRate * criticalCaptureRate / 6)
	criticalCaptureProb = min(criticalCaptureTrashHold / CRITICAL_CAPTURE_TRASH_HOLD_RANGE, 1.0)

	return (1 - criticalCaptureProb) * captureProb + criticalCaptureProb * shakeSuccProb


def main():
	print(prob(
		catchRate=255,
		hpRate=1/48,
		# ballBonus=1.5,
		# statusBonus=2,
		criticalCaptureRate=0.5
	))


if __name__ == "__main__":
	main()
