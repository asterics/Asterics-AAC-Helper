<?php 
mb_internal_encoding('UTF-8');

// CORS enable
header("Access-Control-Allow-Origin: *"); // Allow requests from any origin
header("Access-Control-Allow-Methods: GET, POST, OPTIONS"); // Allowed methods
header("Access-Control-Allow-Headers: Content-Type"); // Allowed headers

require __DIR__ . '/vendor/autoload.php';

use GuzzleHttp\Client; // for making requests to external resources
use Symfony\Component\DomCrawler\Crawler; // parsing and extracting info from HTML documents

// Function to scrape verb conjugation
function scrapeConjugation($verb)
{
    $url = "https://de.wiktionary.org/wiki/Flexion:$verb";


    // Create a Guzzle client to fetch the HTML content
    $httpClient = new Client();
    $response = $httpClient->request('GET', $url);

    // Get the (raw) HTML body
    $html = (string) $response->getBody();

    if (!$html) {
        echo "Request failed. ";
        return [];
    }

    // create instance of crawler to manipulate html elements
    $crawler = new Crawler($html);

    // Locate the "Indikativ und Konjunktiv" section
    $section = $crawler->filter('#Indikativ_und_Konjunktiv')->ancestors()->first();

    if ($section->count() === 0) {
        return ['error' => 'Section not found'];
    }

    // Find all tables immediately following the section header
    $tables = $section->nextAll()->filter('table');

    $results = [];
    $tenses = ["PRAESENS", "PRAETERITUM", "PERFEKT", "PLUSQAMPERFEKT", "FUTURI", "FUTURII"];
    $tenseCount = 0;
    $entriesPerTense = 0;

    $tables->each(function ($table) use (&$results, &$tenses, &$tenseCount, &$entriesPerTense) {
        //iterate over rows in the table
        $table->filter('tr')->each(function ($tr) use (&$results, &$tenses, &$tenseCount, &$entriesPerTense) {
           // selects the table cell(td)
            $tdElements = $tr->filter('td');

            if ($tdElements->count() >= 2) { // if more than 2 cells (Person, indikativ)
                $person = trim($tdElements->eq(0)->text()); //
                $indikativ = trim($tdElements->eq(1)->text());

                if (!empty($person) && $person !== 'Person') {
                    // Remove the personal pronoun from the verb form using regex
                    $verbOnly = preg_replace('/^(ich|du|er\/sie\/es|wir|ihr|sie)\s+/i', '', $indikativ);

                    // Determine the correct tags
                    $tagPerson = strpos($person, "1.") !== false ? "1.PERS" : (strpos($person, "2.") !== false ? "2.PERS" : "3.PERS");
                    $tagPlural = strpos($person, "Plural") !== false ? "PLURAL" : "";
                    $tagNegation = strpos($verbOnly, "nicht") !== false ? "NEGATION" : "";
                    $tagTense = $tenses[$tenseCount];

                    // Advance to the next tense after 6 entries
                    $entriesPerTense++;
                    if ($entriesPerTense === 6) {
                        $entriesPerTense = 0;
                        $tenseCount++;
                    }

                    // Add the entry to result in this format
                    $results[] = [
                        'lang' => 'de',
                        'value' => $verbOnly,
                        'tags' => array_filter([$tagPerson, $tagTense, $tagPlural, $tagNegation])
                    ];
                }
            }
        });
    });

    return $results;
}

// Function to convert data to CSV format
function convertToCSV($data)
{
    $output = fopen('php://temp', 'r+');
    // Add header row
    fputcsv($output, ['lang', 'value', 'tags']);
    // Add data rows
    foreach ($data as $item) {
        fputcsv($output, [$item['lang'], $item['value'], implode(', ', $item['tags'])]);
    }
    rewind($output);
    $csv = stream_get_contents($output);
    fclose($output);
    return $csv;
}

// Handle GET request
if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['verb'])) {
    $verb = mb_strtolower($_GET['verb']); // Convert the verb to lowercase
    $format = isset($_GET['format']) ? mb_strtolower($_GET['format']) : 'json';
    $conjugation = scrapeConjugation($verb);

    if ($format === 'csv') {
        header('Content-Type: text/csv');
        header('Content-Disposition: attachment; filename="conjugation.csv"');
        echo convertToCSV($conjugation);
    } else { // Default to JSON
        header('Content-Type: application/json');
        echo json_encode($conjugation, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    }
} else {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid request. Please provide a verb and format (json or csv) in the GET query string.']);
}

?>