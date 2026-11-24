# ⚡ GPURentalRates.com — Live Cloud GPU Price & Stock Index

Live, normalized per-GPU hourly rates (`$/GPU/hr`), multi-node cluster cost calculator, and real-time datacenter stock across 22 NeoCloud, Bare-Metal, and Hyperscaler providers.

- **Live Web App**: [https://gpurentalrates.com](https://gpurentalrates.com)
- **Live JSON Feed**: [`/gpu_rates.json`](https://gpurentalrates.com/gpu_rates.json) (updated every 6 hours via GitHub Actions)
- **Daily Historical Snapshots**: `/history/YYYY-MM-DD.json` (multi-day floor & market median delta tracking)
- **Programmatic Architecture Sub-Indexes (`v5.0`)**: `/h100-rental-rates/`, `/h200-rental-rates/`, `/b200-rental-rates/`, `/a100-rental-rates/`, `/rtx-5090-rental-rates/`, `/b300-rental-rates/` (configured via `public/seo_targets.json` & built via `scripts/build_seo_pages.py`)

## Tracked Hardware
NVIDIA `B300`, `B200`, `H200`, `H100 (SXM5 / PCIe)`, `A100 (80GB / 40GB)`, `L40S`, `RTX 6000 Ada`, `RTX A6000`, `RTX 5090`, `RTX 4090`, and `RTX 3090`.
