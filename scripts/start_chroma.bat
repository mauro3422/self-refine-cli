@echo off
title ChromaDB Vector Server
color 0B

:: Ensure we are in project root
cd /d %~dp0..

echo ============================================
echo          CHROMADB SERVER
echo ============================================
echo.
echo Data Path: data/vector_memory_server
echo Port: 8100
echo.

:: Create data dir if missing
if not exist "data\vector_memory_server" mkdir "data\vector_memory_server"

echo Starting ChromaDB...
chroma run --path data/vector_memory_server --port 8100

pause
