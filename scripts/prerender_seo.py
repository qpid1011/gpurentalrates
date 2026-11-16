#!/usr/bin/env python3
"""Static HTML SSR Pre-Renderer, JSON-LD FAQ Enricher & IndexNow Notifier for GPURentalRates.com."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.request

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
JSON_PATH = PUBLIC_DIR / "gpu_rates.json"
HTML_PATH = PUBLIC_DIR / "index.html"
SITEMAP_PATH = PUBLIC_DIR / "sitemap.xml"
HOST = "gpurentalrates.com"
SITE_URL = f"https://{HOST}/"
INDEXNOW_KEY = hashlib.sha256(f"indexnow:{HOST}:v1".encode("utf-8")).hexdigest()[:32]


def _esc(val: object) -> str:
    return html.escape(str(val or ""), quote=True)


def _select_ssr_offers(offers: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select up to 8 lowest-price offers per GPU architecture + hyperscaler references (~64 rows)."""
    picked: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for r in offers:
        gkey = str(r.get("gpu_key") or "OTHER")
        if r.get("is_reference"):
            picked.append(r)
            continue
        if counts.get(gkey, 0) < 8:
            picked.append(r)
            counts[gkey] = counts.get(gkey, 0) + 1
    return picked[:72]


def _render_cards_html(gpu_summaries: list[dict[str, object]]) -> str:
    top_keys = {"B300", "B200", "H200", "H100", "A100_80G", "RTX5090", "RTX4090"}
    sums = [g for g in gpu_summaries if str(g.get("gpu_key")) in top_keys][:6]
    parts: list[str] = []
    for g in sums:
        gkey = _esc(g.get("gpu_key"))
        label = _esc(g.get("gpu_label"))
        low = float(g.get("lowest_per_gpu_usd") or 0.0)
        med = float(g.get("median_per_gpu_usd") or 0.0)
        sav = int(g.get("max_savings_pct") or 0)
        parts.append(
            f'<div class="gcard" onclick="selectGpuCard(\'{gkey}\')">'
            f'<div class="gcard-title">{label}</div>'
            f'<div class="gcard-price">${low:.2f}<span style="font-size:0.78rem;font-weight:700;color:var(--text-muted);">/GPU/h</span></div>'
            f'<div class="gcard-sub">Median ${med:.2f} · <span class="badge b-save">Save {sav}%</span></div>'
            f"</div>"
        )
    return "\n      ".join(parts)


def _render_rows_html(offers: list[dict[str, object]]) -> str:
    rows_html: list[str] = []
    for r in _select_ssr_offers(offers):
        if r.get("is_reference"):
            badge = '<span class="badge b-ref">Hyperscaler Reference</span>'
        elif r.get("in_stock"):
            badge = '<span class="badge b-stock">🟢 In Stock</span>'
        else:
            badge = '<span class="badge b-wait">Waitlist / Check</span>'
        regs = " · ".join(str(x) for x in (r.get("live_regions") or [])) or "Global"
        num_gpus = int(r.get("num_gpus") or 1)
        vram_gb = int(r.get("vram_gb") or 0)
        p_gpu = float(r.get("price_per_gpu_hr_usd") or 0.0)
        p_node = float(r.get("node_price_hr_usd") or 0.0)
        rows_html.append(
            "<tr>"
            f'<td><div style="font-weight:800;"><a href="{_esc(r.get("provider_url"))}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;">{_esc(r.get("provider_name"))} ↗</a></div>'
            f'<div style="font-size:0.75rem;color:var(--text-muted);">{_esc(r.get("tier"))}</div></td>'
            f'<td><div style="font-weight:800;">{_esc(r.get("gpu_label"))}</div>'
            f'<div style="font-size:0.75rem;color:var(--text-muted);">{vram_gb} GB VRAM / GPU</div></td>'
            f'<td><div style="font-weight:700;">{num_gpus}× GPU ({num_gpus * vram_gb} GB total)</div>'
            f'<div style="font-size:0.75rem;color:var(--text-muted);">{_esc(r.get("interconnect"))} · {_esc(r.get("vcpus") or "-")} vCPU · {_esc(r.get("ram_gb") or "-")} GB RAM</div></td>'
            f'<td style="font-size:1.02rem;font-weight:900;">${p_gpu:.2f}<span style="font-size:0.74rem;font-weight:600;color:var(--text-muted);">/h</span></td>'
            f'<td style="font-weight:700;">${p_node:.2f}/h</td>'
            f'<td><div>{badge}</div><div style="font-size:0.74rem;color:var(--text-muted);margin-top:3px;">{_esc(regs)}</div></td>'
            "</tr>"
        )
    return "\n        ".join(rows_html)


