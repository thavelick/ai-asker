#!/usr/bin/env python
import argparse
import os
import datetime
import subprocess
import tkinter as tk
from tkinter import ttk
from duckduckgo_search import DDGS
from openai import OpenAI
from sentence_transformers import SentenceTransformer, util

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatClient:
    def chat_stream(self):
        stream = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": f"{self.question} {self.prompt}"},
            ],
            stream=True,
            temperature=0.7,
            max_tokens=512,
        )
        for chunk in stream:
            yield chunk

    def __init__(self, model, question, prompt=""):
        self.model = model
        self.question = question
        self.prompt = prompt
        self.stream = self.chat_stream()

    def __iter__(self):
        return self

    def __next__(self):
        chunk = next(self.stream)
        if chunk.object == "chat.completion.chunk":
            content = chunk.choices[0].delta.content or ""
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
        classification = classify_query(self.chat_client.question)
        print(classification)

        if classification == "general-knowledge-llm":
            for content in self.chat_client:
                self.append_to_answer(content)
            print()
        elif classification == "general-internet-search":
            do_general_internet_search(
                self.chat_client.question, self.chat_client.model
            )
        elif classification == "image-search":
            do_image_search(self.chat_client.question)
        else:
            print("not implemented: ", classification)


def classify_query(query):
    engine_choices = [
        "general-knowledge-llm",
        # "wikipedia",
        "general-internet-search",
        "image-search",
        # "news-internet-search",
    ]
    classify_template = f"""
    <query>{query}</query>
    For the preceding query, don't answer but determine which of the following will provide the
    best answer to it from:
    [{", ".join(engine_choices)}].
    Output your answer inside <engine>...</engine> tags
    """
    chat_client = ChatClient("gpt-4o-mini", classify_template)

    classify_response = "".join(list(chat_client))

    # pull the engine choice from the tag in the response
    try:
        return classify_response.split("<engine>")[1].split("</engine>")[0]
    except IndexError:
        print(
            "Warning: Could not determine engine choice. Defaulting to general-knowledge-llm"
        )
        return "general-knowledge-llm"


def get_query_for_question(question):
    prompt = """
    <date>{date}</date>
    <query>{question}</query>
    For the preceding query, rewrite it as appropriate for use as a query on duck duck go. Don't
    just parrot the question, try to determine relevant search keywords. Remember boolean search
    doesn't work on search engines like DDG. Output in <search>...</search> tags
    """
    date = datetime.datetime.now().isoformat()
    chat_client = ChatClient("gpt-4o-mini", prompt.format(date=date, question=question))
    search_query_response = "".join(list(chat_client))
    return search_query_response.split("<search>")[1].split("</search>")[0]


def get_markdown_for_url(url, word_limit=1000):
    html2md_path = os.path.expanduser("~/go/bin/html2md")
    # First, let's make sure html2md_path exists
    assert os.path.exists(html2md_path)

    # Next, let's convert the URL to markdown
    text = subprocess.run(
        [html2md_path, "-i", url], capture_output=True, text=True
    ).stdout

    # Finally, let's limit the text to a certain number of words. If we cut off the output,
    # add ... to the end of the text
    words = text.split()
    if len(words) > word_limit:
        words = words[:word_limit]
        words.append("...")
    return " ".join(words)


def get_relevant_text_for_url(url, question):
    print("calculating relevant text for: ", url)
    full_text = get_markdown_for_url(url)
    chunk_size = 8000
    chunks = [
        full_text[i : i + chunk_size] for i in range(0, len(full_text), chunk_size)
    ]
    if len(chunks) < 1:
        return ""

    model = SentenceTransformer("all-MiniLM-L6-v2")
    question_embedding = model.encode([question])
    chunk_embeddings = model.encode(chunks)
    similarities = util.pytorch_cos_sim(question_embedding, chunk_embeddings)
    most_similar_chunk = chunks[similarities.argmax().item()]
    return most_similar_chunk


def do_image_search(question):
    query_for_question = get_query_for_question(question)
    print("image searching for: ", query_for_question)
    results = DDGS().images(query_for_question, max_results=3)

    for r in results:
        subprocess.run(["img2sixel", r["thumbnail"]])


def do_general_internet_search(question, model):
    query_for_question = get_query_for_question(question)
    print("searching for: ", query_for_question)
    results = DDGS().text(query_for_question, max_results=8)
    result_tempate = """
    <result>
        <title>{title}</title>
        <href>{href}</href>
        <full_text>
        {full_text}
        </full_text>
    </result>
    """
    result_text = "\n".join(
        [
            result_tempate.format(
                title=r["title"],
                href=r["href"],
                full_text=get_relevant_text_for_url(r["href"], question),
            )
            # reverse the order, so that the most relevant result will be at the bottom,
            # closest to the user's query
            for r in results  # [::-1]
        ]
    )

    prompt = f"""
    {result_text}
    <date>{datetime.datetime.now().isoformat()}</date>
    Given the search results above, {question}.

    Some of the results may not be relevant to the question, so you may need to ignore some of them.
    If multiple results are relevant, summarize them into a single coherent answer.
    Note that the user can't see the search results directly.
    """
    chat_client = ChatClient(model, prompt)
    for content in chat_client:
        print(content, end="")
    print()


def main():
    prompts = {
        "general": "",
        "explain": """ ***
        Write a footnote explaining preceding text. Things you could think about explaining are:
        * You know history, science and philosophy up to about 2020.
        * Thus you know and can explain historical figures, obscure science, companies etc.
        * Define any arcane vocabulary that appears, if present. (if there aren't any, just ignore this part)
        * Also translate any non-English phrases. (if there aren't any, just ignore this part)
        * Generally, help the user understand any context I need to make sense of the text.

        Not everything there is necessarily needed. For instance if there is no arcane vocabulary
        or non-english text, you shouldn't mention anything about those items
        """,
    }

    parser = argparse.ArgumentParser(description="Ask a question to ChatGPT")
    default_model = "gpt-4o-mini"
    parser.add_argument(
        "-m",
        "--model",
        default=default_model,
        help=f"The model to use (default: {default_model})",
    )
    parser.add_argument(
        "--gui", action="store_true", help="Show the answer in a GUI window"
    )
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--prompt", help="Which predefined prompt to use", default="general"
    )
    args = parser.parse_args()

    prompt = prompts.get(args.prompt, prompts["general"])
    chat_client = ChatClient(args.model, args.question, prompt)
    if args.gui:
        ui = GUI(args.question, chat_client)
    else:
        ui = TUI(chat_client)

    ui.run()


if __name__ == "__main__":
    main()
