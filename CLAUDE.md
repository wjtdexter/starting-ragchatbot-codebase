# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Preferences

**IMPORTANT**: When working in this project, **ALWAYS communicate in Chinese (中文)** with the user. All explanations, responses, and interactions should be in Chinese unless the user specifically requests otherwise.

## Repository Status

This is a RAG (Retrieval-Augmented Generation) system for querying educational course materials. The application uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.

### Important: Always Use uv

**CRITICAL**: This project uses `uv` as the Python package manager.

**ALWAYS use `uv` for ALL Python package management:**
- **Install dependencies**: `uv sync`
- **Run any Python script**: `uv run <script>` or `uv run <module>`
- **Add new dependencies**: `uv add <package>` (NEVER use `pip install`)
- **Remove dependencies**: `uv remove <package>` (NEVER use `pip uninstall`)
- **Update dependencies**: `uv sync` will update to latest compatible versions

**NEVER use pip, pip3, or python -m pip directly.** All dependency management MUST go through uv.

### Development Commands

- **Run development server**: `./run.sh` or `cd backend && uv run uvicorn app:app --reload --port 8000`
- **Access application**: http://localhost:8000 (web interface) or http://localhost:8000/docs (API docs)

### Architecture Overview

The system is a full-stack web application with a modular backend architecture:

**Backend Structure (`backend/`):**
- `app.py` - FastAPI main application with endpoints for chat, course listing, and document upload
- `rag_system.py` - Core `RAGSystem` orchestrator class that coordinates all components
- `document_processor.py` - `DocumentProcessor` class for parsing course documents and chunking text
- `vector_store.py` - `VectorStore` class wrapping ChromaDB for semantic search operations
- `ai_generator.py` - `AIGenerator` class managing Anthropic Claude API with tool-based search
- `search_tools.py` - Tool definitions (`CourseSearchTool`) that enable AI to search course content
- `session_manager.py` - `SessionManager` class for conversation history (max 2 exchanges)
- `models.py` - Pydantic data models (Course, Lesson, CourseChunk)
- `config.py` - Configuration constants (chunk size, models, limits)

**Frontend (`frontend/`):**
- Static HTML/CSS/JavaScript files served directly by FastAPI
- No build process required

**Data Flow:**
1. Document ingestion: `DocumentProcessor` parses docs → chunks text (800 chars, 100 overlap) → `VectorStore` stores in ChromaDB
2. Query processing: User query → `AIGenerator` → uses `CourseSearchTool` → `VectorStore` semantic search → returns relevant chunks
3. Response: Claude synthesizes search results with source attribution

**ChromaDB Collections:**
- `course_catalog` - Course metadata (titles, instructors, links)
- `course_content` - Vector embeddings of course content chunks

**Tool-Based Architecture:**
The AI generator uses Anthropic's tool-calling API. When users ask questions, Claude decides whether to:
- Search course content by semantic similarity
- Filter by specific course/lesson
- Use general knowledge for non-course questions

### Document Format Requirements

Course documents in `docs/` must follow this structure:
```
Course Title: [Name]
Course Link: [URL]
Course Instructor: [Instructor Name]

Lesson 1: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]

Lesson 2: [Lesson Title]
...
```

The `DocumentProcessor` extracts metadata, chunks content by lesson, and preserves course/lesson context in each chunk for better search results.

### Configuration Parameters

Key settings in `config.py`:
- `CHUNK_SIZE = 800` - Text chunk size in characters
- `CHUNK_OVERLAP = 100` - Overlap between chunks
- `MAX_RESULTS = 5` - Search results returned
- `MAX_HISTORY = 2` - Conversation exchanges retained
- `EMBEDDING_MODEL = "all-MiniLM-L6-v2"` - Sentence transformer model
- `ANTHROPIC_MODEL = "claude-sonnet-4-20250514"` - AI model version
