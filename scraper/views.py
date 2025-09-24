from django.shortcuts import render
from .utils import WebScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_blog(request):
    url = 'https://healthwire.pk/healthcare/'

    try:
        with WebScraper() as scraper:
            scraped_data = scraper.scrape_url(url)
    except Exception as e:
        scraped_data = {'title': 'Error', 'content': [], 'error': str(e)}

    context = {
        'data': scraped_data,
        'url': url,
    }
    return render(request, 'scraper/results.html', context)

def crawl_links(request):
    from django.http import HttpResponse
    import pandas as pd
    from io import BytesIO

    crawl_result = None
    error = None
    submitted_url = ''

    if request.method == 'POST':
        url = request.POST.get('url')
        submitted_url = url

        if url:
            try:
                # Use conservative limits for web interface to prevent timeouts
                with WebScraper() as scraper:
                    crawl_result = scraper.crawl_website(url, max_depth=2, max_pages=20)
            except Exception as e:
                error = str(e)

        # Handle export
        if 'export' in request.POST and crawl_result and crawl_result['pages']:
            # Create DataFrame with page data
            export_data = []
            for page in crawl_result['pages']:
                content_text = ' '.join(
                    block.get('html', '').replace('<p>', '').replace('</p>', '').replace('<h1>', '').replace('</h1>', '').replace('<h2>', '').replace('</h2>', '').replace('<h3>', '').replace('</h3>', '').strip()
                    for block in page['content']
                    if block['type'] in ['paragraph', 'heading']
                )
                export_data.append({
                    'URL': page['url'],
                    'Title': page['title'],
                    'Content': content_text[:5000],  # Limit content length
                    'Word Count': len(content_text.split())
                })

            df = pd.DataFrame(export_data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Extracted Content')
            output.seek(0)

            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=extracted_content.xlsx'
            return response

    context = {
        'crawl_result': crawl_result,
        'error': error,
        'submitted_url': submitted_url,
    }
    return render(request, 'scraper/crawl_links.html', context)
    return render(request, 'scraper/crawl_links.html', context)

def extract_title_from_result(result):
    # Try to find title in content
    for block in result['content']:
        if 'html' in block:
            soup = BeautifulSoup(block['html'], 'lxml')
            h1 = soup.find('h1')
            if h1:
                return h1.get_text(strip=True)
    return result.get('title', 'No Title')

def extract_content_from_result(result):
    content_texts = []
    for block in result['content']:
        if block.get('type') == 'paragraph' and 'html' in block:
            soup = BeautifulSoup(block['html'], 'lxml')
            text = soup.get_text(strip=True)
            if text:
                content_texts.append(text)
    return ' '.join(content_texts)
