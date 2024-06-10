
# Keyword-Based CrossRef Articles Scraper for Meta-Analysis Creation

## Description

This project is a keyword-based scraper for articles, designed to aid in meta-analysis creation. It is adapted from the [Habanero Project](https://github.com/sckott/habanero).

### What Does This Mean?

There are numerous software solutions that allow you to search for articles based on provided keywords. High-quality solutions often become monetized. 

Why not create your own FREE solution that does the same thing? Think of it as "the Robin Hood" of article searchers.

The main goal of this project is to provide a tool for researchers to create a meta-analysis of articles, helping them effectively filter articles based on specified keywords.

### Project Structure

This project contains Python code that scrapes articles using the CrossRef API and stores them in a database. Articles are searched based on keywords provided in the `config.json` file.

You can access the database using DB Browser for SQLite or any other tool you prefer. This allows you to filter the clutter, select articles matching your criteria, and pass the results to another parsing engine for further analysis, such as deep learning analysis of abstracts based on inclusion criteria.

## Getting Started

These instructions will help you set up the project on your local machine for development and testing purposes.

### Prerequisites

You need Python 3.8 or later to run this project. Check your Python version by running:

```bash
python --version
```

### Setting Up a Virtual Environment

To create a virtual environment, navigate to the project directory and run:

```bash
python -m venv .venv
```

This will create a new virtual environment in a folder named `.venv`. To activate the virtual environment, run:

- On Windows:
    ```bash
    .venv\Scripts\activate
    ```

- On Unix or macOS:
    ```bash
    source .venv/bin/activate
    ```

You should now see `(.venv)` at the beginning of your command line prompt, indicating that you are working inside the virtual environment.

### Installing Dependencies

The project dependencies are listed in the `requirements.txt` file. To install these dependencies, run:

```bash
pip install -r requirements.txt
```

### Running the Project

The `CrossrefRetriever.py` file contains the main code for the project. Follow these steps to run it:

1. Open the `config.json` file and provide your email address under the "mailto" key. This will position you better to get data from the CrossRef API, as you will be assigned to the "polite pool" of users.
2. Provide your keywords under the "keywords" key. These will be used to search for articles in the CrossRef database.
3. Navigate to the project directory and run `CrossrefRetriever.py`:

```bash
python CrossrefRetriever.py
```
