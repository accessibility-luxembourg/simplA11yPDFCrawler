#!/bin/bash
gnutimeout() {
    if hash gtimeout 2>/dev/null; then
        gtimeout "$@"
    else
        timeout "$@"
    fi
}
cat list-sites.txt | while read i; do echo $i; mkdir -p crawled_files/$i ; gnutimeout -s KILL 4h scrapy runspider --logfile=scrapy.log pdf_spider.py -a url=https://$i; done

