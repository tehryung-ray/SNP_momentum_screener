#!/usr/bin/env python3
"""Generate a self-contained HTML report from scan JSON data for GitHub Pages.

Usage:
    python generate_html_report.py
    python generate_html_report.py --input data/daily_scans/latest_scan_data.json
    python generate_html_report.py --output docs/index.html
"""

import argparse
import html
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# S&P 500 GICS 섹터 맵  (ticker → 섹터 약칭)
# ---------------------------------------------------------------------------
_SECTOR_MAP = {
    # ── Information Technology ──────────────────────────────────────────
    "AAPL":"IT","MSFT":"IT","NVDA":"IT","AVGO":"IT","CRM":"IT","AMD":"IT",
    "ORCL":"IT","ADBE":"IT","INTC":"IT","TXN":"IT","QCOM":"IT","AMAT":"IT",
    "ADI":"IT","KLAC":"IT","LRCX":"IT","MCHP":"IT","MU":"IT","NXPI":"IT",
    "TEL":"IT","WDC":"IT","STX":"IT","KEYS":"IT","CTSH":"IT","IT":"IT",
    "ACN":"IT","IBM":"IT","CDNS":"IT","SNPS":"IT","ANSS":"IT","TYL":"IT",
    "CDW":"IT","EPAM":"IT","ROP":"IT","FFIV":"IT","NTAP":"IT","JNPR":"IT",
    "HPQ":"IT","HPE":"IT","GLW":"IT","ZBRA":"IT","SWKS":"IT","QRVO":"IT",
    "TER":"IT","MPWR":"IT","ON":"IT","FTNT":"IT","LDOS":"IT","SAIC":"IT",
    "BAH":"IT","GDDY":"IT","SMCI":"IT","GEN":"IT","ENPH":"IT","SEDG":"IT",
    # ── Health Care ─────────────────────────────────────────────────────
    "UNH":"헬스","LLY":"헬스","JNJ":"헬스","ABBV":"헬스","MRK":"헬스",
    "TMO":"헬스","ABT":"헬스","DHR":"헬스","AMGN":"헬스","ISRG":"헬스",
    "GILD":"헬스","MDT":"헬스","VRTX":"헬스","REGN":"헬스","ELV":"헬스",
    "CI":"헬스","HUM":"헬스","SYK":"헬스","BSX":"헬스","ZTS":"헬스",
    "EW":"헬스","BIIB":"헬스","IDXX":"헬스","DXCM":"헬스","IQV":"헬스",
    "BDX":"헬스","MTD":"헬스","A":"헬스","RMD":"헬스","WAT":"헬스",
    "WST":"헬스","ALGN":"헬스","PODD":"헬스","HOLX":"헬스","STE":"헬스",
    "RVTY":"헬스","BAX":"헬스","ZBH":"헬스","CTLT":"헬스","HCA":"헬스",
    "MRNA":"헬스","PKI":"헬스","INCY":"헬스","TECH":"헬스","VTRS":"헬스",
    "CAH":"헬스","MCK":"헬스","COR":"헬스","HSIC":"헬스","MOH":"헬스",
    # ── Financials ──────────────────────────────────────────────────────
    "JPM":"금융","BAC":"금융","WFC":"금융","GS":"금융","MS":"금융",
    "BLK":"금융","SCHW":"금융","AXP":"금융","USB":"금융","PNC":"금융",
    "TFC":"금융","COF":"금융","CB":"금융","MMC":"금융","AON":"금융",
    "ICE":"금융","CME":"금융","SPGI":"금융","MCO":"금융","MSCI":"금융",
    "AFL":"금융","MET":"금융","PRU":"금융","AIG":"금융","ALL":"금융",
    "HIG":"금융","TRV":"금융","ACGL":"금융","RE":"금융","WRB":"금융",
    "CINF":"금융","GL":"금융","PFG":"금융","LNC":"금융","UNM":"금융",
    "TROW":"금융","BEN":"금융","IVZ":"금융","AMP":"금융","FIS":"금융",
    "FI":"금융","PYPL":"금융","V":"금융","MA":"금융","DFS":"금융",
    "SYF":"금융","BR":"금융","NDAQ":"금융","CBOE":"금융","MKTX":"금융",
    "BK":"금융","STT":"금융","RF":"금융","CFG":"금융","FITB":"금융",
    "KEY":"금융","HBAN":"금융","MTB":"금융","CMA":"금융","ZION":"금융",
    "RJF":"금융","SF":"금융","FHN":"금융",
    # ── Consumer Discretionary ──────────────────────────────────────────
    "AMZN":"소비재","TSLA":"소비재","HD":"소비재","MCD":"소비재",
    "BKNG":"소비재","LOW":"소비재","TJX":"소비재","SBUX":"소비재",
    "NKE":"소비재","GM":"소비재","F":"소비재","ROST":"소비재",
    "YUM":"소비재","MAR":"소비재","HLT":"소비재","MGM":"소비재",
    "WYNN":"소비재","LVS":"소비재","CCL":"소비재","RCL":"소비재",
    "NCLH":"소비재","DAL":"소비재","UAL":"소비재","AAL":"소비재",
    "LUV":"소비재","DLTR":"소비재","DG":"소비재","ULTA":"소비재",
    "TPR":"소비재","PVH":"소비재","RL":"소비재","VFC":"소비재",
    "HAS":"소비재","MHK":"소비재","WHR":"소비재","LEG":"소비재",
    "DECK":"소비재","POOL":"소비재","NVR":"소비재","PHM":"소비재",
    "DHI":"소비재","TOL":"소비재","LEN":"소비재","BLDR":"소비재",
    "GRMN":"소비재","AXON":"소비재","ORLY":"소비재","AZO":"소비재",
    "BBY":"소비재","EBAY":"소비재","ETSY":"소비재","APTV":"소비재",
    # ── Communication Services ──────────────────────────────────────────
    "META":"통신","GOOGL":"통신","GOOG":"통신","NFLX":"통신",
    "CHTR":"통신","CMCSA":"통신","T":"통신","VZ":"통신","TMUS":"통신",
    "DIS":"통신","WBD":"통신","PARA":"통신","FOX":"통신","FOXA":"통신",
    "NWS":"통신","NWSA":"통신","LYV":"통신","EA":"통신","TTWO":"통신",
    "OMC":"통신","IPG":"통신","NYT":"통신",
    # ── Industrials ─────────────────────────────────────────────────────
    "GE":"산업재","CAT":"산업재","HON":"산업재","RTX":"산업재",
    "UPS":"산업재","LMT":"산업재","BA":"산업재","GD":"산업재",
    "NOC":"산업재","DE":"산업재","EMR":"산업재","ETN":"산업재",
    "CSX":"산업재","NSC":"산업재","UNP":"산업재","FDX":"산업재",
    "WM":"산업재","RSG":"산업재","CTAS":"산업재","FAST":"산업재",
    "PCAR":"산업재","PH":"산업재","ROK":"산업재","ITW":"산업재",
    "GWW":"산업재","AME":"산업재","XYL":"산업재","OTIS":"산업재",
    "CARR":"산업재","TT":"산업재","IR":"산업재","SWK":"산업재",
    "EXPD":"산업재","ODFL":"산업재","CHRW":"산업재","DAY":"산업재",
    "HII":"산업재","TDG":"산업재","LHX":"산업재","L3H":"산업재",
    "LDOS":"산업재","SAIC":"산업재","BAH":"산업재","PWR":"산업재",
    "URI":"산업재","VRSK":"산업재","CPRT":"산업재","WAB":"산업재",
    "GXO":"산업재","JBHT":"산업재","SNA":"산업재","MAS":"산업재",
    "PNR":"산업재","ALLE":"산업재","AOS":"산업재","TDY":"산업재",
    # ── Consumer Staples ────────────────────────────────────────────────
    "WMT":"생필품","PG":"생필품","KO":"생필품","PEP":"생필품",
    "COST":"생필품","PM":"생필품","MO":"생필품","CL":"생필품",
    "KMB":"생필품","GIS":"생필품","K":"생필품","CPB":"생필품",
    "HRL":"생필품","SJM":"생필품","CAG":"생필품","MKC":"생필품",
    "MDLZ":"생필품","MNST":"생필품","STZ":"생필품","TAP":"생필품",
    "BF-B":"생필품","SAM":"생필품","CHD":"생필품","CLX":"생필품",
    "EL":"생필품","ULTA":"생필품","KR":"생필품","SYY":"생필품",
    "TSN":"생필품","ADM":"생필품","CTVA":"생필품","FMC":"생필품",
    # ── Energy ──────────────────────────────────────────────────────────
    "XOM":"에너지","CVX":"에너지","SLB":"에너지","MPC":"에너지",
    "PSX":"에너지","VLO":"에너지","OXY":"에너지","COP":"에너지",
    "EOG":"에너지","PXD":"에너지","DVN":"에너지","APA":"에너지",
    "FANG":"에너지","HAL":"에너지","BKR":"에너지","WMB":"에너지",
    "KMI":"에너지","OKE":"에너지","LNG":"에너지","CTRA":"에너지",
    "MRO":"에너지","HES":"에너지","MTDR":"에너지","FSLR":"에너지",
    # ── Utilities ───────────────────────────────────────────────────────
    "NEE":"유틸","DUK":"유틸","SO":"유틸","D":"유틸","AEP":"유틸",
    "EXC":"유틸","XEL":"유틸","WEC":"유틸","ES":"유틸","PCG":"유틸",
    "PEG":"유틸","ED":"유틸","ETR":"유틸","EIX":"유틸","AWK":"유틸",
    "CMS":"유틸","NI":"유틸","PPL":"유틸","AES":"유틸","NRG":"유틸",
    "FE":"유틸","CNP":"유틸","LNT":"유틸","EVRG":"유틸","SRE":"유틸",
    "AEE":"유틸","DTE":"유틸","PNW":"유틸","VST":"유틸",
    # ── Real Estate ─────────────────────────────────────────────────────
    "AMT":"리츠","PLD":"리츠","CCI":"리츠","EQIX":"리츠","PSA":"리츠",
    "SPG":"리츠","O":"리츠","DLR":"리츠","WELL":"리츠","AVB":"리츠",
    "EQR":"리츠","UDR":"리츠","ESS":"리츠","MAA":"리츠","CPT":"리츠",
    "ARE":"리츠","BXP":"리츠","VTR":"리츠","PEAK":"리츠","HST":"리츠",
    "KIM":"리츠","REG":"리츠","FRT":"리츠","NNN":"리츠","CSGP":"리츠",
    "CBRE":"리츠","JLL":"리츠","IRM":"리츠","SUI":"리츠","WY":"리츠",
    # ── Materials ───────────────────────────────────────────────────────
    "LIN":"소재","APD":"소재","SHW":"소재","ECL":"소재","NUE":"소재",
    "FCX":"소재","NEM":"소재","BALL":"소재","PKG":"소재","SEE":"소재",
    "CF":"소재","MOS":"소재","ALB":"소재","CE":"소재","EMN":"소재",
    "PPG":"소재","RPM":"소재","VMC":"소재","MLM":"소재","IFF":"소재",
    "LYB":"소재","DD":"소재","DOW":"소재","CTVA":"소재","FMC":"소재",
}

