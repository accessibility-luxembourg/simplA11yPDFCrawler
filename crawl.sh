#!/bin/bash
cat list-sites.txt | while read i; do echo $i; mkdir -p crawled_files/$i ; timeout -s SIGINT 4h scrapy runspider --logfile=scrapy.log pdf_spider.py -a url=https://$i; done

