# asterics_grid_api_v2

## Project Description

This project is the spiritual successor to https://github.com/Volskaar/asterics_grid_api_v1.git. It does not extend the mentioned projects functionality but is much rather a more functional extension of the original project https://github.com/asterics/AsTeRICS-Grid.git.

This PHP script is a web-based tool for scraping German verb conjugations from Wiktionary. It processes the conjugation tables and provides the data in either JSON or CSV format, based on the user's request.


## Including 2 Versions

### 1 - with dependencies - dep

Scraper with dependencies, which improves code structure.

Dependencies used: 
1. Guzzle: For HTTP requests.
2. Symfony DomCrawler: For HTML parsing.

### 2 - no dependencies - ndep

Backup version in case somehting went wrong with "dep".


## How it works

1. The scraper.php performs a GET request  
e.g. https://wordforms.asterics-foundation.org/wordforms_ndep/scraper.php?verb=insert_word_here&type=json

!!!Please make sure to name the path correctly!!!

2. The application retrieves the required query parameter from the request

3. The application performs its functionality:

    1. curl the contents of the wiktioniary page related to the word
    2. scrape through the page and extract wordforms from the document object model (DOM)
    3. remove unnecessary information like e.g. the german pronouns
    4. assign each word a list of relevant tags based on the data retreived, which is also structured throughout the DOM
    5. format the data accordingly
    6. return an adequate web response (the AstericsGrid application proecesses classic JSON, we also provide .csv files via direct calls to the API in case some developer may require it for future reference)