_SECTOR_COLOR = {
    "IT":    ("#60a5fa", "#1e3a5f"),   # 파랑
    "헬스":  ("#34d399", "#064e3b"),   # 에메랄드
    "금융":  ("#fbbf24", "#3d2000"),   # 노랑
    "소비재":("#fb923c", "#431407"),   # 주황
    "통신":  ("#a78bfa", "#2e1065"),   # 보라
    "산업재":("#94a3b8", "#1e293b"),   # 슬레이트
    "생필품":("#6ee7b7", "#064e3b"),   # 민트
    "에너지":("#f87171", "#450a0a"),   # 빨강
    "유틸":  ("#7dd3fc", "#0c2540"),   # 하늘
    "리츠":  ("#f9a8d4", "#4a0020"),   # 핑크
    "소재":  ("#86efac", "#052e16"),   # 연두
}


def _sector_badge(ticker: str) -> str:
    sector = _SECTOR_MAP.get(ticker.upper())
    if not sector:
        return ""
    text_c, bg_c = _SECTOR_COLOR.get(sector, ("#94a3b8", "#1e293b"))
    return (f'<span class="sector-pill" '
            f'style="color:{text_c};background:{bg_c};border-color:{text_c}44">'
            f'{sector}</span>')


_ALL_SECTORS = ["IT", "헬스", "금융", "소비재", "통신", "산업재", "생필품", "에너지", "유틸", "리츠", "소재"]


