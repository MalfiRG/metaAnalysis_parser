import pandas as pd
from habanero import Crossref
import time
import re


class CrossrefRetriever:
    def __init__(self, mailto, request_interval=1, max_requests=50, excel_file='articles.xlsx', max_articles=50000,
                 cursor_max=1000):
        self.cr = Crossref(mailto=mailto)
        self.request_interval = request_interval
        self.max_requests = max_requests
        self.excel_file = excel_file
        self.max_articles = max_articles
        self.cursor_max = cursor_max
        self.total_articles_retrieved = 0
        self.next_cursor = "*"

    def retrieve_articles(self, keywords):
        all_articles = []
        request_count = 0

        while self.next_cursor and request_count < self.max_requests:
            response = self.cr.works(query=keywords, cursor=self.next_cursor, cursor_max=self.cursor_max)

            for res in response:
                if 'message' in res and 'items' in res['message']:
                    items = res['message']['items']

                    for item in items:
                        title = item.get('title', [None])[0]
                        year = item.get('created', {}).get('date-parts', [[None]])[0][0]
                        abstract = item.get('abstract', None)

                        all_articles.append({
                            'title': title,
                            'year': year,
                            'abstract': abstract
                        })

                    self.next_cursor = res['message'].get('next-cursor', None)
                    self.total_articles_retrieved += len(items)
                    request_count += 1
                    print(
                        f"Request {request_count}: Retrieved {len(items)} records, total articles:"
                        f" {self.total_articles_retrieved}")

                    if self.total_articles_retrieved >= self.max_articles:
                        print(
                            f"Total articles retrieved exceeds the limit of {self.max_articles}"
                            f". Adjust the cursor for next round.")
                        break

                    if request_count < self.max_requests:
                        time.sleep(self.request_interval)  # Respect rate limits and polite pool practices
                else:
                    print("Unexpected response structure.")
                    break

        return all_articles

    def read_existing_articles(self):
        try:
            df = pd.read_excel(self.excel_file)
            existing_articles = df.to_dict('records')
            return existing_articles
        except FileNotFoundError:
            return []

    @staticmethod
    def remove_duplicates(new_articles, existing_articles):
        df_new = pd.DataFrame(new_articles)
        df_existing = pd.DataFrame(existing_articles)

        combined_df = pd.concat([df_existing, df_new]).drop_duplicates(subset=['title', 'year'], keep='first')
        unique_articles = combined_df.to_dict('records')
        return unique_articles

    @staticmethod
    def remove_html_tags(df):
        df['abstract'] = df['abstract'].apply(lambda x: re.sub('<[^<]+?>', '', x) if isinstance(x, str) else x)
        return df

    def save_to_excel(self, articles):
        df = pd.DataFrame(articles)
        df.to_excel(self.excel_file, index=False)

    def process_and_save_articles(self, new_articles):
        existing_articles = self.read_existing_articles()
        unique_articles = self.remove_duplicates(new_articles, existing_articles)
        unique_articles_df = self.remove_html_tags(pd.DataFrame(unique_articles))
        try:
            # convert existing_articles to DataFrame
            existing_articles_df = pd.DataFrame(existing_articles)
            df = pd.concat([existing_articles_df, unique_articles_df])
        except FileNotFoundError:
            df = unique_articles_df
        self.save_to_excel(df)
        print(f"Total articles retrieved in this run: {self.total_articles_retrieved}")


# Usage example
if __name__ == "__main__":
    params = {
        "mailto": ""***REMOVED***"",
        "request_interval": 1,
        "max_requests": 5,
        "cursor_max": 100,
    }
    keywords = "climate+change+AND+CO2+emission+AND+global+warming+AND+planes"

    retriever = CrossrefRetriever(**params)
    new_articles = retriever.retrieve_articles(keywords)
    retriever.process_and_save_articles(new_articles)
