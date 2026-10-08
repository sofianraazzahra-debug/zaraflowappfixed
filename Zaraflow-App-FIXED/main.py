from datetime import datetime, timedelta, date
import calendar
import os
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import NumericProperty
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

# Import engine notifikasi
try:
    from plyer import notification
    NOTIFICATION_ENABLED = True
except ImportError:
    NOTIFICATION_ENABLED = False

from database import (
    init_db, register_user, authenticate_user, 
    set_active_session, get_active_session, clear_session,
    get_user_data, update_user_name, get_profile, update_profile, 
    get_daily_log, update_daily_log, get_recent_history,
    get_all_logs_for_export, get_db_connection
)

if platform not in ('android', 'ios'):
    Window.size = (380, 680)
ACTIVE_USER_ID = None

def send_push_notification(title, message):
    if NOTIFICATION_ENABLED:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Zaraflow",
                ticker="Zaraflow Reminder",
                timeout=10
            )
        except Exception as e:
            print(f"Gagal mengirim notifikasi: {e}")

# ----------------- KELAS SPLASH SCREEN -----------------
class SplashScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.switch_to_next, 3.5)

    def switch_to_next(self, dt):
        global ACTIVE_USER_ID
        saved_uid = get_active_session()
        
        if saved_uid:
            ACTIVE_USER_ID = saved_uid
            self.manager.current = "home"
        else:
            self.manager.current = "auth"
            
        self.manager.transition.duration = 0.15

# ----------------- POPUP KALENDER -----------------
class DatePickerPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Pilih Tanggal Mulai Haid"
        self.size_hint = (0.9, 0.65)
        self.auto_dismiss = True

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        layout = BoxLayout(orientation="vertical", spacing=8, padding=10)
        self.month_lbl = Label(text=f"{calendar.month_name[self.current_month]} {self.current_year}", size_hint_y=0.15, bold=True)
        layout.add_widget(self.month_lbl)

        days_header = GridLayout(cols=7, size_hint_y=0.1)
        for day_name in ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"]:
            days_header.add_widget(Label(text=day_name, font_size="10sp", color=(0.5, 0.5, 0.5, 1)))
        layout.add_widget(days_header)

        self.grid = GridLayout(cols=7, spacing=2)
        layout.add_widget(self.grid)
        self.render_calendar()

        close_btn = Button(text="Tutup", size_hint_y=0.15, background_normal="", background_color=(0.5, 0.5, 0.5, 1))
        close_btn.bind(on_release=self.dismiss)
        layout.add_widget(close_btn)

        self.content = layout

    def render_calendar(self):
        self.grid.clear_widgets()
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        for week in cal:
            for day in week:
                if day == 0:
                    self.grid.add_widget(Button(text="", background_normal="", background_color=(0,0,0,0)))
                else:
                    btn = Button(text=str(day), background_normal="", background_color=(0.95, 0.95, 0.95, 1), color=(0.2,0.2,0.2,1))
                    btn.bind(on_release=lambda instance, d=day: self.select_day(d))
                    self.grid.add_widget(btn)

    def select_day(self, day):
        chosen_date = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
        self.callback(chosen_date)
        self.dismiss()

