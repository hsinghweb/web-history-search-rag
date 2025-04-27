# Web History Search Chrome Extension

This Chrome extension lets you index and semantically search your web browsing history with full user control and privacy.

## Features

- **Manual Indexing:** Only indexes a web page when you click the "Index Current Page" button in the extension popup. No automatic or background indexing.
- **Semantic Search:** Uses Ollama (nomic-embed-text) embeddings and FAISS vector store for fast, relevant search. All embedding is performed locally via Ollama—no cloud API calls.
- **Precise Highlighting:** When you click a search result, the extension opens the page, scrolls to the most relevant section, and highlights both the matching chunk and your search terms.
- **Privacy First:** No background monitoring. Only pages you explicitly choose are indexed. Excludes sensitive domains (e.g., Gmail, WhatsApp, Drive).
- **FastAPI Backend:** Handles embedding, indexing, and search. Runs locally for full control.

## Tech Stack

- **Frontend:** Chrome Extension (HTML, CSS, JavaScript)
- **Backend:** Python FastAPI
- **Embeddings:** Ollama (nomic-embed-text) local model
- **Vector Store:** FAISS

## Architecture (Backend)

- **Agent-based design**: Follows a perception-decision-action loop for robust, extensible processing.
- **Ollama for Embeddings**: All text embeddings (for both indexing and search) are generated using the local Ollama server (model: nomic-embed-text).
- **No Gemini dependency**: All references and logging now reflect Ollama usage.
- **Action Layer**: The agent never calls tools directly; instead, all tool calls are routed through an action layer (action.py), which wraps MCP tools (tools.py).
- **Privacy**: Gmail, WhatsApp, and other sensitive domains are explicitly excluded from indexing.

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com/) running locally (ensure the nomic-embed-text model is pulled)
- Chrome (for extension)

## Installation

### Backend Setup

1. Install Python 3.9+ and create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start Ollama locally: `ollama serve`
4. Pull the embedding model: `ollama pull nomic-embed-text`
5. Start the backend server:
   ```bash
   uvicorn server:app --reload
   ```

### Extension Setup

1. Go to `chrome://extensions` and enable Developer Mode.
2. Click "Load unpacked" and select the `web-history-extension/extension` folder.
3. Set the backend URL in the extension's settings if needed (default: `http://localhost:8000`).

## Usage

1. **Index a Page:**
   - Visit any web page you want to index.
   - Click the extension icon, then click "Index Current Page".
2. **Search:**
   - Enter your search query in the extension popup and press Enter.
   - Click a search result to open the page and highlight the most relevant section and your search terms.

## Privacy & Security

- No automatic or background indexing. Only pages you explicitly choose are indexed.
- Excluded domains ensure sensitive/private sites are never indexed.
- All data stays on your machine unless you configure otherwise.

## Development

- Backend code: `web-history-extension/backend`
- Extension code: `web-history-extension/extension`

---

For questions or issues, open an issue on GitHub or contact the maintainer.
