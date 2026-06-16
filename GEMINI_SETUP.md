# Gemini Setup

This project does not require a committed Gemini key.

If a local experiment needs Gemini, create a key in Google AI Studio and put it
only in `backend/.env`:

```env
GEMINI_API_KEY=replace-with-your-local-key
```

Do not commit API keys, tokens, or provider secrets.

The current Trady RAG flow is designed to run locally with Ollama,
faster-whisper, EasyOCR, FAISS, and local embedding models, so Gemini is not
required for normal local operation.
