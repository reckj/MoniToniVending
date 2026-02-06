---
created: 2026-02-06T15:30
title: Create local chatbot webapp for setup & maintenance help
area: tooling
files: []
---

## Problem

Operators deploying or maintaining the vending machine may have questions about setup procedures, configuration options, or troubleshooting. Currently there's no built-in help system. A local chatbot pretrained with machine context and instructions would provide on-demand assistance without requiring internet or external support.

## Solution

- Small webapp with chatbot interface for answering setup/maintenance questions
- Bot pretrained with machine-specific context and instructions (config options, hardware specs, troubleshooting steps)
- Runs locally on the Pi — only starts when launched (not a background service)
- Desktop icon on screen to launch it
- Could use a lightweight LLM or retrieval-augmented approach with local docs
- TBD: specific framework, model size constraints for Pi hardware