def _build_sector_stats(buy_signals: list, sell_signals: list) -> list:
    """매수·매도 신호에서 섹터별 통계를 집계, 강도 순 정렬."""
    from collections import defaultdict
    buys = defaultdict(list)
    sells = defaultdict(list)
    for s in buy_signals:
        sector = _SECTOR_MAP.get(s["ticker"].upper())
        if sector:
            rs = (s.get("details") or {}).get("rs_slope")
            buys[sector].append({
                "score": s.get("score", 0),
                "rs": rs if isinstance(rs, (int, float)) else None,
            })
    for s in sell_signals:
        sector = _SECTOR_MAP.get(s["ticker"].upper())
        if sector:
            sells[sector].append(s.get("score", 0))

    rows = []
    for sector in _ALL_SECTORS:
        b = buys.get(sector, [])
        sv = sells.get(sector, [])
        buy_cnt = len(b)
        sell_cnt = len(sv)
        rs_vals = [x["rs"] for x in b if x["rs"] is not None]
        avg_rs = round(sum(rs_vals) / len(rs_vals), 3) if rs_vals else None
        avg_score = round(sum(x["score"] for x in b) / buy_cnt, 1) if buy_cnt else 0
        # 강도 점수: 매수 2점, 매도 -3점, RS 보정
        strength = buy_cnt * 2 - sell_cnt * 3 + (avg_rs * 10 if avg_rs else 0)
        rows.append({
            "sector": sector,
            "buy_cnt": buy_cnt,
            "sell_cnt": sell_cnt,
            "avg_rs": avg_rs,
            "avg_score": avg_score,
            "strength": strength,
        })
    rows.sort(key=lambda x: x["strength"], reverse=True)
    return rows


