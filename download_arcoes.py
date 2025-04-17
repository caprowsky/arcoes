import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from tqdm import tqdm
import xml.etree.ElementTree as ET

# Configurazione
SITEMAPS = [
    "https://www.arcoes.it/sitemap.xml",
    "https://www.arcoes.it/blog-categories-sitemap.xml",
    "https://www.arcoes.it/blog-posts-sitemap.xml",
    "https://www.arcoes.it/pages-sitemap.xml"
]
BASE_URL = "https://www.arcoes.it"
OUTPUT_DIR = "arcoes_site"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; arcoes-downloader/1.0)"
}

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def get_urls_from_sitemap(sitemap_url):
    resp = requests.get(sitemap_url, headers=HEADERS)
    resp.raise_for_status()
    tree = ET.fromstring(resp.content)
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = [elem.text for elem in tree.findall('.//ns:loc', ns)]
    return urls

def sanitize_path(url):
    parsed = urlparse(url)
    path = parsed.path.lstrip('/')
    # Se path vuoto o termina con '/', salva come index.html nella directory
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
    else:
        # Se non ha estensione, aggiungi .html
        if not os.path.splitext(path)[1]:
            path = path + '.html'
    return os.path.join(OUTPUT_DIR, path)

def download_file(url, local_path):
    ensure_dir(os.path.dirname(local_path))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"Errore nel download {url}: {e}")
        return False

def make_local_link(url):
    """
    Trasforma un URL assoluto del sito in un path relativo locale per la navigazione offline.
    """
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        # Link esterno
        return url
    # Path locale relativo
    path = parsed.path.lstrip('/')
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
    else:
        # Se non ha estensione, aggiungi .html
        if not os.path.splitext(path)[1]:
            path = path + '.html'
    return path

def parse_and_download_resources(html_content, page_url, page_local_dir):
    soup = BeautifulSoup(html_content, 'lxml')
    tags_attrs = [
        ('img', 'src'),
        ('script', 'src'),
        ('link', 'href'),
        ('a', 'href'),
    ]
    resources = set()
    for tag, attr in tags_attrs:
        for el in soup.find_all(tag):
            src = el.get(attr)
            if src:
                abs_url = urljoin(page_url, src)
                if abs_url.startswith(BASE_URL):
                    resources.add(abs_url)
                # Modifica link interni
                if abs_url.startswith(BASE_URL):
                    local_link = make_local_link(abs_url)
                    el[attr] = os.path.relpath(local_link, os.path.dirname(sanitize_path(page_url)))
    # Scarica risorse statiche
    for res_url in resources:
        res_path = sanitize_path(res_url)
        if not os.path.exists(res_path):
            download_file(res_url, res_path)
    return soup

def main():
    print("Estrazione URL dalle sitemap...")
    all_urls = set()
    for sitemap in SITEMAPS:
        urls = get_urls_from_sitemap(sitemap)
        all_urls.update(urls)
    print(f"Trovati {len(all_urls)} URL da scaricare.")
    for url in tqdm(sorted(all_urls)):
        local_path = sanitize_path(url)
        if os.path.exists(local_path):
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            html = resp.content
            # Scarica risorse statiche e aggiorna i link
            soup = parse_and_download_resources(html, url, os.path.dirname(local_path))
            # Salva la pagina HTML modificata
            ensure_dir(os.path.dirname(local_path))
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
        except Exception as e:
            print(f"Errore scaricando {url}: {e}")

if __name__ == "__main__":
    main()
