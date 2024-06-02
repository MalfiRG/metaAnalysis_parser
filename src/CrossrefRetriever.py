import pandas as pd
from habanero import Crossref
import time
import re
from typing import List, Dict, Any

from Logger import Logger


# TODO Add tests
# TODO Expand error handling
# TODO Refactor to create asynchronous requests


class CrossrefRetriever:
    def __init__(self,
                 mailto: str,
                 request_interval: int = 1,
                 max_requests: int = 50,
                 excel_file: str = 'articles.xlsx',
                 max_articles: int = 50000,
                 cursor_max: int = 1000) -> None:
        """
        Initializes the CrossrefRetriever class.

        :param mailto: Email address for polite pool API usage.
        :param request_interval: Time in seconds to wait between API requests.
        :param max_requests: Maximum number of API requests per run.
        :param excel_file: Name of the Excel file to save articles.
        :param max_articles: Maximum number of articles to retrieve.
        :param cursor_max: Maximum number of records to retrieve per API request.
        """
        self.cr = Crossref(mailto=mailto)
        self.request_interval = request_interval
        self.max_requests = max_requests
        self.excel_file = excel_file
        self.max_articles = max_articles
        self.cursor_max = cursor_max
        self.total_articles_retrieved = 0
        self.next_cursor = "*"
        self.logger = Logger(name=__name__, log_file=f"{__name__}.log").get_logger()

    def retrieve_articles(self, keywords: str) -> List[Dict[str, Any]]:
        """
        Retrieves articles from Crossref based on the given keywords.

        :param keywords: Keywords for querying articles.
        :return: List of retrieved articles.
        """
        all_articles = []
        request_count = 0

        while self.next_cursor and request_count < self.max_requests:
            response = self.cr.works(query=keywords, cursor=self.next_cursor, cursor_max=self.cursor_max)
            for res in response:
                if self._is_valid_response(res):
                    items = res['message']['items']
                    for item in items:
                        all_articles.append(self._extract_article_data(item))
                    self.next_cursor = res['message'].get('next-cursor', None)
                    self.total_articles_retrieved += len(items)
                    request_count += 1
                    self._print_progress(request_count, len(items))
                    if self._has_reached_limit():
                        break
                    time.sleep(self.request_interval)  # Respect rate limits and polite pool practices
                else:
                    self.logger.error("Unexpected response structure.")
                    break
        return all_articles

    def read_existing_articles(self) -> List[Dict[str, Any]]:
        """
        Reads existing articles from the Excel file.

        :return: List of existing articles.
        """
        try:
            return pd.read_excel(self.excel_file).to_dict('records')
        except FileNotFoundError:
            self.logger.info("Excel file not found. Creating a new one.")
            return []

    @staticmethod
    def remove_duplicates(new_articles: List[Dict[str, Any]],
                          existing_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes duplicates between new and existing articles.

        :param new_articles: List of new articles.
        :param existing_articles: List of existing articles.
        :return: List of unique articles.
        """
        df_new = pd.DataFrame(new_articles)
        df_existing = pd.DataFrame(existing_articles)
        combined_df = pd.concat([df_existing, df_new]).drop_duplicates(subset=['title', 'year'], keep='first')
        return combined_df.to_dict('records')

    @staticmethod
    def remove_html_tags(df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes HTML tags from the abstract field.

        :param df: DataFrame containing articles.
        :return: DataFrame with cleaned abstracts.
        """
        df['abstract'] = df['abstract'].apply(lambda x: re.sub('<[^<]+?>', '', x) if isinstance(x, str) else x)
        return df

    def save_to_excel(self, articles: pd.DataFrame) -> None:
        """
        Saves articles to an Excel file.

        :param articles: List of articles to save.
        """
        pd.DataFrame(articles).to_excel(self.excel_file, index=False)

    def process_and_save_articles(self, new_articles: List[Dict[str, Any]]) -> None:
        """
        Processes and saves new articles by removing duplicates and cleaning abstracts.

        :param new_articles: List of new articles.
        """
        existing_articles = self.read_existing_articles()
        unique_articles = self.remove_duplicates(new_articles, existing_articles)
        unique_articles_df = self.remove_html_tags(pd.DataFrame(unique_articles))
        self.save_to_excel(unique_articles_df)
        self.logger.info(f"Total articles retrieved in this run: {self.total_articles_retrieved}")

    @staticmethod
    def _extract_article_data(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts relevant data from an article item.

        :param item: Article item from the API response.
        :return: Dictionary with extracted article data.
        """
        return {
            'title': item.get('title', [None])[0],
            'year': item.get('created', {}).get('date-parts', [[None]])[0][0],
            'abstract': item.get('abstract', None)
        }

    @staticmethod
    def _is_valid_response(res: Dict[str, Any]) -> bool:
        """
        Checks if the API response is valid.

        :param res: API response item.
        :return: True if valid, False otherwise.
        """
        return 'message' in res and 'items' in res['message']

    def _print_progress(self, request_count: int, items_count: int) -> None:
        """
        Prints the progress of API requests.

        :param request_count: Current request count.
        :param items_count: Number of items retrieved in the current request.
        """
        self.logger.info(
            f"Request {request_count}: Retrieved {items_count} records, total articles: {self.total_articles_retrieved}")

    def _has_reached_limit(self) -> bool:
        """
        Checks if the retrieval limit has been reached.

        :return: True if limit is reached, False otherwise.
        """
        return self.total_articles_retrieved >= self.max_articles


# Usage example
if __name__ == "__main__":
    params = {
        "mailto": ""***REMOVED***"",  # adjust to your email
        "request_interval": 1,
        "max_requests": 5,
        "cursor_max": 100,
    }
    # Adjust keywords as needed
    keywords = "climate+change+AND+CO2+emission+AND+global+warming+AND+planes"

    retriever = CrossrefRetriever(**params)
    new_articles = retriever.retrieve_articles(keywords)
    retriever.process_and_save_articles(new_articles)
