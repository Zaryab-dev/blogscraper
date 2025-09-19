from django.shortcuts import render
from .utils import WebScraper

def scrape_blog(request):
    url = 'https://medium.com/swlh/how-to-build-a-web-scraper-with-python-3-10-2023-8d7c6e8c3b4a'

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