def _build_ldjson(data: dict[str, object], iso_date: str) -> str:
    sums = {str(g["gpu_key"]): g for g in (data.get("gpu_summaries") or []) if isinstance(g, dict)}
    h100_low = float((sums.get("H100") or {}).get("lowest_per_gpu_usd") or 1.66)
    b200_low = float((sums.get("B200") or {}).get("lowest_per_gpu_usd") or 3.74)
    h200_low = float((sums.get("H200") or {}).get("lowest_per_gpu_usd") or 2.50)
    total_offers = int((data.get("summary") or {}).get("total_offers") or 190)
    providers = int((data.get("summary") or {}).get("providers_tracked") or 22)
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Dataset",
                "name": "Live Cloud GPU Rental Rates Index (B300, B200, H200, H100, A100, RTX 5090/4090)",
                "description": f"Normalized hourly per-GPU and multi-GPU cluster rental rates and regional stock across {providers} NeoCloud, Bare-Metal, and Hyperscaler providers ({total_offers} verified configurations).",
                "url": SITE_URL,
                "dateModified": iso_date,
                "keywords": ["gpu rental rates", "cloud gpu pricing", "h100 rental price", "b200 cloud price", "h200 hourly rate", "gpu cluster cost calculator"],
                "distribution": {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE_URL}gpu_rates.json"},
            },
            {
                "@type": "WebApplication",
                "name": "GPURentalRates.com — Cloud GPU Price Tracker & Cluster Cost Calculator",
                "url": SITE_URL,
                "applicationCategory": "DeveloperApplication",
                "operatingSystem": "All",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "What are the lowest cloud GPU rental rates for H100, H200, and B200 right now?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": f"Across {providers} tracked providers, verified on-demand hourly GPU rental rates currently start at ${h100_low:.2f}/GPU/hr for NVIDIA H100 80GB, ${h200_low:.2f}/GPU/hr for NVIDIA H200 141GB, and ${b200_low:.2f}/GPU/hr for NVIDIA B200 192GB, saving 64%–81% versus standard Hyperscaler list prices.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "When should I rent SXM5/SXM6 NVLink clusters instead of PCIe GPUs?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Choose SXM5/SXM6 with NVLink and NVSwitch for multi-GPU distributed training or 70B+ full-parameter fine-tuning to avoid gradient communication bottlenecks. Choose PCIe GPUs for single-GPU inference, LoRA adapters, or batch rendering at lower hourly cost.",
                        },
                    },
                ],
            },
        ],
    }
    return json.dumps(graph, indent=2)


def prerender_all(ping_indexnow: bool = False) -> dict[str, object]:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    now_dt = datetime.now(timezone.utc)
    day_str = now_dt.strftime("%Y-%m-%d")
    iso_str = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    offers = list(data.get("offers") or [])
    gpu_sums = list(data.get("gpu_summaries") or [])
    total_offers = int((data.get("summary") or {}).get("total_offers") or len(offers))
    updated_utc = _esc(data.get("updated_at_utc") or day_str)

    doc = HTML_PATH.read_text(encoding="utf-8")
    doc = re.sub(
        r'(<script id="seo-ldjson" type="application/ld\+json">)(.*?)(</script>)',
        lambda m: f"{m.group(1)}\n{_build_ldjson(data, iso_str)}\n  {m.group(3)}",
        doc,
        count=1,
        flags=re.DOTALL,
    )
    doc = re.sub(
        r'(<span id="updated-stamp"[^>]*>)(.*?)(</span>)',
        lambda m: f"{m.group(1)}Updated: {updated_utc} ({total_offers} offers){m.group(3)}",
        doc,
        count=1,
        flags=re.DOTALL,
    )
    doc = re.sub(
        r'(<section id="gpu-summary-cards" class="gpu-cards">)(.*?)(</section>)',
        lambda m: f"{m.group(1)}\n      {_render_cards_html(gpu_sums)}\n    {m.group(3)}",
        doc,
        count=1,
        flags=re.DOTALL,
    )
    doc = re.sub(
        r'(<span id="offer-count-lbl"[^>]*>)(.*?)(</span>)',
        lambda m: f"{m.group(1)}{total_offers} verified configurations{m.group(3)}",
        doc,
        count=1,
        flags=re.DOTALL,
    )
    doc = re.sub(
        r'(<tbody id="offers-tbody">)(.*?)(</tbody>)',
        lambda m: f"{m.group(1)}\n        {_render_rows_html(offers)}\n      {m.group(3)}",
        doc,
        count=1,
        flags=re.DOTALL,
    )
    HTML_PATH.write_text(doc, encoding="utf-8")

    SITEMAP_PATH.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{SITE_URL}</loc>\n    <lastmod>{day_str}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
        f"</urlset>\n",
        encoding="utf-8",
    )
    key_file = PUBLIC_DIR / f"{INDEXNOW_KEY}.txt"
    key_file.write_text(INDEXNOW_KEY, encoding="utf-8")

    ping_status = None
    if ping_indexnow:
        body = json.dumps({
            "host": HOST,
            "key": INDEXNOW_KEY,
            "keyLocation": f"{SITE_URL}{INDEXNOW_KEY}.txt",
            "urlList": [SITE_URL],
        }).encode("utf-8")
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            ping_status = resp.status
    return {"host": HOST, "ssr_rows": len(_select_ssr_offers(offers)), "indexnow_key": INDEXNOW_KEY, "ping_status": ping_status}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ping-indexnow", action="store_true")
    args = ap.parse_args()
    print(json.dumps(prerender_all(ping_indexnow=args.ping_indexnow)))
