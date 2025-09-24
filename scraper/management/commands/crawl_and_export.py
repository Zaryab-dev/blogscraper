from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
import pandas as pd
import os

class Command(BaseCommand):
    help = 'Crawl website and export extracted content to Excel'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Starting URL to crawl')
        parser.add_argument('--depth', type=int, default=2, help='Maximum crawl depth (default: 2)')
        parser.add_argument('--output', type=str, default='scraped_content.xlsx', help='Output Excel file (default: scraped_content.xlsx)')

    def handle(self, *args, **options):
        url = options['url']
        max_depth = options['depth']
        output_file = options['output']

        if not url.startswith(('http://', 'https://')):
            self.stdout.write(self.style.ERROR('Invalid URL. Please provide a valid URL starting with http:// or https://'))
            return

        self.stdout.write(f'Starting crawl of {url} with depth {max_depth}')

        crawled_data, links_found = self.crawl_website(url, max_depth)

        if not crawled_data:
            self.stdout.write(self.style.WARNING('No pages were successfully crawled.'))
            return

        # Create DataFrame
        df = pd.DataFrame(crawled_data)
        df.to_excel(output_file, index=False, engine='openpyxl')

        self.stdout.write(self.style.SUCCESS(f'Crawled {len(crawled_data)} pages, found {len(links_found)} unique links.'))
        self.stdout.write(f'Saved results to {os.path.abspath(output_file)}')

    def crawl_website(self, seed_url, max_depth):
        visited = set()
        to_visit = [(seed_url, 0)]
        results = []
        links_found = set()
        base_domain = urlparse(seed_url).netloc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            while to_visit and len(results) < 100:  # Limit to 100 pages
                current_url, depth = to_visit.pop(0)

                if current_url in visited or depth > max_depth:
                    continue

                visited.add(current_url)

                try:
                    page.goto(current_url, wait_until='domcontentloaded', timeout=30000)
                    html = page.content()
                    soup = BeautifulSoup(html, 'lxml')

                    # Extract data
                    title = self.extract_title(soup)
                    content = self.extract_content(soup)
                    word_count = len(content.split()) if content else 0

                    if content and word_count > 10:  # Only include pages with meaningful content
                        results.append({
                            'URL': current_url,
                            'Title': title,
                            'Content': content,
                            'Word Count': word_count
                        })

                    self.stdout.write(f'Crawling page {len(results)}/{len(visited)}: {current_url}')

                    # Find links
                    if depth < max_depth:
                        for link in soup.find_all('a', href=True):
                            href = link['href'].strip()
                            if href and not href.startswith(('#', 'mailto:', 'javascript:')):
                                full_url = urljoin(current_url, href)
                                parsed = urlparse(full_url)
                                if parsed.netloc == base_domain and full_url not in visited and full_url not in [u for u, d in to_visit]:
                                    to_visit.append((full_url, depth + 1))
                                    links_found.add(full_url)

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error crawling {current_url}: {str(e)}'))
                    continue

            browser.close()

        return results, links_found

    def extract_title(self, soup):
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)

        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)

        return 'No Title'

    def extract_content(self, soup):
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'sidebar', 'ads', 'noscript']):
            tag.decompose()

        # Try to find main content
        content_selectors = [
            'article', 'main',
            'div.content', 'div.post-content', 'div.entry-content', 'div.article-content',
            'div.blog-post', 'div.post', 'div.article'
        ]

        content_text = ''

        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                paragraphs = main_content.find_all('p')
                content_text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if content_text:
                    break

        # Fallback to body paragraphs if no main content found
        if not content_text:
            body = soup.find('body')
            if body:
                paragraphs = body.find_all('p')[:20]  # Limit to first 20 paragraphs
                content_text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        return content_text