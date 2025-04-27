# Web History Search Chrome Extension

This Chrome extension indexes and semantically searches your web browsing history using RAG (Retrieval-Augmented Generation) technology.

## Features

- Automatically indexes web pages you visit (excluding sensitive sites like Gmail, WhatsApp, etc.)
- Semantic search using Nomic embeddings and FAISS vector store
- Highlights relevant content when you open a search result
- Python FastAPI backend for processing and storing embeddings

## Tech Stack

- **Frontend**: Chrome Extension (HTML, CSS, JavaScript)
- **Backend**: Python FastAPI
- **Embeddings**: Nomic (via Ollama)
- **Vector Store**: FAISS
- **LLM**: Gemini Flash (for fallback embeddings)

## Installation

### Backend Setup

1. Install Python dependencies:

```bash
cd web-history-extension
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

3. Start the FastAPI server:

```bash
cd backend
uvicorn server:app --reload
```

### Chrome Extension Setup

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top-right corner)
3. Click "Load unpacked" and select the `extension` folder
4. The extension should now be installed and visible in your Chrome toolbar

## Usage

1. Browse the web as usual - the extension will automatically index pages you visit
2. Click on the extension icon to open the popup
3. Enter a search query and click "Search" or press Enter
4. Click on a search result to open the page with the relevant content highlighted

## API Endpoints

The backend provides the following API endpoints:

- `POST /index`: Index a webpage
- `POST /search`: Search for webpages matching a query
- `GET /stats`: Get indexing statistics
- `DELETE /clear`: Clear the entire index

## Development

### Backend Development

The FastAPI backend is located in the `backend` directory. The main file is `server.py`.

### Extension Development

The Chrome extension is located in the `extension` directory. The main files are:

- `manifest.json`: Extension configuration
- `popup.html/css/js`: Extension popup UI
- `background.js`: Background script for indexing pages
- `content.js`: Content script for extracting text and highlighting

## Notes

- The extension requires the backend server to be running
- Ensure Ollama is running locally with the Nomic model available
- If Ollama is not available, the system will fall back to Gemini embeddings

## Privacy

This extension only indexes the pages you visit and stores the data locally on your machine. No data is sent to external servers except for generating embeddings via Ollama or Gemini API.
