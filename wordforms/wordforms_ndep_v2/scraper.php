<?php
mb_internal_encoding('UTF-8');
// CORS enable
header("Access-Control-Allow-Origin: *"); // Allow requests from any origin
header("Access-Control-Allow-Methods: GET, POST, OPTIONS"); // Allowed methods
header("Access-Control-Allow-Headers: Content-Type"); // Allowed headers

// Function to scrape verb conjugation
function scrape_web($verb) {
    $verb = mb_strtolower($verb);
    $url = "https://de.wiktionary.org/wiki/Flexion:" . urlencode($verb);
    
    // CURL-request, to extract the html content
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    // HTML-Inhalt abrufen
    $html = curl_exec($ch);

    // Check if Curl-request was successful
    if ($html === false) {
        echo("Error retrieving the URL: " . curl_error($ch));
        return ['Person' => [], 'Indikativ' => [], 'Konjunktiv' => []];
    } else {
        // Check if html content is empty
        if (empty($html)) {
            echo("The html content is empty, please check the URL: " . $url);
            return ['Person' => [], 'Indikativ' => [], 'Konjunktiv' => []];
        }
    }
    curl_close($ch);

    // Check if website exists
    if (strpos($html, 'Flexion:' . urlencode($verb)) === false) {
        echo("Website doesn't exist or no data found for verb: $verb");
        return ['Person' => [], 'Indikativ' => [], 'Konjunktiv' => []];
    }

    // DOMDocument to parse the HTML
    $dom = new DOMDocument();
    libxml_use_internal_errors(true); // Interne error handling
    $dom->loadHTML($html);
    libxml_clear_errors(); 

    $xpath = new DOMXPath($dom);

    // Search for h5 with id "Indikativ und Konjunktiv"
    $first_section = $xpath->query('//h5[@id="Indikativ_und_Konjunktiv"]');

    if ($first_section->length === 0) {
        echo(" 'Indikativ und Konjunktiv' not found for verb: $verb.");
        return ['Person' => [], 'Indikativ' => []]; #, 'Konjunktiv' => []
    } else {
        #echo(" 'Indikativ und Konjunktiv' found: " . $first_section->item(0)->nodeValue);
    }

    $first_h5 = $first_section->item(0);
    $current_node = $first_h5->parentNode->nextSibling; // Start with next sibling from Parent-Element

    $tables = []; // Array for all found tables

    // Go through all siblings to find all following tables
    while ($current_node) {
        if ($current_node->nodeName === 'table') {
            $tables[] = $current_node; // Add table to array
        }
        $current_node = $current_node->nextSibling; // Go to next sibling node
    }
    
    // Arrays for all collected data
    $person_list = [];
    $indikativ_list = [];

    foreach ($tables as $table) {
        $rows = $table->getElementsByTagName('tr');
        
        // 'Futur 2' Flag, to check if code reached the end of the wordform table
        $futur2_found = false;
    
        foreach ($rows as $row) {
            $cols = $row->getElementsByTagName('td');
    
            // Check if row has at least 3 columns
            if ($cols->length >= 3) {
                // combine text in <td>-Tags
                $person = getTextFromChildNodes($cols->item(0));
                $indikativ = getTextFromChildNodes($cols->item(1));
    
                // Refactor values
                $indikativ_parts = explode(' ', $indikativ);
    
                if (!empty($person) && $person !== 'Person') {
                    if (!empty($indikativ)) {
                        // Necessary to get rid of undesired words
                        $indikativOnlyVerb = '';
                        if (count($indikativ_parts) > 1) {
                            $rest = implode(' ', array_slice($indikativ_parts, 1));
                            $comma_position = strpos($rest, ',');
                            $indikativOnlyVerb = $comma_position !== false ? substr($rest, 0, $comma_position) : $rest;
                        }
    
                        // Add values to lists
                        $person_list[] = $person;
                        $indikativ_list[] = $indikativOnlyVerb;
                    }
                }
            }
    
            // Check if the "Futur II" flag was found in one of the <td> tags
            foreach ($cols as $col) {
                if (strpos(trim($col->nodeValue), 'Futur II') !== false) {
                    $futur2_found = true; // Setze das Flag
                    break; 
                }
            }
        }
    
        // If "Futur II" flag was found, start last loop
        if ($futur2_found) {
            break;
        }
    }
    
    return ['Person' => $person_list, 'Indikativ' => $indikativ_list];
}    


function getTextFromChildNodes($node) {
    $text = '';
    if ($node instanceof DOMElement) {
        foreach ($node->childNodes as $child) {
            $text .= $child->nodeValue . ' '; // get the text from every child-node
        }
    }
    return trim($text); // Trim empty spaces
}



function format_data($data) {
    $result = [];
    //German tenses
    $tenses = ["PRAESENS", "PRAETERITUM", "PERFEKT", "PLUSQAMPERFEKT", "FUTURI", "FUTURII"];
    $tense_cnt = 0;
    $words_per_tense = 0;

    // Check if the arrays contain 'Person' and 'Indikativ' data
    if (!empty($data['Person']) && !empty($data['Indikativ'])) {
        foreach ($data['Person'] as $index => $person) {
            $tag_person = "";
            if (strpos($person, "1.") !== false) {
                $tag_person = "1.PERS";
            } elseif (strpos($person, "2.") !== false) {
                $tag_person = "2.PERS";
            } elseif (strpos($person, "3.") !== false) {
                $tag_person = "3.PERS";
            }

            $tag_tense = $tenses[$tense_cnt];
            $words_per_tense++;

            if ($words_per_tense == 6) {
                $words_per_tense = 0;
                $tense_cnt++;
            }

            $tag_plural = (strpos($person, "Plural") !== false) ? "PLURAL" : "";
            $tag_negation = (strpos($data['Indikativ'][$index], "nicht") !== false) ? "NEGATION" : "";

            $entry = [
                "lang" => "de",
                "value" => $data['Indikativ'][$index],
                "tags" => array_filter([$tag_person, $tag_tense, $tag_plural, $tag_negation])
            ];

            $result[] = $entry;
        }
    } else {
        error_log("format is invalid or empty");
    }

    return $result;
}


function convert_to_json($data) {
    return json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
}

function convert_to_csv($data) {
    $output = fopen('php://memory', 'r+');
    foreach ($data as $item) {
        $lang = $item["lang"];
        $value = $item["value"];
        $tags = implode(", ", $item["tags"]);
        fputcsv($output, [$lang, $value, $tags]);
    }
    rewind($output);
    $csv_data = stream_get_contents($output);
    fclose($output);

    return $csv_data;
}

function call_web_scraper($verb, $type) {
    $data = scrape_web($verb);
    $formatted_data = format_data($data);

    if ($type === 'json') {
        return convert_to_json($formatted_data);
    } elseif ($type === 'csv') {
        return convert_to_csv($formatted_data);
    }

    return null;
}

// Beispielaufruf der Funktion
if (isset($_GET['verb']) && isset($_GET['type'])) {
    $verb = $_GET['verb'];
    $type = $_GET['type'];
    $output = call_web_scraper($verb, $type);

    if ($type === 'json') {
        header('Content-Type: application/json');
        echo $output;
    } elseif ($type === 'csv') {
        header('Content-Type: text/csv');
        header('Content-Disposition: attachment; filename="output.csv"');
        echo $output;
    }
} else {
    echo "Please apend a verb and format (json or csv) at the end";
}
?>
