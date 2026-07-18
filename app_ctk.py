import sys
import os
import threading
import queue
import time
import asyncio
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.sms_provider_manager import SMSProviderManager
from services.sms_parser import SMSCodeExtractor
from services.local_storage import LocalStorage
from services.sms_providers import IncomingSMS

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class SMSReceiverApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("SMS Receiver - Virtual Number App")
        self.geometry("520x720")
        self.minsize(400, 600)
        self.iconbitmap(default="")  # Optional: set an icon

        self._msg_queue: queue.Queue = queue.Queue()
        self._running = True
        self._selected_number: Optional[str] = None
        self._sms_manager = SMSProviderManager()
        self._local_db = LocalStorage()
        self._poll_thread: Optional[threading.Thread] = None

        self._setup_ui()
        self._init_providers()
        self._load_message_history()
        self._process_queue()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI Setup ----------

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(self, height=48, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="SMS Receiver", font=("Segoe UI", 15, "bold"),
                      text_color="#38bdf8").grid(row=0, column=0, padx=(16, 8), pady=10)

        self._status_label = ctk.CTkLabel(header, text="Başlatılıyor...",
                                           font=("Segoe UI", 11), text_color="#94a3b8")
        self._status_label.grid(row=0, column=1, sticky="w")

        privacy_btn = ctk.CTkButton(header, text="🔒 Özel", width=60, height=24,
                                     font=("Segoe UI", 10), fg_color="#166534",
                                     hover_color="#15803d", state="disabled")
        privacy_btn.grid(row=0, column=2, padx=(0, 8))

        # Number Display
        self._num_frame = ctk.CTkFrame(self, corner_radius=12)
        self._num_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(12, 4))
        self._num_frame.grid_columnconfigure(0, weight=1)

        self._num_label = ctk.CTkLabel(self._num_frame, text="Henüz numara seçilmedi",
                                        font=("Segoe UI", 11), text_color="#64748b")
        self._num_label.grid(row=0, column=0, pady=(10, 0))

        self._num_display = ctk.CTkLabel(self._num_frame, text="—",
                                          font=("Courier New", 28, "bold"),
                                          text_color="#38bdf8")
        self._num_display.grid(row=1, column=0, pady=(0, 6))

        self._num_status = ctk.CTkLabel(self._num_frame, text="",
                                         font=("Segoe UI", 11), text_color="#94a3b8")
        self._num_status.grid(row=2, column=0, pady=(0, 10))

        # Controls Row
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 4))
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        self._country_combo = ctk.CTkComboBox(controls, values=["Yükleniyor..."],
                                               state="readonly", width=140,
                                               command=self._on_country_change)
        self._country_combo.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self._number_combo = ctk.CTkComboBox(controls, values=["Önce ülke seç"],
                                              state="disabled", width=140)
        self._number_combo.grid(row=0, column=1, padx=4, sticky="ew")

        self._select_btn = ctk.CTkButton(controls, text="Numarayı Kullan",
                                          command=self._select_number,
                                          state="disabled", fg_color="#22c55e",
                                          hover_color="#16a34a", text_color="#fff")
        self._select_btn.grid(row=0, column=2, padx=(4, 0), sticky="ew")

        # Provider + Info Row
        info_row = ctk.CTkFrame(self, fg_color="transparent", height=28)
        info_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 2))
        info_row.grid_columnconfigure((0, 1), weight=1)

        self._provider_combo = ctk.CTkComboBox(info_row, values=[""],
                                                state="readonly", width=130,
                                                command=self._on_provider_change)
        self._provider_combo.grid(row=0, column=0, sticky="w")

        right_frame = ctk.CTkFrame(info_row, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="e")

        self._msg_count_label = ctk.CTkLabel(right_frame, text="0 mesaj",
                                              font=("Segoe UI", 11), text_color="#64748b")
        self._msg_count_label.grid(row=0, column=0, padx=(0, 8))

        self._clear_btn = ctk.CTkButton(right_frame, text="Temizle", width=60,
                                         height=22, font=("Segoe UI", 10),
                                         command=self._clear_messages,
                                         fg_color="#334155", hover_color="#475569")
        self._clear_btn.grid(row=0, column=1)

        # SMS Chat Area (scrollable)
        self._chat_frame = ctk.CTkScrollableFrame(self, corner_radius=12,
                                                   border_width=0)
        self._chat_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(4, 8))
        self.grid_rowconfigure(4, weight=1)

        # Empty state
        self._empty_label = ctk.CTkLabel(self._chat_frame, text="📭 SMS bekleniyor...\nBir ülke ve numara seçin",
                                          font=("Segoe UI", 13), text_color="#475569")
        self._empty_label.pack(expand=True, pady=80)

        # Bottom status
        bottom = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#1e293b")
        bottom.grid(row=5, column=0, sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self._bottom_label = ctk.CTkLabel(bottom, text="Hazır",
                                           font=("Segoe UI", 10), text_color="#64748b")
        self._bottom_label.grid(row=0, column=0, padx=12, pady=4, sticky="w")

        self._release_btn = ctk.CTkButton(bottom, text="Numarayı Değiştir",
                                           font=("Segoe UI", 10), height=22,
                                           command=self._release_number,
                                           fg_color="#ef4444", hover_color="#dc2626",
                                           text_color="#fff")
        self._release_btn.grid(row=0, column=1, padx=12, pady=2)
        self._release_btn.grid_remove()

    # ---------- Provider Init ----------

    def _init_providers(self):
        def _start():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._sms_manager.init_defaults())
            loop.close()

            providers = self._sms_manager.get_providers()
            active = self._sms_manager.provider_name

            self.after(0, lambda: self._on_providers_ready(providers, active))

            self._sms_manager.on_new_message(self._on_sms_callback)
            self._sms_manager.start_polling(interval=5)

        threading.Thread(target=_start, daemon=True).start()

    def _on_providers_ready(self, providers, active):
        if providers:
            self._provider_combo.configure(values=providers)
            self._provider_combo.set(active)
        self._set_status(f"{active} — Hazır")
        self._load_countries()
        self._restore_last_number()

    def _on_provider_change(self, choice):
        if not choice:
            return
        self._sms_manager.set_provider(choice)
        self._sms_manager.select_number("")
        self._set_status(f"{choice} — Hazır")
        self._load_countries()
        self._release_number()

    # ---------- Countries ----------

    def _load_countries(self):
        def _fetch():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            countries = loop.run_until_complete(self._sms_manager.get_countries())
            loop.close()
            self.after(0, lambda: self._on_countries_loaded(countries))

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_countries_loaded(self, countries):
        if not countries:
            self._country_combo.configure(values=["Hata"])
            return
        labels = [f"{c.get('flag', '')} {c['name']}" for c in countries]
        codes = [c["code"] for c in countries]
        self._country_combo._codes = codes
        self._country_combo.configure(values=labels)
        self._country_combo.set("")

    def _on_country_change(self, choice):
        idx = self._country_combo._values.index(choice) if hasattr(self._country_combo, '_values') and choice in self._country_combo._values else -1
        code = ""
        if hasattr(self._country_combo, '_codes') and idx >= 0 and idx < len(self._country_combo._codes):
            code = self._country_combo._codes[idx]

        if not code:
            return

        self._number_combo.configure(state="disabled", values=["Yükleniyor..."])
        self._select_btn.configure(state="disabled")

        def _fetch():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            nums = loop.run_until_complete(self._sms_manager.get_numbers(code))
            loop.close()
            self.after(0, lambda: self._on_numbers_loaded(nums))

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_numbers_loaded(self, nums):
        if not nums:
            self._number_combo.configure(values=["Bu ülkede numara yok"], state="disabled")
            return
        self._number_combo.configure(values=nums, state="normal")
        self._number_combo.set(nums[0] if nums else "")
        self._select_btn.configure(state="normal")

    # ---------- Number Selection ----------

    def _select_number(self):
        num = self._number_combo.get()
        if not num or num in ("Bu ülkede numara yok", "Önce ülke seç"):
            return

        self._selected_number = num
        self._sms_manager.select_number(num)
        self._local_db.set_setting("last_number", num)

        self._num_display.configure(text=num)
        self._num_status.configure(text="Siteye bu numarayı girin, SMS bekleniyor...")
        self._num_label.configure(text="SEÇİLİ NUMARA")

        self._select_btn.grid_remove()
        self._release_btn.grid()
        self._country_combo.configure(state="disabled")
        self._number_combo.configure(state="disabled")
        self._provider_combo.configure(state="disabled")

        self._set_status(f"{num} — SMS bekleniyor")
        self._load_messages()

    def _release_number(self):
        self._selected_number = None
        self._sms_manager.select_number("")

        self._num_display.configure(text="—")
        self._num_status.configure(text="")
        self._num_label.configure(text="Henüz numara seçilmedi")

        self._release_btn.grid_remove()
        self._select_btn.grid()
        self._select_btn.configure(state="disabled")
        self._country_combo.configure(state="normal")
        self._number_combo.configure(state="disabled")
        self._provider_combo.configure(state="normal")

        self._set_status("Hazır")

    def _restore_last_number(self):
        last = self._local_db.get_setting("last_number", "")
        if last:
            self._selected_number = last
            self._sms_manager.select_number(last)
            self._num_display.configure(text=last)
            self._num_status.configure(text="Siteye bu numarayı girin, SMS bekleniyor...")
            self._num_label.configure(text="SEÇİLİ NUMARA")
            self._select_btn.grid_remove()
            self._release_btn.grid()
            self._country_combo.configure(state="disabled")
            self._number_combo.configure(state="disabled")
            self._provider_combo.configure(state="disabled")
            self._set_status(f"{last} — SMS bekleniyor")
            self._load_messages()

    # ---------- Messages ----------

    def _load_messages(self):
        msgs = self._local_db.get_messages(limit=200)
        self._render_messages(msgs)

    def _load_message_history(self):
        self._load_messages()

    def _render_messages(self, msgs):
        for w in self._chat_frame.winfo_children():
            w.destroy()
        self._empty_label = None

        if not msgs:
            self._empty_label = ctk.CTkLabel(self._chat_frame,
                                              text="📭 SMS bekleniyor...\nBir numara seçin ve siteye kaydolun.",
                                              font=("Segoe UI", 13), text_color="#475569")
            self._empty_label.pack(expand=True, pady=80)
            self._msg_count_label.configure(text="0 mesaj")
            return

        for msg in msgs:
            self._add_message_widget(msg, animate=False)

        self._msg_count_label.configure(text=f"{len(msgs)} mesaj")
        self._scroll_to_bottom()

    def _add_message_widget(self, msg: dict, animate: bool = True):
        if self._empty_label:
            self._empty_label.destroy()
            self._empty_label = None

        sender = msg.get("sender", msg.get("from", "Bilinmeyen"))
        text = msg.get("text", msg.get("content", ""))
        code = msg.get("code", "")
        provider = msg.get("provider", "")
        received = msg.get("received_at", "")
        time_str = ""
        if received:
            try:
                dt = datetime.fromisoformat(received)
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = received

        msg_frame = ctk.CTkFrame(self._chat_frame, fg_color="#1e293b",
                                  corner_radius=12, border_width=0)
        msg_frame.pack(fill="x", padx=4, pady=(0, 6))

        inner = ctk.CTkFrame(msg_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=6)
        inner.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        top_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_row, text=sender, font=("Segoe UI", 10, "bold"),
                      text_color="#94a3b8").grid(row=0, column=0, sticky="w")
        if provider:
            ctk.CTkLabel(top_row, text=f"· {provider}", font=("Segoe UI", 9),
                          text_color="#64748b").grid(row=0, column=2, padx=(4, 0), sticky="e")
        ctk.CTkLabel(top_row, text=time_str, font=("Segoe UI", 9),
                      text_color="#64748b").grid(row=0, column=3, padx=(4, 0), sticky="e")

        ctk.CTkLabel(inner, text=text, font=("Segoe UI", 12),
                      text_color="#e2e8f0", wraplength=400, justify="left").grid(
            row=1, column=0, sticky="w", pady=(0, 2))

        if code:
            code_frame = ctk.CTkFrame(inner, fg_color="#0f172a",
                                       corner_radius=8, border_width=1,
                                       border_color="#166534")
            code_frame.grid(row=2, column=0, sticky="w", pady=(2, 0))
            ctk.CTkLabel(code_frame, text=code, font=("Courier New", 16, "bold"),
                          text_color="#34d399").pack(padx=8, pady=2)

        self._msg_count_label.configure(
            text=f"{len(self._local_db.get_messages(limit=99999))} mesaj")

    def _scroll_to_bottom(self):
        self._chat_frame._parent_canvas.yview_moveto(1.0)

    # ---------- SMS Callback (from polling thread) ----------

    def _on_sms_callback(self, msg: IncomingSMS):
        code = SMSCodeExtractor.extract(msg.text) or msg.code or ""
        masked = SMSCodeExtractor.mask_sensitive(msg.text)

        self._local_db.save_message(
            number=msg.number,
            sender=msg.sender,
            text=masked,
            code=str(code) if code else "",
            provider=msg.provider,
        )

        self._msg_queue.put({
            "sender": msg.sender,
            "text": masked,
            "code": str(code) if code else "",
            "provider": msg.provider,
            "received_at": datetime.utcnow().isoformat(),
        })

    def _process_queue(self):
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                if self._selected_number:
                    self._add_message_widget(msg, animate=True)
                    self._scroll_to_bottom()
                    self._flash_notification(msg)
        except queue.Empty:
            pass
        self.after(200, self._process_queue)

    def _flash_notification(self, msg):
        code = msg.get("code", "")
        sender = msg.get("sender", "")
        self._set_status(f"✉️ {sender}: {code or 'SMS alındı'}")
        self.after(3000, lambda: self._set_status(
            f"{self._selected_number or 'Hazır'} — SMS bekleniyor" if self._selected_number else "Hazır"))

    # ---------- Actions ----------

    def _clear_messages(self):
        self._local_db.clear_messages()
        for w in self._chat_frame.winfo_children():
            w.destroy()
        self._empty_label = ctk.CTkLabel(self._chat_frame,
                                          text="📭 SMS bekleniyor...\nBir numara seçin ve siteye kaydolun.",
                                          font=("Segoe UI", 13), text_color="#475569")
        self._empty_label.pack(expand=True, pady=80)
        self._msg_count_label.configure(text="0 mesaj")

    def _set_status(self, text):
        self._status_label.configure(text=text)
        self._bottom_label.configure(text=text)

    def _on_close(self):
        self._running = False
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._sms_manager.stop_polling())
        loop.close()
        self.destroy()


if __name__ == "__main__":
    app = SMSReceiverApp()
    app.mainloop()
