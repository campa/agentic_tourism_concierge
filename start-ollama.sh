#!/bin/bash
# Start Ollama server

# Default values (should match config.py)
MAIN_MODEL="${LLM_MODEL:-qwen3:8b}"
KV_CACHE_TYPE="${LLM_KV_CACHE_TYPE:-}"

# Parse command line args
while [[ $# -gt 0 ]]; do
    case $1 in
        --kv-cache)
            KV_CACHE_TYPE="$2"
            shift 2
            ;;
        --no-kv-cache)
            KV_CACHE_TYPE=""
            shift
            ;;
        --model)
            MAIN_MODEL="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 [--model MODEL] [--kv-cache q4_0|q8_0|f16] [--no-kv-cache]"
            exit 1
            ;;
    esac
done

echo "🚀 Starting Ollama..."
echo "   Model: $MAIN_MODEL"

# Set KV Cache Quantization if enabled (Qwen 3 optimization for Apple Silicon)
if [ -n "$KV_CACHE_TYPE" ]; then
    echo "   KV Cache: $KV_CACHE_TYPE"
    export OLLAMA_KV_CACHE_TYPE="$KV_CACHE_TYPE"
else
    echo "   KV Cache: default (f16)"
fi

echo ""

# Check if Ollama is already running
if lsof -i :11434 >/dev/null 2>&1; then
    echo "✅ Ollama server already running on port 11434"
    echo "📥 Ensuring model is available..."
    ollama pull "$MAIN_MODEL" 2>/dev/null || true
    echo ""
    echo "Ready to use."
    exit 0
fi

# Start server in background, then pull model
echo "▶️  Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
sleep 2

echo "📥 Ensuring model is available..."
ollama pull "$MAIN_MODEL" 2>/dev/null || true

echo ""
echo "✅ Ollama server running (PID: $OLLAMA_PID)"
echo "   Press Ctrl+C to stop"

# Wait for the server process
wait $OLLAMA_PID
