# Bundle B02: Gemma 2 2B / Qwen2.5-Coder 3B (Medium Static Analysis)

- **Parameter Count**: 2 Billion - 3 Billion
- **Target Tasks**: `syntax`, cyclomatic complexity analysis, rule validation
- **License Tier**: $15,000 / year (or $8,250 / 6 months)
- **Minimum VRAM**: 6 GB (or 8 GB System RAM for CPU quantized execution)
- **Recommended Hardware**: Developer workstations, lightweight CI servers

## Loading Instructions
Place weights in this directory:
```bash
models/b02_gemma2_2b_or_qwen3b/
  ├── model.bin (or .gguf / safetensors)
  └── config.json
```
