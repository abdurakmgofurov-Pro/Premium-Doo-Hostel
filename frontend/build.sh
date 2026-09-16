#!/bin/sh
# Regenerates ../static/js/*.js from src/*.ts. Run this after editing any
# TypeScript source; the compiled output is committed to git so the Flask
# app works without a Node build step at deploy time.
set -e
cd "$(dirname "$0")"
npm install
npm run build
