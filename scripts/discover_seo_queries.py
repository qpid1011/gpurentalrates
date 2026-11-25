#!/usr/bin/env python3
"""Live US Google Autocomplete & GSC Query Poller + Guardrailed Subpage Auto-Expander for GPURentalRates.com."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
RATES_PATH = PUBLIC_DIR / "gpu_rates.json"
TARGETS_PATH = PUBLIC_DIR / "seo_targets.json"
SIGNALS_PATH = PUBLIC_DIR / "live_search_signals.json"
SITE_PROP = "sc-domain:gpurentalrates.com"

SEED_PREFIXES: tuple[str, ...] = (
    "gpu rental ",
    "cloud gpu ",
    "h100 rental ",
    "h200 rental ",
    "b200 gpu ",
    "l40s gpu ",
    "rtx a6000 cloud",
    "a6000 gpu rental",
    "rtx 4090 cloud ",
    "rtx 6000 ada ",
    "gh200 cloud ",
    "a100 rental ",
)

BLUEPRINT_POOL: tuple[dict[str, object], ...] = (
    {
        "trigger_tokens": ["l40s"],
        "min_offers": 5,
        "page": {
            "slug": "l40s-rental-rates",
            "gpu_keys": ["L40S"],
            "target_query": "NVIDIA L40S 48GB Cloud GPU Rental Rates & Hourly Pricing",
            "short_label": "NVIDIA L40S 48GB",
            "default_gpu_count": 4,
            "default_hours": 72,
            "ref_label": "AWS EC2 g6e / Standard Hyperscaler L40S List",
            "interconnect_faq": "NVIDIA L40S (48 GB GDDR6 ECC, Ada Lovelace FP8 Transformer Engine) omits NVLink, making PCIe Gen4 single-GPU and 2x–4x data-parallel inference, multimodal serving, and Omniverse/3D rendering 40%–60% cheaper per hour than H100 when HBM3 bandwidth is not the bottleneck.",
        },
    },
    {
        "trigger_tokens": ["a6000", "rtx a6000"],
        "min_offers": 5,
        "page": {
            "slug": "a6000-rental-rates",
            "gpu_keys": ["A6000", "RTX6000Ada"],
            "target_query": "NVIDIA RTX A6000 & 6000 Ada 48GB Cloud GPU Rental Rates",
            "short_label": "RTX A6000 & 6000 Ada 48GB",
            "default_gpu_count": 2,
            "default_hours": 72,
            "ref_label": "Managed Cloud Workstation 48GB GPU Benchmark",
            "interconnect_faq": "RTX A6000 (48 GB Ampere) and RTX 6000 Ada (48 GB Ada Lovelace) provide generous 48 GB VRAM per PCIe slot—ideal for 32B–70B quantized vLLM/Ollama serving, LoRA fine-tuning, and Diffusion pipelines that exceed 24 GB consumer cards without paying H100 SXM5 rates.",
        },
    },
    {
        "trigger_tokens": ["4090", "rtx 4090"],
        "min_offers": 4,
        "page": {
            "slug": "rtx-4090-rental-rates",
            "gpu_keys": ["RTX4090"],
            "target_query": "NVIDIA RTX 4090 24GB Cloud GPU Rental Rates & Hourly Cost",
            "short_label": "NVIDIA RTX 4090 24GB",
            "default_gpu_count": 2,
            "default_hours": 40,
            "ref_label": "On-Demand Prosumer Cloud GPU Benchmark",
            "interconnect_faq": "RTX 4090 (24 GB GDDR6X, 1.01 TB/s) delivers top price-performance per dollar for 7B–14B LLM inference, ComfyUI/Flux image-video generation, Whisper transcription, and CI evaluation jobs that fit inside 24 GB VRAM.",
        },
    },
)


def _fetch_us_autocomplete(prefix: str) -> list[dict[str, object]]:
    url = "https://suggestqueries.google.com/complete/search?client=chrome&hl=en&gl=us&q=" + urllib.parse.quote(prefix)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    queries = list(data[1] or [])[:8]
    rels = list(((data[4] if len(data) > 4 and isinstance(data[4], dict) else {}).get("google:suggestrelevance")) or [])
    out: list[dict[str, object]] = []
    for idx, q in enumerate(queries):
        score = int(rels[idx]) if idx < len(rels) else max(500, 900 - idx * 50)
        out.append({"query": str(q).strip().lower(), "score": score, "source": "google_us_autocomplete", "seed": prefix.strip()})
    return out


def _fetch_gsc_api_if_configured() -> list[dict[str, object]]:
    cid = os.environ.get("GSC_CLIENT_ID", "").strip()
    csec = os.environ.get("GSC_CLIENT_SECRET", "").strip()
    rtok = os.environ.get("GSC_REFRESH_TOKEN", "").strip()
    if not (cid and csec and rtok):
        return []
    tbody = urllib.parse.urlencode({"client_id": cid, "client_secret": csec, "refresh_token": rtok, "grant_type": "refresh_token"}).encode("utf-8")
    treq = urllib.request.Request("https://oauth2.googleapis.com/token", data=tbody, method="POST")
    with urllib.request.urlopen(treq, timeout=10) as tresp:
        atok = json.loads(tresp.read().decode("utf-8"))["access_token"]
    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=28)
    api_url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(SITE_PROP, safe='')}/searchAnalytics/query"
    qbody = json.dumps({"startDate": str(start_d), "endDate": str(end_d), "dimensions": ["query"], "rowLimit": 50}).encode("utf-8")
    qreq = urllib.request.Request(api_url, data=qbody, headers={"Authorization": f"Bearer {atok}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(qreq, timeout=10) as qresp:
        rows = json.loads(qresp.read().decode("utf-8")).get("rows") or []
    return [
        {
            "query": str((r.get("keys") or [""])[0]).lower(),
            "impressions": int(r.get("impressions") or 0),
            "clicks": int(r.get("clicks") or 0),
            "position": round(float(r.get("position") or 0.0), 1),
            "score": 1000 + int(r.get("impressions") or 0) * 20,
            "source": "google_search_console_api",
        }
        for r in rows
    ]


def run_discovery() -> dict[str, object]:
    now_dt = datetime.now(timezone.utc)
    iso_week = f"{now_dt.isocalendar()[0]}-W{now_dt.isocalendar()[1]:02d}"
    now_utc = now_dt.strftime("%Y-%m-%d %H:%M UTC")

    seen: dict[str, dict[str, object]] = {}
    for pref in SEED_PREFIXES:
        try:
            for item in _fetch_us_autocomplete(pref):
                q = str(item["query"])
                if q not in seen or int(item["score"]) > int(seen[q]["score"]):
                    seen[q] = item
        except Exception:
            continue
    try:
        for item in _fetch_gsc_api_if_configured():
            q = str(item["query"])
            seen[q] = item
    except Exception:
        pass

    ranked_signals = sorted(seen.values(), key=lambda x: int(x.get("score") or 0), reverse=True)
    rates_data = json.loads(RATES_PATH.read_text(encoding="utf-8"))
    offers = list(rates_data.get("offers") or [])
    targets_cfg = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    pages = list(targets_cfg.get("pages") or [])
    existing_slugs = {str(p.get("slug")) for p in pages}
    promotions = list(targets_cfg.get("auto_promotions") or [])

    max_weekly = int(targets_cfg.get("max_new_pages_per_week") or 2)
    max_total = int(targets_cfg.get("max_total_pages") or 15)
    added_this_week = sum(1 for x in promotions if str(x.get("iso_week")) == iso_week)
    newly_promoted: list[dict[str, object]] = []

    for bp in BLUEPRINT_POOL:
        if len(pages) >= max_total or added_this_week >= max_weekly:
            break
        page_def = dict(bp["page"])  # type: ignore[arg-type]
        slug = str(page_def["slug"])
        if slug in existing_slugs:
            continue
        gkeys = set(page_def.get("gpu_keys") or [])
        live_cnt = sum(1 for r in offers if str(r.get("gpu_key")) in gkeys and not r.get("is_reference"))
        if live_cnt < int(bp.get("min_offers") or 3):
            continue
        tokens = [str(t).lower() for t in (bp.get("trigger_tokens") or [])]
        matched = [s for s in ranked_signals if any(tok in str(s["query"]) for tok in tokens) and int(s.get("score") or 0) >= 550]
        if not matched:
            continue
        best = matched[0]
        pages.append(page_def)
        existing_slugs.add(slug)
        rec = {
            "slug": slug,
            "iso_week": iso_week,
            "promoted_at_utc": now_utc,
            "trigger_query": best["query"],
            "trigger_score": best["score"],
            "trigger_source": best["source"],
            "live_offers_verified": live_cnt,
        }
        promotions.append(rec)
        newly_promoted.append(rec)
        added_this_week += 1

    targets_cfg["pages"] = pages
    targets_cfg["auto_promotions"] = promotions
    targets_cfg["observed_gsc_queries"] = [s for s in ranked_signals[:25]]
    TARGETS_PATH.write_text(json.dumps(targets_cfg, indent=2) + "\n", encoding="utf-8")

    signals_payload = {
        "site": "GPURentalRates.com",
        "updated_at_utc": now_utc,
        "iso_week": iso_week,
        "total_signals_collected": len(ranked_signals),
        "active_subpages_count": len(pages),
        "newly_promoted_this_run": newly_promoted,
        "top_live_queries": ranked_signals[:30],
    }
    SIGNALS_PATH.write_text(json.dumps(signals_payload, indent=2) + "\n", encoding="utf-8")
    return {"signals": len(ranked_signals), "active_pages": len(pages), "newly_promoted": newly_promoted}


if __name__ == "__main__":
    print(json.dumps(run_discovery()))
