import requests
import pandas as pd
import os
from fpdf import FPDF


class ContentFetcher:
    def __init__(self, url, jina_endpoint="https://r.jina.ai/", headers={"Accept": "application/json"}):
        self.url = url
        self.jina_endpoint = jina_endpoint
        self.headers = headers

    def fetch_content(self):
        response = requests.get(f"{self.jina_endpoint}{self.url}", headers=self.headers)
        response.raise_for_status()
        content_json = response.json()
        return content_json.get('data', {}).get('content', None)


class KeywordClassifier:
    def __init__(self, api_key, keywords, model="llama-3-sonar-small-32k-online", base_url="https://api.perplexity.ai"):
        self.api_key = api_key
        self.keywords = keywords
        self.model = model
        self.base_url = base_url

    def classify_content(self, content):
        keyword_string = ", ".join(self.keywords)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an artificial intelligence assistant. Given an article and a list of keywords, "
                        "check if any of the keywords are present in the article. If any keyword is found, "
                        "save the article."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Article content: {content}\n\nKeywords: {keyword_string}",
                },
            ]
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }

        response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class ArticleSaver:
    @staticmethod
    def save_article(content, filepath="~/article_with_keywords.pdf"):
        save_path = os.path.expanduser(filepath)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        content = content.encode('latin-1', 'ignore').decode('latin-1')
        for line in content.split('\n'):
            pdf.multi_cell(0, 10, line)

        pdf.output(save_path)
        print(f"Article saved to {save_path}")


class ContentProcessor:
    def __init__(self, fetcher, classifier, saver):
        self.fetcher = fetcher
        self.classifier = classifier
        self.saver = saver

    def process_content(self):
        content = self.fetcher.fetch_content()
        if content:
            response_content = self.classifier.classify_content(content)
            if any(keyword in response_content for keyword in self.classifier.keywords):
                self.saver.save_article(content)
            else:
                print("No keywords found in the article.")
        else:
            print("Failed to fetch content.")


if __name__ == "__main__":
    url = "https://sci-hub.se/10.21608/ejvs.2024.278774.1959"
    keywords = ["transcription", "keyword2", "keyword3"]
    api_key = "your_api_key_here"

    fetcher = ContentFetcher(url)
    classifier = KeywordClassifier(api_key, keywords)
    saver = ArticleSaver()

    processor = ContentProcessor(fetcher, classifier, saver)
    processor.process_content()
