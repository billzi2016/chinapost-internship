# SFT Basics

SFT is the other core training concept behind the model-adaptation side of this project.

## What SFT Means

SFT stands for Supervised Fine-Tuning.

The idea is straightforward:

1. prepare paired input and target-output examples,
2. train the model on those examples,
3. move the model closer to the target domain and output style.

## Why This Project Uses SFT

The base model already has general instruction-following ability, but it is not automatically aligned with postal customer-service language, boundaries, or task formats.

SFT is used here to make the model:

1. sound closer to a postal customer-service assistant,
2. respond better on postal-domain tasks,
3. keep output structure more stable for the project workflow.

## Relationship Between SFT and RAG

In this project, SFT and RAG are not substitutes.

They solve different parts of the problem:

1. SFT makes the model behave more like the target assistant.
2. RAG gives the model external knowledge support at answer time.

## Current Project Training Path

In the current reconstructed version, the SFT path is mainly organized through Apple MLX and LoRA.

That means:

1. the training objective is SFT,
2. the main parameter-update method is LoRA.

