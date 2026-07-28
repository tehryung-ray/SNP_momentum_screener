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
      <div class="ticker buy-color">{ticker}</div>
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
      <div class="ticker sell-color">{ticker}</div>
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
    <a href="guide.html" style="display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--muted);border:1px solid var(--border);border-radius:6px;padding:4px 10px;text-decoration:none;margin-top:4px;transition:color .15s,border-color .15s" onmouseover="this.style.color='var(--text)';this.style.borderColor='var(--muted)'" onmouseout="this.style.color='var(--muted)';this.style.borderColor='var(--border)'">📖 완전 가이드</a>
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
