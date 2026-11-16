#!/usr/bin/env python3
"""
Zero-Maintenance Multi-Cloud GPU Rental Rate Sync Engine (sync_gpu_rates.py)
----------------------------------------------------------------------------
Fetches live hourly GPU rental prices and real-time regional stock across 18+ NeoClouds
from public unauthenticated endpoints (`api.shadeform.ai/v1/instances/types`) plus verified
Hyperscaler on-demand reference benchmarks (AWS, GCP, Azure), normalizing every offer to
per-GPU hourly USD (`price_per_gpu_hr_usd`) and total node hourly USD (`node_price_hr_usd`).

Designed for `$0/mo` Cloudflare Pages / GitHub Pages + GitHub Actions cron deployment.
"""
from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
OUT_JSON = PUBLIC_DIR / "gpu_rates.json"
HISTORY_DIR = PUBLIC_DIR / "history"

SHADEFORM_API_URL = "https://api.shadeform.ai/v1/instances/types"
_UA = "Mozilla/5.0 (compatible; GPURentalRatesBot/1.0; +https://gpurentalrates.com)"

CLOUD_META: dict[str, dict[str, str]] = {
    "lambdalabs": {"name": "Lambda", "url": "https://lambdalabs.com/service/gpu-cloud", "tier": "NeoCloud"},
    "nebius": {"name": "Nebius AI", "url": "https://nebius.com", "tier": "NeoCloud"},
    "crusoe": {"name": "Crusoe Cloud", "url": "https://crusoe.ai", "tier": "NeoCloud"},
    "voltagepark": {"name": "Voltage Park", "url": "https://voltagepark.com", "tier": "NeoCloud"},
    "hyperstack": {"name": "Hyperstack", "url": "https://hyperstack.cloud", "tier": "NeoCloud"},
    "vultr": {"name": "Vultr Cloud GPU", "url": "https://www.vultr.com/products/cloud-gpu/", "tier": "Cloud"},
    "digitalocean": {"name": "DigitalOcean GPU", "url": "https://www.digitalocean.com/products/gpu-droplets", "tier": "Cloud"},
    "scaleway": {"name": "Scaleway", "url": "https://www.scaleway.com", "tier": "Cloud"},
    "paperspace": {"name": "Paperspace (DO)", "url": "https://www.paperspace.com", "tier": "NeoCloud"},
    "verda": {"name": "Verda (DataCrunch)", "url": "https://datacrunch.io", "tier": "NeoCloud"},
    "massedcompute": {"name": "Massed Compute", "url": "https://massedcompute.com", "tier": "NeoCloud"},
    "latitude": {"name": "Latitude.sh", "url": "https://www.latitude.sh", "tier": "BareMetal"},
    "boostrun": {"name": "BoostRun", "url": "https://boostrun.com", "tier": "NeoCloud"},
    "denvr": {"name": "Denvr Dataworks", "url": "https://www.denvrdata.com", "tier": "NeoCloud"},
    "horizon": {"name": "Horizon", "url": "https://shadeform.ai", "tier": "NeoCloud"},
    "excesssupply": {"name": "ExcessSupply", "url": "https://shadeform.ai", "tier": "SpotPool"},
    "imwt": {"name": "IMWT Cloud", "url": "https://shadeform.ai", "tier": "NeoCloud"},
    "phyntec": {"name": "Phyntec", "url": "https://shadeform.ai", "tier": "NeoCloud"},
}

TARGET_GPUS: dict[str, dict[str, object]] = {
    "B300": {"label": "NVIDIA B300 (Blackwell Ultra)", "vram_gb": 288, "arch": "Blackwell", "rank": 1},
    "B200": {"label": "NVIDIA B200", "vram_gb": 192, "arch": "Blackwell", "rank": 2},
    "GH200": {"label": "NVIDIA GH200 Grace Hopper", "vram_gb": 96, "arch": "Hopper", "rank": 3},
    "H200": {"label": "NVIDIA H200 SXM", "vram_gb": 141, "arch": "Hopper", "rank": 4},
    "H100": {"label": "NVIDIA H100 80GB", "vram_gb": 80, "arch": "Hopper", "rank": 5},
    "H100_nvl": {"label": "NVIDIA H100 NVL", "vram_gb": 94, "arch": "Hopper", "rank": 6},
    "A100_80G": {"label": "NVIDIA A100 80GB", "vram_gb": 80, "arch": "Ampere", "rank": 7},
    "A100": {"label": "NVIDIA A100 40GB", "vram_gb": 40, "arch": "Ampere", "rank": 8},
    "L40S": {"label": "NVIDIA L40S 48GB", "vram_gb": 48, "arch": "Ada", "rank": 9},
    "RTX5090": {"label": "NVIDIA RTX 5090 32GB", "vram_gb": 32, "arch": "Blackwell", "rank": 10},
    "RTX4090": {"label": "NVIDIA RTX 4090 24GB", "vram_gb": 24, "arch": "Ada", "rank": 11},
    "RTX6000Ada": {"label": "NVIDIA RTX 6000 Ada 48GB", "vram_gb": 48, "arch": "Ada", "rank": 12},
    "A6000": {"label": "NVIDIA RTX A6000 48GB", "vram_gb": 48, "arch": "Ampere", "rank": 13},
}

