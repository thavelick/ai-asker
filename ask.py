#!/bin/python3
import argparse
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_question(model, question):
    for chunk in openai.ChatCompletion.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "you are a helpful assistant. If using backticks to delimit a programming or bash shell block, specify a language like '```python'"
            },
            {
                "role": "user",
                "content": question
            }
        ],
        stream=True
    ):
        if chunk["object"] == "chat.completion.chunk":
            content = chunk["choices"][0]["delta"].get("content", "")
            print(content, end='', flush=True)
    print()

def main():
    parser = argparse.ArgumentParser(description="Ask a question to ChatGPT")
    parser.add_argument("-m", "--model", default="gpt-3.5-turbo", help="The model to use (default: gpt-3.5-turbo)")
    parser.add_argument("question", help="The question to ask")
    args = parser.parse_args()

    ask_question(args.model, args.question)

if __name__ == "__main__":
    main()