# ----------------- AUTH SCREEN -----------------
class AuthScreen(Screen):
    mode = "login"

    def switch_tab(self, mode):
        self.mode = mode
        if mode == "login":
            self.ids.tab_login_btn.background_color = (0.91, 0.28, 0.46, 1)
            self.ids.tab_login_btn.color = (1, 1, 1, 1)
            self.ids.tab_reg_btn.background_color = (0.85, 0.85, 0.85, 1)
            self.ids.tab_reg_btn.color = (0.3, 0.3, 0.3, 1)
            self.ids.auth_submit_btn.text = "Masuk ke Akun"
            self.ids.lbl_fullname.opacity = 0
            self.ids.input_fullname.opacity = 0
            self.ids.input_fullname.disabled = True
        else:
            self.ids.tab_reg_btn.background_color = (0.91, 0.28, 0.46, 1)
            self.ids.tab_reg_btn.color = (1, 1, 1, 1)
            self.ids.tab_login_btn.background_color = (0.85, 0.85, 0.85, 1)
            self.ids.tab_login_btn.color = (0.3, 0.3, 0.3, 1)
            self.ids.auth_submit_btn.text = "Buat Akun Sekarang"
            self.ids.lbl_fullname.opacity = 1
            self.ids.input_fullname.opacity = 1
            self.ids.input_fullname.disabled = False
        self.ids.auth_status_lbl.text = ""

    def submit_auth(self):
        global ACTIVE_USER_ID
        email = self.ids.input_email.text.strip()
        pw = self.ids.input_password.text.strip()

        if not email or not pw:
            self.ids.auth_status_lbl.text = "Mohon lengkapi data Anda."
            return

        if self.mode == "register":
            fullname = self.ids.input_fullname.text.strip()
            if not fullname or len(pw) < 6:
                self.ids.auth_status_lbl.text = "Password minimal 6 karakter."
                return
            ok, msg = register_user(fullname, email, pw)
            self.ids.auth_status_lbl.text = msg
            if ok:
                self.switch_tab("login")
        else:
            user = authenticate_user(email, pw)
            if user:
                ACTIVE_USER_ID = user[0]
                set_active_session(ACTIVE_USER_ID)
                self.ids.input_email.text = ""
                self.ids.input_password.text = ""
                self.ids.auth_status_lbl.text = ""
                self.manager.current = "home"
            else:
                self.ids.auth_status_lbl.text = "Email atau password salah!"

