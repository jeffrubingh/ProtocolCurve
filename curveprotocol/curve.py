"""Fixed-point curve kernel.

Everything here is integer arithmetic on micro-USDT so that a curve projection
is reproducible across machines and across the language ports. No floats, no
rounding drift, no dependency on the host libm.

The curve is a discrete compounding step clamped by a ceiling:

    next = balance + balance * rate_bps // 10_000

A ceiling is always applied after the step, which is what makes the curve
*exponential with a shoulder* rather than a runaway.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from curveprotocol.model import BANDS, MICRO

#: Basis points denominator.
BPS: int = 10_000

#: Hard cap on compounding rounds per call, so a hostile rate cannot spin.
MAX_ROUNDS: int = 4_096

#: FNV-1a 64-bit offset basis and prime.
FNV_OFFSET: int = 0xCBF29CE484222325
FNV_PRIME: int = 0x100000001B3
MASK64: int = 0xFFFFFFFFFFFFFFFF


def compound(balance: int, rate_bps: int, ceiling: int) -> int:
    """One curve step, clamped by *ceiling*."""
    if balance <= 0:
        return 0
    rate = max(0, int(rate_bps))
    grown = balance + (balance * rate) // BPS
    return min(grown, int(ceiling)) if ceiling > 0 else grown


def project(balance: int, rate_bps: int, ceiling: int, epochs: int) -> List[int]:
    """Run *epochs* steps and return the whole series, starting with *balance*."""
    series = [int(balance)]
    for _ in range(min(int(epochs), MAX_ROUNDS)):
        series.append(compound(series[-1], rate_bps, ceiling))
    return series


def epochs_to_ceiling(balance: int, rate_bps: int, ceiling: int) -> int:
    """How many steps until *ceiling* is reached. ``-1`` when it never is."""
    if balance <= 0:
        return 0
    if rate_bps <= 0:
        return -1
    value = int(balance)
    for step in range(1, MAX_ROUNDS + 1):
        value = compound(value, rate_bps, ceiling)
        if ceiling > 0 and value >= ceiling:
            return step
    return -1


def split_bands(total: int, weights: Sequence[float]) -> List[int]:
    """Split *total* across bands by weight, integer only."""
    if total <= 0:
        return [0 for _ in weights]
    clean = [max(0.0, float(w)) for w in weights]
    if not any(clean):
        clean = [1.0 for _ in clean]
    denom = sum(clean)
    parts: List[int] = []
    handed = 0
    for weight in clean[:-1]:
        part = int((total * weight) / denom)
        parts.append(part)
        handed += part
    parts.append(total - handed)
    return parts


def band_weights(balances: Iterable[int]) -> Tuple[float, ...]:
    """Normalise balances into band weights in ``[0, 1]``."""
    values = [max(0, int(b)) for b in balances]
    top = max(values) if values else 0
    if top == 0:
        return tuple(0.0 for _ in values)
    return tuple(round(v / top, 6) for v in values)


def depth_of(balances: Sequence[int], weights: Sequence[float]) -> int:
    """Weighted depth in micro-USDT."""
    return sum(max(0, int(b)) * _as_micro(w) for b, w in zip(balances, weights))


def _as_micro(weight: float) -> int:
    return int(round(max(0.0, min(1.0, float(weight))) * MICRO))


def canonical(parts: Iterable[object]) -> bytes:
    """Canonical byte form used by the fingerprint: ``|``-joined, UTF-8."""
    return "|".join(str(p) for p in parts).encode()


def fnv1a64(payload: bytes) -> int:
    """FNV-1a 64-bit. Dependency free, identical in every port."""
    digest = FNV_OFFSET
    for byte in payload:
        digest ^= byte
        digest = (digest * FNV_PRIME) & MASK64
    return digest


def fingerprint(parts: Iterable[object]) -> str:
    """Hex fingerprint of a canonical tuple, used for cross-language parity."""
    return format(fnv1a64(canonical(parts)), "016x")


def band_index(band: str) -> int:
    """Position of *band* in :data:`curveprotocol.model.BANDS`, ``-1`` if unknown."""
    try:
        return BANDS.index(band)
    except ValueError:
        return -1