def _render_sector_ranking(spy: dict, sector_stats: list) -> str:
    """SPY + 11 GICS 섹터를 강도 순 한 줄 카드로 렌더."""
    spy_phase = spy.get("phase", 0)
    spy_price = spy.get("current_price", 0)
    spy_slope50 = spy.get("slope_50", 0)
    spy_conf = spy.get("confidence", 0)
    phase_colors = {1: "#94a3b8", 2: "#22c55e", 3: "#eab308", 4: "#ef4444"}
    spy_col = phase_colors.get(spy_phase, "#94a3b8")
    spy_trend_label = {1: "횡보", 2: "상승", 3: "분산", 4: "하락"}.get(spy_phase, "N/A")

    # SPY 카드
    spy_card = f"""<div class="sr-chip sr-spy">
  <div class="sr-name" style="color:{spy_col}">SPY</div>
  <div class="sr-sub">벤치마크</div>
  <div class="sr-price">${spy_price:.0f}</div>
  <div class="sr-meta"><span style="color:{spy_col}">{spy_trend_label} P{spy_phase}</span> · {spy_conf:.0f}%</div>
</div>"""

    chips = [spy_card]
    for i, row in enumerate(sector_stats):
        sector = row["sector"]
        text_c, bg_c = _SECTOR_COLOR.get(sector, ("#94a3b8", "#1e293b"))
        b, sv = row["buy_cnt"], row["sell_cnt"]
        avg_rs = row["avg_rs"]

        if b > 0 and sv == 0:
            border_col = "#22c55e"
            signal = "강세"
            sig_col = "#22c55e"
        elif sv > 0 and b == 0:
            border_col = "#ef4444"
            signal = "약세"
            sig_col = "#ef4444"
        elif b > sv:
            border_col = "#22c55e88"
            signal = "우세"
            sig_col = "#86efac"
        elif sv > b:
            border_col = "#ef444488"
            signal = "혼조"
            sig_col = "#fca5a5"
        else:
            border_col = "#64748b"
            signal = "중립"
            sig_col = "#94a3b8"

        rs_str = f"RS {avg_rs:+.2f}" if avg_rs is not None else "RS —"
        rank_num = f"#{i+1}" if i < 5 else ""

        chips.append(f"""<div class="sr-chip" style="border-color:{border_col}">
  <div class="sr-rank">{rank_num}</div>
  <div class="sr-name" style="color:{text_c}">{sector}</div>
  <div class="sr-signal" style="color:{sig_col}">{signal}</div>
  <div class="sr-counts">매수 <b>{b}</b> · 매도 <b style="color:#ef4444">{sv}</b></div>
  <div class="sr-meta">{rs_str}</div>
</div>""")

    inner = "\n".join(chips)
    return f"""<div class="sector-rank-box">
  <div class="breadth-title">GICS 섹터 강도 순위 — SPY 포함 12개</div>
  <div class="sr-row">{inner}</div>
</div>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _e(text) -> str:
    """HTML-escape a value (handles None, numbers, etc.)."""
    return html.escape(str(text)) if text is not None else ""


def _phase_label(phase: int) -> str:
    labels = {1: "베이스", 2: "상승추세", 3: "분산", 4: "하락추세", 0: "N/A"}
    return labels.get(phase, "N/A")


def _phase_color(phase: int) -> str:
    colors = {1: "#94a3b8", 2: "#22c55e", 3: "#eab308", 4: "#ef4444", 0: "#64748b"}
    return colors.get(phase, "#64748b")


def _score_class(score: float, max_score: float = 125) -> str:
    pct = score / max_score * 100
    if pct >= 80:
        return "excellent"
    if pct >= 65:
        return "good"
    return "ok"


def _severity_color(severity: str) -> str:
    return {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308"}.get(
        severity.lower(), "#94a3b8"
    )


def _spy_class(phase: int) -> str:
    return {1: "consolidating", 2: "bullish", 3: "topping", 4: "bearish"}.get(
        phase, "consolidating"
    )


def _minervini_dots(criteria_passed: int, total: int = 8) -> str:
    dots = []
    for i in range(total):
        cls = "pass" if i < criteria_passed else "fail"
        dots.append(f'<span class="mdot {cls}" title="{i+1}번 기준"></span>')
    return "".join(dots)


def _render_reasons(reasons: list, limit: int = 6) -> str:
    items = []
    for r in (reasons or [])[:limit]:
        items.append(f"<li>{_e(r)}</li>")
    return "<ul class='reasons'>" + "".join(items) + "</ul>" if items else ""


# --- 값 번역 함수 ---

def _tr_trend(trend: str) -> str:
    return {
        "Bullish": "강세", "Bearish": "약세",
        "Consolidating": "횡보", "Topping": "고점권",
    }.get(trend, trend)


def _tr_phase_name(name: str) -> str:
    return {
        "Base Building": "베이스 형성", "Uptrend": "상승추세",
        "Distribution": "분산", "Downtrend": "하락추세",
    }.get(name, name)


def _tr_entry_quality(eq: str) -> str:
    return {"Good": "좋음", "Extended": "과매수", "Poor": "나쁨"}.get(eq, eq)


def _tr_severity(sev: str) -> str:
    return {"CRITICAL": "위급", "HIGH": "높음", "MEDIUM": "보통",
            "critical": "위급", "high": "높음", "medium": "보통"}.get(sev, sev)


def _tr_breadth_quality(bq: str) -> str:
    return {"Excellent": "매우 좋음", "Good": "좋음",
            "Moderate": "보통", "Poor": "나쁨", "Weak": "약함"}.get(bq, bq)


def _tr_regime(regime: str) -> str:
    return (regime
            .replace("RISK-ON", "위험선호")
            .replace("RISK-OFF", "위험회피")
            .replace("Mixed", "혼합")
            .replace("Weak", "약세")
            .replace("Strong", "강세"))


# ---------------------------------------------------------------------------
# Card renderers
# ---------------------------------------------------------------------------

def _render_buy_card(sig: dict, rank: int) -> str:
    ticker = _e(sig.get("ticker", "???"))
    score = sig.get("score", 0)
    phase = sig.get("phase", 0)
    stop = sig.get("stop_loss")
    rr = sig.get("risk_reward_ratio", 0)
    bp = sig.get("breakout_price")
    eq = sig.get("entry_quality", "")
    mc_passed = sig.get("minervini_criteria_passed", 0)
    wm = sig.get("weighted_momentum")

    details = sig.get("details") or {}
    rs = details.get("rs_slope")
    vol = details.get("volume_ratio")
    risk_amt = details.get("risk_amount")
    reward_target = details.get("reward_target")
    vcp = details.get("vcp_data")

    # 종가 = 손절가 + 리스크금액으로 역산
    current_price = round(stop + risk_amt, 2) if stop and risk_amt else None

    sc = _score_class(score, 125)
    eq_kr = _tr_entry_quality(eq)

    # VCP badge
    vcp_badge = ""
    if vcp and vcp.get("quality", 0) >= 50:
        q = vcp["quality"]
        color = "#22c55e" if q >= 80 else "#eab308"
        vcp_badge = f'<span class="tag" style="background:{color}22;color:{color};border-color:{color}44">⭐ VCP {q:.0f}/100</span>'

    eq_color = "#22c55e" if eq == "Good" else "#eab308" if eq == "Extended" else "#ef4444"
    eq_badge = f'<span class="tag" style="color:{eq_color};border-color:{eq_color}44">{_e(eq_kr)}</span>' if eq else ""

    price_str  = f"${current_price:.2f}" if current_price else "—"
    stop_str   = f"${stop:.2f}" if stop else "—"
    target_str = f"${reward_target:.2f}" if reward_target else "—"
    rr_str = f"{rr:.1f}:1" if rr else "—"
    rr_color = "#22c55e" if rr >= 3 else "#eab308" if rr >= 2 else "#ef4444"
    rs_str = f"{rs:+.3f}" if rs is not None else "—"
    rs_color = "#22c55e" if (rs or 0) > 0.1 else "#eab308" if (rs or 0) > 0 else "#ef4444"
    vol_str = f"{vol:.1f}×" if vol else "—"
    vol_color = "#22c55e" if (vol or 0) >= 1.5 else "#eab308" if (vol or 0) >= 1 else "#ef4444"
    wm_str = f"{wm:+.2f}" if wm is not None else "—"
    wm_color = "#22c55e" if (wm or 0) > 1.0 else "#eab308" if (wm or 0) > 0 else "#ef4444"
    bp_line = f'<div class="bp-line">돌파가 <span>${bp:.2f}</span></div>' if bp else ""

    return f"""