# ----------------- HOME SCREEN -----------------
class HomeScreen(Screen):
    cycle_angle = NumericProperty(0)
    current_water = 0

    def on_enter(self):
        Clock.schedule_once(self.init_home_data, 0.05)

    def init_home_data(self, dt=None):
        global ACTIVE_USER_ID
        if not ACTIVE_USER_ID:
            self.manager.current = "auth"
            return

        user = get_user_data(ACTIVE_USER_ID)
        if user and "user_greeting_lbl" in self.ids:
            first_name = user[0].split()[0]
            self.ids.user_greeting_lbl.text = f"[b]Halo, {first_name}![/b]"

        self.update_cycle_state()
        self.load_today_water()
        self.check_cycle_notification()

    def check_cycle_notification(self):
        global ACTIVE_USER_ID
        prof = get_profile(ACTIVE_USER_ID)
        if not prof:
            return

        last_str, cycle_len, duration, _ = prof
        try:
            last_date = datetime.strptime(last_str, "%Y-%m-%d").date()
            today = date.today()
            days_passed = (today - last_date).days
            days_until_next = cycle_len - (days_passed % cycle_len)
            day_in_cycle = (days_passed % cycle_len) + 1

            if days_until_next == 0 or days_until_next == cycle_len:
                send_push_notification(
                    "Zaraflow: Hari Pertama Haid Tiba! 🩸",
                    "Prediksi siklus barumu dimulai hari ini. Jangan lupa catat intensitas darah dan gejala di aplikasi ya!"
                )
            elif days_until_next <= 2:
                send_push_notification(
                    "Zaraflow: Pengingat Siklus Haid 🌸",
                    f"Haid diperkirakan tiba {days_until_next} hari lagi. Siapkan pembalut dan jaga hidrasi tubuhmu!"
                )
            elif day_in_cycle == (cycle_len - 14):
                send_push_notification(
                    "Zaraflow: Puncak Masa Subur (Ovulasi) ⭐",
                    "Hari ini adalah hari ovulasimu. Kondisi energi dan hormonmu sedang berada di titik optimum."
                )
        except Exception as e:
            print(f"Error pengecekan notifikasi: {e}")

    def update_cycle_state(self):
        global ACTIVE_USER_ID
        if not hasattr(self, "ids") or "cycle_day_lbl" not in self.ids:
            return

        prof = get_profile(ACTIVE_USER_ID)
        if not prof:
            return

        last_str, cycle_len, duration, _ = prof
        try:
            last_date = datetime.strptime(last_str, "%Y-%m-%d").date()
            today = date.today()
            days_passed = (today - last_date).days
            day_in_cycle = (days_passed % cycle_len) + 1
            days_until_next = cycle_len - (days_passed % cycle_len)

            self.cycle_angle = (day_in_cycle / cycle_len) * 360

            next_period = today + timedelta(days=days_until_next)
            ovulation = next_period - timedelta(days=14)
            fertile_start = ovulation - timedelta(days=4)
            fertile_end = ovulation + timedelta(days=1)

            if day_in_cycle <= duration:
                phase = "Fase Menstruasi"
                sub_text = f"{days_until_next} hari menuju siklus baru"
            elif day_in_cycle < (cycle_len - 14):
                phase = "Fase Folikular"
                sub_text = f"Puncak masa subur dalam {((cycle_len - 14) - day_in_cycle)} hari"
            elif day_in_cycle in [cycle_len - 14, cycle_len - 13]:
                phase = "Puncak Ovulasi"
                sub_text = "Kemungkinan pembuahan sel telur tertinggi"
            else:
                phase = "Fase Luteal (PMS)"
                sub_text = f"Haid diperkirakan {days_until_next} hari lagi"

            self.ids.cycle_day_lbl.text = f"Hari ke-{day_in_cycle}"
            self.ids.cycle_status_lbl.text = f"{phase}\n{sub_text}"

            # Quote pesan harian statis
            self.ids.insight_title_lbl.text = "[b]4 Fase Siklus Hormon dan Menstruasi[/b]"
            self.ids.insight_desc_lbl.text = '"Dengarkan tubuhmu, rawat dirimu, dan luangkan waktu untuk beristirahat."'

            self.ids.fertility_lbl.text = (
                f"• Haid Berikutnya: {next_period.strftime('%d %b %Y')}\n"
                f"• Puncak Ovulasi: {ovulation.strftime('%d %b %Y')}\n"
                f"• Masa Subur: {fertile_start.strftime('%d %b')} – {fertile_end.strftime('%d %b')}"
            )
        except Exception:
            self.ids.cycle_day_lbl.text = "Atur Data"
            self.ids.cycle_status_lbl.text = "Buka pengaturan (⚙)"

    def load_today_water(self):
        global ACTIVE_USER_ID
        today_str = date.today().strftime("%Y-%m-%d")
        log = get_daily_log(ACTIVE_USER_ID, today_str)
        self.current_water = log[3] if log else 0
        self.update_water_label()

    def add_water(self):
        global ACTIVE_USER_ID
        if self.current_water < 12:
            self.current_water += 1
            today_str = date.today().strftime("%Y-%m-%d")
            log = get_daily_log(ACTIVE_USER_ID, today_str)
            flow = log[0] if log else "Tidak Ada"
            mood = log[1] if log else "Stabil"
            sym = log[2] if log else "Nihil"
            update_daily_log(ACTIVE_USER_ID, today_str, flow, mood, sym, self.current_water)
            self.update_water_label()

    def update_water_label(self):
        if hasattr(self, "ids") and "water_lbl" in self.ids:
            pct = int((self.current_water / 8) * 100)
            self.ids.water_lbl.text = f"{self.current_water} / 8 Gelas ({pct}%)"

