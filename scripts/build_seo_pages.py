#!/usr/bin/env python3
"""Closed-Loop Programmatic SEO Subpage Builder & Historical Trend Engine (v5.0)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
RATES_PATH, TARGETS_PATH, HISTORY_DIR = PUBLIC_DIR / "gpu_rates.json", PUBLIC_DIR / "seo_targets.json", PUBLIC_DIR / "history"
INDEX_PATH, SITEMAP_PATH, WATCHLIST_PATH = PUBLIC_DIR / "index.html", PUBLIC_DIR / "sitemap.xml", PUBLIC_DIR / "seo_Watchlist_candidates.json"
SITE_URL = "https://gpurentalrates.com/"
KEY_ALIASES: dict[str, str] = {"A100_40G": "A100"}

GA4_SNIPPET = """  <script async src="https://www.googletagmanager.com/gtag/js?id=G-VNWP0EE6SS"></script>
  <script>
    window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date()); gtag('config', 'G-VNWP0EE6SS', { anonymize_ip: true });
    document.addEventListener('click', function(e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href^="http"]') : null;
      if (a && a.hostname && a.hostname.indexOf('gpurentalrates.com') === -1) {
        gtag('event', 'provider_outbound_click', { provider_domain: a.hostname, link_url: a.href });
      }
    });
  </script>"""

SUBPAGE_CSS = """    :root { --bg:#0f172a; --surface:#1e293b; --surface-alt:#0b1220; --border:#334155; --text:#f8fafc; --text-muted:#94a3b8; --accent:#38bdf8; --row-hover:rgba(56,189,248,0.06); }
    html.light-theme, body.light-theme { --bg:#f8fafc; --surface:#ffffff; --surface-alt:#f1f5f9; --border:#cbd5e1; --text:#0f172a; --text-muted:#475569; --accent:#0369a1; --row-hover:#f1f5f9; }
    * { box-sizing:border-box; } body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--text); line-height:1.5; }
    .topbar { position:sticky; top:0; z-index:30; background:var(--surface); border-bottom:1px solid var(--border); padding:13px 24px; display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px; }
    .brand { display:flex; align-items:center; gap:10px; flex-wrap:wrap; } .brand-link { font-size:1.18rem; font-weight:900; letter-spacing:-0.02em; color:var(--text); text-decoration:none; }
    .live-pill { background:#d9f99d; color:#1a2e05; border:1px solid #65a30d; padding:2px 9px; border-radius:999px; font-size:0.74rem; font-weight:800; }
    .btn { background:var(--surface-alt); color:var(--text); border:1px solid var(--border); padding:7px 13px; border-radius:8px; font-size:0.82rem; font-weight:700; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; }
    .btn:hover, .preset-btn:hover, .hub-card:hover { border-color:var(--accent); } .container { max-width:1380px; margin:20px auto 64px; padding:0 20px; }
    .breadcrumb { font-size:0.81rem; font-weight:700; color:var(--text-muted); margin-bottom:12px; } .breadcrumb a { color:var(--accent); text-decoration:none; }
    .hero { margin-bottom:16px; } .hero h1 { margin:0 0 6px; font-size:1.62rem; font-weight:900; letter-spacing:-0.02em; } .hero p { margin:0; color:var(--text-muted); font-size:0.92rem; }
    .kpi-grid, .calc-controls, .calc-results, .hub-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(195px,1fr)); gap:11px; } .kpi-grid { margin-bottom:16px; } .calc-results { margin-top:14px; padding-top:12px; border-top:1px solid var(--border); } .hub-grid { margin-top:10px; }
    .kpi-card, .res-box { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:12px 14px; } .res-box { background:var(--surface-alt); border-radius:10px; }
    .kpi-lbl, .res-lbl, .field label { font-size:0.76rem; font-weight:800; color:var(--text-muted); } .field label { display:block; margin-bottom:5px; } .kpi-val, .res-val { font-size:1.34rem; font-weight:900; margin:3px 0; color:var(--text); } .kpi-sub { font-size:0.75rem; color:var(--text-muted); }
    .trend-banner { background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--accent); border-radius:12px; padding:13px 16px; margin-bottom:18px; display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; font-size:0.85rem; }
    .calc-panel, .faq-section, .hub-box { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:18px 20px; margin-bottom:20px; } .faq-section, .hub-box { margin-top:24px; margin-bottom:0; } .faq-section h2, .hub-box h2 { margin:0 0 10px; font-size:1.08rem; }
    .calc-header, .filter-bar { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; } .preset-row, .filter-group { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
    .preset-btn { padding:5px 10px; border-radius:999px; border:1px solid var(--border); background:var(--surface-alt); color:var(--text); font-size:0.76rem; font-weight:700; cursor:pointer; } .ctrl-input { width:100%; padding:8px 11px; border-radius:8px; border:1px solid var(--border); background:var(--surface-alt); color:var(--text); font-size:0.86rem; font-weight:700; }
    table { width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--border); border-radius:12px; overflow:hidden; } th, td { padding:11px 13px; text-align:left; border-bottom:1px solid var(--border); font-size:0.85rem; color:var(--text); } th { background:var(--surface-alt); font-size:0.77rem; font-weight:800; } tr:hover td { background:var(--row-hover); } .hidden-row { display:none !important; }
    .badge { display:inline-block; padding:2px 8px; border-radius:6px; font-size:0.72rem; font-weight:800; }
    .b-stock, .b-down { background:#064e3b; color:#a7f3d0; border:1px solid #10b981; } html.light-theme .b-stock, body.light-theme .b-stock, html.light-theme .b-down, body.light-theme .b-down { background:#d1fae5; color:#065f46; border:1px solid #10b981; }
    .b-wait, .b-flat { background:#1e293b; color:#cbd5e1; border:1px solid #64748b; } html.light-theme .b-wait, body.light-theme .b-wait, html.light-theme .b-flat, body.light-theme .b-flat { background:#f1f5f9; color:#334155; border:1px solid #94a3b8; }
    .b-save { background:#14532d; color:#bbf7d0; border:1px solid #22c55e; } html.light-theme .b-save, body.light-theme .b-save { background:#dcfce7; color:#166534; border:1px solid #22c55e; }
    .b-ref, .b-up { background:#451a03; color:#fde68a; border:1px solid #f59e0b; } html.light-theme .b-ref, body.light-theme .b-ref, html.light-theme .b-up, body.light-theme .b-up { background:#fef3c7; color:#92400e; border:1px solid #d97706; }
    .hub-card { display:block; text-decoration:none; color:var(--text); background:var(--surface-alt); border:1px solid var(--border); border-radius:10px; padding:10px 12px; } .footer { margin-top:26px; font-size:0.78rem; color:var(--text-muted); text-align:center; padding-top:16px; border-top:1px solid var(--border); }"""


def _esc(val: object) -> str:
    return html.escape(str(val or ""), quote=True)


def _norm_key(gkey: str) -> str:
    return KEY_ALIASES.get(gkey, gkey)


def load_history_trends(history_dir: Path = HISTORY_DIR) -> dict[str, object]:
    files = sorted(history_dir.glob("*.json"))
    snaps = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    if not snaps:
        return {"days": 0, "earliest_date": "-", "latest_date": "-", "by_gpu": {}}
    first_map = {str(g["gpu_key"]): g for g in snaps[0].get("gpu_summaries") or []}
    last_map = {str(g["gpu_key"]): g for g in snaps[-1].get("gpu_summaries") or []}
    by_gpu: dict[str, dict[str, float]] = {}
    for k, lg in last_map.items():
        fg = first_map.get(k, lg)
        f_low, l_low = float(fg.get("lowest_per_gpu_usd") or 0.0), float(lg.get("lowest_per_gpu_usd") or 0.0)
        f_med, l_med = float(fg.get("median_per_gpu_usd") or 0.0), float(lg.get("median_per_gpu_usd") or 0.0)
        by_gpu[k] = {
            "first_low": f_low, "last_low": l_low, "low_delta_usd": round(l_low - f_low, 2),
            "low_delta_pct": round(((l_low - f_low) / f_low) * 100.0, 1) if f_low > 0 else 0.0,
            "first_med": f_med, "last_med": l_med, "med_delta_usd": round(l_med - f_med, 2),
            "med_delta_pct": round(((l_med - f_med) / f_med) * 100.0, 1) if f_med > 0 else 0.0,
        }
    return {"days": len(snaps), "earliest_date": str(snaps[0].get("date_utc") or files[0].stem), "latest_date": str(snaps[-1].get("date_utc") or files[-1].stem), "by_gpu": by_gpu}


def _fmt_delta_badge(tr: dict[str, float], days: int) -> tuple[str, str]:
    ld, lp, md, mp = tr.get("low_delta_usd", 0.0), tr.get("low_delta_pct", 0.0), tr.get("med_delta_usd", 0.0), tr.get("med_delta_pct", 0.0)
    if abs(ld) >= 0.01:
        cls, sign = ("b-down", "-") if ld < 0 else ("b-up", "+")
        txt = f"Floor {sign}${abs(ld):.2f}/h ({sign}{abs(lp):.1f}%)"
        return f'<span class="badge {cls}">{txt}</span>', txt
    if abs(md) >= 0.01:
        cls, sign = ("b-down", "-") if md < 0 else ("b-up", "+")
        txt = f"Median {sign}${abs(md):.2f}/h ({sign}{abs(mp):.1f}%)"
        return f'<span class="badge {cls}">{txt}</span>', txt
    return f'<span class="badge b-flat">Stable 0.0% ({days}d)</span>', f"Floor & Median 0.0% ({days}d)"


def _collect_offers(all_offers: list[dict[str, object]], sums_map: dict[str, dict[str, object]], page: dict[str, object]) -> list[dict[str, object]]:
    target_set = {_norm_key(str(k)) for k in (page.get("gpu_keys") or [])}
    rows = [dict(r) for r in all_offers if str(r.get("gpu_key")) in target_set]
    rows.sort(key=lambda r: (bool(r.get("is_reference")), float(r.get("price_per_gpu_hr_usd") or 0.0), int(r.get("num_gpus") or 1)))
    if not any(r.get("is_reference") for r in rows):
        pkey = _norm_key(str((page.get("gpu_keys") or ["H100"])[0]))
        gsum = sums_map.get(pkey) or {}
        ref_hr, vram = float(gsum.get("reference_cloud_usd") or 8.80), int(gsum.get("vram_gb") or 80)
        rows.append({
            "provider_name": str(page.get("ref_label") or "Hyperscaler On-Demand Benchmark"),
            "provider_url": "https://cloud.google.com/compute/gpus-pricing", "tier": "Hyperscaler",
            "gpu_key": pkey, "gpu_label": str(gsum.get("gpu_label") or page.get("short_label") or pkey),
            "vram_gb": vram, "num_gpus": 8, "interconnect": "8x Standard Public List", "vcpus": 192, "ram_gb": 1536,
            "node_price_hr_usd": round(ref_hr * 8, 2), "price_per_gpu_hr_usd": ref_hr,
            "in_stock": True, "live_regions": ["US / EU Public List"], "is_reference": True,
        })
    return rows


def _render_offer_rows(rows: list[dict[str, object]]) -> str:
    out: list[str] = []
    for r in rows:
        is_ref, in_stk = bool(r.get("is_reference")), bool(r.get("in_stock"))
        badge = '<span class="badge b-ref">Hyperscaler Reference</span>' if is_ref else ('<span class="badge b-stock">🟢 In Stock</span>' if in_stk else '<span class="badge b-wait">Waitlist / Check</span>')
        regs = " · ".join(str(x) for x in (r.get("live_regions") or [])) or "Global"
        ng, vram = int(r.get("num_gpus") or 1), int(r.get("vram_gb") or 0)
        pg, pn = float(r.get("price_per_gpu_hr_usd") or 0.0), float(r.get("node_price_hr_usd") or 0.0)
        out.append(
            f'<tr class="offer-row" data-num="{ng}" data-stock="{"1" if (in_stk or is_ref) else "0"}">'
            f'<td><div style="font-weight:800;"><a href="{_esc(r.get("provider_url"))}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;">{_esc(r.get("provider_name"))} ↗</a></div><div style="font-size:0.75rem;color:var(--text-muted);">{_esc(r.get("tier"))}</div></td>'
            f'<td><div style="font-weight:800;">{_esc(r.get("gpu_label"))}</div><div style="font-size:0.75rem;color:var(--text-muted);">{vram} GB VRAM / GPU</div></td>'
            f'<td><div style="font-weight:700;">{ng}× GPU ({ng * vram} GB total)</div><div style="font-size:0.75rem;color:var(--text-muted);">{_esc(r.get("interconnect"))} · {_esc(r.get("vcpus") or "-")} vCPU · {_esc(r.get("ram_gb") or "-")} GB RAM</div></td>'
            f'<td style="font-size:1.02rem;font-weight:900;">${pg:.2f}<span style="font-size:0.74rem;font-weight:600;color:var(--text-muted);">/h</span></td>'
            f'<td style="font-weight:700;">${pn:.2f}/h</td>'
            f'<td><div>{badge}</div><div style="font-size:0.74rem;color:var(--text-muted);margin-top:3px;">{_esc(regs)}</div></td></tr>'
        )
    return "\n        ".join(out)


def _inject_homepage_hub(pages: list[dict[str, object]], sums_map: dict[str, dict[str, object]], trends: dict[str, object], all_offers: list[dict[str, object]]) -> None:
    days, earliest, latest = int(trends["days"]), _esc(trends["earliest_date"]), _esc(trends["latest_date"])
    by_gpu = dict(trends.get("by_gpu") or {})
    cards = [
        f'<a class="hub-card" href="/{_esc(p["slug"])}/"><div class="hub-card-top"><span>{_esc(p["short_label"])}</span><span>→</span></div>'
        f'<div class="hub-card-mid">From ${float((sums_map.get(_norm_key(str(p["gpu_keys"][0]))) or {}).get("lowest_per_gpu_usd") or 0.0):.2f}/h · '
        f'<span style="font-size:0.78rem;font-weight:700;color:var(--text-muted);">Med ${float((sums_map.get(_norm_key(str(p["gpu_keys"][0]))) or {}).get("median_per_gpu_usd") or 0.0):.2f}/h</span></div>'
        f'<div class="hub-card-bot">{_fmt_delta_badge(by_gpu.get(_norm_key(str(p["gpu_keys"][0]))) or {}, days)[0]}<span>{len(_collect_offers(all_offers, sums_map, p))} offers</span></div></a>'
        for p in pages
    ]
    cards_str = "\n        ".join(cards)
    hub_block = (
        '<!-- SEO_HUB_START -->\n    <section class="seo-hub" aria-label="Historical GPU Price Trends and Deep-Dive Benchmarks">\n'
        '      <div class="seo-hub-head"><strong style="font-size:0.95rem;">📈 Multi-Day GPU Price Trend Archive &amp; Architecture Sub-Indexes</strong>'
        f'<span class="badge b-flat">Tracked across {days} daily snapshots ({earliest} → {latest})</span></div>\n'
        f'      <div class="hub-grid">\n        {cards_str}\n      </div>\n    </section>\n    <!-- SEO_HUB_END -->'
    )
    doc = INDEX_PATH.read_text(encoding="utf-8")
    doc = re.sub(r"<!-- SEO_HUB_START -->.*?<!-- SEO_HUB_END -->", lambda _: hub_block, doc, count=1, flags=re.DOTALL) if "<!-- SEO_HUB_START -->" in doc else doc.replace('<section class="filter-bar">', f'{hub_block}\n\n    <section class="filter-bar">', 1)
    INDEX_PATH.write_text(doc, encoding="utf-8")


def _render_subpage(page: dict[str, object], pages: list[dict[str, object]], sums_map: dict[str, dict[str, object]], all_offers: list[dict[str, object]], trends: dict[str, object], updated_utc: str, iso_str: str) -> tuple[str, int]:
    slug, q_target, short_lbl, faq_ic = str(page["slug"]), str(page["target_query"]), str(page["short_label"]), str(page["interconnect_faq"])
    url = f"{SITE_URL}{slug}/"
    norm_keys = [_norm_key(str(k)) for k in (page.get("gpu_keys") or [])]
    pkey = norm_keys[0]
    gsum = sums_map.get(pkey) or {}
    rows = _collect_offers(all_offers, sums_map, page)
    cloud_rows = [r for r in rows if not r.get("is_reference")]
    in_stock_cnt = sum(1 for r in cloud_rows if r.get("in_stock"))
    low = min((float(r["price_per_gpu_hr_usd"]) for r in cloud_rows), default=float(gsum.get("lowest_per_gpu_usd") or 0.0))
    med, ref_usd = float(gsum.get("median_per_gpu_usd") or low), float(gsum.get("reference_cloud_usd") or round(low * 2.8, 2))
    sav_pct, def_cnt, def_hrs = int(gsum.get("max_savings_pct") or 64), int(page.get("default_gpu_count") or 8), int(page.get("default_hours") or 72)
    days, earliest, latest = int(trends["days"]), str(trends["earliest_date"]), str(trends["latest_date"])
    tr = dict((trends.get("by_gpu") or {}).get(pkey) or {})
    badge_html, delta_plain = _fmt_delta_badge(tr, days)
    f_low, f_med = float(tr.get("first_low") or low), float(tr.get("first_med") or med)
    est_tot, med_tot, ref_tot = low * def_cnt * def_hrs, med * def_cnt * def_hrs, ref_usd * def_cnt * def_hrs
    sav_tot, vram_tot = max(0.0, ref_tot - est_tot), int(gsum.get("vram_gb") or 80) * def_cnt
    title_txt = f"{q_target} (2026 Live — From ${low:.2f}/hr)"
    desc_txt = f"Compare {len(rows)} live {short_lbl} cloud GPU rental rates starting at ${low:.2f}/GPU/hr (median ${med:.2f}/hr, {in_stock_cnt} in stock). Tracked across {days} daily snapshots since {earliest} ({delta_plain})."

    ld_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Dataset", "name": f"{q_target} — Live Multi-Cloud Price & Stock Dataset", "description": desc_txt, "url": url, "dateModified": iso_str, "keywords": [q_target.lower(), f"{short_lbl.lower()} rental price", "cloud gpu hourly rate"], "distribution": {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}gpu_rates.json"}},
            {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL}, {"@type": "ListItem", "position": 2, "name": short_lbl, "item": url}]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f"What is the lowest {short_lbl} hourly cloud rental rate right now?", "acceptedAnswer": {"@type": "Answer", "text": f"Verified {short_lbl} cloud instances start at ${low:.2f}/GPU/hr (market median ${med:.2f}/GPU/hr) across {len(cloud_rows)} NeoCloud and Bare-Metal offers ({in_stock_cnt} in stock), saving up to {sav_pct}% vs ${ref_usd:.2f}/GPU/hr Hyperscaler list pricing."}},
                {"@type": "Question", "name": f"How have {short_lbl} rental prices trended since {earliest}?", "acceptedAnswer": {"@type": "Answer", "text": f"Across {days} daily snapshots from {earliest} to {latest}, the {short_lbl} floor moved from ${f_low:.2f}/hr to ${low:.2f}/hr and the market median moved from ${f_med:.2f}/hr to ${med:.2f}/hr ({delta_plain}). A {def_cnt}x GPU run for {def_hrs}h costs ${est_tot:,.2f} at the floor."}},
                {"@type": "Question", "name": f"Should I rent SXM/NVLink or PCIe for {short_lbl} workloads?", "acceptedAnswer": {"@type": "Answer", "text": faq_ic}},
            ]},
        ],
    }
    calc_gpus = [sums_map[k] for k in norm_keys if k in sums_map]
    gpu_opts = "".join(f'<option value="{_esc(g["gpu_key"])}" {"selected" if i == 0 else ""}>{_esc(g["gpu_label"])} — from ${float(g["lowest_per_gpu_usd"]):.2f}/h</option>' for i, g in enumerate(calc_gpus))
    cnt_opts = "".join(f'<option value="{n}" {"selected" if n == def_cnt else ""}>{n}× GPU{"s" if n > 1 else ""}</option>' for n in (1, 2, 4, 8))
    sib_cards = "\n        ".join(
        f'<a class="hub-card" href="/{_esc(sp["slug"])}/"><div style="font-size:0.82rem;font-weight:800;color:var(--accent);">{_esc(sp["short_label"])} →</div>'
        f'<div style="font-size:0.94rem;font-weight:900;margin-top:3px;">From ${float((sums_map.get(_norm_key(str(sp["gpu_keys"][0]))) or {}).get("lowest_per_gpu_usd") or 0.0):.2f}/GPU/h</div></a>'
        for sp in pages if sp["slug"] != slug
    )
    page_html = f"""<!DOCTYPE html>
<html lang="en" class="light-theme"><head>
  <meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title_txt)}</title><meta name="description" content="{_esc(desc_txt)}" /><link rel="canonical" href="{_esc(url)}" />
{GA4_SNIPPET}
  <meta property="og:title" content="{_esc(title_txt)}" /><meta property="og:description" content="{_esc(desc_txt)}" /><meta property="og:url" content="{_esc(url)}" /><meta property="og:type" content="website" /><meta name="twitter:card" content="summary" />
  <script type="application/ld+json">{json.dumps(ld_graph)}</script>
  <style>\n{SUBPAGE_CSS}\n  </style>
</head><body class="light-theme">
  <header class="topbar">
    <div class="brand"><a class="brand-link" href="/">⚡ GPURentalRates<span style="color:var(--accent);">.com</span></a><span class="live-pill">LIVE BENCHMARK</span><span style="font-size:0.78rem;color:var(--text-muted);font-weight:600;">Updated: {_esc(updated_utc)}</span></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;"><a class="btn" href="/">← All GPUs Index</a><button id="theme-btn" class="btn" onclick="toggleTheme()">🌙 Dark Mode</button></div>
  </header>
  <main class="container">
    <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> → <span>{_esc(short_lbl)}</span></nav>
    <section class="hero"><h1>{_esc(q_target)}</h1><p>Normalized per-GPU hourly pricing (<code>$/GPU/hr</code>), multi-GPU node totals, and live datacenter stock across {len(cloud_rows)} verified cloud configurations plus Hyperscaler reference benchmarks.</p></section>
    <section class="kpi-grid">
      <div class="kpi-card"><div class="kpi-lbl">Lowest Verified Rate</div><div class="kpi-val">${low:.2f}<span style="font-size:0.78rem;color:var(--text-muted);">/GPU/h</span></div><div class="kpi-sub"><span class="badge b-save">Save up to {sav_pct}%</span> vs ${ref_usd:.2f}/h list</div></div>
      <div class="kpi-card"><div class="kpi-lbl">Market Median Rate</div><div class="kpi-val">${med:.2f}<span style="font-size:0.78rem;color:var(--text-muted);">/GPU/h</span></div><div class="kpi-sub">Across {len(cloud_rows)} NeoCloud &amp; Bare-Metal offers</div></div>
      <div class="kpi-card"><div class="kpi-lbl">Live Stock Right Now</div><div class="kpi-val">{in_stock_cnt}<span style="font-size:0.78rem;color:var(--text-muted);"> / {len(cloud_rows)} offers</span></div><div class="kpi-sub">Instant API-verified regional availability</div></div>
      <div class="kpi-card"><div class="kpi-lbl">{days}-Day Price Trend</div><div class="kpi-val" style="font-size:1.05rem;margin:7px 0;">{badge_html}</div><div class="kpi-sub">{_esc(earliest)} (${f_low:.2f}) → {_esc(latest)} (${low:.2f})</div></div>
    </section>
    <section class="trend-banner"><div><strong>📈 Multi-Day Historical Price Delta:</strong> Tracked across <strong>{days} daily snapshots since {_esc(earliest)}</strong> (latest: {_esc(latest)}). Floor moved <code>${f_low:.2f}/hr → ${low:.2f}/hr</code> ({tr.get("low_delta_usd", 0.0):+.2f}/hr, {tr.get("low_delta_pct", 0.0):+.1f}%) · Market median moved <code>${f_med:.2f}/hr → ${med:.2f}/hr</code> ({tr.get("med_delta_usd", 0.0):+.2f}/hr, {tr.get("med_delta_pct", 0.0):+.1f}%).</div><div>{badge_html}</div></section>
    <section class="calc-panel">
      <div class="calc-header"><strong style="font-size:1rem;">🧮 {_esc(short_lbl)} Cluster Cost Mini-Calculator</strong><div class="preset-row"><button class="preset-btn" onclick="setCalc(1, 24)">1× GPU · 24h</button><button class="preset-btn" onclick="setCalc(2, 40)">2× GPUs · 40h</button><button class="preset-btn" onclick="setCalc(4, 72)">4× GPUs · 72h</button><button class="preset-btn" onclick="setCalc(8, 168)">8× Node · 1wk (168h)</button></div></div>
      <div class="calc-controls">
        <div class="field"><label for="sub-gpu">GPU Variant</label><select id="sub-gpu" class="ctrl-input" onchange="recalc()">{gpu_opts}</select></div>
        <div class="field"><label for="sub-cnt">Cluster Size (1×–8× GPUs)</label><select id="sub-cnt" class="ctrl-input" onchange="recalc()">{cnt_opts}</select></div>
        <div class="field"><label for="sub-hrs">Runtime Duration (Hours)</label><input id="sub-hrs" class="ctrl-input" type="number" min="1" max="8760" value="{def_hrs}" oninput="recalc()" /></div>
      </div>
      <div class="calc-results">
        <div class="res-box"><div class="res-lbl">Lowest NeoCloud Total</div><div id="sub-low" class="res-val">${est_tot:,.2f}</div><div id="sub-low-note" class="kpi-sub">${low:.2f}/GPU/h × {def_cnt} GPUs × {def_hrs}h</div></div>
        <div class="res-box"><div class="res-lbl">Market Median Total</div><div id="sub-med" class="res-val">${med_tot:,.2f}</div><div id="sub-med-note" class="kpi-sub">${med:.2f}/GPU/h median</div></div>
        <div class="res-box"><div class="res-lbl">Hyperscaler List Benchmark</div><div id="sub-ref" class="res-val">${ref_tot:,.2f}</div><div class="kpi-sub">Public on-demand reference</div></div>
        <div class="res-box"><div class="res-lbl">Estimated Net Savings</div><div id="sub-sav" class="res-val">${sav_tot:,.2f} ({sav_pct}%)</div><div id="sub-vram" class="kpi-sub">Total Cluster VRAM: {vram_tot:,} GB</div></div>
      </div>
    </section>
    <section class="filter-bar">
      <div class="filter-group"><select id="flt-size" class="ctrl-input" style="width:auto;" onchange="filterRows()"><option value="ALL">All Node Sizes (1×–8×)</option><option value="1">1× Single GPU</option><option value="2">2× GPUs</option><option value="4">4× GPUs</option><option value="8">8× Cluster Node</option></select><label style="display:inline-flex;align-items:center;gap:6px;font-size:0.83rem;font-weight:700;cursor:pointer;"><input id="flt-stk" type="checkbox" onchange="filterRows()" /> 🟢 In-Stock Only</label></div>
      <span id="row-cnt-lbl" style="font-size:0.8rem;font-weight:700;color:var(--text-muted);">{len(rows)} configurations (including Hyperscaler reference)</span>
    </section>
    <table><thead><tr><th>Provider &amp; Tier</th><th>GPU Model &amp; VRAM</th><th>Config &amp; Interconnect</th><th>Price / GPU / hr</th><th>Total Node / hr</th><th>Live Stock &amp; Regions</th></tr></thead><tbody id="sub-tbody">\n        {_render_offer_rows(rows)}\n      </tbody></table>
    <section class="faq-section">
      <h2>Engineering &amp; Pricing FAQ — {_esc(short_lbl)}</h2>
      <p style="font-size:0.86rem;"><strong>1. What is the lowest {_esc(short_lbl)} hourly rental rate right now?</strong><br/>Verified {_esc(short_lbl)} instances start at <code>${low:.2f}/GPU/hr</code> (market median <code>${med:.2f}/GPU/hr</code>) across {len(cloud_rows)} NeoCloud and Bare-Metal offers ({in_stock_cnt} currently in stock), compared against <code>${ref_usd:.2f}/GPU/hr</code> Hyperscaler reference pricing.</p>
      <p style="font-size:0.86rem;"><strong>2. How have {_esc(short_lbl)} cloud prices moved over the past {days} daily snapshots?</strong><br/>Since {_esc(earliest)}, the verified floor moved from <code>${f_low:.2f}/hr</code> to <code>${low:.2f}/hr</code> and the market median shifted from <code>${f_med:.2f}/hr</code> to <code>${med:.2f}/hr</code> ({_esc(delta_plain)}).</p>
      <p style="font-size:0.86rem;margin-bottom:0;"><strong>3. SXM / NVLink vs PCIe Architecture Selection Guide:</strong><br/>{_esc(faq_ic)}</p>
    </section>
    <section class="hub-box"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;"><h2 style="margin:0;">Explore Other Cloud GPU Rental Rate Benchmarks</h2><a class="btn" href="/">Compare All 13 GPU Models on Homepage →</a></div><div class="hub-grid">\n        {sib_cards}\n      </div></section>
    <footer class="footer"><div>Independent public cloud GPU rate index &amp; cluster cost calculator (<a href="/" style="color:var(--accent);">GPURentalRates.com</a>). Verify interconnect, egress, and SLA terms directly with each cloud vendor.</div></footer>
  </main>
  <script>
    const SUB_GPUS = {json.dumps(calc_gpus)};
    function applyTheme() {{ const isDark = (localStorage.getItem("gpu_rates_theme") || "light") === "dark"; document.documentElement.classList.toggle("light-theme", !isDark); document.body.classList.toggle("light-theme", !isDark); const btn = document.getElementById("theme-btn"); if (btn) btn.textContent = isDark ? "☀️ Light Mode" : "🌙 Dark Mode"; }}
    function toggleTheme() {{ localStorage.setItem("gpu_rates_theme", document.documentElement.classList.contains("light-theme") ? "dark" : "light"); applyTheme(); }}
    function fmtUsd(n) {{ return "$" + Number(n || 0).toLocaleString("en-US", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}); }}
    function setCalc(cnt, hrs) {{ document.getElementById("sub-cnt").value = String(cnt); document.getElementById("sub-hrs").value = String(hrs); recalc(); }}
    function recalc() {{
      const g = SUB_GPUS.find(x => x.gpu_key === document.getElementById("sub-gpu").value) || SUB_GPUS[0]; if (!g) return;
      const cnt = Math.max(1, parseInt(document.getElementById("sub-cnt").value || "8", 10)), hrs = Math.max(1, parseFloat(document.getElementById("sub-hrs").value || "72"));
      const lowT = g.lowest_per_gpu_usd * cnt * hrs, medT = g.median_per_gpu_usd * cnt * hrs, refT = g.reference_cloud_usd * cnt * hrs, savT = Math.max(0, refT - lowT), pct = refT > 0 ? Math.round((savT / refT) * 100) : 0;
      document.getElementById("sub-low").textContent = fmtUsd(lowT); document.getElementById("sub-low-note").textContent = `$${{g.lowest_per_gpu_usd.toFixed(2)}}/GPU/h × ${{cnt}} GPUs × ${{hrs}}h`;
      document.getElementById("sub-med").textContent = fmtUsd(medT); document.getElementById("sub-med-note").textContent = `$${{g.median_per_gpu_usd.toFixed(2)}}/GPU/h median`;
      document.getElementById("sub-ref").textContent = fmtUsd(refT); document.getElementById("sub-sav").textContent = `${{fmtUsd(savT)}} (${{pct}}%)`;
      document.getElementById("sub-vram").textContent = `Total Cluster VRAM: ${{(g.vram_gb * cnt).toLocaleString()}} GB`;
    }}
    function filterRows() {{
      const sz = document.getElementById("flt-size").value, stk = document.getElementById("flt-stk").checked; let vis = 0;
      document.querySelectorAll("#sub-tbody .offer-row").forEach(tr => {{ const ok = (sz === "ALL" || tr.dataset.num === sz) && (!stk || tr.dataset.stock === "1"); tr.classList.toggle("hidden-row", !ok); if (ok) vis += 1; }});
      document.getElementById("row-cnt-lbl").textContent = `${{vis}} configurations shown`;
    }}
    applyTheme();
  </script>
</body></html>
"""
    return page_html, len(rows)


def _ingest_gsc_queries(gsc_path: Path, targets_cfg: dict[str, object]) -> int:
    raw = json.loads(gsc_path.read_text(encoding="utf-8"))
    rows = raw.get("rows", []) if isinstance(raw, dict) else list(raw)
    cands = [
        {"query": str((r.get("keys") or [r.get("query") or ""])[0]).strip(), "impressions": int(r.get("impressions") or 0), "clicks": int(r.get("clicks") or 0), "position": round(float(r.get("position") or 0.0), 2)}
        for r in rows if str((r.get("keys") or [r.get("query") or ""])[0]).strip() and int(r.get("impressions") or 0) >= 2 and 8.0 <= float(r.get("position") or 0.0) <= 80.0
    ]
    cands.sort(key=lambda x: (-int(x["impressions"]), float(x["position"])))
    WATCHLIST_PATH.write_text(json.dumps({"max_new_pages_per_week": targets_cfg.get("max_new_pages_per_week", 2), "candidates": cands}, indent=2) + "\n", encoding="utf-8")
    targets_cfg["observed_gsc_queries"] = cands[:25]
    TARGETS_PATH.write_text(json.dumps(targets_cfg, indent=2) + "\n", encoding="utf-8")
    return len(cands)


def build_all_seo_pages(gsc_queries_json: str | None = None) -> dict[str, object]:
    rates = json.loads(RATES_PATH.read_text(encoding="utf-8"))
    targets_cfg = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    pages = list(targets_cfg.get("pages") or [])[: int(targets_cfg.get("max_total_pages") or 15)]
    epoch = int(rates.get("updated_epoch") or 0)
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch > 0 else datetime.now(timezone.utc)
    day_str, iso_str = dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_utc = str(rates.get("updated_at_utc") or day_str)
    sums_map = {str(g["gpu_key"]): g for g in (rates.get("gpu_summaries") or []) if isinstance(g, dict)}
    all_offers = list(rates.get("offers") or [])
    trends = load_history_trends(HISTORY_DIR)

    _inject_homepage_hub(pages, sums_map, trends, all_offers)
    built: dict[str, int] = {}
    for p in pages:
        sub_dir = PUBLIC_DIR / str(p["slug"])
        sub_dir.mkdir(parents=True, exist_ok=True)
        html_doc, row_cnt = _render_subpage(p, pages, sums_map, all_offers, trends, updated_utc, iso_str)
        (sub_dir / "index.html").write_text(html_doc, encoding="utf-8")
        built[str(p["slug"])] = row_cnt

    urls_xml = [f"  <url>\n    <loc>{SITE_URL}</loc>\n    <lastmod>{day_str}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>"]
    for p in pages:
        urls_xml.append(f"  <url>\n    <loc>{SITE_URL}{p['slug']}/</loc>\n    <lastmod>{day_str}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.85</priority>\n  </url>")
    SITEMAP_PATH.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls_xml) + "\n</urlset>\n", encoding="utf-8")

    gsc_cnt = _ingest_gsc_queries(Path(gsc_queries_json), targets_cfg) if gsc_queries_json else 0
    return {"history_days": trends["days"], "earliest": trends["earliest_date"], "latest": trends["latest_date"], "subpages": built, "sitemap_urls": len(urls_xml), "gsc_candidates": gsc_cnt}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsc-queries-json", default=None)
    ns = ap.parse_args()
    print(json.dumps(build_all_seo_pages(gsc_queries_json=ns.gsc_queries_json)))
