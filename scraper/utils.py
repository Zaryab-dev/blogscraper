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
        """Fetch HTML using Playwright for dynamic sites with enhanced loading"""
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

            # Navigate and wait for network idle
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except:
                # If networkidle times out, just continue
                pass

            # Scroll to bottom to trigger lazy loading
            page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
            """)
            time.sleep(1)  # Wait for lazy content to load

            # Try to find and click "Load more" buttons (quick check)
            load_more_selectors = [
                'button:has-text("Load more")',
                'button:has-text("Load More")',
                'button:has-text("Show more")',
                '.load-more',
                '[data-testid="load-more"]'
            ]

            for selector in load_more_selectors:
                try:
                    load_button = page.query_selector(selector)
                    if load_button and load_button.is_visible():
                        load_button.click()
                        time.sleep(1)  # Brief wait for new content
                        break
                except:
                    continue

            # Additional scroll
            page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
            """)
            time.sleep(0.5)

            html = page.content()
            page.close()
            return html
        except Exception as e:
            try:
                page.close()
            except:
                pass
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

    def crawl_website(self, seed_url, max_depth=5, max_pages=1000):
        """
        Robustly crawl website to discover all links and extract content.

        Args:
            seed_url (str): Starting URL to crawl
            max_depth (int): Maximum crawl depth (default: 5)
            max_pages (int): Maximum number of pages to crawl (default: 1000)

        Returns:
            dict: {
                "seed_url": seed_url,
                "total_links": len(all_links),
                "links": list(all_links),
                "pages": list of page data with content
            }
        """
        # Normalize seed URL
        seed_url = self._normalize_url(seed_url)

        # Initialize data structures
        visited = set()
        to_visit = [(seed_url, 0)]  # (url, depth)
        all_links = set()
        pages_data = []

        # Get base domain for subdomain allowance
        parsed_seed = urlparse(seed_url)
        base_domain = parsed_seed.netloc
        base_domain_parts = base_domain.split('.')
        if len(base_domain_parts) > 2:
            # For subdomains like blog.example.com, allow *.example.com
            base_domain_root = '.'.join(base_domain_parts[-2:])
        else:
            base_domain_root = base_domain

        print(f"Starting crawl of {seed_url} (domain: {base_domain_root}, max_depth: {max_depth}, max_pages: {max_pages})")

        while to_visit and len(visited) < max_pages:
            current_url, depth = to_visit.pop(0)

            # Skip if already visited or too deep
            if current_url in visited or depth > max_depth:
                continue

            visited.add(current_url)
            print(f"Crawling [{len(visited)}/{min(max_pages, len(to_visit) + len(visited))}]: {current_url}")

            try:
                # Always use Playwright for robust dynamic content handling
                html = self.fetch_html_playwright(current_url)

                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')

                # Extract content
                content_data = self.extract_content(html, current_url)

                # Only include pages with meaningful content
                if content_data['content']:
                    pages_data.append({
                        'url': current_url,
                        'title': content_data['title'],
                        'content': content_data['content']
                    })

                # Extract all links
                page_links = set()
                for link in soup.find_all('a', href=True):
                    href = link['href'].strip()

                    # Skip empty, fragment-only, or non-HTTP links
                    if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
                        continue

                    # Normalize URL
                    full_url = urljoin(current_url, href)
                    normalized_url = self._normalize_url(full_url)

                    # Check if URL is valid and within allowed domain
                    parsed_url = urlparse(normalized_url)
                    if parsed_url.scheme in ('http', 'https') and base_domain_root in parsed_url.netloc:
                        page_links.add(normalized_url)

                # Add discovered links to global set
                all_links.update(page_links)

                # Add new links to visit queue if within depth limit
                if depth < max_depth:
                    for link_url in page_links:
                        if link_url not in visited and link_url not in [u for u, d in to_visit]:
                            to_visit.append((link_url, depth + 1))

            except Exception as e:
                print(f"Error crawling {current_url}: {str(e)}")
                continue

        print(f"Crawl completed. Visited {len(visited)} pages, discovered {len(all_links)} unique links, extracted content from {len(pages_data)} pages.")

        return {
            "seed_url": seed_url,
            "total_links": len(all_links),
            "links": sorted(list(all_links)),
            "pages": pages_data
        }

    def _normalize_url(self, url):
        """Normalize URL by removing fragments and standardizing format"""
        parsed = urlparse(url)
        # Remove fragment
        normalized = parsed._replace(fragment='')
        # Reconstruct URL
        return normalized.geturl()

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