# ----------------- CALENDAR SCREEN -----------------
class CalendarScreen(Screen):
    view_year = 2026
    view_month = 9

    def on_enter(self):
        today = date.today()
        self.view_year = today.year
        self.view_month = today.month
        self.generate_calendar()

    def prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self.generate_calendar()

    def next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self.generate_calendar()

    def generate_calendar(self):
        global ACTIVE_USER_ID
        if not hasattr(self, "ids") or "calendar_grid" not in self.ids:
            return

        self.ids.calendar_grid.clear_widgets()
        month_names = [
            "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        self.ids.month_header.text = f"{month_names[self.view_month]} {self.view_year}"

        # 1. Ambil data profil untuk tahu rata-rata siklus pengguna
        prof = get_profile(ACTIVE_USER_ID)
        cycle_len = prof[1] if prof else 28

        # 2. Cari semua tanggal haid yang PERNAH DICATAT MANUAL oleh pengguna
        logged_period_days = set()
        
        # Periksa catatan tanggal di rentang bulan yang sedang dilihat (dan sekitarnya)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT log_date FROM daily_logs WHERE user_id = ? AND flow IN ('Flek', 'Sedang', 'Deras')",
            (ACTIVE_USER_ID,)
        )
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            try:
                logged_period_days.add(datetime.strptime(r[0], "%Y-%m-%d").date())
            except Exception:
                pass

        # 3. Hitung Masa Subur & Ovulasi OTOMATIS hanya dari tanggal pertama haid yang tercatat
        fertile_days = set()
        ovulation_days = set()

        sorted_period_days = sorted(list(logged_period_days))
        
        # Kelompokkan hari pertama dari setiap periode haid yang dicatat
        period_starts = []
        for d in sorted_period_days:
            # Jika hari sebelumnya bukan haid, berarti ini tanggal mulai haid baru
            if (d - timedelta(days=1)) not in logged_period_days:
                period_starts.append(d)

        # Hitung subur dan ovulasi untuk setiap periode haid yang ada
        for start_date in period_starts:
            ov_date = start_date + timedelta(days=(cycle_len - 14))
            ovulation_days.add(ov_date)
            # Jendela masa subur (4 hari sebelum ovulasi sampai 1 hari setelahnya)
            for f in range(-4, 2):
                f_date = ov_date + timedelta(days=f)
                if f_date not in logged_period_days:
                    fertile_days.add(f_date)

        # 4. Render tampilan kalender
        cal = calendar.monthcalendar(self.view_year, self.view_month)
        today = date.today()

        for week in cal:
            for day in week:
                if day == 0:
                    btn = Button(text="", background_normal="", background_color=(0, 0, 0, 0))
                else:
                    this_date = date(self.view_year, self.view_month, day)
                    btn = Button(text=str(day), bold=True, background_normal="")

                    # Urutan prioritas warna:
                    if this_date in logged_period_days:
                        # MERAH MUDA: Hanya jika Anda catat haid secara manual
                        btn.background_color = (0.91, 0.28, 0.46, 0.95)
                        btn.color = (1, 1, 1, 1)
                    elif this_date in ovulation_days:
                        # ORANYE: Ovulasi otomatis muncul karena ada catatan haid
                        btn.background_color = (0.95, 0.6, 0.1, 1)
                        btn.color = (1, 1, 1, 1)
                    elif this_date in fertile_days:
                        # BIRU: Masa subur otomatis muncul karena ada catatan haid
                        btn.background_color = (0.2, 0.6, 0.85, 0.85)
                        btn.color = (1, 1, 1, 1)
                    else:
                        # Tanggal biasa: Putih bersih
                        btn.background_color = (1, 1, 1, 0.9)
                        btn.color = (0.2, 0.2, 0.2, 1)

                    if this_date == today:
                        btn.text = f"{day}\n."

                    # Klik tanggal untuk menambah/menghapus catatan haid manual
                    btn.bind(on_release=lambda instance, d=this_date: self.toggle_period_day(d))

                self.ids.calendar_grid.add_widget(btn)

    def toggle_period_day(self, chosen_date):
        global ACTIVE_USER_ID
        date_str = chosen_date.strftime("%Y-%m-%d")
        existing_log = get_daily_log(ACTIVE_USER_ID, date_str)

        if existing_log and existing_log[0] in ["Flek", "Sedang", "Deras"]:
            flow = "Tidak Ada"
            mood = existing_log[1]
            sym = existing_log[2]
            water = existing_log[3]
            msg = f"Tanda haid {chosen_date.strftime('%d %b')} dihapus."
        else:
            flow = "Sedang"
            mood = existing_log[1] if existing_log else "Stabil"
            sym = existing_log[2] if existing_log else "Nihil"
            water = existing_log[3] if existing_log else 0
            msg = f"Haid dicatat pada {chosen_date.strftime('%d %b %Y')}!"

        update_daily_log(ACTIVE_USER_ID, date_str, flow, mood, sym, water)
        if "cal_feedback_lbl" in self.ids:
            self.ids.cal_feedback_lbl.text = msg

        # Render ulang kalender agar warnanya langsung berubah seketika
        self.generate_calendar()

