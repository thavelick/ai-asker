#!/bin/python3
import argparse
import os
import openai
import tkinter as tk
from tkinter import ttk

openai.api_key = os.getenv("OPENAI_API_KEY")


def ask_question(model, question):
    response = ""
    for chunk in openai.ChatCompletion.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "you are a helpful assistant. If using backticks to delimit a programming or bash shell block, specify a language like '```python'",
            },
            {"role": "user", "content": question},
        ],
        stream=True,
    ):
        if chunk["object"] == "chat.completion.chunk":
            content = chunk["choices"][0]["delta"].get("content", "")
            response += content
    return response


class GUI:
    def __init__(self, question, answer):
        self.answer = answer

        self.root = tk.Tk()
        self.root.configure(bg="white")  # Set window background to white
        self.root.title("AI Answer")

        # Set up a custom style for the frame background color
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

    def create_answer_text(self):
        # Create a Scrollbar widget
        scrollbar = tk.Scrollbar(self.frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add the 'yscrollcommand' argument to the Text widget and link it to the Scrollbar
        answer_text = tk.Text(
            self.frame,
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        answer_text.insert(tk.END, self.answer)
        answer_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        answer_text.config(state=tk.DISABLED)

        # Configure the Scrollbar to control the Text widget
        scrollbar.config(command=answer_text.yview)
        return answer_text

    def run(self):
        self.root.mainloop()


def show_gui(question, answer):
    gui = GUI(question, answer)
    gui.run()


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

    answer = ask_question(args.model, args.question)

    if args.gui:
        show_gui(args.question, answer)
    else:
        print(answer)


if __name__ == "__main__":
    main()
