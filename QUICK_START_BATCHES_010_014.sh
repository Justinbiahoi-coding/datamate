#!/bin/bash
# Quick start: Process batches 010-014

set -e

echo "════════════════════════════════════════════════════════════════"
echo " DataMate Batch Processing: 010-014 (125 questions)"
echo "════════════════════════════════════════════════════════════════"

# Check requirements
echo ""
echo "[CHECK] Requirements..."

if [ ! -f "code/process_batches_010_014_v2.py" ]; then
    echo "✗ Script not found: code/process_batches_010_014_v2.py"
    exit 1
fi
echo "✓ Processing script found"

if [ ! -f "batches_retry7/retry7_010.jsonl" ]; then
    echo "✗ Batch files not found in batches_retry7/"
    exit 1
fi
echo "✓ Batch files found (010-014)"

if [ ! -f "sub_sonnet.jsonl" ]; then
    echo "✗ Output file not found: sub_sonnet.jsonl"
    exit 1
fi
echo "✓ Output file exists (will append)"

# Check API key
echo ""
echo "[API KEY] Configuration..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "✗ ANTHROPIC_API_KEY not set"
    echo ""
    echo "  Please set: export ANTHROPIC_API_KEY=<your-key>"
    echo "  Then retry: ./QUICK_START_BATCHES_010_014.sh"
    exit 1
fi
echo "✓ ANTHROPIC_API_KEY is set"

if [ -z "$DATAMATE_LLM_BACKEND" ]; then
    echo "  DATAMATE_LLM_BACKEND not set, using default (anthropic)"
    export DATAMATE_LLM_BACKEND=anthropic
fi
echo "✓ Backend: $DATAMATE_LLM_BACKEND"

# Run test
echo ""
echo "[TEST] Validation pipeline..."
python3 code/test_processing_pipeline.py | tail -10

# Run processing
echo ""
echo "[PROCESSING] Starting batch 010-014 processing..."
echo "  Expected time: ~30 minutes (125 questions × 10-15s each)"
echo ""

python3 code/process_batches_010_014_v2.py

# Verify
echo ""
echo "[VERIFY] Checking results..."
TOTAL=$(wc -l < sub_sonnet.jsonl)
echo "✓ Total lines in sub_sonnet.jsonl: $TOTAL"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " Done! Results appended to sub_sonnet.jsonl"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next: python3 code/scorer.py --sub sub_sonnet.jsonl"