# ----------------- DAILY LOG SCREEN -----------------
class DailyLogScreen(Screen):
    flow_val = "Tidak Ada"
    mood_val = "Bahagia"
    sym_val = "Nihil"

    def load_today_log(self):
        Clock.schedule_once(self._populate_log, 0.05)

    def _populate_log(self, dt=None):
        global ACTIVE_USER_ID
        today_str = date.today().strftime("%Y-%m-%d")
        log = get_daily_log(ACTIVE_USER_ID, today_str)
        if log:
            self.set_flow(log[0])
            self.set_mood(log[1])
            self.set_symptom(log[2])

    def set_flow(self, val):
        self.flow_val = val
        if hasattr(self, "ids") and "btn_flow_tidak" in self.ids:
            self.ids.btn_flow_tidak.background_color = (0.91, 0.28, 0.46, 1) if val == "Tidak Ada" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_flow_flek.background_color = (0.91, 0.28, 0.46, 1) if val == "Flek" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_flow_sedang.background_color = (0.91, 0.28, 0.46, 1) if val == "Sedang" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_flow_deras.background_color = (0.91, 0.28, 0.46, 1) if val == "Deras" else (0.8, 0.8, 0.8, 1)
        self.update_status()

    def set_mood(self, val):
        self.mood_val = val
        if hasattr(self, "ids") and "btn_mood_bahagia" in self.ids:
            self.ids.btn_mood_bahagia.background_color = (0.91, 0.28, 0.46, 1) if val == "Bahagia" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_mood_sensitif.background_color = (0.91, 0.28, 0.46, 1) if val == "Sensitif" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_mood_lelah.background_color = (0.91, 0.28, 0.46, 1) if val == "Lelah" else (0.8, 0.8, 0.8, 1)
        self.update_status()

    def set_symptom(self, val):
        self.sym_val = val
        if hasattr(self, "ids") and "btn_sym_kram" in self.ids:
            self.ids.btn_sym_kram.background_color = (0.91, 0.28, 0.46, 1) if val == "Kram Perut" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_sym_pusing.background_color = (0.91, 0.28, 0.46, 1) if val == "Sakit Kepala" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_sym_jerawat.background_color = (0.91, 0.28, 0.46, 1) if val == "Jerawat" else (0.8, 0.8, 0.8, 1)
            self.ids.btn_sym_nihil.background_color = (0.91, 0.28, 0.46, 1) if val == "Nihil" else (0.8, 0.8, 0.8, 1)
        self.update_status()

    def update_status(self):
        if hasattr(self, "ids") and "log_status_lbl" in self.ids:
            self.ids.log_status_lbl.text = f"Pilihan: {self.flow_val} | Mood: {self.mood_val} | Gejala: {self.sym_val}"

    def save_log(self):
        global ACTIVE_USER_ID
        today_str = date.today().strftime("%Y-%m-%d")
        log = get_daily_log(ACTIVE_USER_ID, today_str)
        water = log[3] if log else 0
        update_daily_log(ACTIVE_USER_ID, today_str, self.flow_val, self.mood_val, self.sym_val, water)
        if hasattr(self, "ids") and "log_status_lbl" in self.ids:
            self.ids.log_status_lbl.text = "Catatan berhasil disimpan ke perangkat!"

