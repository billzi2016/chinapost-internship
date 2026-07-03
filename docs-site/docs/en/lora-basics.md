# LoRA Basics

LoRA is one of the core methods behind the model-adaptation track in this project.

## What LoRA Does

LoRA does not retrain the whole base model. Instead, it adds a small low-rank parameter set on top of the existing model weights and trains that smaller set.

That means:

1. the original model mostly stays fixed,
2. only a much smaller parameter block is updated,
3. the adapter is used together with the base model at inference time.

## Why LoRA Fits This Project

The goal here is not to build a model from scratch. The goal is to adapt an existing model toward the postal customer-service domain.

That makes LoRA a practical fit because it keeps training lighter, cheaper, and easier to compare across multiple settings.

Full fine-tuning would raise memory cost, training cost, and experiment time without matching the real need of the task. Postal customer service mostly needs adaptation in answer format, service tone, intent understanding, and how the model organizes retrieved evidence. LoRA keeps that work in the adapter layer, which makes rank sweep experiments and rollback to a stable adapter much easier.

## Role in This Project

In this project, LoRA is not isolated. Together with RAG, it forms one of the two main capability tracks:

1. RAG provides external knowledge support.
2. LoRA improves domain expression, response style, and task fit.

## Why Rank Matters

One of the key LoRA hyperparameters is `rank`.

In simple terms, rank controls the capacity of the adapter. Smaller rank means fewer parameters. Larger rank means more adaptation space, but also a higher chance of instability or drift.

The current documentation keeps one stable summary:

1. `Qwen2.5-3B` -> `rank 2`
2. `Qwen2.5-7B` -> `rank 4`
