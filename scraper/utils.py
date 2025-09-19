import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re
from urllib.parse import urljoin, urlparse
import time

class WebScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def is_dynamic_site(self, url):
        """Check if site likely needs JavaScript rendering"""
        dynamic_indicators = ['medium.com', 'substack.com', 'dev.to', 'twitter.com', 'facebook.com']
        domain = urlparse(url).netloc.lower()
        return any(indicator in domain for indicator in dynamic_indicators)

    def fetch_html_requests(self, url):
        """Fetch HTML using requests for static sites"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to fetch with requests: {str(e)}")

    def fetch_html_playwright(self, url):
        """Fetch HTML using Playwright for dynamic sites"""
        try:
            # Create page with stealth options
            page = self.browser.new_page(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )

            # Set additional headers to appear more like a real browser
            page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait for main content to load - try multiple selectors
            content_selectors = ['article', 'main', '[data-testid="post-content"]', '.post-content', '.entry-content', '.article-body']
            content_found = False
            for selector in content_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    content_found = True
                    break
                except:
                    continue

            if not content_found:
                # Just wait for body to load
                page.wait_for_selector('body', timeout=5000)

            # Give extra time for dynamic content
            time.sleep(3)

            html = page.content()
            page.close()
            return html
        except Exception as e:
            raise Exception(f"Failed to fetch with Playwright: {str(e)}")

    def extract_content(self, html, url):
        """Extract valuable content from HTML"""
        soup = BeautifulSoup(html, 'lxml')

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()

        # Get body
        body = soup.find('body')
        if not body:
            return {'title': 'No Title', 'content': []}

        # Remove layout elements
        for elem in body.find_all(['header', 'nav', 'footer', 'aside', 'sidebar']):
            elem.decompose()

        # Find main content
        main_content = None
        content_selectors = [
            'article', 'main',
            'div[id="mw-content-text"]',  # Wikipedia
            'div[data-testid="post-content"]', 'div[data-testid="story-content"]',  # Medium
            'div[class*="post-content"]', 'div[class*="story-content"]',
            'section[data-testid="post-content"]',  # Medium alternative
            'div.entry-content', 'div.post-content', 'div.content',  # WordPress
            'div.crayons-article__body', 'div.article-body',  # Dev.to
            'div[class*="content"]', 'div[id*="content"]'
        ]

        for selector in content_selectors:
            main_content = body.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = body

        # Extract title
        title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "No Title"

        # Clean and extract content
        content_blocks = self._extract_content_blocks(main_content)

        return {
            'title': title,
            'content': content_blocks
        }

    def _extract_content_blocks(self, main_content):
        """Extract structured content blocks"""
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = set()

        def clean_html(html_str):
            soup_temp = BeautifulSoup(html_str, 'lxml')
            allowed_tags = {'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong', 'em', 'u', 'code', 'ul', 'ol', 'li', 'blockquote'}
            allowed_attrs = {
                'a': ['href'],
                'img': ['src', 'alt'],
            }

            for tag in soup_temp.find_all():
                if tag.name not in allowed_tags:
                    tag.unwrap()
                    continue
                # Remove unwanted attributes
                attrs_to_remove = []
                for attr in tag.attrs:
                    if attr not in allowed_attrs.get(tag.name, []):
                        attrs_to_remove.append(attr)
                for attr in attrs_to_remove:
                    del tag[attr]

            return str(soup_temp)

        content_blocks = []

        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'img', 'ul', 'ol', 'blockquote']):
            if element.name.startswith('h'):
                level = int(element.name[1])
                html = clean_html(str(element))
                text = element.get_text()
                found_emails = re.findall(email_regex, text, re.IGNORECASE)
                emails.update(found_emails)
                highlighted_html = re.sub(email_regex, r'<span class="email-highlight">\g<0></span>', html, flags=re.IGNORECASE)
                content_blocks.append({
                    'type': 'heading',
                    'level': level,
                    'html': highlighted_html
                })
            elif element.name == 'p':
                html = clean_html(str(element))
                text = element.get_text()
                if text.strip():
                    found_emails = re.findall(email_regex, text, re.IGNORECASE)
                    emails.update(found_emails)
                    highlighted_html = re.sub(email_regex, r'<span class="email-highlight">\g<0></span>', html, flags=re.IGNORECASE)
                    content_blocks.append({
                        'type': 'paragraph',
                        'html': highlighted_html
                    })
            elif element.name == 'img':
                src = element.get('src')
                alt = element.get('alt', '')
                if src:
                    html = clean_html(str(element))
                    content_blocks.append({
                        'type': 'image',
                        'html': html,
                        'src': src,
                        'alt': alt
                    })
            elif element.name in ['ul', 'ol', 'blockquote']:
                html = clean_html(str(element))
                text = element.get_text()
                found_emails = re.findall(email_regex, text, re.IGNORECASE)
                emails.update(found_emails)
                highlighted_html = re.sub(email_regex, r'<span class="email-highlight">\g<0></span>', html, flags=re.IGNORECASE)
                content_blocks.append({
                    'type': 'block',
                    'html': highlighted_html
                })

        return content_blocks

    def crawl_website(self, seed_url, max_depth=2, max_pages=10):
        """Crawl website starting from seed URL"""
        visited = set()
        to_visit = [(seed_url, 0)]  # (url, depth)
        results = []

        base_domain = urlparse(seed_url).netloc

        while to_visit and len(results) < max_pages:
            current_url, depth = to_visit.pop(0)

            if current_url in visited or depth > max_depth:
                continue

            visited.add(current_url)

            try:
                # Check if same domain (basic check)
                if urlparse(current_url).netloc != base_domain:
                    continue

                html = self.fetch_html(current_url) if self.is_dynamic_site(current_url) else self.fetch_html_requests(current_url)
                content = self.extract_content(html, current_url)

                results.append({
                    'url': current_url,
                    'title': content['title'],
                    'content': content['content']
                })

                # Extract links for next level
                if depth < max_depth:
                    soup = BeautifulSoup(html, 'lxml')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(current_url, href)
                        # Only internal links
                        if urlparse(full_url).netloc == base_domain and full_url not in visited:
                            to_visit.append((full_url, depth + 1))

            except Exception as e:
                print(f"Error crawling {current_url}: {str(e)}")
                continue

        return results

    def scrape_url(self, url):
        """Main method to scrape a single URL"""
        try:
            if self.is_dynamic_site(url):
                html = self.fetch_html_playwright(url)
            else:
                html = self.fetch_html_requests(url)

            return self.extract_content(html, url)
        except Exception as e:
            return {'title': 'Error', 'content': [], 'error': str(e)}