# ----------------- ANALYTICS SCREEN -----------------
class AnalyticsScreen(Screen):
    def load_analytics(self):
        Clock.schedule_once(self._populate_analytics, 0.05)

    def _populate_analytics(self, dt=None):
        global ACTIVE_USER_ID
        if not hasattr(self, "ids") or "history_container" not in self.ids:
            return

        self.ids.history_container.clear_widgets()
        history = get_recent_history(ACTIVE_USER_ID)
        for row in history:
            s_date, c_len, dur = row
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=64, padding=10)
            card.canvas.before.clear()
            title = Label(
                text=f"[b]Siklus {s_date}[/b] — Panjang: {c_len} Hari", 
                markup=True, color=(0.91, 0.28, 0.46, 1), halign="left", text_size=(340, None)
            )
            sub = Label(
                text=f"Lama Haid: {dur} Hari • Status: Reguler", 
                font_size="11sp", color=(0.4, 0.4, 0.4, 1), halign="left", text_size=(340, None)
            )
            card.add_widget(title)
            card.add_widget(sub)
            self.ids.history_container.add_widget(card)

    def export_report(self):
        global ACTIVE_USER_ID
        user = get_user_data(ACTIVE_USER_ID)
        logs = get_all_logs_for_export(ACTIVE_USER_ID)
        history = get_recent_history(ACTIVE_USER_ID)
        
        filename = f"Laporan_Siklus_Zaraflow_{user[0].replace(' ', '_')}.txt"
        report_path = os.path.join(App.get_running_app().user_data_dir, filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write("      REKAP MEDIS KESEHATAN SIKLUS ZARAFLOW\n")
            f.write("=" * 50 + "\n")
            f.write(f"Nama Pasien : {user[0]}\n")
            f.write(f"Email Terkait: {user[1]}\n")
            f.write(f"Tanggal Unduh: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("-" * 50 + "\n\n")
            
            f.write("[1. RIWAYAT SIKLUS SEBELUMNYA]\n")
            for h in history:
                f.write(f"- Siklus Mulai: {h[0]} | Durasi: {h[1]} Hari | Masa Haid: {h[2]} Hari\n")
            f.write("\n[2. CATATAN GEJALA & MOOD HARIAN]\n")
            for l in logs:
                f.write(f"- {l[0]}: Aliran={l[1]}, Mood={l[2]}, Gejala={l[3]}, Air={l[4]} gelas\n")
            f.write("\n" + "=" * 50 + "\n")
            f.write("Dokumen ini dihasilkan secara otomatis oleh sistem Zaraflow.\n")

        self.ids.stats_lbl.text = f"✓ Laporan berhasil disimpan di perangkat:\n{report_path}"

# ----------------- SETTINGS SCREEN -----------------
class SettingsScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self._populate_settings, 0.05)

    def _populate_settings(self, dt=None):
        global ACTIVE_USER_ID
        if not hasattr(self, "ids") or "last_date_in" not in self.ids:
            return
        
        user = get_user_data(ACTIVE_USER_ID)
        if user:
            self.ids.user_email_lbl.text = f"Akun: {user[0]} ({user[1]})"

        prof = get_profile(ACTIVE_USER_ID)
        if prof:
            self.ids.last_date_in.text = prof[0]
            self.ids.cycle_in.text = str(prof[1])
            self.ids.dur_in.text = str(prof[2])

    def open_date_picker(self):
        popup = DatePickerPopup(callback=self.on_date_selected)
        popup.open()

    def on_date_selected(self, selected_date):
        self.ids.last_date_in.text = selected_date

    def save_settings(self):
        global ACTIVE_USER_ID
        d_str = self.ids.last_date_in.text.strip()
        c_len = self.ids.cycle_in.text.strip()
        dur = self.ids.dur_in.text.strip()

        try:
            datetime.strptime(d_str, "%Y-%m-%d")
            update_profile(ACTIVE_USER_ID, d_str, int(c_len), int(dur))
            self.ids.info_msg.text = "✓ Parameter siklus berhasil diperbarui!"
        except ValueError:
            self.ids.info_msg.text = "Format tanggal salah atau data bukan angka."

    def trigger_manual_notification(self):
        send_push_notification(
            "Zaraflow: Pengingat Siklus Haid 🌸",
            "Notifikasi berhasil terhubung! Kamu akan menerima pengingat otomatis saat hari haid tiba."
        )

    def logout(self):
        global ACTIVE_USER_ID
        clear_session()
        ACTIVE_USER_ID = None
        self.manager.current = "auth"

# ----------------- PROFILE SCREEN -----------------
class ProfileScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self._load_profile, 0.05)

    def _load_profile(self, dt=None):
        global ACTIVE_USER_ID
        if not ACTIVE_USER_ID:
            self.manager.current = "auth"
            return

        # Database sudah menangani migrasi birth_date saat startup.
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT birth_date FROM users WHERE id = ?",
                (ACTIVE_USER_ID,)
            )
            b_row = cursor.fetchone()
            bdate = b_row[0] if (b_row and b_row[0]) else ""
        finally:
            conn.close()

        # Gunakan fungsi bawaan get_user_data yang sudah ada
        user = get_user_data(ACTIVE_USER_ID)
        prof = get_profile(ACTIVE_USER_ID)

        if user:
            fullname, email = user[0], user[1]
            if "profile_name_lbl" in self.ids:
                self.ids.profile_name_lbl.text = fullname
            if "profile_email_lbl" in self.ids:
                self.ids.profile_email_lbl.text = email
            if "edit_name_in" in self.ids:
                self.ids.edit_name_in.text = fullname
            if "birth_date_in" in self.ids:
                self.ids.birth_date_in.text = bdate

        if prof:
            _, cycle_len, duration, water = prof
            stats_text = (
                f"• Panjang Rata-rata Siklus: {cycle_len} Hari\n"
                f"• Lama Masa Haid: {duration} Hari\n"
                f"• Target Hidrasi Sehat: {water} Gelas / Hari"
            )
            if "lbl_profile_stats" in self.ids:
                self.ids.lbl_profile_stats.text = stats_text

    def save_personal_info(self):
        global ACTIVE_USER_ID
        new_name = self.ids.edit_name_in.text.strip()
        new_bdate = self.ids.birth_date_in.text.strip()

        if not new_name:
            if "profile_status_lbl" in self.ids:
                self.ids.profile_status_lbl.text = "Nama tidak boleh kosong."
            return

        if new_bdate:
            try:
                datetime.strptime(new_bdate, "%Y-%m-%d")
            except ValueError:
                if "profile_status_lbl" in self.ids:
                    self.ids.profile_status_lbl.text = "Format tanggal lahir salah! Contoh: 2002-08-15"
                return

        # Update nama menggunakan fungsi bawaan
        update_user_name(ACTIVE_USER_ID, new_name)

        # Update tanggal lahir
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET birth_date = ? WHERE id = ?",
                (new_bdate, ACTIVE_USER_ID)
            )
            conn.commit()
        finally:
            conn.close()

        if "profile_name_lbl" in self.ids:
            self.ids.profile_name_lbl.text = new_name
        if "profile_status_lbl" in self.ids:
            self.ids.profile_status_lbl.text = "Data berhasil disimpan!"

    def download_report(self):
        global ACTIVE_USER_ID
        try:
            user = get_user_data(ACTIVE_USER_ID)
            logs = get_all_logs_for_export(ACTIVE_USER_ID)
            history = get_recent_history(ACTIVE_USER_ID)
            
            clean_name = user[0].replace(' ', '_')
            filename = f"Laporan_Siklus_Zaraflow_{clean_name}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 50 + "\n")
                f.write("      REKAP KESEHATAN SIKLUS ZARAFLOW\n")
                f.write("=" * 50 + "\n")
                f.write(f"Nama Pengguna : {user[0]}\n")
                f.write(f"Email Terkait : {user[1]}\n")
                f.write(f"Tanggal Unduh : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("-" * 50 + "\n\n")
                
                f.write("[1. RIWAYAT SIKLUS TERAKHIR]\n")
                if history:
                    for h in history:
                        f.write(f"- Mulai: {h[0]} | Durasi: {h[1]} Hari | Lama Haid: {h[2]} Hari\n")
                else:
                    f.write("- Belum ada data riwayat.\n")
                    
                f.write("\n[2. CATATAN KONDISI TUBUH HARIAN]\n")
                if logs:
                    for l in logs:
                        f.write(f"- {l[0]}: Aliran={l[1]}, Mood={l[2]}, Gejala={l[3]}, Air={l[4]} gelas\n")
                else:
                    f.write("- Belum ada data catatan harian.\n")
                    
                f.write("\n" + "=" * 50 + "\n")
                f.write("Dokumen rekap otomatis dari aplikasi Zaraflow.\n")

            if "profile_status_lbl" in self.ids:
                self.ids.profile_status_lbl.text = f"Laporan berhasil disimpan di perangkat:\n{report_path}"
        except Exception as e:
            if "profile_status_lbl" in self.ids:
                self.ids.profile_status_lbl.text = f"Gagal mengunduh: {e}"

    def logout(self):
        global ACTIVE_USER_ID
        clear_session()
        ACTIVE_USER_ID = None
        self.manager.current = "auth"

class RootScreenManager(ScreenManager):
    pass

class ZaraflowApp(App):
    def build(self):
        init_db()
        sm = RootScreenManager(transition=FadeTransition(duration=1.2))
        sm.current = "splash"
        return sm

if __name__ == "__main__":
    ZaraflowApp().run()