# Project Overview

This project is organized around the postal customer-service domain. The goal was not just to build a chat page, but to connect data processing, knowledge retrieval, model adaptation, the web system, and model serving into one complete chain.

The two main lines are:

1. building a usable RAG workflow for postal knowledge,
2. adapting the model through LoRA fine-tuning.

The Django UI, APIs, inference serving, and load-balancing layer are not separate side pieces. They turn the RAG and LoRA work into an interactive system that can be tested, compared, and demonstrated.

At the engineering level, the project covers several complete paths:

1. filtering, cleaning, and organizing postal knowledge from customer-service data and public web materials,
2. turning that knowledge into a retrievable and traceable vector database with citations shown on the page,
3. adapting the model to the postal customer-service domain through LoRA,
4. using Django to connect sessions, streaming responses, citations, ticket JSON, and four-mode comparison,
5. serving model capability through vLLM, an A100 8-card machine, and nginx.

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

The project priority can be read very directly:

1. `RAG` is one core line.
2. `LoRA` is the other core line.
3. Django pages and serving layers mainly act as the demo and integration shell around them.

Main directory:

- `week3/`
