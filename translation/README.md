# TranslateGrid: a translation tool for Asterics AAC grid files

A Python utility for analyzing and modifying Asterics AAC `.grd` backup files.

It can:

- detect which languages are used in a `.grd` file
- fill missing translations for selected or all used languages
- prune the file so that only selected languages remain
- translate using different providers
- show progress and logs during translation

## Features

- Reads `.grd` files as JSON, including files with UTF-8 BOM
- Detects languages from:
  - translation maps like `{ "en": "Hello", "de": "Hallo" }`
  - `wordForms[].lang`
- Supports translation providers:
  - `google` via `deep-translator` (default)
  - `libretranslate`
  - `deepl`
  - `openai`
- Supports:
  - `--languages` to restrict which target languages should be filled
  - `--keeponly` to remove all other languages from the file
- Progress UI:
  - `ansi`
  - `plain`
  - `off`

## Installation

### Requirements

- Python 3.9+
- `deep-translator`

Install:

```bash
pip install deep-translator
```

## Basic usage

### Analyze a file

```bash
python translateGrid.py backup.grd --report-only
```

### Fill missing translations in all used languages

```bash
python translateGrid.py backup.grd
```

### Add (or fill) selected target languages

```bash
python translateGrid.py backup.grd --languages es,de
```

This means:
- Spanish and German will be added (or filled if partly missing)
- other languages in the file are left unchanged

### Keep only selected languages

```bash
python translateGrid.py backup.grd --keeponly "de,en,es"
```

This means:
- all translation-map entries not in `de,en,es` are removed
- all `wordForms` with explicit other languages are removed
- language-neutral word forms are preserved

### Combine both options

```bash
python translateGrid.py backup.grd --keeponly "de,en,es" --languages es,de
```

This means:
1. the file is first reduced to only `de`, `en`, and `es`
2. then only missing `es` and `de` translations are generated

## Providers

## 1. Google via deep-translator (default)

```bash
python translateGrid.py backup.grd --provider google
```

Notes:
- free/unofficial
- no API key required
- uses `deep-translator`
- some language codes are internally mapped:
  - `he -> iw`
  - `zh -> zh-CN`
  - `zh-tw -> zh-TW`
  - `pt-br -> pt`

## 2. LibreTranslate

```bash
python translateGrid.py backup.grd \
  --provider libretranslate \
  --api-url http://localhost:5000/translate
```

Optional:
```bash
--api-key YOUR_KEY
```

Notes:
- public instances may fail or rate-limit
- self-hosted instance recommended

## 3. DeepL

```bash
export DEEPL_API_KEY=your_key
python translateGrid.py backup.grd --provider deepl
```

Or:

```bash
python translateGrid.py backup.grd --provider deepl --api-key your_key
```

## 4. OpenAI

```bash
export OPENAI_API_KEY=your_key
python translateGrid.py backup.grd --provider openai --model gpt-4.1-mini
```

Or:

```bash
python translateGrid.py backup.grd \
  --provider openai \
  --api-key your_key \
  --model gpt-4.1-mini
```

## Command line options

### Positional argument

- `input`  
  Path to the input `.grd` file

### General options

- `-o, --output`  
  Output file path  
  Default: `<input>.translated.grd`

- `--report-only`  
  Only analyze the file and print used languages; do not modify anything

### Translation scope

- `--languages es,de`  
  Restrict translation targets to these languages only

- `--keeponly "de,en,es"`  
  Remove all languages from the `.grd` file except those listed

### Provider selection

- `--provider google|libretranslate|deepl|openai`  
  Select translation provider  
  Default: `google`

- `--api-url URL`  
  Override API URL for providers that use HTTP endpoints

- `--api-key KEY`  
  API key for DeepL, OpenAI, or LibreTranslate if required

- `--model MODEL`  
  Model name for OpenAI

### Execution behavior

- `--timeout 60`  
  HTTP timeout in seconds

- `--retries 3`  
  Number of retries for provider/API calls

- `--retry-delay 2.0`  
  Base retry delay in seconds

- `--no-wordforms`  
  Do not translate or add missing `wordForms`

- `--dry-run-translate`  
  Do not call real translation APIs; simulate translations

- `--minify`  
  minify the resulting JSON file to reduce the file size


### UI

- `--ui ansi|plain|off`  
  Progress display mode

Defaults:
- Windows: `plain`
- other systems: `ansi`

Recommended on Windows:

```bash
python translateGrid.py backup.grd --ui plain
```

## What counts as a translation map

The tool detects translation maps as objects like:

