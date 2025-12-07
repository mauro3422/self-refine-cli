@echo off
title ChromaDB Vector Server
echo Starting ChromaDB Server on port 8100...
echo Data directory: outputs/vector_memory_server

mkdir outputs\vector_memory_server 2>nul

chroma run --path outputs/vector_memory_server --port 8100

pause
