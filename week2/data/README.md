# Data

This directory contains data moved from week 1 filter outputs:

- `week1/filter/outputs/embeddings` -> `week2/data/embeddings`
- `week1/filter/outputs/llm_filter` -> `week2/data/llm_filter`

## Offline Embedding Generation

Embedding generation is an offline data-preparation step. It should not run inside Django import commands.

Generate or resume the old CSDS dialogue embedding H5:

```bash
cd embedding_pipeline
python dialogue_embedding_store.py
```

Generate or resume the policy / FAQ embedding H5 from `dataset.jsonl`:

```bash
cd embedding_pipeline
python policy_embedding_store.py
```

Expected outputs:

```text
embeddings/dialogue_embeddings.h5
embeddings/dialogue_metadata.json
embeddings/policy_embeddings.h5
embeddings/policy_metadata.json
```
