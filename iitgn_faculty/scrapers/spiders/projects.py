import scrapy


class ProjectsSpider(scrapy.Spider):
    name = "projects"
    allowed_domains = ["iitgn.ac.in"]
    start_urls = ["https://iitgn.ac.in/research/projects"]

    def parse(self, response):
        pass
