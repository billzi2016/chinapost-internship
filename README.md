# ChinaPost Internship

This repository is a reconstructed and organized internship project for China Post customer-service data analysis, postal RAG assistance, local Qwen2.5 SFT experiments on Apple MLX, and automated transcription tooling.

> Note: this is a reconstructed historical internship project. Git commit timestamps represent the time when the files were reorganized into this repository, not the original development timeline. The original remote internship machine is no longer available, so this repository was rebuilt from the available materials and requirements.
>
> This repository is also a reconstructed project version. The `week1`, `week2`, `week3`, and later stage names reflect project sequencing only and do not correspond to real calendar weeks. Time spent on manual tuning, sample filtering, validation-dataset preparation, onboarding training, and internal meetings has already been removed from this staged view, so the week labels should be read strictly as task phases rather than any natural-week timeline.

Chinese documentation is available in [README_CN.md](README_CN.md).

Documentation site: <https://billzi2016.github.io/chinapost-internship/>

## Repository Structure

- `week1/`: postal customer-service data filtering, statistical analysis, keyword extraction, visualization, model selection notes, and classification boundary-case analysis.
- `week2/`: postal intelligent customer-service RAG system, including data organization and the Django application.
- `week3/`: Apple MLX LoRA fine-tuning workflow for Qwen2.5 3B / 7B Instruct models, with training-time regression evaluation and best-adapter retention.
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
- The formal data path is PostgreSQL + pgvector. Any local `db.sqlite3` file should be read as development residue rather than the intended system database.
- From an architecture perspective, the Django + PostgreSQL + pgvector layer is already suitable for internal or demo workloads at the scale of hundreds to around a thousand users. The main scaling pressure is model inference: local models need more work around vLLM instances, GPU resources, nginx / Ingress routing, and load balancing; external model APIs need stronger API security, access control, traffic walls, rate limiting, and failure fallback.

Supporting tools:

- Postman: API request debugging and validation.
- DBeaver: PostgreSQL inspection for conversations, messages, tickets, and vector tables.

## Week 2 UI Screenshot

![Django Week 2 UI](django_week2.png)

## Week 3

`week3` contains the local SFT workflow for postal customer-service model adaptation on Apple Silicon.

- `week3/PRD_Qwen2.5_MLX_LoRA微调方案.md`: product and technical plan for Qwen2.5 3B / 7B MLX LoRA fine-tuning.
- `week3/mlx_qwen_sft`: the reproducible MLX training project.
- Base models are `Qwen/Qwen2.5-3B-Instruct` and `Qwen/Qwen2.5-7B-Instruct`.
- The workflow uses `mlx-lm` LoRA configuration files, not CUDA or NVIDIA-specific tooling.
- Raw and generated training data, adapters, fused models, logs, evaluation outputs, and plots are excluded from git.

The Week 3 workflow includes scripted steps for:

- organizing raw SFT data into the MLX project layout;
- converting raw JSON into chat-style JSONL for `mlx-lm`;
- downloading C-Eval samples and generating postal-domain, format, and safety evaluation sets;
- running chunked LoRA training with regression checks during training;
- keeping only one best adapter under `adapters/best/<label>/`;
- stopping training when collapse gates are triggered;
- exporting evaluation summaries and JPG plots.

Main entry point:

- `week3/mlx_qwen_sft/README.md`

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

Week 3 MLX fine-tuning instructions are maintained in:

- `week3/mlx_qwen_sft/README.md`

After the Django service starts, Swagger / API documentation is available at:

- `http://127.0.0.1:9999/api/docs`

## Swagger Screenshot

![Week 2 Swagger API Docs](127.0.0.1_9999_api_docs_week2.png)
