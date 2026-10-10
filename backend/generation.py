"""
FUNCTIONALITY: FPG orchestrator.
    1. computes recency scores & picks frontier words (DB - read)
    2. builds the prompt by calling llm.py
    3. calls segmentation & pinyin pipeline
    4. writes to passages table (DB - write)
"""
