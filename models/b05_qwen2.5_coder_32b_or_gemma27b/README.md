# Bundle B05: Qwen2.5-Coder 32B / Gemma 2 27B (Heavyweight HFT & Defense Tier)

- **Parameter Count**: 27 Billion - 32 Billion
- **Target Tasks**: `auto_remediation`, deep code synthesis, high-assurance security audit
- **License Tier**: $75,000 / year (or $41,250 / 6 months) — **Heavyweight Defense & HFT Tier**
- **Minimum VRAM**: 64 GB - 80 GB (NVIDIA A100-80GB, H100, or multi-GPU cluster)
- **Recommended Hardware**: Dedicated air-gapped GPU rack or secure sovereign cloud enclave

## Capability Overview
The premier 32B tier provides maximal reasoning depth, capable of generating complex multi-step security patches, verifying formal specifications, and performing autonomous bug remediation with high precision.

## Loading Instructions
Place model weights here:
```bash
models/b05_qwen2.5_coder_32b_or_gemma27b/
  ├── model.bin (or .safetensors / .gguf)
  └── config.json
```
