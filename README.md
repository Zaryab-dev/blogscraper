# Django Web Scraper with Playwright

A powerful Django-based web scraper that can extract content from both static and dynamic websites using Playwright for JavaScript-heavy sites and BeautifulSoup for HTML parsing. Features a clean reader-mode interface and supports multiple blogging platforms.

## 🚀 Features

- **Dual Scraping Engines**: Automatically detects and uses the appropriate scraping method
  - **Static Sites**: Uses `requests` + `BeautifulSoup` (fast, lightweight)
  - **Dynamic Sites**: Uses `Playwright` + `BeautifulSoup` (handles JavaScript rendering)

- **Smart Content Detection**: Recognizes and extracts content from popular platforms:
  - Medium, Substack, Dev.to
  - WordPress blogs
  - Wikipedia
  - General websites

- **Clean Reader Mode**: Strips away navigation, ads, and layout elements to provide distraction-free reading

- **Content Extraction**:
  - Headings (H1-H6)
  - Paragraphs
  - Images with alt text
  - Links
  - Lists and blockquotes
  - Email address detection and highlighting

- **Modern UI**: Bootstrap-styled responsive interface

- **Crawling Support**: Built-in web crawler with configurable depth and robots.txt respect

## 📋 Requirements

- Python 3.8+
- Django 4.2+
- Playwright
- BeautifulSoup4
- lxml
- requests

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd blogscraper
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install
```

### 5. Run Django Migrations
```bash
python manage.py migrate
```

### 6. Start Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/scrape/` to test the scraper.

## 📖 Usage

### Basic Scraping
The scraper automatically detects the best method for each website:

```python
from scraper.utils import WebScraper

# For any URL
with WebScraper() as scraper:
    data = scraper.scrape_url('https://example.com/article')
    print(data['title'])
    for block in data['content']:
        print(block['html'])
```

### Supported Platforms

#### Static Sites (Fast)
- Wikipedia
- Most WordPress blogs
- Simple HTML sites

#### Dynamic Sites (Playwright)
- Medium articles
- Substack posts
- Dev.to articles
- JavaScript-heavy blogs

### URL Configuration
Edit `scraper/views.py` to change the target URL:

```python
def scrape_blog(request):
    url = 'https://your-target-url.com/article'  # Change this URL
    # ... rest of code
```

## 🏗️ Project Structure

```
blogscraper/
├── blogscraper/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── scraper/              # Main scraping app
│   ├── utils.py          # Core scraping logic
│   ├── views.py          # Django views
│   ├── models.py         # Database models (for future)
│   ├── urls.py           # URL routing
│   └── templates/scraper/results.html  # UI template
├── manage.py
├── requirements.txt
└── README.md
```

## ⚙️ Configuration

### Content Selectors
The scraper uses intelligent content detection. You can extend platform support by adding selectors in `scraper/utils.py`:

```python
content_selectors = [
    'article', 'main',
    'div[id="mw-content-text"]',  # Wikipedia
    'div[data-testid="post-content"]',  # Medium
    # Add your custom selectors here
]
```

### Crawling Configuration
Modify crawling parameters in the `crawl_website` method:

```python
def crawl_website(self, seed_url, max_depth=2, max_pages=10):
    # Adjust depth and page limits
```

## 🔧 API Reference

### WebScraper Class

#### Methods
- `scrape_url(url)`: Scrape a single URL
- `crawl_website(seed_url, max_depth, max_pages)`: Crawl multiple pages
- `is_dynamic_site(url)`: Check if site needs JavaScript rendering

#### Return Format
```python
{
    'title': 'Page Title',
    'content': [
        {'type': 'heading', 'level': 1, 'html': '<h1>Title</h1>'},
        {'type': 'paragraph', 'html': '<p>Content...</p>'},
        {'type': 'image', 'html': '<img src="..." alt="...">', 'src': '...', 'alt': '...'}
    ],
    'emails': ['email@example.com']
}
```

## 🎨 Customization

### Adding New Platforms
1. Add domain detection in `is_dynamic_site()`
2. Add content selectors in `extract_content()`
3. Test with sample URLs

### UI Customization
Modify `scraper/templates/scraper/results.html` to change the appearance:
- Update Bootstrap classes
- Add custom CSS
- Modify content rendering logic

### Email Detection
The regex pattern can be customized in `scraper/utils.py`:
```python
email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
```

## 🚨 Important Notes

### Anti-Bot Measures
- Some sites (like Medium) may block automated requests
- Playwright includes stealth features but may still be detected
- Respect robots.txt and terms of service
- Consider rate limiting for production use

### Performance
- Playwright is resource-intensive for dynamic sites
- Use requests for static sites when possible
- Configure appropriate timeouts

### Legal Considerations
- Only scrape publicly available content
- Respect copyright and terms of service
- Consider the ethical implications of web scraping

## 🔮 Future Enhancements

- **Dynamic URL Input**: Form-based URL submission
- **Database Storage**: Save scraped content
- **REST API**: JSON endpoints for scraped data
- **User Authentication**: Private scraping sessions
- **Export Options**: PDF, Markdown, JSON export
- **Scheduling**: Automated scraping jobs
- **Proxy Support**: Rotate IPs for large-scale scraping

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Playwright Issues
```bash
# Reinstall browsers
playwright install

# Check installation
playwright --version
```

### Django Issues
```bash
# Clear cache
python manage.py clear_cache

# Reset migrations
python manage.py migrate --reset
```

### Content Not Extracting
- Check if the website has changed its HTML structure
- Add new selectors to `content_selectors` list
- Verify the URL is accessible and not behind a paywall

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Django and Playwright documentation
3. Open an issue on GitHub

---

**Happy Scraping!** 🕷️📊