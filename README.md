# HIPAA PHI De-identification using Local LLMs

This repository contains the code implementation discussed in my dev.to article [De-identifying HIPAA PHI Using Local LLMs with Ollama](https://dev.to/b-d055/de-identifying-hipaa-phi-using-local-llms-with-ollama-38j3).

Note that all data provided is synthetic.

## Overview

This project demonstrates how to use local Large Language Models (LLMs) through Ollama to identify and remove Protected Health Information (PHI) from medical texts. The implementation runs entirely locally on consumer-grade hardware, ensuring data privacy and security.

## Requirements

- Python 3.10+
- Ollama installed locally
- Mistral model pulled in Ollama (`ollama pull mistral-small:24b`)
- Required Python packages: `requests`, `json`, `datetime`, `typing`

## Quick Start

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Add your text files to `patient_charts` directory
4. Run: `python main.py`

Processed files will be saved in the `outputs` directory.

## Note

This is a proof of concept. Always have qualified personnel review de-identified data before use in production.