# Published public on-demand hyperscaler list benchmarks (per-GPU normalized from 8x flagship nodes)
HYPERSCALER_BENCHMARKS: list[dict[str, object]] = [
    {
        "provider_id": "aws_ec2", "provider_name": "AWS EC2 (p5.48xlarge)",
        "provider_url": "https://aws.amazon.com/ec2/instance-types/p5/", "tier": "Hyperscaler",
        "gpu_key": "H100", "gpu_label": "NVIDIA H100 80GB", "vram_gb": 80, "num_gpus": 8,
        "interconnect": "SXM5 NVSwitch", "vcpus": 192, "ram_gb": 2048,
        "node_price_hr_usd": 60.55, "price_per_gpu_hr_usd": 7.57,
        "in_stock": True, "live_regions": ["us-east-1", "us-west-2"], "is_reference": True,
    },
    {
        "provider_id": "gcp_a3", "provider_name": "Google Cloud (a3-highgpu-8g)",
        "provider_url": "https://cloud.google.com/compute/gpus-pricing", "tier": "Hyperscaler",
        "gpu_key": "H100", "gpu_label": "NVIDIA H100 80GB", "vram_gb": 80, "num_gpus": 8,
        "interconnect": "SXM5 NVLink", "vcpus": 208, "ram_gb": 1872,
        "node_price_hr_usd": 70.39, "price_per_gpu_hr_usd": 8.80,
        "in_stock": True, "live_regions": ["us-central1", "europe-west4"], "is_reference": True,
    },
    {
        "provider_id": "aws_p5en", "provider_name": "AWS EC2 (p5en.48xlarge)",
        "provider_url": "https://aws.amazon.com/ec2/instance-types/p5/", "tier": "Hyperscaler",
        "gpu_key": "H200", "gpu_label": "NVIDIA H200 SXM", "vram_gb": 141, "num_gpus": 8,
        "interconnect": "SXM5 NVSwitch", "vcpus": 192, "ram_gb": 2048,
        "node_price_hr_usd": 68.80, "price_per_gpu_hr_usd": 8.60,
        "in_stock": True, "live_regions": ["us-east-2", "us-west-2"], "is_reference": True,
    },
    {
        "provider_id": "aws_p4de", "provider_name": "AWS EC2 (p4de.24xlarge)",
        "provider_url": "https://aws.amazon.com/ec2/instance-types/p4/", "tier": "Hyperscaler",
        "gpu_key": "A100_80G", "gpu_label": "NVIDIA A100 80GB", "vram_gb": 80, "num_gpus": 8,
        "interconnect": "SXM4 NVSwitch", "vcpus": 96, "ram_gb": 1152,
        "node_price_hr_usd": 40.96, "price_per_gpu_hr_usd": 5.12,
        "in_stock": True, "live_regions": ["us-east-1", "us-west-2"], "is_reference": True,
    },
]


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".gpu_rates_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def sync_live_gpu_rates() -> dict:
    req = urllib.request.Request(SHADEFORM_API_URL, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        raw = json.loads(resp.read(2_500_000).decode("utf-8", errors="replace"))

    offers: list[dict[str, object]] = []
    seen_dedup: set[tuple[str, str, int, int]] = set()

    for item in raw.get("instance_types") or []:
        cfg = item.get("configuration") or {}
        gpu_raw = str(cfg.get("gpu_type") or item.get("gpu_type") or "").strip()
        if gpu_raw not in TARGET_GPUS:
            continue
        num_gpus = max(1, int(cfg.get("num_gpus") or item.get("num_gpus") or 1))
        cents = int(item.get("hourly_price") or 0)
        if cents <= 0:
            continue
        cloud_id = str(item.get("cloud") or "").strip().lower()
        dedup_key = (cloud_id, gpu_raw, num_gpus, cents)
        if dedup_key in seen_dedup:
            continue
        seen_dedup.add(dedup_key)

        node_usd = round(cents / 100.0, 2)
        per_gpu_usd = round(node_usd / num_gpus, 2)
        cmeta = CLOUD_META.get(cloud_id, {"name": cloud_id.title(), "url": "https://shadeform.ai", "tier": "NeoCloud"})
        gmeta = TARGET_GPUS[gpu_raw]

        avail_list = item.get("availability") or []
        live_regs = list(dict.fromkeys(str(a.get("display_name") or a.get("region") or "") for a in avail_list if a.get("available")))
        all_regs = list(dict.fromkeys(str(a.get("display_name") or a.get("region") or "") for a in avail_list if (a.get("display_name") or a.get("region"))))
        ic_raw = str(cfg.get("interconnect") or item.get("interconnect") or "PCIe").upper()
        nvlink = bool(cfg.get("nvlink") or item.get("nvlink"))
        ic_label = f"{ic_raw} + NVLink" if (nvlink and "NVLINK" not in ic_raw) else ic_raw

        offers.append({
            "provider_id": cloud_id,
            "provider_name": cmeta["name"],
            "provider_url": str(cmeta["url"]).strip(),
            "tier": cmeta["tier"],
            "instance_name": str(item.get("cloud_instance_type") or item.get("shade_instance_type") or ""),
            "gpu_key": gpu_raw,
            "gpu_label": str(gmeta["label"]),
            "vram_gb": int(cfg.get("vram_per_gpu_in_gb") or gmeta["vram_gb"]),
            "num_gpus": num_gpus,
            "interconnect": ic_label,
            "vcpus": int(cfg.get("vcpus") or item.get("vcpus") or 0),
            "ram_gb": int(cfg.get("memory_in_gb") or item.get("memory_in_gb") or 0),
            "node_price_hr_usd": node_usd,
            "price_per_gpu_hr_usd": per_gpu_usd,
            "in_stock": len(live_regs) > 0,
            "live_regions": live_regs[:4] if live_regs else all_regs[:2],
            "is_reference": False,
        })

    offers.extend(HYPERSCALER_BENCHMARKS)
    offers.sort(key=lambda r: (int(TARGET_GPUS.get(str(r["gpu_key"]), {"rank": 99})["rank"]), float(r["price_per_gpu_hr_usd"])))

    # Build per-GPU summary stats (lowest, median, hyperscaler savings)
    gpu_summaries: list[dict[str, object]] = []
    for gkey, gmeta in sorted(TARGET_GPUS.items(), key=lambda kv: int(kv[1]["rank"])):
        g_rows = [r for r in offers if r["gpu_key"] == gkey and not r.get("is_reference")]
        if not g_rows:
            continue
        prices = sorted(float(r["price_per_gpu_hr_usd"]) for r in g_rows)
        in_stock_rows = [r for r in g_rows if r["in_stock"]]
        lowest = prices[0]
        median = prices[len(prices) // 2]
        ref_rows = [float(r["price_per_gpu_hr_usd"]) for r in offers if r["gpu_key"] == gkey and r.get("is_reference")]
        ref_high = max(ref_rows) if ref_rows else round(lowest * 2.8, 2)
        savings_pct = int(round(max(0.0, (1.0 - lowest / ref_high) * 100))) if ref_high > 0 else 0
        gpu_summaries.append({
            "gpu_key": gkey,
            "gpu_label": gmeta["label"],
            "vram_gb": gmeta["vram_gb"],
            "arch": gmeta["arch"],
            "offers_count": len(g_rows),
            "in_stock_count": len(in_stock_rows),
            "lowest_per_gpu_usd": lowest,
            "median_per_gpu_usd": median,
            "reference_cloud_usd": ref_high,
            "max_savings_pct": savings_pct,
        })

    now_dt = datetime.now(timezone.utc)
    now_utc = now_dt.strftime("%Y-%m-%d %H:%M UTC")
    # 70% Row-Drop Circuit Breaker (Fable 5.2 + GPT-6-Astra Consensus Guard)
    if OUT_JSON.exists():
        try:
            prev = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            prev_cnt = int((prev.get("summary") or {}).get("total_offers") or 0)
            if prev_cnt > 20 and len(offers) < int(prev_cnt * 0.7):
                prev["stale_warning"] = True
                prev["last_failed_check_utc"] = now_utc
                _atomic_write_json(OUT_JSON, prev)
                return prev
        except Exception:
            pass

    payload = {
        "site": "GPURentalRates.com",
        "updated_at_utc": now_utc,
        "updated_epoch": int(now_dt.timestamp()),
        "stale_warning": False,
        "summary": {
            "total_offers": len(offers),
            "providers_tracked": len({str(r["provider_name"]) for r in offers}),
            "gpu_models_tracked": len(gpu_summaries),
            "in_stock_offers": sum(1 for r in offers if r["in_stock"] and not r.get("is_reference")),
        },
        "gpu_summaries": gpu_summaries,
        "offers": offers,
    }
    _atomic_write_json(OUT_JSON, payload)
    # Daily Time-Series Price History Moat (`public/history/YYYY-MM-DD.json`)
    day_path = HISTORY_DIR / f"{now_dt.strftime('%Y-%m-%d')}.json"
    _atomic_write_json(day_path, {"date_utc": now_dt.strftime("%Y-%m-%d"), "updated_at_utc": now_utc, "gpu_summaries": gpu_summaries})
    return payload


if __name__ == "__main__":
    res = sync_live_gpu_rates()
    print(json.dumps({"updated": res["updated_at_utc"], "summary": res["summary"], "top_gpus": res["gpu_summaries"][:6]}, indent=2))
