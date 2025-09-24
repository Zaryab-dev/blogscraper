from django.urls import path
from . import views

urlpatterns = [
    path('scrape/', views.scrape_blog, name='scrape_blog'),
    path('crawl/', views.crawl_links, name='crawl_links'),
]