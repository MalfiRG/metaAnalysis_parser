import json
import pathlib
import logging
import pandas as pd
from habanero import Crossref
import time
import re
from typing import List, Dict, Any
import requests
import sqlite3
from Logger import Logger


class CrossrefRetriever:
    def __init__(self,
                 mailto: str,
                 request_interval: int = 1,
                 max_requests: int = 50,
                 db_file: str = 'articles.db',
                 max_articles: int = 50000,
                 cursor_max: int = 5000,
                 limit: int = 1000) -> None:
        """
        Initializes the CrossrefRetriever class.

        :param mailto: Email address for polite pool API usage.
        :param request_interval: Time in seconds to wait between API requests.
        :param max_requests: Maximum number of API requests per run.
        :param db_file: Name of the SQLite database file to save articles.
        :param max_articles: Maximum number of articles to retrieve.
        :param cursor_max: Maximum number of records to retrieve per API request.
        :param limit: Maximum number of records to retrieve per API request, default is 20; maximum is 1000.
        """
        self.cr = Crossref(mailto=mailto)
        self.request_interval = request_interval
        self.max_requests = max_requests
        self.db_file = db_file
        self.max_articles = max_articles
        self.cursor_max = cursor_max
        self.total_articles_retrieved = 0
        self.next_cursor = "*"
        self.limit = limit
        self.logger = Logger(name=__name__, log_file=f"{__name__}.log").get_logger()
        self._initialize_database()

    def _initialize_database(self) -> None:
        """
        Initializes the SQLite database and creates the articles table if it does not exist.
        """
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    title TEXT,
                    year INTEGER,
                    authors TEXT,
                    abstract TEXT,
                    full_text TEXT,
                    type TEXT,
                    doi TEXT PRIMARY KEY,
                    url TEXT,
                    language TEXT
                )
            ''')
            conn.commit()

    def retrieve_articles(self, keywords: str) -> List[Dict[str, Any]]:
        """
        Retrieves articles from Crossref based on the given keywords.

        :param keywords: Keywords for querying articles.
        :return: List of retrieved articles.
        """
        all_articles = []
        request_count = 0
        select_fields = "DOI,title,created,author,abstract,link,type,URL"

        while self.next_cursor and request_count < self.max_requests:
            try:
                response = self.cr.works(
                    query=keywords,
                    cursor=self.next_cursor,
                    cursor_max=self.cursor_max,
                    limit=self.limit,
                    progress_bar=True,
                    warn=True,
                    sort='published',
                    select=select_fields
                )
                for res in response if isinstance(response, list) else [response]:
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
                self.process_and_save_articles(all_articles)
            except Exception as e:
                self.logger.error(f"Error retrieving articles: {e}")
                break
        return all_articles

    def read_existing_articles(self) -> List[Dict[str, Any]]:
        """
        Reads existing articles from the SQLite database.

        :return: List of existing articles.
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                df_existing = pd.read_sql_query("SELECT * FROM articles", conn)
            return df_existing.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error reading from SQLite database: {e}")
            return []

    @staticmethod
    def remove_duplicates(new_articles: List[Dict[str, Any]],
                          existing_articles: List[Dict[str, Any]], logger: logging.Logger) -> List[Dict[str, Any]]:
        """
        Removes duplicates between new and existing articles.

        :param new_articles: List of new articles.
        :param existing_articles: List of existing articles.
        :return: List of unique articles.
        """
        try:
            df_new = pd.DataFrame(new_articles)
            df_existing = pd.DataFrame(existing_articles)
            combined_df = pd.concat([df_existing, df_new]).drop_duplicates(subset=['doi'], keep='first')
            # TODO fix the unique_articles variable and logger message
            unique_articles = combined_df[~combined_df['doi'].isin(df_existing['doi'])]  # Keep only new unique articles
            logger.info(f"Removed {len(new_articles) - len(unique_articles)} duplicates.")
            return unique_articles.to_dict('records')
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return new_articles

    @staticmethod
    def remove_html_tags(df: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
        """
        Removes HTML tags from the abstract field.

        :param df: DataFrame containing articles.
        :return: DataFrame with cleaned abstracts.
        """
        try:
            df['abstract'] = df['abstract'].apply(lambda x: re.sub('<[^<]+?>', '', x) if isinstance(x, str) else x)
            logger.info("HTML tags removed.")
            return df
        except Exception as e:
            logger.error(f"Error removing HTML tags: {e}")
            return df

    def save_to_database(self, articles: List[Dict[str, Any]]) -> None:
        """
        Saves articles to the SQLite database.

        :param articles: List of articles to save.
        """
        try:
            df_articles = pd.DataFrame(articles)
            with sqlite3.connect(self.db_file) as conn:
                df_articles.to_sql('articles', conn, if_exists='append', index=False)
            self.logger.info(f"Articles saved to {self.db_file}")
        except Exception as e:
            self.logger.error(f"Error saving articles to SQLite database: {e}")

    def process_and_save_articles(self, new_articles: List[Dict[str, Any]]) -> None:
        """
        Processes and saves new articles by removing duplicates and cleaning abstracts.

        :param new_articles: List of new articles.
        """
        if not new_articles:
            self.logger.info("No new articles to process.")
            return

        existing_articles = self.read_existing_articles()
        unique_articles = self.remove_duplicates(new_articles, existing_articles, self.logger)
        unique_articles_df = self.remove_html_tags(pd.DataFrame(unique_articles), self.logger)
        self.save_to_database(unique_articles_df.to_dict('records'))
        self.logger.info(f"Total articles retrieved in this run: {self.total_articles_retrieved}")

    @staticmethod
    def _extract_article_data(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts relevant data from an article item.

        :param item: Article item from the API response.
        :return: Dictionary with extracted article data.
        """
        authors = ', '.join([author.get('given', '') + ' ' + author.get('family', '') for author in item.get('author', [])])
        return {
            'title': item.get('title', [None])[0],
            'year': item.get('created', {}).get('date-parts', [[None]])[0][0],
            'authors': authors,
            'abstract': item.get('abstract', None),
            'full_text': item.get('link', [{'URL': None}])[0]['URL'] if 'link' in item else None,
            'type': item.get('type', None),
            'doi': item.get('DOI', None),
            'url': item.get('URL', None),
            'language': item.get('language', None)
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

    def retrieve_full_text(self, url: str) -> str:
        """
        Retrieves the full text from the given URL.

        :param url: URL to retrieve the full text from.
        :return: Full text content as a string.
        """
        try:
            with requests.Session() as session:
                response = session.get(url)
                response.raise_for_status()
                return response.text
        except requests.RequestException as e:
            self.logger.error(f"Error retrieving full text from {url}: {e}")
            return None


# Usage example
if __name__ == "__main__":
    """ Specify the parameters and keywords for the CrossrefRetriever. 
    If no parameters are specified, the default values will be used along with the specified ones.
    """

    config_path = pathlib.Path(__file__).parent.absolute() / "config.json"

    with open(config_path) as config_file:
        config = json.load(config_file)

    params = config['params']
    keywords = config['keywords']

    retriever = CrossrefRetriever(**params)
    new_articles = retriever.retrieve_articles(keywords)
