# Project Overview

This project is organized around the postal customer-service domain, but the real core is not the page layer itself. The two main lines are:

1. building a usable RAG workflow for postal knowledge,
2. adapting the model through LoRA fine-tuning.

The Django UI, APIs, inference serving, and load-balancing layer all exist, but mainly as the system demo and integration layer around those two core tracks.

The project can still be read in three major phases.

## Phase 1: Data Filtering and Knowledge Preparation

This phase focused on filtering postal-domain conversations, analyzing samples, and organizing knowledge for later use.

Main directories:

- `week1/`
- `week1-module-Web-Crawler/`

## Phase 2: RAG Customer-Service System

This phase focused on connecting the knowledge base and the customer-service application into a usable RAG workflow with citation support.

Main directory:

- `week2/`

## Phase 3: Local LoRA Fine-Tuning

This phase focused on LoRA adaptation and inference integration for Qwen2.5 in the postal customer-service setting.

At the current documentation level, the project priority can be read very directly:

1. `RAG` is one core line.
2. `LoRA` is the other core line.
3. Django pages and serving layers mainly act as the demo and integration shell around them.

Main directory:

- `week3/`
