#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import shutil
import platform
from collections import deque, Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import urllib.request
import urllib.error
import urllib.parse

from deep_translator import GoogleTranslator


TRANSLATABLE_DICT_KEYS = {
    "label",
    "description",
    "name",
    "text",
    "title",
    "speakText",
    "pronunciation",
}

GOOGLE_LANG_MAP = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "he": "iw",
    "jw": "jv",
    "fil": "tl",
    "pt-br": "pt",
    "pt-pt": "pt",
    "en-us": "en",
    "en-gb": "en",
}

GOOGLE_SUPPORTED_LANGS = {
    "af": "afrikaans",
    "sq": "albanian",
    "am": "amharic",
    "ar": "arabic",
    "hy": "armenian",
    "as": "assamese",
    "ay": "aymara",
    "az": "azerbaijani",
    "bm": "bambara",
    "eu": "basque",
    "be": "belarusian",
    "bn": "bengali",
    "bho": "bhojpuri",
    "bs": "bosnian",
    "bg": "bulgarian",
    "ca": "catalan",
    "ceb": "cebuano",
    "ny": "chichewa",
    "zh-CN": "chinese (simplified)",
    "zh-TW": "chinese (traditional)",
    "co": "corsican",
    "hr": "croatian",
    "cs": "czech",
    "da": "danish",
    "dv": "dhivehi",
    "doi": "dogri",
    "nl": "dutch",
    "en": "english",
    "eo": "esperanto",
    "et": "estonian",
    "ee": "ewe",
    "tl": "filipino",
    "fi": "finnish",
    "fr": "french",
    "fy": "frisian",
    "gl": "galician",
    "ka": "georgian",
    "de": "german",
    "el": "greek",
    "gn": "guarani",
    "gu": "gujarati",
    "ht": "haitian creole",
    "ha": "hausa",
    "haw": "hawaiian",
    "iw": "hebrew",
    "hi": "hindi",
    "hmn": "hmong",
    "hu": "hungarian",
    "is": "icelandic",
    "ig": "igbo",
    "ilo": "ilocano",
    "id": "indonesian",
    "ga": "irish",
    "it": "italian",
    "ja": "japanese",
    "jv": "javanese",
    "kn": "kannada",
    "kk": "kazakh",
    "km": "khmer",
    "rw": "kinyarwanda",
    "gom": "konkani",
    "ko": "korean",
    "kri": "krio",
    "ku": "kurdish (kurmanji)",
    "ckb": "kurdish (sorani)",
    "ky": "kyrgyz",
    "lo": "lao",
    "la": "latin",
    "lv": "latvian",
    "ln": "lingala",
    "lt": "lithuanian",
    "lg": "luganda",
    "lb": "luxembourgish",
    "mk": "macedonian",
    "mai": "maithili",
    "mg": "malagasy",
    "ms": "malay",
    "ml": "malayalam",
    "mt": "maltese",
    "mi": "maori",
    "mr": "marathi",
    "mni-Mtei": "meiteilon (manipuri)",
    "lus": "mizo",
    "mn": "mongolian",
    "my": "myanmar",
    "ne": "nepali",
    "no": "norwegian",
    "or": "odia",
    "om": "oromo",
    "ps": "pashto",
    "fa": "persian",
    "pl": "polish",
    "pt": "portuguese",
    "pa": "punjabi",
    "qu": "quechua",
    "ro": "romanian",
    "ru": "russian",
    "sm": "samoan",
    "sa": "sanskrit",
    "gd": "scots gaelic",
    "nso": "sepedi",
    "sr": "serbian",
    "st": "sesotho",
    "sn": "shona",
    "sd": "sindhi",
    "si": "sinhala",
    "sk": "slovak",
    "sl": "slovenian",
    "so": "somali",
    "es": "spanish",
    "su": "sundanese",
    "sw": "swahili",
    "sv": "swedish",
    "tg": "tajik",
    "ta": "tamil",
    "tt": "tatar",
    "te": "telugu",
    "th": "thai",
    "ti": "tigrinya",
    "ts": "tsonga",
    "tr": "turkish",
    "tk": "turkmen",
    "ak": "twi",
    "uk": "ukrainian",
    "ur": "urdu",
    "ug": "uyghur",
    "uz": "uzbek",
    "vi": "vietnamese",
    "cy": "welsh",
    "xh": "xhosa",
    "yi": "yiddish",
    "yo": "yoruba",
    "zu": "zulu",
}