<div class="card buy-card">
  <div class="card-head">
    <div>
      <div class="rank">#{rank}</div>
      <div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap">
        <div class="ticker buy-color">{ticker}</div>
        {_sector_badge(ticker)}
      </div>
      <div class="phase-tag" style="color:{_phase_color(phase)}">{phase}페이즈 · {_e(_phase_label(phase))}</div>
    </div>
    <div class="score-ring {sc}">
      <div class="score-num">{score:.0f}</div>
      <div class="score-sub">/125</div>
    </div>
  </div>

  <div class="mdots" title="미너비니 추세 템플릿">{_minervini_dots(mc_passed)} <span class="mdots-label">{mc_passed}/8</span></div>

  <div class="badges">{vcp_badge}{eq_badge}</div>

  <div class="price-row">
    <div class="price-box">
      <div class="p-label">종가</div>
      <div class="p-value">{price_str}</div>
    </div>
    <div class="price-box" style="border:1px solid #ef444444">
      <div class="p-label">손절가</div>
      <div class="p-value" style="color:#ef4444">{stop_str}</div>
    </div>
    <div class="price-box" style="border:1px solid #22c55e44">
      <div class="p-label">익절가</div>
      <div class="p-value" style="color:#22c55e">{target_str}</div>
    </div>
  </div>

  <div class="metrics">
    <div class="metric">
      <div class="m-label">손익비</div>
      <div class="m-value" style="color:{rr_color}">{rr_str}</div>
    </div>
    <div class="metric">
      <div class="m-label">RS 기울기</div>
      <div class="m-value" style="color:{rs_color}">{rs_str}</div>
    </div>
    <div class="metric">
      <div class="m-label">거래량</div>
      <div class="m-value" style="color:{vol_color}">{vol_str}</div>
    </div>
    <div class="metric">
      <div class="m-label">진입 품질</div>
      <div class="m-value" style="color:{eq_color}">{_e(eq_kr) or '—'}</div>
    </div>
    <div class="metric" title="가중모멘텀: 12×(1개월) + 4×(3개월) + 2×(6개월) + 1×(12개월)">
      <div class="m-label">WM</div>
      <div class="m-value" style="color:{wm_color}">{wm_str}</div>
    </div>
  </div>
  {bp_line}
  {_render_reasons(sig.get("reasons", []))}
</div>"""


def _render_sell_card(sig: dict, rank: int) -> str:
    ticker = _e(sig.get("ticker", "???"))
    score = sig.get("score", 0)
    phase = sig.get("phase", 0)
    severity = sig.get("severity", "medium")
    bd = sig.get("breakdown_level")

    details = sig.get("details") or {}
    rs = details.get("rs_slope")
    vol = details.get("volume_ratio")

    sc = _score_class(score, 100)
    sev_color = _severity_color(severity)
    sev_kr = _tr_severity(severity.upper())

    bd_str = f"${bd:.2f}" if bd else "—"
    rs_str = f"{rs:+.3f}" if rs is not None else "—"
    vol_str = f"{vol:.1f}×" if vol else "—"
    rs_color = "#22c55e" if (rs or 0) > 0 else "#ef4444"
    vol_color = "#ef4444" if (vol or 0) >= 1.5 else "#eab308"

    return f"""
<div class="card sell-card">
  <div class="card-head">
    <div>
      <div class="rank">#{rank}</div>
      <div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap">
        <div class="ticker sell-color">{ticker}</div>
        {_sector_badge(ticker)}
      </div>
      <div class="phase-tag" style="color:{_phase_color(phase)}">{phase}페이즈 · {_e(_phase_label(phase))}</div>
    </div>
    <div class="score-ring {sc}">
      <div class="score-num">{score:.0f}</div>
      <div class="score-sub">/100</div>
    </div>
  </div>

  <div class="badges">
    <span class="tag" style="color:{sev_color};border-color:{sev_color}44;background:{sev_color}11">
      {_e(sev_kr)}
    </span>
  </div>

  <div class="metrics">
    <div class="metric">
      <div class="m-label">지지 붕괴선</div>
      <div class="m-value">{bd_str}</div>
    </div>
    <div class="metric">
      <div class="m-label">RS 기울기</div>
      <div class="m-value" style="color:{rs_color}">{rs_str}</div>
    </div>
    <div class="metric">
      <div class="m-label">거래량</div>
      <div class="m-value" style="color:{vol_color}">{vol_str}</div>
    </div>
  </div>
  {_render_reasons(sig.get("reasons", []))}
