# ChinaPost Internship

This repository is a reconstructed and organized internship project for China Post customer-service data analysis, postal RAG assistance, and automated transcription tooling.

> Note: this is a reconstructed historical internship project. Git commit timestamps represent the time when the files were reorganized into this repository, not the original development timeline. The original remote internship machine is no longer available, so this repository was rebuilt from the available materials and requirements.

Chinese documentation is available in [README_CN.md](README_CN.md).

## Repository Structure

- `week1/`: postal customer-service data filtering, statistical analysis, keyword extraction, visualization, model selection notes, and classification boundary-case analysis.
- `week2/`: postal intelligent customer-service RAG system, including data organization and the Django application.
- `Whisper-main/`: a batch transcription tool for public meetings and course recordings.

## Week 1

`week1` focuses on early-stage data processing and analysis for postal customer-service conversations.

- `week1/第一版`: initial filtering pipeline, keyword statistics, word clouds, clustering visualization, model selection notes, and risk-control documentation.
- `week1/第二版`: additional classification evaluation, boundary-case analysis, model-selection supplements, repository management notes, and visualization/label optimization records.
- The main goal is to identify postal-service-related conversations from broader customer-service data and prepare cleaner data for the Week 2 RAG system.

## Week 2

`week2` contains the postal intelligent customer-service RAG application.

- `week2/data`: raw data, filtered postal data, embedding artifacts, and SFT training-data placeholders.
- `week2/post-service-agent`: the formal Django project using Django, Django Ninja, SSE, PostgreSQL, pgvector, Ollama, and the standalone `post_ai` toolkit.
- The application supports conversation history, a ChatGPT-style chat panel, RAG citation display, ticket JSON generation, Markdown rendering, provider health indicators, and PostgreSQL + pgvector retrieval.
- The AI layer keeps both FAISS/local and PostgreSQL-pgvector/microservice modes for easier local debugging and production-style switching.

Supporting tools:

- Postman: API request debugging and validation.
- DBeaver: PostgreSQL inspection for conversations, messages, tickets, and vector tables.

## Week 2 UI Screenshot

![Django Week 2 UI](django_week2.png)

## Whisper-main

`Whisper-main` is a tool for batch automated accurate transcription of public meetings and course content. It supports audio/video inputs, subtitle generation, and transcription-result organization.

Runtime media outputs are intentionally excluded from git:

- `Whisper-main/media/`: audio/video input files.
- `Whisper-main/subtitles/`: generated subtitle outputs.

## Running The Project

Detailed startup, database migration, PostgreSQL, Ollama, and Django service instructions are maintained in:

- `week2/post-service-agent/README.md`
- `week2/post-service-agent/QUICKSTART.md`
- `week2/post-service-agent/docs/`

After the Django service starts, Swagger / API documentation is available at:

- `http://127.0.0.1:9999/api/docs`

## Swagger Screenshot

![Week 2 Swagger API Docs](127.0.0.1_9999_api_docs_week2.png)