def is_lang_code(key: str) -> bool:
    if not isinstance(key, str):
        return False
    k = key.lower().replace("_", "-")
    parts = k.split("-")
    if len(parts) == 1:
        return len(parts[0]) in (2, 3) and parts[0].isalpha()
    if len(parts) == 2:
        return (
            len(parts[0]) in (2, 3)
            and parts[0].isalpha()
            and len(parts[1]) in (2, 8)
            and parts[1].isalnum()
        )
    return False


def normalize_lang(lang: str) -> str:
    return (lang or "").strip().replace("_", "-").lower()


def base_lang(lang: str) -> str:
    return normalize_lang(lang).split("-")[0]


def map_google_lang(lang: str) -> str:
    lang = normalize_lang(lang)
    return GOOGLE_LANG_MAP.get(lang, GOOGLE_LANG_MAP.get(base_lang(lang), base_lang(lang)))


def looks_like_translation_map(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    keys = list(value.keys())
    lang_like = [k for k in keys if is_lang_code(k)]
    return len(lang_like) > 0 and len(lang_like) == len(keys)


def choose_source_translation(translations: Dict[str, Any], preferred=("en", "en-us", "en-gb", "de")):
    normalized = {normalize_lang(k): v for k, v in translations.items()}
    for lang in preferred:
        if lang in normalized and isinstance(normalized[lang], str) and normalized[lang].strip():
            return lang, normalized[lang]
    for k, v in normalized.items():
        if isinstance(v, str) and v.strip():
            return k, v
    return None, None


def collect_used_languages(obj: Any, langs: Set[str]) -> None:
    if isinstance(obj, dict):
        if looks_like_translation_map(obj):
            langs.update(normalize_lang(k) for k in obj.keys())
        if "lang" in obj and isinstance(obj["lang"], str) and obj["lang"].strip():
            langs.add(normalize_lang(obj["lang"]))
        for v in obj.values():
            collect_used_languages(v, langs)
    elif isinstance(obj, list):
        for item in obj:
            collect_used_languages(item, langs)


def should_fill_dict(parent_key: str, obj: Dict[str, Any]) -> bool:
    if looks_like_translation_map(obj):
        return True
    if parent_key in TRANSLATABLE_DICT_KEYS:
        lang_keys = [k for k in obj.keys() if is_lang_code(k)]
        return len(lang_keys) > 0
    return False


def summarize_languages(langs: Set[str]) -> List[str]:
    return sorted(langs, key=lambda x: (base_lang(x), x))


def load_json_with_bom(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def shorten(text: str, width: int) -> str:
    text = str(text).replace("\n", " ").replace("\r", " ")
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def default_ui_mode():
    if platform.system().lower().startswith("win"):
        return "plain"
    return "ansi"


def parse_languages_arg(value: Optional[str]) -> Optional[Set[str]]:
    if not value:
        return None
    result = set()
    for part in value.split(","):
        p = normalize_lang(part)
        if p:
            result.add(p)
    return result if result else None


def language_display_name(provider: str, lang: str) -> str:
    if provider == "google":
        mapped = map_google_lang(lang)
        return GOOGLE_SUPPORTED_LANGS.get(mapped, GOOGLE_SUPPORTED_LANGS.get(base_lang(mapped), "unknown"))
    return "unknown"


def supported_languages_help_text() -> str:
    lines = []
    lines.append("Supported language codes for --provider google:")
    for code in sorted(GOOGLE_SUPPORTED_LANGS.keys(), key=lambda c: c.lower()):
        lines.append(f"  {code:10} {GOOGLE_SUPPORTED_LANGS[code]}")
    lines.append("")
    lines.append("Examples:")
    lines.append("  python translateGrid.py backup.grd --languages es,de")
    lines.append('  python translateGrid.py backup.grd --keeponly "de,en,es"')
    lines.append('  python translateGrid.py backup.grd --keeponly "de,en,es" --languages es,de')
    lines.append("  python translateGrid.py backup.grd --ui plain")
    lines.append("")
    lines.append("Notes:")
    lines.append("  - --languages restricts which target languages are filled")
    lines.append("  - --keeponly removes all other languages from the .grd before translation")
    lines.append("  - source languages already present in the GRD are still used as translation sources")
    lines.append("  - provider google internally maps some codes, e.g. he->iw, zh->zh-CN")
    return "\n".join(lines)


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    pass


class TerminalUI:
    def __init__(self, mode: str = "ansi", log_lines: int = 10):
        self.mode = mode
        self.enabled = mode != "off"
        self.log_lines = log_lines
        self.logs = deque(maxlen=log_lines)
        self.current_text = ""
        self.current_meta = ""
        self.total = 0
        self.done = 0
        self.stats = {}
        self.start_time = time.time()
        self.last_render = 0.0
        self.render_interval = 0.2

    def log(self, message: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.logs.append(entry)
        if self.mode == "plain":
            print(entry)
        elif self.mode == "ansi":
            self.render(force=True)

    def set_total(self, total: int):
        self.total = total
        if self.mode == "ansi":
            self.render(force=True)

    def set_progress(self, done: int, current_text: str = "", current_meta: str = "", stats: Optional[Dict] = None):
        self.done = done
        if current_text is not None:
            self.current_text = current_text
        if current_meta is not None:
            self.current_meta = current_meta
        if stats is not None:
            self.stats = stats

        if self.mode == "ansi":
            self.render()
        elif self.mode == "plain":
            self.render_plain()

    def render_plain(self):
        now = time.time()
        if now - self.last_render < self.render_interval:
            return
        self.last_render = now

        pct = 0 if self.total == 0 else (self.done / self.total) * 100
        attempts = self.stats.get("attempts", 0)
        success = self.stats.get("success", 0)
        failed = self.stats.get("failed", 0)
        cached = self.stats.get("cached", 0)

        print(
            f"[{pct:6.2f}%] {self.done}/{self.total} "
            f"attempts={attempts} success={success} failed={failed} cached={cached}"
        )
        print(f"  {shorten(self.current_meta, 120)}")
        print(f"  {shorten(self.current_text, 120)}")

    def render(self, force: bool = False):
        if self.mode != "ansi":
            return

        now = time.time()
        if not force and now - self.last_render < self.render_interval:
            return
        self.last_render = now

        cols = shutil.get_terminal_size((100, 30)).columns
        bar_width = max(10, min(50, cols - 40))
        pct = 0 if self.total == 0 else min(1.0, self.done / self.total)
        filled = int(bar_width * pct)
        bar = "█" * filled + "░" * (bar_width - filled)

        attempts = self.stats.get("attempts", 0)
        success = self.stats.get("success", 0)
        failed = self.stats.get("failed", 0)
        skipped = self.stats.get("skipped", 0)
        cached = self.stats.get("cached", 0)

        elapsed = int(time.time() - self.start_time)
        eta = 0
        if self.done > 0 and self.total > self.done:
            eta = int((elapsed / self.done) * (self.total - self.done))

        out = []
        out.append("\x1b[H")
        out.append("\x1b[J")
        out.append("GRD Translation Progress")
        out.append(f"[{bar}] {pct * 100:6.2f}%  {self.done}/{self.total}  elapsed={elapsed}s  eta={eta}s")
        out.append(
            f"attempts={attempts}  success={success}  failed={failed}  skipped={skipped}  cached={cached}"
        )
        out.append("")
        out.append("Current translation")
        out.append("┌" + "─" * (cols - 2) + "┐")
        out.append("│ " + shorten(self.current_meta, cols - 4).ljust(cols - 4) + " │")
        out.append("│ " + shorten(self.current_text, cols - 4).ljust(cols - 4) + " │")
        out.append("└" + "─" * (cols - 2) + "┘")
        out.append("")
        out.append("Logs")
        out.append("┌" + "─" * (cols - 2) + "┐")
        visible_logs = list(self.logs)[-self.log_lines :]
        while len(visible_logs) < self.log_lines:
            visible_logs.insert(0, "")
        for msg in visible_logs:
            out.append("│ " + shorten(msg, cols - 4).ljust(cols - 4) + " │")
        out.append("└" + "─" * (cols - 2) + "┘")

        sys.stdout.write("\x1b[?25l")
        sys.stdout.write("\n".join(out))
        sys.stdout.flush()

    def finish(self):
        if self.mode == "ansi":
            self.render(force=True)
            sys.stdout.write("\x1b[?25h\n")
            sys.stdout.flush()


class RunStats:
    def __init__(self):
        self.attempts = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.cached = 0
        self.filled_translation_entries = 0
        self.added_wordforms = 0
        self.error_counter = Counter()

    def as_dict(self):
        return {
            "attempts": self.attempts,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "cached": self.cached,
            "filled_translation_entries": self.filled_translation_entries,
            "added_wordforms": self.added_wordforms,
        }


class Translator:
    def __init__(
        self,
        provider: str = "google",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        retries: int = 3,
        retry_delay: float = 2.0,
        dry_run: bool = False,
        stats: Optional[RunStats] = None,
        ui: Optional[TerminalUI] = None,
    ):
        self.provider = provider.lower()
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.dry_run = dry_run
        self.cache: Dict[Tuple[str, str, str], str] = {}
        self.stats = stats or RunStats()
        self.ui = ui

        if self.provider == "google":
            self.api_url = None
        elif self.provider == "libretranslate":
            self.api_url = self.api_url or "https://libretranslate.de/translate"
        elif self.provider == "deepl":
            self.api_url = self.api_url or "https://api-free.deepl.com/v2/translate"
        elif self.provider == "openai":
            self.api_url = self.api_url or "https://api.openai.com/v1/chat/completions"
            self.model = self.model or "gpt-4.1-mini"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        source_lang = normalize_lang(source_lang)
        target_lang = normalize_lang(target_lang)

        if not text or source_lang == target_lang:
            self.stats.skipped += 1
            return text

        key = (text, source_lang, target_lang)
        if key in self.cache:
            self.stats.cached += 1
            return self.cache[key]

        self.stats.attempts += 1

        if self.dry_run:
            translated = f"[{target_lang}] {text}"
            self.cache[key] = translated
            self.stats.success += 1
            return translated

        if self.provider == "google":
            translated = self._translate_google(text, source_lang, target_lang)
        elif self.provider == "libretranslate":
            translated = self._translate_libretranslate(text, source_lang, target_lang)
        elif self.provider == "deepl":
            translated = self._translate_deepl(text, source_lang, target_lang)
        elif self.provider == "openai":
            translated = self._translate_openai(text, source_lang, target_lang)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        self.cache[key] = translated
        self.stats.success += 1
        return translated

    def _translate_google(self, text: str, source_lang: str, target_lang: str) -> str:
        src = map_google_lang(source_lang) or "auto"
        dst = map_google_lang(target_lang)
        translator = GoogleTranslator(source=src, target=dst)
        return translator.translate(text)

    def _request_with_retries(self, request_fn):
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                return request_fn()
            except Exception as e:
                last_error = e
                if attempt < self.retries:
                    if self.ui:
                        self.ui.log(f"retry {attempt}/{self.retries - 1} after error: {e}")
                    time.sleep(self.retry_delay * attempt)
                else:
                    raise last_error

    def _post_json(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        def do_request():
            data = json.dumps(payload).encode("utf-8")
            merged_headers = {
                "User-Agent": "grd-translation-tool/1.0",
                **headers,
            }
            req = urllib.request.Request(url, data=data, headers=merged_headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)

        return self._request_with_retries(do_request)

    def _post_form(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        def do_request():
            data = urllib.parse.urlencode(payload).encode("utf-8")
            merged_headers = {
                "User-Agent": "grd-translation-tool/1.0",
                **headers,
            }
            req = urllib.request.Request(url, data=data, headers=merged_headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)

        return self._request_with_retries(do_request)

    def _translate_libretranslate(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            "q": text,
            "source": base_lang(source_lang),
            "target": base_lang(target_lang),
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        result = self._post_json(self.api_url, payload, headers)
        return result.get("translatedText", text)

    def _translate_deepl(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self.api_key:
            raise ValueError("DeepL requires --api-key or DEEPL_API_KEY")
        payload = {
            "text": text,
            "source_lang": base_lang(source_lang).upper(),
            "target_lang": base_lang(target_lang).upper(),
        }
        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        result = self._post_form(self.api_url, payload, headers)
        translations = result.get("translations", [])
        if translations:
            return translations[0].get("text", text)
        return text

    def _translate_openai(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self.api_key:
            raise ValueError("OpenAI requires --api-key or OPENAI_API_KEY")

        system_prompt = (
            "You are a translation engine. Translate accurately. "
            "Return only the translated text. Preserve placeholders like {0}, {name}, %s, HTML tags, and line breaks."
        )
        user_prompt = (
            f"Translate this text from {source_lang} to {target_lang}. "
            f"Preserve meaning, punctuation, placeholders, short AAC labels, and markup.\n\n{text}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        result = self._post_json(self.api_url, payload, headers)
        return result["choices"][0]["message"]["content"].strip()


def probe_provider(translator, ui=None):
    sample_text = "Hello"
    source_lang = "en"
    target_lang = "de"
    try:
        if ui:
            ui.log(f"probing provider with {source_lang}->{target_lang}: '{sample_text}'")
        result = translator.translate(sample_text, source_lang, target_lang)
        if ui:
            ui.log(f"provider probe OK: '{result}'")
        return True, result
    except Exception as e:
        if ui:
            ui.log(f"provider probe FAILED: {e}")
        return False, str(e)


def prune_to_languages(obj: Any, keep_langs: Set[str]) -> None:
    if isinstance(obj, dict):
        if looks_like_translation_map(obj):
            keys_to_delete = [k for k in list(obj.keys()) if normalize_lang(k) not in keep_langs]
            for k in keys_to_delete:
                del obj[k]

        if "wordForms" in obj and isinstance(obj["wordForms"], list):
            filtered = []
            for wf in obj["wordForms"]:
                if not isinstance(wf, dict):
                    filtered.append(wf)
                    continue
                lang = normalize_lang(wf.get("lang", ""))
                if not lang or lang in keep_langs:
                    filtered.append(wf)
            obj["wordForms"] = filtered

        for v in list(obj.values()):
            prune_to_languages(v, keep_langs)

    elif isinstance(obj, list):
        for item in obj:
            prune_to_languages(item, keep_langs)


def count_translation_tasks(
    obj: Any,
    used_langs: List[str],
    selected_langs: Optional[Set[str]] = None,
    translate_wordforms: bool = True,
    parent_key: str = "",
) -> int:
    total = 0
    if isinstance(obj, dict):
        if should_fill_dict(parent_key, obj):
            normalized_map = {normalize_lang(k): v for k, v in obj.items()}
            source_lang, source_text = choose_source_translation(normalized_map)
            if source_text:
                for lang in used_langs:
                    if selected_langs and normalize_lang(lang) not in selected_langs:
                        continue
                    if lang not in normalized_map or normalized_map[lang] in (None, ""):
                        if normalize_lang(source_lang) != normalize_lang(lang):
                            total += 1

        if translate_wordforms and "wordForms" in obj and isinstance(obj["wordForms"], list):
            by_lang = {}
            for wf in obj["wordForms"]:
                if isinstance(wf, dict):
                    lang = normalize_lang(wf.get("lang", ""))
                    if lang:
                        by_lang.setdefault(lang, []).append(wf)

            template = None
            for wf_list in by_lang.values():
                if wf_list:
                    template = wf_list[0]
                    break

            if template is not None:
                existing_langs = set(by_lang.keys())
                for lang in used_langs:
                    if selected_langs and normalize_lang(lang) not in selected_langs:
                        continue
                    if lang not in existing_langs:
                        if isinstance(template.get("value"), str) and template["value"].strip():
                            total += 1
                        if isinstance(template.get("pronunciation"), str) and template["pronunciation"].strip():
                            total += 1

        for k, v in obj.items():
            total += count_translation_tasks(v, used_langs, selected_langs, translate_wordforms, k)

    elif isinstance(obj, list):
        for item in obj:
            total += count_translation_tasks(item, used_langs, selected_langs, translate_wordforms, parent_key)

    return total


def fill_missing_translations(
    obj: Any,
    used_langs: List[str],
    selected_langs: Optional[Set[str]],
    translator: Translator,
    stats: RunStats,
    ui: TerminalUI,
    progress: Dict[str, int],
    parent_key: str = "",
    translate_wordforms: bool = True,
    path: str = "$",
) -> None:
    if isinstance(obj, dict):
        if should_fill_dict(parent_key, obj):
            normalized_map = {normalize_lang(k): v for k, v in list(obj.items())}
            source_lang, source_text = choose_source_translation(normalized_map)

            if source_text:
                for lang in used_langs:
                    if selected_langs and normalize_lang(lang) not in selected_langs:
                        continue
                    if lang not in normalized_map or normalized_map[lang] in (None, ""):
                        if normalize_lang(source_lang) == normalize_lang(lang):
                            continue
                        meta = f"{path}.{parent_key}  {source_lang} -> {lang}"
                        ui.set_progress(progress["done"], current_text=source_text, current_meta=meta, stats=stats.as_dict())
                        try:
                            translated = translator.translate(source_text, source_lang, lang)
                            obj[lang] = translated
                            stats.filled_translation_entries += 1
                            progress["done"] += 1
                            ui.set_progress(progress["done"], current_text=source_text, current_meta=meta, stats=stats.as_dict())
                        except Exception as e:
                            stats.failed += 1
                            stats.error_counter[str(e)] += 1
                            progress["done"] += 1
                            ui.log(f"FAIL {meta}: {e}")
                            ui.set_progress(progress["done"], current_text=source_text, current_meta=meta, stats=stats.as_dict())

        if translate_wordforms and "wordForms" in obj and isinstance(obj["wordForms"], list):
            by_lang: Dict[str, List[Dict[str, Any]]] = {}
            for wf in obj["wordForms"]:
                if isinstance(wf, dict):
                    lang = normalize_lang(wf.get("lang", ""))
                    if lang:
                        by_lang.setdefault(lang, []).append(wf)

            template = None
            for wf_list in by_lang.values():
                if wf_list:
                    template = wf_list[0]
                    break

            if template is not None:
                existing_langs = set(by_lang.keys())
                source_lang = normalize_lang(template.get("lang", ""))
                for lang in used_langs:
                    if selected_langs and normalize_lang(lang) not in selected_langs:
                        continue
                    if lang not in existing_langs:
                        new_wf = deepcopy(template)
                        new_wf["lang"] = lang

                        if isinstance(new_wf.get("value"), str) and new_wf["value"].strip():
                            meta = f"{path}.wordForms.value  {source_lang} -> {lang}"
                            text = new_wf["value"]
                            ui.set_progress(progress["done"], current_text=text, current_meta=meta, stats=stats.as_dict())
                            try:
                                new_wf["value"] = translator.translate(text, source_lang, lang)
                            except Exception as e:
                                stats.failed += 1
                                stats.error_counter[str(e)] += 1
                                ui.log(f"FAIL {meta}: {e}")
                            progress["done"] += 1
                            ui.set_progress(progress["done"], current_text=text, current_meta=meta, stats=stats.as_dict())

                        if isinstance(new_wf.get("pronunciation"), str) and new_wf["pronunciation"].strip():
                            meta = f"{path}.wordForms.pronunciation  {source_lang} -> {lang}"
                            text = new_wf["pronunciation"]
                            ui.set_progress(progress["done"], current_text=text, current_meta=meta, stats=stats.as_dict())
                            try:
                                new_wf["pronunciation"] = translator.translate(text, source_lang, lang)
                            except Exception as e:
                                stats.failed += 1
                                stats.error_counter[str(e)] += 1
                                ui.log(f"FAIL {meta}: {e}")
                            progress["done"] += 1
                            ui.set_progress(progress["done"], current_text=text, current_meta=meta, stats=stats.as_dict())

                        obj["wordForms"].append(new_wf)
                        stats.added_wordforms += 1

        for k, v in obj.items():
            next_path = f"{path}.{k}" if path != "$" else f"$.{k}"
            fill_missing_translations(
                v,
                used_langs,
                selected_langs,
                translator,
                stats,
                ui,
                progress,
                k,
                translate_wordforms,
                next_path,
            )

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            next_path = f"{path}[{i}]"
            fill_missing_translations(
                item,
                used_langs,
                selected_langs,
                translator,
                stats,
                ui,
                progress,
                parent_key,
                translate_wordforms,
                next_path,
            )


def build_parser() -> argparse.ArgumentParser:
    description = (
        "Analyze Asterics AAC .grd files, count languages, and fill missing translations using external APIs.\n\n"
        + supported_languages_help_text()
    )
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=CustomHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="Path to input .grd file")
    parser.add_argument("-o", "--output", help="Output file path (default: <input>.translated.grd)")
    parser.add_argument("--report-only", action="store_true", help="Only report used languages")
    parser.add_argument(
        "--provider",
        choices=["google", "libretranslate", "deepl", "openai"],
        default="google",
        help="Translation provider (default: google via deep-translator)",
    )
    parser.add_argument(
        "--languages",
        help="Comma-separated target languages to fill, e.g. es,de or zh,he,ja. If omitted, all used languages are filled.",
    )
    parser.add_argument(
        "--keeponly",
        help='Comma-separated language list to keep in the .grd file, e.g. "de,en,es". '
             "All other languages are removed from translation maps and wordForms before translation.",
    )
    parser.add_argument("--api-url", help="Override provider API URL")
    parser.add_argument("--api-key", help="API key for DeepL/OpenAI, or LibreTranslate if needed")
    parser.add_argument("--model", help="Model name for OpenAI")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries for API calls")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Base retry delay in seconds")
    parser.add_argument("--no-wordforms", action="store_true", help="Do not translate/add missing wordForms")
    parser.add_argument("--dry-run-translate", action="store_true", help="Fake translation without calling APIs")
    parser.add_argument(
        "--ui",
        choices=["ansi", "plain", "off"],
        default=default_ui_mode(),
        help="UI mode: ansi, plain, or off. Default: plain on Windows, ansi elsewhere.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".translated.grd")
    selected_langs = parse_languages_arg(args.languages)
    keep_only_langs = parse_languages_arg(args.keeponly)

    api_key = args.api_key
    if not api_key:
        if args.provider == "deepl":
            api_key = os.getenv("DEEPL_API_KEY")
        elif args.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif args.provider == "libretranslate":
            api_key = os.getenv("LIBRETRANSLATE_API_KEY")

    data = load_json_with_bom(input_path)

    if not isinstance(data, dict) or not any(k in data for k in ("grids", "metadata", "dictionaries")):
        raise ValueError("Input does not look like a valid Asterics AAC .grd backup file")

    used_langs: Set[str] = set()
    collect_used_languages(data, used_langs)
    used_langs_list = summarize_languages(used_langs)

    print("Used languages in file:")
    for lang in used_langs_list:
        print(f" - {lang}")

    if keep_only_langs:
        print("\nKeeping only languages:")
        for lang in sorted(keep_only_langs):
            print(f" - {lang} ({language_display_name(args.provider, lang)})")

        prune_to_languages(data, keep_only_langs)

        used_langs = set()
        collect_used_languages(data, used_langs)
        used_langs_list = summarize_languages(used_langs)

        print("\nLanguages in file after --keeponly pruning:")
        for lang in used_langs_list:
            print(f" - {lang}")

    if selected_langs and keep_only_langs:
        selected_langs = {lang for lang in selected_langs if lang in keep_only_langs}

    if selected_langs:
        print("\nRestricted target languages:")
        for lang in sorted(selected_langs):
            print(f" - {lang} ({language_display_name(args.provider, lang)})")

    print(f"\nLanguage count in file: {len(used_langs_list)}")

    if args.report_only:
        return

    stats = RunStats()
    ui = TerminalUI(mode=args.ui, log_lines=10)
    total_tasks = count_translation_tasks(
        data,
        used_langs_list,
        selected_langs=selected_langs,
        translate_wordforms=not args.no_wordforms,
    )
    ui.set_total(total_tasks)
    ui.log(f"provider={args.provider}")
    ui.log(f"ui={args.ui}")
    ui.log(f"api_url={args.api_url or '(n/a)'}")
    ui.log(f"used_languages={', '.join(used_langs_list)}")
    ui.log(f"selected_languages={', '.join(sorted(selected_langs)) if selected_langs else '(all used languages)'}")
    ui.log(f"keep_only_languages={', '.join(sorted(keep_only_langs)) if keep_only_langs else '(none)'}")
    ui.log(f"planned translation tasks={total_tasks}")

    translator = Translator(
        provider=args.provider,
        api_url=args.api_url,
        api_key=api_key,
        model=args.model,
        timeout=args.timeout,
        retries=args.retries,
        retry_delay=args.retry_delay,
        dry_run=args.dry_run_translate,
        stats=stats,
        ui=ui,
    )

    ok, probe_result = probe_provider(translator, ui)

    if not ok:
        ui.finish()
        print("\nProvider check failed before processing the file.")
        print(f"Provider: {args.provider}")
        print(f"API URL: {translator.api_url or '(n/a)'}")
        print(f"Error: {probe_result}")
        print("\nSuggested fixes:")
        print(" - try again later if using google/deep-translator")
        print(" - switch to --provider openai or --provider deepl")
        print(" - for libretranslate, use --api-url with a working instance")
        sys.exit(2)

    progress = {"done": 0}

    fill_missing_translations(
        data,
        used_langs_list,
        selected_langs,
        translator,
        stats,
        ui,
        progress,
        translate_wordforms=not args.no_wordforms,
    )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    ui.log(f"output written to: {output_path}")
    ui.finish()

    print("Summary")
    print("-------")
    print(f"Provider: {args.provider}")
    print(f"UI mode: {args.ui}")
    print(f"API URL: {translator.api_url or '(n/a)'}")
    print(f"Output: {output_path}")
    print(f"Attempts: {stats.attempts}")
    print(f"Success: {stats.success}")
    print(f"Failed: {stats.failed}")
    print(f"Skipped: {stats.skipped}")
    print(f"Cached: {stats.cached}")
    print(f"Filled translation entries: {stats.filled_translation_entries}")
    print(f"Added wordForms: {stats.added_wordforms}")

    if stats.error_counter:
        print("\nTop errors:")
        for err, count in stats.error_counter.most_common(10):
            print(f" - {count}x {err}")


if __name__ == "__main__":
    main()