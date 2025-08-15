# scoring.py
from dataclasses import dataclass
from typing import Dict, Tuple

STATS = ["HP", "POW", "SKL", "SPD", "LCK", "DEF", "RES"]

@dataclass
class UnitInput:
    name: str
    level: int
    role: str  # "physical" or "magical"
    init: Dict[str, float]
    cur: Dict[str, float]
    cap: Dict[str, float]

def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def _safe_div(a, b, default=0.0):
    return (a / b) if b not in (0, None) else default

def _norm_by_cap(cur: Dict[str, float], cap: Dict[str, float]) -> Dict[str, float]:
    return {k: _clip(_safe_div(cur[k], cap[k], 0.0), 0.0, 1.0) for k in STATS}

def _growth_ratio(init: Dict[str, float], cur: Dict[str, float], cap: Dict[str, float]) -> Dict[str, float]:
    out = {}
    for k in STATS:
        denom = cap[k] - init[k]
        if denom <= 0:
            out[k] = 0.0
        else:
            out[k] = _clip((cur[k] - init[k]) / denom, 0.0, 1.0)
    return out

def compute_scores(u: UnitInput) -> Tuple[Dict[str, float], str]:
    # 正規化
    x_cap = _norm_by_cap(u.cur, u.cap)
    g     = _growth_ratio(u.init, u.cur, u.cap)

    # ==== 職別重み設定 ====
    if u.role == "physical":
        w_off = {"POW":0.50, "SKL":0.25, "SPD":0.20, "LCK":0.05}
        w_def = {"HP":0.40, "DEF":0.40, "RES":0.15, "SPD":0.05}
        w_g   = {"POW":0.30, "SKL":0.20, "SPD":0.20, "HP":0.15, "DEF":0.10, "RES":0.05}
    else:  # magical
        w_off = {"POW":0.50, "SKL":0.20, "SPD":0.20, "LCK":0.10}
        w_def = {"HP":0.35, "RES":0.40, "DEF":0.20, "SPD":0.05}
        w_g   = {"POW":0.30, "SKL":0.15, "SPD":0.20, "HP":0.15, "RES":0.15, "DEF":0.05}

    def weighted_mean(vec: Dict[str, float], w: Dict[str, float]) -> float:
        num = sum(vec[k]*w.get(k,0.0) for k in w)
        den = sum(w.values())
        return _safe_div(num, den, 0.0)

    # 攻撃面
    O = weighted_mean(x_cap, w_off)
    # 防御面
    D = weighted_mean(x_cap, w_def)
    # 攻防コア
    K = (max(1e-6, O) * max(1e-6, D)) ** 0.5

    # 素体 S
    S = sum(x_cap[k] for k in STATS) / len(STATS)
    # 成長 G
    G = weighted_mean(g, w_g)
    # 上限接近 C（今はSと同じ）
    C = S

    # 合成スコア
    wK, wS, wG, wC = 0.45, 0.20, 0.20, 0.15
    T01 = _clip(wK*K + wS*S + wG*G + wC*C, 0.0, 1.0)

    total = round(T01 * 100, 2)
    if   total >= 80: rank = "A"
    elif total >= 60: rank = "B"
    elif total >= 40: rank = "C"
    else:             rank = "D"

    scores = {
        "O_offense": round(O, 4),
        "D_defense": round(D, 4),
        "K_core":    round(K, 4),
        "S_sum":     round(S, 4),
        "G_growth":  round(G, 4),
        "C_cap":     round(C, 4),
        "TOTAL_100": total
    }
    return scores, rank