</div>"""


# ---------------------------------------------------------------------------
# Main HTML builder
# ---------------------------------------------------------------------------

def generate_html(data: dict) -> str:
    scan_date = _e(data.get("scan_date", "Unknown"))
    generated_at = _e(data.get("generated_at", ""))
    universe = _e(data.get("universe", "S&P 500"))

    stats = data.get("stats") or {}
    total_analyzed = stats.get("total_analyzed", 0)
    scan_mins = stats.get("processing_time_minutes", 0)
    err_pct = stats.get("error_rate_pct", 0)

    spy = data.get("spy_analysis") or {}
    spy_phase = spy.get("phase", 0)
    spy_trend = _tr_trend(spy.get("trend", "Unknown"))
    spy_price = spy.get("current_price", 0)
    spy_sma50 = spy.get("sma_50", 0)
    spy_sma200 = spy.get("sma_200", 0)
    spy_conf = spy.get("confidence", 0)
    spy_phase_name = _tr_phase_name(spy.get("phase_name", ""))
    spy_cls = _spy_class(spy_phase)

    breadth = data.get("breadth") or {}
    p1_pct = breadth.get("phase_1_pct", 0)
    p2_pct = breadth.get("phase_2_pct", 0)
    p3_pct = breadth.get("phase_3_pct", 0)
    p4_pct = breadth.get("phase_4_pct", 0)
    p1_cnt = breadth.get("phase_1_count", 0)
    p2_cnt = breadth.get("phase_2_count", 0)
    p3_cnt = breadth.get("phase_3_count", 0)
    p4_cnt = breadth.get("phase_4_count", 0)
    bq = _e(_tr_breadth_quality(breadth.get("breadth_quality", "")))

    rec = data.get("signal_recommendation") or {}
    regime_raw = rec.get("regime", "")
    regime = _e(_tr_regime(regime_raw))
    regime_color = "#22c55e" if "RISK-ON" in regime_raw else "#ef4444" if "RISK-OFF" in regime_raw else "#eab308"

    buy_signals = data.get("buy_signals") or []
    sell_signals = data.get("sell_signals") or []

    sector_stats = _build_sector_stats(buy_signals, sell_signals)
    sector_ranking_html = _render_sector_ranking(spy, sector_stats)

    no_buy = '<div class="empty-state">오늘 매수 신호 없음. 시장 상황이 불리할 수 있습니다.</div>'
    no_sell = '<div class="empty-state">오늘 매도 신호 없음.</div>'

    spy_sma_info = ""
    if spy_sma50 and spy_sma200:
        s50_color = "#22c55e" if spy_price > spy_sma50 else "#ef4444"
        s200_color = "#22c55e" if spy_price > spy_sma200 else "#ef4444"
        spy_sma_info = f"""
        <div class="spy-detail">
          <span>50 SMA <strong style="color:{s50_color}">${spy_sma50:.2f}</strong></span>
          <span>200 SMA <strong style="color:{s200_color}">${spy_sma200:.2f}</strong></span>
          <span>신뢰도 <strong>{spy_conf:.0f}%</strong></span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{universe} 스크리너 · {scan_date}</title>