```json
{
  "en": "Hello",
  "de": "Hallo",
  "es": "Hola"
}
```

It also considers certain common keys as translatable when they contain language-keyed objects, such as:

- `label`
- `description`
- `name`
- `text`
- `title`
- `speakText`
- `pronunciation`

## How missing translations are filled

For each translation map:

1. The script chooses a source language/value, preferring:
   - `en`
   - `en-us`
   - `en-gb`
   - `de`
   - otherwise the first non-empty entry

2. For each selected target language that is missing:
   - it translates the source text
   - stores the result in that language key

## Word forms behavior

If `wordForms` are present and `--no-wordforms` is not used:

- the script detects which languages already have word forms
- for missing target languages, it clones one existing word form template
- then translates:
  - `value`
  - `pronunciation` if present

### Important
Word forms without a `lang` field are preserved even when `--keeponly` is used.

## Examples

### Report only

```bash
python translateGrid.py backup.grd --report-only
```

### Translate only Spanish and German

```bash
python translateGrid.py backup.grd --languages es,de
```

### Keep only German, English, Spanish

```bash
python translateGrid.py backup.grd --keeponly "de,en,es"
```

### Keep only German, English, Spanish and fill only German/Spanish

```bash
python translateGrid.py backup.grd --keeponly "de,en,es" --languages es,de
```

### Use plain console mode

```bash
python translateGrid.py backup.grd --ui plain
```

### Minified output

Use the `--minify` flag to write compact JSON output (no indentation), which can reduce file size.

```bash
python translateGrid.py backup.grd --minify
```

### Simulate translations without API calls

```bash
python translateGrid.py backup.grd --dry-run-translate
```

### Use LibreTranslate

```bash
python translateGrid.py backup.grd \
  --provider libretranslate \
  --api-url http://localhost:5000/translate
```

### Use DeepL

```bash
python translateGrid.py backup.grd --provider deepl --api-key YOUR_KEY
```

### Use OpenAI

```bash
python translateGrid.py backup.grd \
  --provider openai \
  --api-key YOUR_KEY \
  --model gpt-4.1-mini
```

## Output

The script writes a translated `.grd` file to:

```text
<input>.translated.grd
```

unless `--output` is specified.

At the end it prints a summary including:

- attempts
- successes
- failures
- skipped
- cached
- number of filled translation entries
- number of added word forms
- top errors

## Supported Google language codes

Run:

```bash
python translateGrid.py --help
```

The help output includes all supported codes and language names for the default `google` provider.

## Notes and limitations

- Google via `deep-translator` is unofficial and may occasionally fail or rate-limit.
- Public LibreTranslate instances often reject automated traffic.
- DeepL and OpenAI require API keys.
- The script assumes `.grd` files follow the Asterics AAC JSON structure.
- Translation quality depends on the provider.

## Error handling

### `Unexpected UTF-8 BOM`
Handled automatically by reading with `utf-8-sig`.

### If ANSI UI does not work (e.g. on Windows)
Use:

```bash
--ui plain
```

### Unsupported language code
For Google, the script maps common codes automatically, such as:
- `he -> iw`
- `zh -> zh-CN`

### Provider probe fails
The script checks the provider before processing the whole file. If the probe fails:
- verify API key
- verify API URL
- try another provider


---

## GUI overview (`translateGridGui.py`)

A GUI wrapper is available to simplify common translation tasks.

Run it from the `translation` folder:

```bash
python translateGridGui.py
```

### What the GUI provides

- Input/output file picker for `.grd` files
- Provider selection (`google`, `libretranslate`, `deepl`, `openai`)
- Provider-specific fields shown only when needed:
  - `google`: no API fields
  - `libretranslate`: API URL (+ optional API key)
  - `deepl`: API key (+ optional API URL override)
  - `openai`: API key, model (+ optional API URL override)
- Language workflow mode selection:
  - **Add languages** → builds `--languages`
  - **Purge languages** → builds `--keeponly`
- Human-readable language picker (language code + name) that fills CSV fields
- Optional flags:
  - `--report-only`
  - `--no-wordforms`
  - `--dry-run-translate`
  - `--minify`
- Live processing output/log view while translation runs
- Start/Stop controls

### Notes

- The GUI launches `translateGrid.py` in unbuffered mode so logs appear during processing.
- Advanced execution parameters (UI mode, timeout, retries, retry delay) are intentionally left at script defaults in the GUI.
- This script is an external utility for working with Asterics AAC `.grd` files. Review generated translations before importing them back into production data.
