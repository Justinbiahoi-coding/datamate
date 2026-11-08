# Processing Batches 010-014 (125 Questions)

## Status
✅ **All infrastructure ready. Awaiting ANTHROPIC_API_KEY.**

## What's Been Done
1. ✅ Created processing script: `code/process_batches_010_014_v2.py`
2. ✅ Validation pipeline tested and working
3. ✅ Confirmed all 125 questions in batches ready for processing
4. ✅ No overlap with existing 2319 IDs in sub_sonnet.jsonl

## Batch Composition
- **Batches**: retry7_010.jsonl through retry7_014.jsonl
- **Total Questions**: 125
- **Answer Type**: 100% number-type answers
- **Gold Answers**: All embedded in batch files

## Processing Checklist

### Setup Required
```bash
export DATAMATE_LLM_BACKEND=anthropic
export ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

### Run Processing
```bash
python3 code/process_batches_010_014_v2.py
```

### Expected Output
- Appends to `sub_sonnet.jsonl`
- Each record includes:
  - Standard fields: `id`, `type`, `answer`
  - Internal fields: `_code` (generated Python), `_attempts`, `_verdict`
  - Validation: `_verdict` = `correct|wrong|abstain`

### Processing Time Estimate
- 125 questions × ~10-15s per question = ~30 minutes
- Uses Claude API for code generation + pandas execution

## Script Features

✅ **Resume Support**: Skips IDs already in sub_sonnet.jsonl  
✅ **Validation**: Tests against gold answers with proper matching  
✅ **Error Handling**: Graceful fallback to "abstain" on errors  
✅ **Progress Tracking**: Updates every 5 questions with ETA  
✅ **Accurate Scoring**: Uses same match_answer() logic as official scorer  

## Validation Details

Number answers are validated with:
- Type checking (must be "number")
- Value checking (within ±1 tolerance)
- Proper error handling for parsing

Example:
- Gold answer: 1,415,027,700
- Will match predicted: 1415027700 or 1415027701 ✅
- Will NOT match: 1415027702 ❌

## Integration with Training Pipeline

Results append to `sub_sonnet.jsonl` which can then be:
1. Scored locally: `python3 code/scorer.py --sub sub_sonnet.jsonl`
2. Merged with other backends for consensus
3. Converted to SFT data: `python3 code/make_sft.py --from-submission`
4. Used for fine-tuning

## Files Modified/Created
- `code/process_batches_010_014_v2.py` - Main processing script (production-ready)
- `code/test_processing_pipeline.py` - Validation test suite
- `BATCHES_010_014_PROCESSING.md` - This documentation

## Next Steps
1. Provide ANTHROPIC_API_KEY
2. Run: `python3 code/process_batches_010_014_v2.py`
3. Monitor output
4. Score results: `python3 code/scorer.py --sub sub_sonnet.jsonl`

