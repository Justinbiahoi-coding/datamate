# Zalo AI DataMate Competition - Final Submission

## 1. Overview
This repository contains the official, high-performance, and offline-ready inference engine and training pipeline for the **Zalo AI DataMate** competition. Our solution is built upon a robust hybrid architecture combining a fine-tuned Qwen2.5-14B-Instruct model (running via vLLM with Tensor Parallelism across dual GPUs) with deterministic Python-based execution and optimized data caching to ensure maximum accuracy and lightning-fast inference speed within strict time limits.

---

## 2. System Architecture & Features
- **Inference Engine:** Powered by `vLLM` to maximize GPU utilization, leveraging PagedAttention and Tensor Parallelism (`tp=2`) optimized for a 2x RTX 5090 environment.
- **Offline Compliance:** Fully isolated design. All model weights (`Qwen3-14B`), dependencies, and local caches are pre-packaged inside the container with network access completely disabled (`--network none`).
- **Hybrid Data Processing:** Employs smart data caching to load enterprise financial records, calendars, and rulebooks into memory once, minimizing I/O latency during batch inference over 1000+ questions.
- **Reproducibility:** Includes a dedicated `training_code/` module containing the exact SFT/QLoRA scripts (powered by Unsloth) used for domain adaptation and fine-tuning.

---

## 3. Directory Structure
```text
/code/
├── Dockerfile              # Immutable container configuration
├── predict.sh              # Execution entry point for batch evaluation
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── models/
│   └── Qwen3-14B/          # Pre-downloaded offline model weights (~29.5GB)
├── training_code/          # Training pipeline & reproducibility assets
│   ├── README.md
│   ├── train.sh
│   └── src/
│       └── train_sft.py    # Unsloth QLoRA fine-tuning script
└── src/                    # Core inference logic
    ├── __init__.py
    ├── engine.py           # vLLM integration, caching, and reasoning router
    └── utils.py            # Helper modules for data parsing