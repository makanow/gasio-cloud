from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

def excel_round(x: float, digits: int = 0) -> float:
    # Excel ROUND equivalent (half away from zero)
    if x is None:
        return 0.0
    q = Decimal('1') if digits == 0 else Decimal('1').scaleb(-digits)
    d = Decimal(str(x))
    return float(d.quantize(q, rounding=ROUND_HALF_UP))

def nz(x, default=0.0) -> float:
    try:
        if x is None or x == '':
            return float(default)
        return float(x)
    except Exception:
        return float(default)
