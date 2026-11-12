# Kaggle notebook/script: resume training session t2 from checkpoint-10 (see HANDOFF_TEAM.md section 5).
# Inputs: a Kaggle dataset containing the colab_t2 folder (sft_t2.jsonl, train_kaggle.py, out/checkpoint-10/).
# Settings: Accelerator = GPU T4 x2, Internet = On (account must be phone-verified). Run with "Save & Run All".
import glob, os, subprocess, sys, time

T0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "unsloth"], check=False)


def one(pattern):
    hits = glob.glob(pattern, recursive=True)
    assert len(hits) == 1, f"expected exactly one match for {pattern}, got {hits}"
    return hits[0]


data = one("/kaggle/input/**/sft_t2.jsonl")
script = one("/kaggle/input/**/train_kaggle.py")
ckpt = os.path.dirname(one("/kaggle/input/**/checkpoint-10/adapter_model.safetensors"))
print("DATA", data, "| SCRIPT", script, "| CKPT", ckpt, flush=True)

env = dict(os.environ, KERNEL_T0=str(T0), PYTHONUNBUFFERED="1",
           SFT_DATA_PATH=data, INIT_ADAPTER=ckpt, RESUME_CKPT=ckpt, OUTPUT_DIR="/kaggle/working/out",
           EPOCHS="1", LR="7e-5", LOG_STEPS="5", SAVE_STEPS="20", EVAL_STEPS="0",
           MAX_SEQ_LEN="12288", TIME_LIMIT_H="11")
rc = subprocess.run([sys.executable, script], env=env).returncode
print("exit code", rc, "| final adapter:",
      os.listdir("/kaggle/working/out/final_lora") if os.path.isdir("/kaggle/working/out/final_lora") else "missing",
      flush=True)
