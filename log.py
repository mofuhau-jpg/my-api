# セル2: 解析用関数（そのまま貼って実行）
import requests, json, time, random, pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36"
}

def _get_soup(url, timeout=15):
    res = requests.get(url, headers=HEADERS, timeout=timeout)
    res.encoding = res.apparent_encoding  # 自動判定で正しい文字コードを設定
    return BeautifulSoup(res.text, "lxml")

def _parse_json_ld(soup):
    """ページ内のJSON-LDを探して辞書で返す（複数あれば先頭）"""
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            j = json.loads(s.string)
            if isinstance(j, list) and j:
                return j[0]
            return j
        except Exception:
            continue
    return None

def _meta_content(soup, *names):
    """metaタグで探す（property または name 属性）"""
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None

def _extract_author(jsonld, soup):
    # 1) JSON-LD
    if jsonld:
        a = jsonld.get("author") or jsonld.get("creator")
        if a:
            if isinstance(a, list):
                a = a[0]
            if isinstance(a, dict):
                return a.get("name") or a.get("@id") or None
            if isinstance(a, str):
                return a
    # 2) meta name=author
    m = _meta_content(soup, "author", "article:author")
    if m:
        return m
    # 3) bylineクラスなど
    by = soup.find(class_="byline") or soup.find(class_="author")
    if by:
        txt = by.get_text(strip=True)
        if txt:
            return txt
    return "不明"

def _extract_pubdate(jsonld, soup):
    # 1) JSON-LD datePublished
    if jsonld:
        for key in ("datePublished", "dateCreated", "uploadDate"):
            if key in jsonld:
                try:
                    dt = dateparser.parse(jsonld[key])
                    return dt.date().isoformat()
                except Exception:
                    return jsonld[key]
    # 2) meta property
    m = _meta_content(soup, "article:published_time", "date", "pubdate", "publishdate")
    if m:
        try:
            dt = dateparser.parse(m)
            return dt.date().isoformat()
        except Exception:
            return m
    # 3) <time datetime="...">
    t = soup.find("time")
    if t and t.get("datetime"):
        try:
            dt = dateparser.parse(t["datetime"])
            return dt.date().isoformat()
        except Exception:
            return t["datetime"]
    return "n.d"

def _extract_title(jsonld, soup, url):
    # 1) JSON-LD headline
    if jsonld:
        for key in ("headline","name","title"):
            if key in jsonld:
                return jsonld[key]
    # 2) og:title / twitter:title / title tag
    for key in ("og:title", "twitter:title"):
        m = _meta_content(soup, key)
        if m:
            return m
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # fallback: domain
    return urlparse(url).netloc

def _extract_site_name(jsonld, soup, url):
    # og:site_name or JSON-LD publisher.name or domain
    s = _meta_content(soup, "og:site_name")
    if s:
        return s
    if jsonld:
        pub = jsonld.get("publisher")
        if isinstance(pub, dict):
            return pub.get("name") or urlparse(url).netloc
    return urlparse(url).netloc

def extract_metadata(url, parse_delay=(1.0, 2.0)):
    """
    url -> dict: author, pub_date, title, site_name, url, access_date, citation
    """
    try:
        soup = _get_soup(url)
    except Exception as e:
        return {
            "author": "不明",
            "pub_date": "不明",
            "title": f"取得失敗: {e}",
            "site_name": urlparse(url).netloc,
            "url": url,
            "access_date": datetime.now().strftime("%Y-%m-%d"),
            "citation": f"不明 (不明). 「取得失敗: {e}」. 『{urlparse(url).netloc}』. {url} (取得・閲覧 {datetime.now().strftime('%Y-%m-%d')})"
        }
    jsonld = _parse_json_ld(soup)
    author = _extract_author(jsonld, soup)
    pub_date = _extract_pubdate(jsonld, soup)
    title = _extract_title(jsonld, soup, url)
    site_name = _extract_site_name(jsonld, soup, url)
    access_date = datetime.now().strftime("%Y-%m-%d")

    citation = f"{author} ({pub_date}). 「{title}」. 『{site_name}』. {url} (取得・閲覧 {access_date})"
    # polite delay
    time.sleep(random.uniform(*parse_delay))
    return {
        "author": author,
        "pub_date": pub_date,
        "title": title,
        "site_name": site_name,
        "url": url,
        "access_date": access_date,
        "citation": citation
    }


# セル3: ここに解析したいURLを直接書いて実行する例
urls = [
    "https://open-shelf.appspot.com/AnimalFarm/chapter1.html"

]

rows = []
for u in urls:
    print("処理中:", u)
    meta = extract_metadata(u)
    print(meta["citation"])   # ターミナルに出力
    rows.append(meta)

# log.py の最後に追加
def generate_reference(url):
    """URLから参考文献情報を取得して辞書で返す"""
    meta = extract_metadata(url)
    return meta