<style>
:root {{
  --bg: #0f172a;
  --bg2: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --green: #22c55e;
  --red: #ef4444;
  --yellow: #eab308;
  --blue: #3b82f6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans KR',sans-serif;font-size:14px;line-height:1.5}}
a{{color:var(--blue);text-decoration:none}}

/* Header */
.hdr{{background:#020617;border-bottom:1px solid var(--border);padding:14px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}}
.hdr-title{{font-size:18px;font-weight:800;color:#fff;letter-spacing:-0.3px}}
.hdr-meta{{color:var(--muted);font-size:12px;text-align:right}}

/* Main */
.main{{max-width:1440px;margin:0 auto;padding:20px 24px}}

/* Stats row */
.stats-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:20px}}
.stat{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:12px 14px}}
.stat-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}}
.stat-value{{font-size:22px;font-weight:800}}

/* SPY Banner */
.spy-banner{{border-radius:10px;padding:16px 20px;margin-bottom:20px}}
.spy-banner.bullish{{background:linear-gradient(135deg,#052e16,#14532d);border:1px solid #166534}}
.spy-banner.bearish{{background:linear-gradient(135deg,#450a0a,#7f1d1d);border:1px solid #991b1b}}
.spy-banner.consolidating{{background:linear-gradient(135deg,#1c1917,#292524);border:1px solid #57534e}}
.spy-banner.topping{{background:linear-gradient(135deg,#451a03,#78350f);border:1px solid #92400e}}
.spy-top{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px}}
.spy-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px}}
.spy-trend{{font-size:22px;font-weight:800}}
.spy-price{{font-size:14px;color:var(--muted);margin-top:2px}}
.spy-detail{{display:flex;gap:20px;margin-top:10px;flex-wrap:wrap;font-size:13px;color:var(--muted)}}
.regime-badge{{padding:6px 12px;border-radius:20px;font-size:13px;font-weight:700;white-space:nowrap}}

/* Breadth */
.breadth-box{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:20px}}
.breadth-title{{font-size:13px;font-weight:600;margin-bottom:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}}
.breadth-bar{{display:flex;height:22px;border-radius:11px;overflow:hidden;gap:1px}}
.bseg{{display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;min-width:2%}}
.b1{{background:#64748b}}.b2{{background:#22c55e}}.b3{{background:#eab308}}.b4{{background:#ef4444}}
.breadth-legend{{display:flex;gap:16px;margin-top:8px;flex-wrap:wrap}}
.bl-item{{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--muted)}}
.bl-dot{{width:10px;height:10px;border-radius:50%}}

/* Section title */
.section-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:14px;margin-top:28px}}
.section-hdr h2{{font-size:16px;font-weight:700}}
.count-badge{{font-size:12px;padding:2px 8px;border-radius:10px;font-weight:700}}
.buy-badge{{background:#052e16;color:var(--green)}}
.sell-badge{{background:#450a0a;color:var(--red)}}

/* Signal grid */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px;margin-bottom:32px}}

/* Card */
.card{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px;position:relative}}
.buy-card{{border-left:3px solid var(--green)}}
.sell-card{{border-left:3px solid var(--red)}}
.card-head{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}}
.rank{{font-size:10px;color:var(--muted);margin-bottom:1px}}
.ticker{{font-size:24px;font-weight:900;letter-spacing:-1px;line-height:1}}
.buy-color{{color:var(--green)}}
.sell-color{{color:var(--red)}}
.phase-tag{{font-size:11px;color:var(--muted);margin-top:3px}}
.score-ring{{width:54px;height:54px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;border:2px solid;flex-shrink:0}}
.score-ring.excellent{{border-color:var(--green);color:var(--green);background:#052e16}}
.score-ring.good{{border-color:#86efac;color:#86efac;background:#052e1620}}
.score-ring.ok{{border-color:var(--yellow);color:var(--yellow);background:#1c100320}}
.score-num{{font-size:17px;font-weight:800;line-height:1}}
.score-sub{{font-size:9px;color:var(--muted)}}

/* Minervini dots */
.mdots{{display:flex;align-items:center;gap:3px;margin-bottom:8px}}
.mdot{{width:13px;height:13px;border-radius:50%;border:1px solid var(--border);display:inline-block}}
.mdot.pass{{background:var(--green);border-color:var(--green)}}
.mdot.fail{{background:#1e293b}}
.mdots-label{{font-size:11px;color:var(--muted);margin-left:5px}}

/* Badges */
.badges{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}}
.tag{{font-size:11px;padding:2px 7px;border-radius:10px;border:1px solid;font-weight:600}}
.sector-pill{{font-size:10px;padding:2px 7px;border-radius:4px;border:1px solid;font-weight:700;letter-spacing:.3px;vertical-align:middle}}

/* Price row (종가 / 손절가 / 익절가) */
.price-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:10px 0}}
.price-box{{background:#0f172a;border-radius:8px;padding:8px 10px;text-align:center}}
.p-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}}
.p-value{{font-size:15px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.3px}}

/* Metrics */
.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:8px}}
.metric{{background:#0f172a;border-radius:6px;padding:6px 8px}}
.m-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}}
.m-value{{font-size:12px;font-weight:700;margin-top:2px}}
.bp-line{{font-size:11px;color:var(--muted);margin-bottom:8px}}
.bp-line span{{color:var(--text);font-weight:700}}

/* Reasons */
.reasons{{list-style:none;font-size:12px;color:var(--muted);border-top:1px solid var(--border);padding-top:8px;margin-top:8px}}
.reasons li{{padding:2px 0;padding-left:12px;position:relative}}
.reasons li::before{{content:'·';position:absolute;left:0;color:var(--border)}}

/* Empty */
.empty-state{{text-align:center;color:var(--muted);padding:40px;border:1px dashed var(--border);border-radius:10px;margin-bottom:32px}}

/* Footer */
.footer{{text-align:center;color:var(--muted);font-size:11px;padding:20px 24px;border-top:1px solid var(--border);margin-top:12px;line-height:1.7}}

@media(max-width:768px){{
  .main{{padding:12px}}
  .hdr{{padding:12px 14px}}
  .grid{{grid-template-columns:1fr}}
  .stats-row{{grid-template-columns:repeat(2,1fr)}}
  .price-row{{grid-template-columns:repeat(3,1fr)}}
  .metrics{{grid-template-columns:repeat(3,1fr)}}
  .spy-top{{flex-direction:column}}
}}
.ad-banner{{text-align:center;margin:16px 0;overflow:hidden}}
.ad-banner iframe{{max-width:100%;border:none}}

/* Sector Ranking Row */
.sector-rank-box{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:20px}}
.sr-row{{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;scrollbar-width:thin}}
.sr-row::-webkit-scrollbar{{height:4px}}
.sr-row::-webkit-scrollbar-track{{background:transparent}}
.sr-row::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
.sr-chip{{min-width:80px;flex-shrink:0;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;text-align:center;position:relative}}
.sr-spy{{min-width:90px;border:1px solid #60a5fa44;background:#1e3a5f22}}
.sr-rank{{position:absolute;top:4px;right:5px;font-size:8px;color:var(--muted);font-weight:700}}
.sr-name{{font-size:13px;font-weight:900;letter-spacing:-.2px;margin-bottom:1px}}
.sr-sub{{font-size:9px;color:var(--muted);margin-bottom:3px}}
.sr-price{{font-size:12px;font-weight:700;margin-bottom:2px;font-variant-numeric:tabular-nums}}
.sr-signal{{font-size:10px;font-weight:700;margin-bottom:2px}}
.sr-counts{{font-size:10px;color:var(--muted);margin-bottom:1px;white-space:nowrap}}
.sr-meta{{font-size:9px;color:var(--muted);white-space:nowrap}}
</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9724013230967786" crossorigin="anonymous"></script>
</head>
<body>

<div class="hdr">
  <div>
    <div class="hdr-title">📊 {universe} 주식 스크리너</div>
    <div style="font-size:12px;color:var(--muted);margin-top:2px">미너비니 SEPA · 페이즈 분석 · VCP 탐지</div>
  </div>
  <div class="hdr-meta">
    <div>스캔 날짜: <strong style="color:var(--text)">{scan_date}</strong></div>
    <div>{generated_at}</div>
    <a href="guide.html" style="display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:4px 10px;text-decoration:none;margin-top:4px;transition:color .15s,border-color .15s" onmouseover="this.style.color='var(--text)';this.style.borderColor='var(--muted)'" onmouseout="this.style.color='var(--muted)';this.style.borderColor='var(--border)'">📖 사용설명서</a>
  </div>
</div>

<div class="main">

  <!-- 통계 요약 -->
  <div class="stats-row">
    <div class="stat">
      <div class="stat-label">분석 종목</div>
      <div class="stat-value">{total_analyzed:,}</div>
    </div>
    <div class="stat">
      <div class="stat-label">매수 신호</div>
      <div class="stat-value" style="color:var(--green)">{len(buy_signals)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">매도 신호</div>
      <div class="stat-value" style="color:var(--red)">{len(sell_signals)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">스캔 시간</div>
      <div class="stat-value" style="font-size:18px">{scan_mins:.0f}분</div>
    </div>
    <div class="stat">
      <div class="stat-label">오류율</div>
      <div class="stat-value" style="font-size:18px;color:{'var(--red)' if err_pct > 5 else 'var(--green)'}">{err_pct:.1f}%</div>
    </div>
    <div class="stat">
      <div class="stat-label">시장 국면</div>
      <div class="stat-value" style="font-size:13px;color:{regime_color}">{regime}</div>
    </div>
  </div>

  <!-- 광고 1 -->
  <div class="ad-banner">
    <ins class="adsbygoogle" style="display:block;" data-ad-client="ca-pub-9724013230967786" data-ad-slot="5386218570" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>
  <div class="ad-banner">
    <iframe src="https://ads-partners.coupang.com/widgets.html?id=962570&template=carousel&trackingCode=AF1576178&subId=&width=728&height=90&tsource=" width="728" height="90" frameborder="0" scrolling="no" referrerpolicy="unsafe-url" style="max-width:100%;"></iframe>
  </div>

  <!-- SPY 배너 -->
  <div class="spy-banner {spy_cls}">
    <div class="spy-top">
      <div>
        <div class="spy-label">SPY — 시장 벤치마크</div>
        <div class="spy-trend">{spy_trend} <span style="font-size:14px;font-weight:400;color:var(--muted)">{spy_phase}페이즈 · {spy_phase_name}</span></div>
        <div class="spy-price">${spy_price:.2f}</div>
        {spy_sma_info}
      </div>
      <div class="regime-badge" style="color:{regime_color};background:{regime_color}22;border:1px solid {regime_color}55">
        {regime}
      </div>
    </div>
  </div>

  <!-- 시장 폭 -->
  <div class="breadth-box">
    <div class="breadth-title">시장 폭 — S&P 500 페이즈 분포</div>
    <div class="breadth-bar">
      <div class="bseg b1" style="width:{p1_pct}%" title="1페이즈 베이스: {p1_cnt}개 ({p1_pct:.1f}%)">{f'{p1_pct:.0f}%' if p1_pct > 5 else ''}</div>
      <div class="bseg b2" style="width:{p2_pct}%" title="2페이즈 상승추세: {p2_cnt}개 ({p2_pct:.1f}%)">{f'{p2_pct:.0f}%' if p2_pct > 5 else ''}</div>
      <div class="bseg b3" style="width:{p3_pct}%" title="3페이즈 분산: {p3_cnt}개 ({p3_pct:.1f}%)">{f'{p3_pct:.0f}%' if p3_pct > 5 else ''}</div>
      <div class="bseg b4" style="width:{p4_pct}%" title="4페이즈 하락추세: {p4_cnt}개 ({p4_pct:.1f}%)">{f'{p4_pct:.0f}%' if p4_pct > 5 else ''}</div>
    </div>
    <div class="breadth-legend">
      <div class="bl-item"><div class="bl-dot" style="background:#64748b"></div>1페이즈 베이스 {p1_cnt}개 ({p1_pct:.1f}%)</div>
      <div class="bl-item"><div class="bl-dot" style="background:#22c55e"></div>2페이즈 상승추세 {p2_cnt}개 ({p2_pct:.1f}%)</div>
      <div class="bl-item"><div class="bl-dot" style="background:#eab308"></div>3페이즈 분산 {p3_cnt}개 ({p3_pct:.1f}%)</div>
      <div class="bl-item"><div class="bl-dot" style="background:#ef4444"></div>4페이즈 하락추세 {p4_cnt}개 ({p4_pct:.1f}%)</div>
      <div class="bl-item" style="margin-left:auto">시장 폭 품질: <strong style="color:var(--text)">{bq}</strong></div>
    </div>
  </div>

  {sector_ranking_html}

  <!-- 매수 신호 -->
  <div class="section-hdr">
    <h2>🟢 매수 신호</h2>
    <span class="count-badge buy-badge">{len(buy_signals)}개</span>
  </div>
  <div class="grid">
    {"".join([_render_buy_card(s, i+1) for i, s in enumerate(buy_signals[:30])]) if buy_signals else no_buy}
  </div>

  <!-- 광고 2 -->
  <div class="ad-banner">
    <ins class="adsbygoogle" style="display:block;" data-ad-client="ca-pub-9724013230967786" data-ad-slot="5386218570" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>
  <div class="ad-banner">
    <iframe src="https://ads-partners.coupang.com/widgets.html?id=962570&template=carousel&trackingCode=AF1576178&subId=&width=728&height=90&tsource=" width="728" height="90" frameborder="0" scrolling="no" referrerpolicy="unsafe-url" style="max-width:100%;"></iframe>
  </div>

  <!-- 매도 신호 -->
  <div class="section-hdr">
    <h2>🔴 매도 신호</h2>
    <span class="count-badge sell-badge">{len(sell_signals)}개</span>
  </div>
  <div class="grid">
    {"".join([_render_sell_card(s, i+1) for i, s in enumerate(sell_signals[:20])]) if sell_signals else no_sell}
  </div>

</div>

<div class="footer">
  <strong>⚠️ 투자 권유가 아닙니다.</strong> 교육 및 정보 제공 목적입니다.<br>
  주식 거래는 손실 위험을 수반합니다. 항상 자체적으로 조사하십시오. 투자 결정 전 공인 재무 전문가와 상담하십시오.<br>
  <span style="opacity:.5">미너비니 SEPA 방법론 기반 · 페이즈 분석 · VCP 탐지 · GitHub Actions 자동 업데이트</span>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from scan JSON")
    parser.add_argument(
        "--input",
        default="data/daily_scans/latest_scan_data.json",
        help="Path to scan JSON file",
    )
    parser.add_argument(
        "--output",
        default="docs/index.html",
        help="Output HTML path (default: docs/index.html)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "<html><body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h1>스캔 데이터 없음</h1>"
            "<p>일일 스캔이 아직 실행되지 않았습니다. 장 마감 후 다시 확인하세요.</p></div></body></html>",
            encoding="utf-8",
        )
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    html_content = generate_html(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    buy_count = len(data.get("buy_signals") or [])
    sell_count = len(data.get("sell_signals") or [])
    print(f"HTML report generated: {output_path}")
    print(f"  Buy signals: {buy_count}  |  Sell signals: {sell_count}")


if __name__ == "__main__":
    main()
