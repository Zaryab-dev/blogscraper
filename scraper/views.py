from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
import re

def scrape_blog(request):
    url = 'https://medium.com/@rathod9/rocket-new-the-one-platform-to-build-a-1m-application-in-a-single-prompt-70bf69ff064f'
    blog_content = {}
    error = None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()

        # Get the body content
        body = soup.find('body')
        if body:
            # Remove layout elements
            for elem in body.find_all(['header', 'nav', 'footer', 'aside', 'sidebar']):
                elem.decompose()

            # Find main content area - enhanced for blog platforms
            main_content = None
            # Priority: main > article > specific blog selectors
            main_content = body.find('main') or body.find('article')
            if not main_content:
                # Blog platform specific selectors
                content_selectors = [
                    # Wikipedia
                    'div[id="mw-content-text"]',
                    # Medium
                    'div[data-testid="post-content"]',
                    'div[data-testid="story-content"]',
                    'div[class*="post-content"]',
                    'div[class*="story-content"]',
                    'article[class*="post"]',
                    # WordPress
                    'div.entry-content',
                    'div.post-content',
                    'div.content',
                    'article.post',
                    'div.single-content',
                    # Dev.to and similar
                    'div.crayons-article__body',
                    'div.article-body',
                    'div.post-body',
                    # General
                    'div[class*="content"]',
                    'div[id*="content"]',
                    'section[class*="content"]',
                    'div[class*="article"]',
                    'div[id*="article"]',
                    'div[class*="post"]',
                    'div[id*="post"]',
                    'div[class*="entry"]',
                    'div[id*="entry"]'
                ]
                for selector in content_selectors:
                    main_content = body.select_one(selector)
                    if main_content:
                        break
            # Fallback to body if no specific content area found
            if not main_content:
                main_content = body

            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else "No Title"

            # Email regex
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = set()

            # Clean function for individual elements
            def clean_html(html_str):
                soup_temp = BeautifulSoup(html_str, 'html.parser')
                allowed_attrs = {
                    'a': ['href'],
                    'img': ['src', 'alt'],
                    'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': [],
                    'p': [], 'strong': [], 'em': [], 'u': [], 'code': [],
                    'ul': [], 'ol': [], 'li': [], 'blockquote': []
                }
                for tag in soup_temp.find_all():
                    if tag.name not in allowed_attrs:
                        tag.unwrap()  # Remove tag but keep contents
                        continue
                    # Remove unwanted attributes
                    attrs_to_remove = []
                    for attr in tag.attrs:
                        if attr not in allowed_attrs.get(tag.name, []):
                            attrs_to_remove.append(attr)
                    for attr in attrs_to_remove:
                        del tag[attr]
                return str(soup_temp)

            # Extract content by type from main content
            headings = []
            paragraphs = []
            links = []
            images = []

            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img', 'ul', 'ol', 'li', 'strong', 'em', 'u', 'blockquote', 'code']):
                if element.name.startswith('h'):
                    level = int(element.name[1])
                    html = clean_html(str(element))
                    text = element.get_text()
                    # Find and highlight emails
                    found_emails = re.findall(email_regex, text, re.IGNORECASE)
                    emails.update(found_emails)
                    highlighted_html = re.sub(email_regex, r'<span class="email-highlight">\g<0></span>', html, flags=re.IGNORECASE)
                    headings.append({
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
                        paragraphs.append(highlighted_html)
                elif element.name == 'a':
                    html = clean_html(str(element))
                    text = element.get_text()
                    if text.strip():
                        found_emails = re.findall(email_regex, text, re.IGNORECASE)
                        emails.update(found_emails)
                        highlighted_html = re.sub(email_regex, r'<span class="email-highlight">\g<0></span>', html, flags=re.IGNORECASE)
                        links.append(highlighted_html)
                elif element.name == 'img':
                    src = element.get('src')
                    alt = element.get('alt', '')
                    if src:
                        html = clean_html(str(element))
                        images.append({
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
                    paragraphs.append(highlighted_html)  # Add to paragraphs for display

            scraped_data = {
                'title': title,
                'headings': headings,
                'paragraphs': paragraphs,
                'links': links,
                'images': images,
                'emails': list(emails),
            }
        else:
            error = "No body found on the page."
            scraped_data = {}
    except requests.RequestException as e:
        error = f"Error fetching the page: {str(e)}"
        scraped_data = {}
    except Exception as e:
        error = f"Error parsing the page: {str(e)}"
        scraped_data = {}

    context = {
        'data': scraped_data,
        'error': error,
        'url': url,
    }
    return render(request, 'scraper/results.html', context)
