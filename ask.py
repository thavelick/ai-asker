#!/bin/python3
import argparse
import os
import tkinter as tk
from tkinter import ttk

import openai


openai.api_key = os.getenv("OPENAI_API_KEY")


class ChatClient:
    @staticmethod
    def chat_stream(model, question):
        for chunk in openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """you are a helpful assistant. If using backtick to delimit a programming or bash shell block, specify a language like '```python'""",
                },
                {"role": "user", "content": question},
            ],
            stream=True,
        ):
            yield chunk

    def __init__(self, model, question):
        self.model = model
        self.question = question
        self.stream = self.chat_stream(self.model, self.question)

    def __iter__(self):
        return self

    def __next__(self):
        chunk = next(self.stream)
        if chunk["object"] == "chat.completion.chunk":
            content = chunk["choices"][0]["delta"].get("content", "")
            return content
        else:
            return next(self)


class GUI:
    def __init__(self, question, chat_client):
        self.root = tk.Tk()
        self.root.configure(bg="white")
        self.root.title("AI Answer")
        self.chat_client = chat_client

        style = ttk.Style()
        style.configure("Custom.TFrame", background="white")
        self.frame = ttk.Frame(self.root, padding="10", style="Custom.TFrame")
        self.frame.pack(fill=tk.BOTH, expand=True)

        question_label = ttk.Label(
            self.frame,
            text="Question: " + question,
            wraplength=300,
            background="white",
        )
        question_label.pack(fill=tk.X, pady=(0, 10))

        self.answer_text = self.create_answer_text()

    def process_next_chunk(self):
        try:
            content = next(self.chat_client)
            self.append_to_answer(content)
        except StopIteration:
            return

        self.root.after(100, self.process_next_chunk)

    def append_to_answer(self, content):
        self.update_ui(self.answer_text.config, state=tk.NORMAL)
        self.update_ui(self.answer_text.insert, tk.END, content)
        self.update_ui(self.answer_text.config, state=tk.DISABLED)

    def update_ui(self, func, *args, **kwargs):
        self.root.after(0, lambda: func(*args, **kwargs))

    def create_answer_text(self):
        scrollbar = tk.Scrollbar(self.frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        answer_text = tk.Text(
            self.frame,
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        # answer_text.insert(tk.END, self.answer)
        answer_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        answer_text.config(state=tk.DISABLED)

        scrollbar.config(command=answer_text.yview)
        return answer_text

    def run(self):
        self.process_next_chunk()
        self.root.mainloop()


class TUI:
    def __init__(self, chat_client):
        self.chat_client = chat_client

    def append_to_answer(self, content):
        print(content, end="")

    def run(self):
        for content in self.chat_client:
            self.append_to_answer(content)
        print()


def main():
    parser = argparse.ArgumentParser(description="Ask a question to ChatGPT")
    parser.add_argument(
        "-m",
        "--model",
        default="gpt-3.5-turbo",
        help="The model to use (default: gpt-3.5-turbo)",
    )
    parser.add_argument(
        "--gui", action="store_true", help="Show the answer in a GUI window"
    )
    parser.add_argument("question", help="The question to ask")
    args = parser.parse_args()

    chat_client = ChatClient(args.model, args.question)
    if args.gui:
        ui = GUI(args.question, chat_client)
    else:
        ui = TUI(chat_client)

    ui.run()


if __name__ == "__main__":
    main()
