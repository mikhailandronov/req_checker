# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ReqChecker is a multi-agent AI system powered by CrewAI for automated requirements analysis. The project analyzes requirement documents (RFPs, SOWs, technical specifications) against comprehensive question lists to ensure completeness before contractor selection. It's designed for Russian regulatory standards (ГОСТ, ФЗ 152) and business requirements.

## Development Commands

```bash
# Install dependencies (optional - uses uv for dependency management)
crewai install

# Run the crew (generates question lists for requirements analysis)
crewai run
# or
run_crew

# Other CLI commands
train    # Train the crew
replay   # Replay execution from task
test     # Test crew execution
```

## Running the Streamlit Interface

The project includes a Streamlit web interface for document analysis:

```bash
streamlit run src/req_checker/st_app.py
```

The web interface allows:
- Uploading requirement documents (.md, .txt, .docx)
- Managing question structures (upload JSON, generate with AI agents)
- Running RAG-based analysis to extract answers from documents
- Downloading markdown reports with findings

## Architecture

### Multi-Stage Agent Pipeline

The system uses a two-phase CrewAI agent architecture:

**Phase 1 - Methodology Crew** (`methodology_crew` in crew.py:138)
- `req_methodologist` agent: Generates comprehensive requirement aspects
- Uses SerperDevTool for web search
- Outputs Python list of dictionaries with aspect names and initial questions

**Phase 2 - Details Crew** (`req_details_crew` in crew.py:148)
- Dynamically creates expert agents per aspect (`req_expert` in crew.py:30)
- Each expert specializes in one requirement aspect
- `req_checklist_builder` agent: Consolidates all expert outputs
- Returns final question structure as Python list of dicts

### RAG Pipeline for Document Analysis

The Streamlit app (st_app.py) implements a retrieval-augmented generation pipeline:

1. **Document Processing** (st_app.py:77-149)
   - DOCX → Markdown conversion via pypandoc with temporary files
   - Markdown header-based text splitting (fallback to character splitting)
   - FAISS vector indexing with OpenAI embeddings

2. **Question-Answering** (st_app.py:152-194)
   - Iterates through question structure with progress tracking
   - Uses RetrievalQA chain for each question
   - Returns "Информация отсутствует" if answer not found

3. **Report Generation** (st_app.py:197-211)
   - Formats results as Markdown tables
   - Highlights missing information in red

## Configuration

Agents and tasks are defined in YAML files under `src/req_checker/config/`:
- `agents.yaml`: Agent configurations (roles, goals, backstories)
- `tasks.yaml`: Task definitions with expected outputs

All agent prompts and task descriptions are in Russian, focused on Russian regulatory standards.

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY`: OpenAI API key for LLM and embeddings
- Optional: Other API keys (Gemini, Tavily, Serper) depending on tools used

## Key Patterns

### Dynamic Agent Creation
Agents are created dynamically based on methodology crew output:
```python
for aspect_desc in aspects:
    expert = self.req_expert(aspect_questions=aspect_desc)
    task = self.req_details_task(aspect_questions=aspect_desc, agent=expert)
```

### Strict Output Parsing
Agents return Python dictionaries/lists as strings, parsed with `ast.literal_eval()`. Fallback to default questions if parsing fails.

### Streamlit Session State
Question structure managed in `st.session_state.current_questions_structure` to persist across UI interactions.

## File Structure

```
src/req_checker/
├── main.py          # CLI entry points (run, train, replay, test)
├── crew.py          # CrewAI agent and crew definitions
├── st_app.py        # Streamlit web interface with RAG pipeline
├── config/
│   ├── agents.yaml  # Agent role/goal/backstory configurations
│   └── tasks.yaml   # Task descriptions and expected outputs
└── tools/
    └── custom_tool.py  # Custom tool template
```

## Important Notes

- Python 3.10-3.13 required
- Uses UV for dependency management
- Pandoc must be installed for DOCX conversion
- All user-facing content is in Russian
- Default fallback question structure provided for robustness
