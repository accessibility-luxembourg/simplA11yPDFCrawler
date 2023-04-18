import scrapy, urllib.parse, re, os, itertools
from scrapy.http import Request

# based on the quotesSpider from Scrapy Tutorial
# https://docs.scrapy.org/en/latest/intro/tutorial.html

class pdf_a11y(scrapy.Spider):
  name = "pdf_a11y_crawler"
  custom_settings = {
    'DOWNLOAD_DELAY': '1',
    'COOKIES_ENABLED': True
  } 

  def __init__(self, url=None, *args, **kwargs):
    super(pdf_a11y, self).__init__(*args, **kwargs)
    self.url = url
    self.parsed_url = urllib.parse.urlparse(url)
    self.allowed_domains = [self.parsed_url.netloc]
    self.start_urls = [url]

  def checkExtension(self, path):
    # list of extensions to be downloaded
    # not able to detect daisy books because they are distributed as zip files
    extensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.doc', '.ppt', '.xls', '.epub', '.odt', '.ods', '.odp']
    for ext in extensions:
      if (path.endswith(ext)):
        return True
    return False

  def parse(self, response):
    base_url = self.parsed_url.scheme+'://'+self.parsed_url.netloc
    if (isinstance(response, scrapy.http.response.html.HtmlResponse)):
      for a in response.xpath('//a[@href]/@href'):
        link = a.extract().strip()
        parsed_link = urllib.parse.urlparse(link)
        path = parsed_link.path
        scheme = parsed_link.scheme
        path = re.sub(r'\/+$', '' , path)
        link = response.urljoin(link)
        if (scheme == '' or scheme == 'http' or scheme == 'https'):
          if self.checkExtension(path):
            self.logger.info(link)
            yield Request(link, callback=self.save_pdf)
          else:
            if (path.lower().find('recherche') != -1 or path.lower().find('search') != -1):
                self.logger.info('Avoided search page:'+link)
            else:
                yield response.follow(link, self.parse)

  def save_pdf(self, response):
    path = response.url.split('/')[-1]
    basename = os.path.basename(path)
    splitext = os.path.splitext(basename)
    basename = splitext[0]
    ext = splitext[1]
    subfolder = self.parsed_url.netloc
    savePath = 'crawled_files/'+subfolder+'/'
    filename = self.unique_file(savePath, basename, ext)
    self.logger.info('Saving PDF %s', savePath + filename)
    with open(savePath + filename, 'wb') as f:
      f.write(response.body)

  def unique_file(self, path, basename, ext):
    actualname = "%s%s" % (basename, ext)
    c = itertools.count()
    while os.path.exists(path+actualname):
      actualname = "%s-%d%s" % (basename, next(c), ext)
    return actualname
