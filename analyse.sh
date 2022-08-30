for i in ./crawled_files/*; do j=$(basename $i); find ./crawled_files/$j/*.pdf | while read k; do if [ ! -d $k ]; then echo $k; python3 ./pdfCheck.py tocsv  $j $k; fi done done
echo "site,files,not-pdf" > ./out/distribution.csv
for i in ./crawled_files/*; do echo `basename $i`,`find  $i  -type f  | wc -l`,`find  $i -not -name '*.pdf'  -type f  | wc -l`; done | sort -n >> ./out/distribution.csv
node ./docAnalysis.js
