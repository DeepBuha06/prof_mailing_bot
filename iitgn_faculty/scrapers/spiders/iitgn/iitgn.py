import scrapy
import re

class FacultySpider(scrapy.Spider):
    name = 'iitgn'
    allowed_domains = ['iitgn.ac.in']
    start_urls = ['https://iitgn.ac.in/faculty']

    def parse(self, response):
        dept_links = response.xpath('//a[contains(@href, "/faculty/")]/@href').getall()
        dept_links = [response.urljoin(link) for link in dept_links if "/faculty/" in link]
        for dept_url in dept_links:
            yield scrapy.Request(url=dept_url, callback=self.parse_department)

    def parse_department(self, response):
        profile_links = response.xpath('//a[contains(@href, "/faculty/")]/@href').getall()
        blacklist = ['bioe', 'civil', 'cse', 'cl', 'chemistry', 'cogs', 'guestprof', 'me', 'design', 'maths', 'mse', 'hss', 'earths', 'phy', 'ee', 'former']
        profile_links = [
            response.urljoin(link)
            for link in profile_links
            if not link.rstrip('/').split('/')[-1] in blacklist
        ]
        for profile_url in profile_links:
            department = response.url.rstrip('/').split('/')[-1]
            yield scrapy.Request(url=profile_url, callback=self.parse_profile, cb_kwargs={'department': department})

    def parse_profile(self, response, department):
        name = response.css('p::text').get()
        designation = response.css("span b::text").get()

        parts = response.css('p:contains("Email")::text').getall()
        email_raw = ""
        for part in parts:
            if "@iitgn.ac.in" in part or "-AT-" in part:
                email_raw = part.strip()
                break
        email = email_raw.replace(" -AT- ", "@").replace(" ", "").lstrip(":")

        website = response.css('p:contains("Website") a::attr(href)').get()

        research_interests = ', '.join(response.xpath('//h5[contains(text(), "Research Interests")]/following-sibling::ul[1]/li/text()').getall())
        academic_background = ', '.join(response.xpath('(//ul[li[contains(text(), "University") or contains(text(), "PhD") or contains(text(), "IIT")]])[1]/li/text()').getall())
        # work_experience = ', '.join(response.xpath('(//ul[li[contains(text(), "Pvt") or contains(text(), "Ltd") or contains(text(), "Company") or contains(text(), "present") or contains(text(), "Jan") or contains(text(), "Dec")]])[1]/li/text()').getall())

        publication_list = [
            ' '.join(li.xpath('.//text()').getall()).strip()
            for li in response.xpath('//ol[li]/li')
        ]

        img_src = response.css('img.border--round::attr(src)').get()
        photo = response.urljoin(img_src) if img_src else None

        yield {
            "name": name,
            "designation": designation,
            "email": email,
            "website": website,
            "research_interests": research_interests,
            "academic_background": academic_background,
            # "work_experience": work_experience,
            "selected_publications": publication_list,
            "department": department,
            "photo": photo,
            "profile_url": response.url
        }
