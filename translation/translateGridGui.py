#!/usr/bin/env python3
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Matches translateGrid.py google language support
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


class TranslateGridGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TranslateGrid GUI")
        self.geometry("1100x760")
        self.minsize(980, 680)

        self.proc = None
        self.log_queue = queue.Queue()

        self._build_language_maps()
        self._build_vars()
        self._build_ui()
        self._refresh_provider_fields()
        self._refresh_language_mode_visibility()
        self.after(100, self._poll_log_queue)

    def _build_language_maps(self):
        items = sorted(GOOGLE_SUPPORTED_LANGS.items(), key=lambda kv: kv[1].lower())
        self.lang_display_to_code = {f"{code} — {name}": code for code, name in items}
        self.lang_codes = [code for code, _ in items]
        self.lang_displays = list(self.lang_display_to_code.keys())

    def _build_vars(self):
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()

        self.provider_var = tk.StringVar(value="google")
        self.languages_var = tk.StringVar()
        self.keeponly_var = tk.StringVar()

        # mode radio state
        self.language_mode_var = tk.StringVar(value="add")

        self.api_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.model_var = tk.StringVar()

        self.report_only_var = tk.BooleanVar(value=False)
        self.no_wordforms_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.minify_var = tk.BooleanVar(value=False)

        self.add_lang_picker_var = tk.StringVar()
        self.keep_lang_picker_var = tk.StringVar()

    def _build_ui(self):
        pad_outer = {"padx": 10, "pady": 8}
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X, **pad_outer)

        # Files
        files_frame = ttk.LabelFrame(top, text="Files")
        files_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(files_frame, text="Input .grd").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(files_frame, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(files_frame, text="Browse...", command=self._pick_input).grid(row=0, column=2, padx=8, pady=6)

        ttk.Label(files_frame, text="Output .grd").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(files_frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(files_frame, text="Browse...", command=self._pick_output).grid(row=1, column=2, padx=8, pady=6)

        files_frame.columnconfigure(1, weight=1)

        # Provider
        provider_frame = ttk.LabelFrame(top, text="Provider")
        provider_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(provider_frame, text="Provider").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_var,
            values=["google", "libretranslate", "deepl", "openai"],
            state="readonly",
            width=20,
        )
        provider_combo.grid(row=0, column=1, sticky="w", padx=8, pady=6)
        provider_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_provider_fields())

        self.provider_specific_frame = ttk.Frame(provider_frame)
        self.provider_specific_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4, pady=2)
        self.provider_specific_frame.columnconfigure(1, weight=1)
        self.provider_specific_frame.columnconfigure(3, weight=1)

        self.api_url_label = ttk.Label(self.provider_specific_frame, text="API URL")
        self.api_url_entry = ttk.Entry(self.provider_specific_frame, textvariable=self.api_url_var)
        self.api_key_label = ttk.Label(self.provider_specific_frame, text="API Key")
        self.api_key_entry = ttk.Entry(self.provider_specific_frame, textvariable=self.api_key_var, show="*")
        self.model_label = ttk.Label(self.provider_specific_frame, text="Model")
        self.model_entry = ttk.Entry(self.provider_specific_frame, textvariable=self.model_var)

        # Languages
        lang_outer = ttk.LabelFrame(top, text="Languages")
        lang_outer.pack(fill=tk.X, pady=(0, 10))

        lang_center = ttk.Frame(lang_outer)
        lang_center.pack(anchor="center", pady=6)

        mode_row = ttk.Frame(lang_center)
        mode_row.grid(row=0, column=0, columnspan=4, pady=(0, 8))
        ttk.Radiobutton(
            mode_row,
            text="Add languages",
            value="add",
            variable=self.language_mode_var,
            command=self._refresh_language_mode_visibility,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(
            mode_row,
            text="Purge languages",
            value="purge",
            variable=self.language_mode_var,
            command=self._refresh_language_mode_visibility,
        ).pack(side=tk.LEFT, padx=8)

        # ADD block
        self.add_block = ttk.Frame(lang_center)
        self.add_block.grid(row=1, column=0, columnspan=4, sticky="ew")

        ttk.Label(self.add_block, text="Add Translations for these Languages:").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4)
        )

        self.add_lang_combo = ttk.Combobox(
            self.add_block,
            textvariable=self.add_lang_picker_var,
            values=self.lang_displays,
            width=38,
        )
        self.add_lang_combo.grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Button(self.add_block, text="Add", command=self._add_to_languages_csv, width=10).grid(
            row=1, column=1, padx=6, pady=4
        )
        ttk.Button(self.add_block, text="Clear", command=lambda: self.languages_var.set(""), width=10).grid(
            row=1, column=2, padx=6, pady=4
        )

        ttk.Entry(self.add_block, textvariable=self.languages_var, width=70, justify="center").grid(
            row=2, column=0, columnspan=4, padx=6, pady=(0, 10), sticky="ew"
        )

        # PURGE block
        self.purge_block = ttk.Frame(lang_center)
        self.purge_block.grid(row=2, column=0, columnspan=4, sticky="ew")

        ttk.Label(self.purge_block, text="Keep only these Languages:").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4)
        )

        self.keep_lang_combo = ttk.Combobox(
            self.purge_block,
            textvariable=self.keep_lang_picker_var,
            values=self.lang_displays,
            width=38,
        )
        self.keep_lang_combo.grid(row=1, column=0, padx=6, pady=4, sticky="w")
        ttk.Button(self.purge_block, text="Add", command=self._add_to_keeponly_csv, width=10).grid(
            row=1, column=1, padx=6, pady=4
        )
        ttk.Button(self.purge_block, text="Clear", command=lambda: self.keeponly_var.set(""), width=10).grid(
            row=1, column=2, padx=6, pady=4
        )

        ttk.Entry(self.purge_block, textvariable=self.keeponly_var, width=70, justify="center").grid(
            row=2, column=0, columnspan=4, padx=6, pady=(0, 6), sticky="ew"
        )

        # Flags
        flags_frame = ttk.LabelFrame(top, text="Flags")
        flags_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(flags_frame, text="Report only", variable=self.report_only_var).pack(side=tk.LEFT, padx=8, pady=6)
        ttk.Checkbutton(flags_frame, text="No wordForms", variable=self.no_wordforms_var).pack(side=tk.LEFT, padx=8, pady=6)
        ttk.Checkbutton(flags_frame, text="Dry run translate", variable=self.dry_run_var).pack(side=tk.LEFT, padx=8, pady=6)
        ttk.Checkbutton(flags_frame, text="Minify output JSON", variable=self.minify_var).pack(side=tk.LEFT, padx=8, pady=6)

        # Run controls
        controls = ttk.Frame(top)
        controls.pack(fill=tk.X, pady=(0, 4))

        self.run_btn = ttk.Button(controls, text="Start", command=self._start_run)
        self.run_btn.pack(side=tk.LEFT, padx=6)

        self.stop_btn = ttk.Button(controls, text="Stop", command=self._stop_run, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=6)

        self.progress = ttk.Progressbar(controls, mode="indeterminate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        # Logs
        logs_frame = ttk.LabelFrame(main, text="Processing output (live)")
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(logs_frame, wrap="word")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(logs_frame, orient="vertical", command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

    def _refresh_language_mode_visibility(self):
        mode = self.language_mode_var.get()
        if mode == "add":
            self.purge_block.grid_remove()
            self.add_block.grid()
        else:
            self.add_block.grid_remove()
            self.purge_block.grid()

    # ---------- language helpers ----------
    @staticmethod
    def _normalize_csv_codes(value: str):
        items = []
        seen = set()
        for part in (value or "").split(","):
            c = part.strip()
            if not c:
                continue
            c_low = c.lower()
            if c_low not in seen:
                seen.add(c_low)
                items.append(c)
        return items

    def _code_from_picker(self, picker_value: str):
        v = (picker_value or "").strip()
        if not v:
            return ""
        if v in self.lang_display_to_code:
            return self.lang_display_to_code[v]
        if v in self.lang_codes:
            return v
        return ""

    def _append_code_to_csv_var(self, var: tk.StringVar, code: str):
        if not code:
            return
        existing = self._normalize_csv_codes(var.get())
        if code.lower() not in {x.lower() for x in existing}:
            existing.append(code)
            var.set(",".join(existing))

    def _add_to_languages_csv(self):
        code = self._code_from_picker(self.add_lang_picker_var.get())
        if not code:
            messagebox.showwarning("Invalid language", "Please select a valid language from the picker.")
            return
        self._append_code_to_csv_var(self.languages_var, code)

    def _add_to_keeponly_csv(self):
        code = self._code_from_picker(self.keep_lang_picker_var.get())
        if not code:
            messagebox.showwarning("Invalid language", "Please select a valid language from the picker.")
            return
        self._append_code_to_csv_var(self.keeponly_var, code)

    # ---------- provider fields ----------
    def _clear_provider_specific_grid(self):
        for w in (self.api_url_label, self.api_url_entry, self.api_key_label, self.api_key_entry, self.model_label, self.model_entry):
            w.grid_forget()

    def _refresh_provider_fields(self):
        provider = self.provider_var.get().strip().lower()
        self._clear_provider_specific_grid()

        if provider == "google":
            return
        if provider == "libretranslate":
            self.api_url_label.grid(row=0, column=0, sticky="w", padx=8, pady=6)
            self.api_url_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
            self.api_key_label.grid(row=0, column=2, sticky="w", padx=8, pady=6)
            self.api_key_entry.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
            return
        if provider == "deepl":
            self.api_key_label.grid(row=0, column=0, sticky="w", padx=8, pady=6)
            self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
            self.api_url_label.grid(row=0, column=2, sticky="w", padx=8, pady=6)
            self.api_url_entry.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
            return
        if provider == "openai":
            self.api_key_label.grid(row=0, column=0, sticky="w", padx=8, pady=6)
            self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
            self.model_label.grid(row=0, column=2, sticky="w", padx=8, pady=6)
            self.model_entry.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
            self.api_url_label.grid(row=1, column=0, sticky="w", padx=8, pady=6)
            self.api_url_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    # ---------- file pickers ----------
    def _pick_input(self):
        path = filedialog.askopenfilename(
            title="Select input .grd file",
            filetypes=[("GRD files", "*.grd"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get().strip():
                base, ext = os.path.splitext(path)
                out = f"{base}.translated{ext if ext else '.grd'}"
                self.output_var.set(out)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            title="Select output file",
            defaultextension=".grd",
            filetypes=[("GRD files", "*.grd"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    # ---------- process ----------
    def _append_log(self, line: str):
        self.log_text.insert(tk.END, line)
        if not line.endswith("\n"):
            self.log_text.insert(tk.END, "\n")
        self.log_text.see(tk.END)

    def _build_command(self):
        input_path = self.input_var.get().strip()
        if not input_path:
            raise ValueError("Please select an input file.")

        cmd = [sys.executable, "-u", "translateGrid.py", input_path]

        output_path = self.output_var.get().strip()
        if output_path:
            cmd += ["--output", output_path]

        provider = self.provider_var.get().strip()
        if provider:
            cmd += ["--provider", provider]

        mode = self.language_mode_var.get()
        if mode == "add":
            langs_csv = ",".join(self._normalize_csv_codes(self.languages_var.get()))
            if langs_csv:
                cmd += ["--languages", langs_csv]
        else:
            keep_csv = ",".join(self._normalize_csv_codes(self.keeponly_var.get()))
            if keep_csv:
                cmd += ["--keeponly", keep_csv]

        api_url = self.api_url_var.get().strip()
        api_key = self.api_key_var.get().strip()
        model = self.model_var.get().strip()

        if provider == "libretranslate":
            if api_url:
                cmd += ["--api-url", api_url]
            if api_key:
                cmd += ["--api-key", api_key]
        elif provider == "deepl":
            if api_key:
                cmd += ["--api-key", api_key]
            if api_url:
                cmd += ["--api-url", api_url]
        elif provider == "openai":
            if api_key:
                cmd += ["--api-key", api_key]
            if model:
                cmd += ["--model", model]
            if api_url:
                cmd += ["--api-url", api_url]

        if self.report_only_var.get():
            cmd += ["--report-only"]
        if self.no_wordforms_var.get():
            cmd += ["--no-wordforms"]
        if self.dry_run_var.get():
            cmd += ["--dry-run-translate"]
        if self.minify_var.get():
            cmd += ["--minify"]

        return cmd

    def _set_running_state(self, running: bool):
        self.run_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        if running:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _start_run(self):
        if self.proc is not None:
            return
        try:
            cmd = self._build_command()
        except ValueError as e:
            messagebox.showerror("Missing input", str(e))
            return

        self.log_text.delete("1.0", tk.END)
        self._append_log("Starting:")
        self._append_log(" ".join(cmd))
        self._append_log("")
        self._set_running_state(True)

        t = threading.Thread(target=self._run_subprocess, args=(cmd,), daemon=True)
        t.start()

    def _run_subprocess(self, cmd):
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self.proc = subprocess.Popen(
                cmd,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                self.log_queue.put(line)

            code = self.proc.wait()
            self.log_queue.put(f"\nProcess finished with exit code {code}\n")
        except Exception as e:
            self.log_queue.put(f"\nFailed to run process: {e}\n")
        finally:
            self.proc = None
            self.log_queue.put("__PROCESS_DONE__")

    def _stop_run(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self._append_log("\nStop requested...\n")
            except Exception as e:
                self._append_log(f"\nFailed to stop process: {e}\n")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__PROCESS_DONE__":
                    self._set_running_state(False)
                else:
                    self._append_log(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)


if __name__ == "__main__":
    app = TranslateGridGUI()
    app.mainloop()