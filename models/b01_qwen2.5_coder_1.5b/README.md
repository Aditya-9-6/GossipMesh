# Bundle B01: Qwen2.5-Coder 1.5B (Syntax & Lint Specialist)

- **Parameter Count**: 1.5 Billion
- **Target Tasks**: `syntax` checking, code formatting analysis, AST-level validation
- **License Tier**: $10,000 / year (or $5,500 / 6 months)
- **Minimum VRAM**: 4 GB (CPU-only runnable with GGUF Q4_K_M)
- **Recommended Hardware**: Any commodity x86_64 / ARM64 workstation, laptop, or cloud runner

## Loading Instructions
Place HuggingFace weights or GGUF files in this directory:
```bash
# Example layout:
models/b01_qwen2.5_coder_1.5b/
  ├── model.bin (or .gguf / safetensors)
  └── config.json
```
