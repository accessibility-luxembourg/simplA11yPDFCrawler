const parse = require('csv-parse/lib/sync')
const fs = require('fs')
const pdfCheck = parse(fs.readFileSync('./out/pdfCheck.csv'), {
    columns: true,
    skip_empty_lines: true
  })
  const distrib = parse(fs.readFileSync('./out/distribution.csv'), {
    columns: true,
    skip_empty_lines: true
  })

// We compute for every website:
// - the number of exempt PDFs (law in Luxembourg considers that PDFs published before the 23 September 2020 do not need to be compliant)
// - the number of non-exempt PDFs
// - the number of files available to download 
// - the percentage of PDF among all the files available to download
// - the percentage of PDF forms among all the files available to download
// - the percentage of PDF files with blocking accessibility issues among non-exempt PDFs

let results = {}

pdfCheck.forEach((line) =>  {
    if (results[line['Site']] === undefined) {
        results[line['Site']] = {'files':0, 'pdf':0, 'pdf-exempt':0, 'pdf-non-exempt': 0, 'pdf-form':0, 'pdf-blocking-pb-access':0}
    }
    if (line['Exempt'].toLowerCase() == 'true') {
        results[line['Site']]['pdf-exempt']++
    } else {
        results[line['Site']]['pdf-non-exempt']++
        if (line['TotallyInaccessible'].toLowerCase() == 'true') {
            results[line['Site']]['pdf-blocking-pb-access']++
        }
    }
    if (line['Form'].toLowerCase() == 'true') {
        results[line['Site']]['pdf-form']++
    }
})

distrib.forEach((line) =>  {
    if (results[line['site']] !== undefined) {
        results[line['site']]['files'] = parseInt(line['files'])
        results[line['site']]['pdf'] = parseInt(line['files']) - parseInt(line['not-pdf'])
    }
})

Object.keys(results).forEach(site => {
    if (results[site]['files'] != 0) {
        results[site]['pcent-pdf'] = Math.round(results[site]['pdf']/results[site]['files'] * 100)
        results[site]['pcent-form'] = Math.round(results[site]['pdf-form']/results[site]['files'] * 100)
    }
    if (results[site]['pdf-non-exempt'] != 0) {
        results[site]['pcent-pdf-blocking-pb-access'] = Math.round(results[site]['pdf-blocking-pb-access']/results[site]['pdf-non-exempt'] * 100)
    }
})

fs.writeFileSync('./out/office-files.json', JSON.stringify(results, null, 4))

