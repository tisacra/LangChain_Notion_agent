# HuggingFaceを使って挨拶するテスト
from langchain_huggingface import HuggingFacePipeline
from transformers import pipeline
from huggingface_hub import login
import os


HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if not HUGGINGFACE_TOKEN:
    raise ValueError("HUGGINGFACE_TOKEN is not set in .env file")


login(token=HUGGINGFACE_TOKEN)


# 要約専用パイプライン
summarizer = pipeline("summarization", model="google/gemma-3-27b-it")
local_summarizer = HuggingFacePipeline(pipeline=summarizer)

prompt = """
強化学習は、エージェントが報酬を最大化するために行動を学習するものです。
"""
summary = local_summarizer(prompt, max_length=2, min_length=1)
print(summary)
