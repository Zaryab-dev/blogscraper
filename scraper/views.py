from django.shortcuts import render
import requests
from bs4 import BeautifulSoup

def scrape_blog(request):
    url = 'https://medium.com/@noureldin_z3r0/how-to-write-the-perfect-blog-post-my-10-000-word-journey-7b5b38525848'
    blog_content = {}
    error = None
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract the main article content
        article = soup.find('article')
        if article:
            # Extract title
            title_elem = article.find('h1') or soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else "No Title"

            # Extract structured content: headings, paragraphs, images
            content_blocks = []
            for element in article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'img']):
                if element.name.startswith('h'):
                    level = int(element.name[1])
                    content_blocks.append({
                        'type': 'heading',
                        'level': level,
                        'text': element.get_text(strip=True)
                    })
                elif element.name == 'p':
                    text = element.get_text(strip=True)
                    if text:  # Only add non-empty paragraphs
                        content_blocks.append({
                            'type': 'paragraph',
                            'text': text
                        })
                elif element.name == 'img':
                    src = element.get('src')
                    alt = element.get('alt', '')
                    if src:
                        content_blocks.append({
                            'type': 'image',
                            'src': src,
                            'alt': alt
                        })

            blog_content = {
                'title': title,
                'content_blocks': content_blocks,
            }
        else:
            error = "No article found on the page."
    except requests.RequestException as e:
        error = f"Error fetching the page: {str(e)}"
    except Exception as e:
        error = f"Error parsing the page: {str(e)}"

    context = {
        'blog': blog_content,
        'error': error,
        'url': url,
    }
    return render(request, 'scraper/results.html', context)
