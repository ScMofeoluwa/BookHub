import re

import requests
from bs4 import BeautifulSoup


def find_page(title):
    search_result = []
    req = requests.get(
        f"http://libgen.rs/search.php?&res=100&req={title}&phrase=1&view=simple&column=def&sort=def&sortmode=ASC&page=1"
    ).text

    soup = BeautifulSoup(req, "lxml")
    book_table = soup.find("table", class_="c")
    books = book_table.find_all("tr")[1:]
    for book in books:
        book = book.find_all("td")
        if book[8].text == "pdf" and book[6].text == "English":
            title = book[2].text.split(",")[0]
            search_result.append(
                {
                    "Link": book[10].a["href"],
                    "Size": book[7].text,
                    "Title": " ".join(title.split(" ")[:-1]),
                }
            )

    return len(search_result), search_result


def fetch_link(link):
    req = requests.get(link).text
    soup = BeautifulSoup(req, "lxml")
    link = soup.find("a")["href"]
    author = soup.find("br").find_next_sibling(text=True).strip()
    img = "libgen.gs" + soup.find("img")["src"]

    return link, author, img
