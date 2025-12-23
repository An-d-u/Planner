import customtkinter as ctk
import tkinter as tk
import json
import os
import random
import calendar
import sys
import threading
import pygame
from datetime import datetime, timedelta
from tkinter import messagebox, Canvas

# 그래프 라이브러리 (설치 확인)
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# 트레이 아이콘 라이브러리
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# 알림 기능 라이브러리
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# --- 초기 설정 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
pygame.mixer.init()

# 폰트 설정
FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_HEADER = ("Segoe UI", 18, "bold")
FONT_NORMAL = ("Segoe UI", 14)
FONT_SMALL = ("Segoe UI", 12)
FONT_CAL_HEADER = ("Segoe UI", 14, "bold")
FONT_CAL_DAY = ("Segoe UI", 12)

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# ======================================================
#  0. 유틸리티 함수
# ======================================================

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_tray_icon_image():
    icon_path = resource_path("icon.ico") 
    if os.path.exists(icon_path):
        return Image.open(icon_path)
    else:
        width = 64; height = 64
        image = Image.new('RGB', (width, height), "#3B8ED0")
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, 3 * width // 4, 3 * height // 4), fill="white")
        return image

def play_sound(file_name):
    file_path = resource_path(file_name)
    if os.path.exists(file_path):
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Sound Error: {e}")
    else:
        print(f"File not found: {file_path}")

# ======================================================
#  1. 커스텀 위젯 및 효과
# ======================================================

class WeeklyReportWindow(ctk.CTkToplevel):
    """[NEW] 시각화된 주간 리포트 윈도우"""
    def __init__(self, master):
        super().__init__(master)
        self.title("Weekly Insights")
        self.geometry("800x600")
        self.attributes('-topmost', True)
        
        # 데이터 수집
        self.days, self.rates, self.total_done, self.total_goals, self.energies = self.collect_data()
        
        # 메인 컨테이너
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. 헤더
        ctk.CTkLabel(main_frame, text="📊 이번 주 리포트", font=("Segoe UI", 28, "bold")).pack(pady=(0, 20))
        
        # 2. 요약 카드 (3개 나란히)
        stats_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.create_stat_card(stats_frame, 0, "평균 달성률", f"{int(sum(self.rates)/7)}%" if self.rates else "0%", "#3B8ED0")
        self.create_stat_card(stats_frame, 1, "완료한 목표", f"{self.total_done}개", "#2CC985")
        
        avg_energy = "-"
        if self.energies:
            # 에너지 문자열을 점수로 변환 (High=3, Medium=2, Low=1)
            e_map = {"HIGH 🔥": 3, "MEDIUM ⚡": 2, "LOW 💤": 1, "Medium": 2}
            score_sum = sum([e_map.get(e, 2) for e in self.energies])
            avg_score = score_sum / len(self.energies)
            if avg_score > 2.3: avg_energy = "HIGH 🔥"
            elif avg_score > 1.6: avg_energy = "MEDIUM ⚡"
            else: avg_energy = "LOW 💤"
            
        self.create_stat_card(stats_frame, 2, "평균 에너지", avg_energy, "#E67E22")

        # 3. 그래프 영역
        if MATPLOTLIB_AVAILABLE:
            graph_frame = ctk.CTkFrame(main_frame, fg_color=("white", "gray20"))
            graph_frame.pack(fill="both", expand=True, pady=(0, 10))
            self.draw_graph(graph_frame)
        else:
            ctk.CTkLabel(main_frame, text="그래프를 보려면 matplotlib을 설치하세요.\n(pip install matplotlib)", text_color="gray").pack(expand=True)

        # 4. 코멘트
        comment = "기록이 부족해요. 조금씩 채워나가봐요!"
        if self.total_goals > 0:
            rate = self.total_done / self.total_goals
            if rate > 0.8: comment = "🔥 와우! 정말 불태운 한 주였네요! 완벽해요!"
            elif rate > 0.5: comment = "👍 꾸준히 잘하고 있어요. 이대로만 가요!"
            else: comment = "🌱 괜찮아요. 다음 주에 조금 더 집중해보면 돼요."
            
        ctk.CTkLabel(main_frame, text=comment, font=("Segoe UI", 16), text_color="gray").pack()

    def create_stat_card(self, parent, col, title, value, color):
        frame = ctk.CTkFrame(parent, fg_color=color, corner_radius=15)
        frame.grid(row=0, column=col, padx=10, sticky="ew")
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=(15, 5))
        ctk.CTkLabel(frame, text=value, font=("Segoe UI", 24, "bold"), text_color="white").pack(pady=(0, 15))

    def collect_data(self):
        today = datetime.now().date()
        days = []
        rates = [] # 퍼센트 (0~100)
        energies = []
        total_done = 0
        total_goals = 0
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            # 그래프 X축 라벨 (월/일)
            days.append(day.strftime("%m/%d"))
            
            path = os.path.join(DATA_DIR, f"{day_str}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    goals = data.get("goals", [])
                    # 목표 + 루틴 + 이브닝 체크박스 다 합쳐서 계산 (간단하게 목표만 계산할 수도 있음)
                    done_count = sum(1 for g in goals if g.get("done", False))
                    goal_count = len(goals)
                    
                    if goal_count > 0:
                        rates.append((done_count / goal_count) * 100)
                    else:
                        rates.append(0)
                        
                    total_done += done_count
                    total_goals += goal_count
                    if data.get("energy"):
                        energies.append(data.get("energy"))
                except:
                    rates.append(0)
            else:
                rates.append(0)
                
        return days, rates, total_done, total_goals, energies

    def draw_graph(self, parent):
        # matplotlib 그래프 생성
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        
        # 다크모드 대응 색상
        bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "white"
        text_color = "white" if ctk.get_appearance_mode() == "Dark" else "black"
        bar_color = "#3B8ED0"
        
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # 막대 그래프 그리기
        bars = ax.bar(self.days, self.rates, color=bar_color, width=0.5)
        
        # 스타일링
        ax.set_ylim(0, 100)
        ax.set_ylabel("Completion (%)", color=text_color)
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(text_color)

        # 막대 위에 숫자 표시
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}%',
                        ha='center', va='bottom', color=text_color, fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


class RoulettePopup(ctk.CTkFrame):
    def __init__(self, master, goals, callback=None):
        super().__init__(master, width=400, height=250, corner_radius=20, 
                         fg_color=("white", "gray20"), border_width=3, border_color="#9B59B6")
        self.goals = goals
        self.callback = callback
        self.place(relx=0.5, rely=0.5, anchor="center")
        
        self.title_lbl = ctk.CTkLabel(self, text="🎲 두구두구...", font=("Segoe UI", 24, "bold"), text_color="gray")
        self.title_lbl.pack(pady=(30, 10))
        self.result_lbl = ctk.CTkLabel(self, text="", font=("Segoe UI", 28, "bold"), text_color="#8E44AD", wraplength=350)
        self.result_lbl.pack(pady=10)
        self.btn = ctk.CTkButton(self, text="바로 시작하기!", command=self.close, width=150, height=40, state="disabled", fg_color="gray")
        self.btn.pack(pady=20)

        self.steps = 0; self.max_steps = 25; self.speed = 50; self.final_pick = ""
        self.animate()

    def animate(self):
        temp_pick = random.choice(self.goals)
        self.result_lbl.configure(text=temp_pick)
        if self.steps < self.max_steps:
            self.steps += 1
            if self.steps > self.max_steps * 0.7: self.speed += 30
            self.after(self.speed, self.animate)
        else:
            self.final_pick = random.choice(self.goals)
            self.result_lbl.configure(text=f"🎯 {self.final_pick}")
            self.title_lbl.configure(text="이것부터 하세요!")
            self.btn.configure(state="normal", fg_color="#9B59B6", hover_color="#8E44AD")
            play_sound("fanfare.mp3")

    def close(self):
        if self.callback and self.final_pick: self.callback(self.final_pick)
        self.destroy()

class ConfettiOverlay:
    def __init__(self, master):
        self.master = master
        x = master.winfo_x(); y = master.winfo_y(); w = master.winfo_width(); h = master.winfo_height()
        self.top = tk.Toplevel(master)
        self.top.geometry(f"{w}x{h}+{x}+{y}")
        self.top.overrideredirect(True); self.top.attributes('-topmost', True)
        self.transparent_color = "#000001" 
        self.top.config(bg=self.transparent_color); self.top.attributes('-transparentcolor', self.transparent_color)
        self.canvas = tk.Canvas(self.top, bg=self.transparent_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.particles = []; self.colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#FFA500"]
        self.width = w; self.height = h
        
    def start(self):
        for _ in range(120):
            self.particles.append({
                "x": random.randint(0, self.width), "y": random.randint(self.height // 2, self.height + 100),
                "speed_x": random.uniform(-4, 4), "speed_y": random.uniform(-18, -8),
                "gravity": 0.5, "color": random.choice(self.colors), "size": random.randint(5, 9)
            })
        play_sound("fanfare.mp3")
        self.animate()

    def animate(self):
        self.canvas.delete("all")
        active_particles = False
        for p in self.particles:
            p["x"] += p["speed_x"]; p["y"] += p["speed_y"]; p["speed_y"] += p["gravity"]
            if p["y"] < self.height + 20:
                active_particles = True
                self.canvas.create_oval(p["x"], p["y"], p["x"]+p["size"], p["y"]+p["size"], fill=p["color"], outline="")
        if active_particles: self.master.after(20, self.animate)
        else: self.top.destroy()

class PomodoroTimer(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=("gray90", "gray20"), corner_radius=10, **kwargs)
        self.default_time = 1500 
        self.time_left = self.default_time
        self.running = False
        
        lbl = ctk.CTkLabel(self, text="🍅 POMODORO", font=("Segoe UI", 12, "bold"), text_color="gray")
        lbl.pack(pady=(10, 0))

        self.time_entry = ctk.CTkEntry(self, font=("Segoe UI", 32, "bold"), text_color="#E74C3C", 
                                       justify="center", border_width=0, fg_color="transparent", width=120)
        self.time_entry.insert(0, "25") 
        self.time_entry.pack(pady=5)
        
        self.unit_lbl = ctk.CTkLabel(self, text="min", font=("Segoe UI", 10), text_color="gray")
        self.unit_lbl.place(relx=0.8, rely=0.45)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        self.start_btn = ctk.CTkButton(btn_frame, text="Start", width=60, height=24, fg_color="#2ECC71", hover_color="#27AE60", command=self.toggle_timer)
        self.start_btn.pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Reset", width=60, height=24, fg_color="gray", hover_color="gray30", command=self.reset_timer).pack(side="left", padx=5)

    def toggle_timer(self):
        if self.running:
            self.running = False
            self.start_btn.configure(text="Start", fg_color="#2ECC71")
            self.time_entry.configure(state="normal")
        else:
            try:
                current_text = self.time_entry.get().split(":")[0]
                minutes = int(current_text)
                self.time_left = minutes * 60
                self.running = True
                self.start_btn.configure(text="Pause", fg_color="#E67E22")
                self.time_entry.configure(state="disabled")
                self.countdown()
            except ValueError:
                messagebox.showerror("오류", "올바른 시간을 입력해주세요")

    def countdown(self):
        if self.running and self.time_left > 0:
            self.time_left -= 1
            mins, secs = divmod(self.time_left, 60)
            self.time_entry.configure(state="normal")
            self.time_entry.delete(0, "end")
            self.time_entry.insert(0, f"{mins:02d}:{secs:02d}")
            self.time_entry.configure(state="disabled")
            self.after(1000, self.countdown)
        elif self.time_left == 0 and self.running:
            self.running = False
            self.start_btn.configure(text="Start", fg_color="#2ECC71")
            self.time_entry.configure(state="normal")
            self.show_notification()
            messagebox.showinfo("Pomodoro", "🍅 집중 시간 끝!")

    def show_notification(self):
        if PLYER_AVAILABLE:
            try: notification.notify(title='ADHD Dashboard', message='집중 시간 종료!', app_name='ADHD Planner', timeout=10)
            except: pass

    def reset_timer(self):
        self.running = False
        self.time_entry.configure(state="normal")
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, "25")
        self.start_btn.configure(text="Start", fg_color="#2ECC71")

class CTkCalendar(ctk.CTkFrame):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.command = command 
        self.selected_date = datetime.now().date()
        self.current_month_date = datetime.now().date()
        self.setup_header()
        self.setup_days_labels()
        self.setup_calendar_grid()
        self.update_calendar()

    def setup_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(header_frame, text="<", width=30, height=30, fg_color="transparent", hover_color=("gray85", "gray25"),
                      text_color=("black", "white"), font=FONT_CAL_HEADER, command=lambda: self.change_month(-1)).pack(side="left")
        self.lbl_month = ctk.CTkLabel(header_frame, text="YYYY-MM", font=FONT_CAL_HEADER, width=120)
        self.lbl_month.pack(side="left", expand=True)
        ctk.CTkButton(header_frame, text=">", width=30, height=30, fg_color="transparent", hover_color=("gray85", "gray25"),
                      text_color=("black", "white"), font=FONT_CAL_HEADER, command=lambda: self.change_month(1)).pack(side="right")

    def setup_days_labels(self):
        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="x", pady=(0, 5))
        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for day in weekdays:
            color = "#FF6B6B" if day == "Sun" else ("gray30", "gray70")
            ctk.CTkLabel(days_frame, text=day, font=("Segoe UI", 10, "bold"), text_color=color, width=38, anchor="center").pack(side="left", expand=True)

    def setup_calendar_grid(self):
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        self.day_buttons = []
        for row in range(6):
            row_buttons = []
            row_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
            row_frame.pack(fill="x")
            for col in range(7):
                btn = ctk.CTkButton(row_frame, text="", width=38, height=38, fg_color="transparent", corner_radius=10, font=FONT_CAL_DAY,
                                    command=lambda r=row, c=col: self.on_day_click(r, c))
                btn.pack(side="left", padx=1, pady=1, expand=True)
                row_buttons.append(btn)
            self.day_buttons.append(row_buttons)

    def update_calendar(self):
        year, month = self.current_month_date.year, self.current_month_date.month
        self.lbl_month.configure(text=f"{year}. {month:02d}")
        month_range = calendar.monthrange(year, month)
        first_weekday, num_days = (month_range[0] + 1) % 7, month_range[1]
        day_counter = 1
        for row in range(6):
            for col in range(7):
                btn = self.day_buttons[row][col]
                if (row == 0 and col < first_weekday) or day_counter > num_days:
                    btn.configure(text="", state="disabled", fg_color="transparent", border_width=0)
                    btn.date_val = None
                else:
                    curr_date = datetime(year, month, day_counter).date()
                    btn.configure(text=str(day_counter), state="normal")
                    if curr_date == self.selected_date:
                        btn.configure(fg_color=["#3B8ED0", "#1F6AA5"], text_color="white", border_width=0)
                    elif curr_date == datetime.now().date():
                        btn.configure(fg_color="transparent", border_width=1, border_color="gray", text_color=("black", "white"))
                    else:
                        btn.configure(fg_color="transparent", border_width=0, text_color=("black", "white"))
                    btn.date_val = curr_date
                    day_counter += 1

    def change_month(self, step):
        month = self.current_month_date.month + step
        year = self.current_month_date.year
        if month > 12: month, year = 1, year + 1
        elif month < 1: month, year = 12, year - 1
        self.current_month_date = datetime(year, month, 1).date()
        self.update_calendar()

    def on_day_click(self, row, col):
        btn = self.day_buttons[row][col]
        if btn.date_val:
            self.selected_date = btn.date_val
            self.update_calendar()
            if self.command: self.command(self.selected_date)

    def get_date(self): return self.selected_date.strftime("%Y-%m-%d")


class DynamicChecklist(ctk.CTkFrame):
    def __init__(self, master, title, default_items=[], command=None):
        super().__init__(master, fg_color="transparent")
        self.items = [] 
        self.command = command 
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5))
        ctk.CTkLabel(header_frame, text=f" {title}", font=FONT_HEADER, anchor="w").pack(side="left")
        ctk.CTkButton(header_frame, text="+ Add", width=60, height=24, font=("Segoe UI", 11, "bold"), fg_color="transparent", 
                      border_width=1, text_color=("gray10", "gray90"), command=self.add_item).pack(side="right")
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="x", expand=True)
        for text in default_items: self.add_item(text=text)

    def add_item(self, text="", checked=False):
        row = ctk.CTkFrame(self.list_frame, fg_color=("gray95", "gray20"), corner_radius=6)
        row.pack(fill="x", pady=3, ipady=2)
        var = ctk.BooleanVar(value=checked)
        chk = ctk.CTkCheckBox(row, text="", variable=var, width=24, height=24, corner_radius=12, command=self.on_check)
        chk.pack(side="left", padx=(10, 5))
        entry = ctk.CTkEntry(row, font=FONT_NORMAL, height=30, border_width=0, fg_color="transparent")
        entry.insert(0, text)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(row, text="×", width=25, height=25, fg_color="transparent", hover_color="#FF6B6B",
                      text_color=("gray50", "gray90"), font=("Arial", 16),
                      command=lambda: self.delete_item(row)).pack(side="right", padx=5)
        self.items.append({"var": var, "entry": entry, "row": row})
        if self.command: self.command()

    def delete_item(self, row_widget):
        for item in self.items:
            if item["row"] == row_widget:
                item["row"].destroy(); self.items.remove(item); break
        if self.command: self.command()

    def on_check(self):
        if self.command: self.command()

    def get_data(self):
        return [{"text": item["entry"].get(), "done": item["var"].get()} for item in self.items]

    def load_data(self, data_list):
        for item in self.items: item["row"].destroy()
        self.items = []
        for item in data_list: self.add_item(text=item.get("text", ""), checked=item.get("done", False))


# ======================================================
#  2. 메인 애플리케이션
# ======================================================
class ADHDPlannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Daily Dashboard")
        self.geometry("1400x1100")
        
        try: self.iconbitmap(resource_path("icon.ico"))
        except: pass

        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.current_date_str = datetime.now().strftime("%Y-%m-%d")
        self.selected_date_ideas = "" 
        self.previous_progress = 0.0
        
        self.setup_sidebar()
        self.setup_dashboard()
        self.load_date_data(self.current_date_str)

    def setup_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="MY DASHBOARD", font=("Segoe UI", 26, "bold")).pack(pady=(30, 10))
        cal_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        cal_container.pack(fill="x", padx=15, pady=10)
        self.cal = CTkCalendar(cal_container, command=self.on_date_select)
        self.cal.pack()

        self.timer = PomodoroTimer(self.sidebar)
        self.timer.pack(fill="x", padx=20, pady=10)

        self.info_frame = ctk.CTkFrame(self.sidebar, fg_color=("gray90", "gray20"), corner_radius=10)
        self.info_frame.pack(fill="x", padx=20, pady=10)
        self.preview_date_label = ctk.CTkLabel(self.info_frame, text=self.current_date_str, font=("Segoe UI", 14, "bold"))
        self.preview_date_label.pack(pady=(10, 5))
        self.stats_label = ctk.CTkLabel(self.info_frame, text="오늘의 기록을 시작하세요!", font=FONT_SMALL, justify="center")
        self.stats_label.pack(pady=5)

        self.day_idea_btn = ctk.CTkButton(self.sidebar, text="이 날의 아이디어 확인", command=self.show_day_idea, state="disabled", fg_color="transparent", text_color=("gray10", "gray90"))
        self.day_idea_btn.pack(fill="x", padx=20, pady=(10, 5))
        
        self.random_all_btn = ctk.CTkButton(self.sidebar, text="🎲 전체 랜덤 아이디어", command=self.show_real_random_idea, fg_color="#8E44AD", hover_color="#732D91")
        self.random_all_btn.pack(fill="x", padx=20, pady=5)

        # [수정] 주간 리포트 기능 연결
        ctk.CTkButton(self.sidebar, text="📈 주간 리포트 (통계)", command=self.show_weekly_report, fg_color="#34495E", hover_color="#2C3E50").pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(self.sidebar, text="📌 Mini Mode (플로팅)", command=self.switch_to_mini_mode, fg_color="#E67E22", hover_color="#D35400").pack(fill="x", padx=20, pady=5)

        self.load_btn = ctk.CTkButton(self.sidebar, text="이 날짜 열기 ➔", command=self.load_selected_dashboard, fg_color="#3B8ED0", hover_color="#36719F", height=40, font=("Segoe UI", 14, "bold"))
        self.load_btn.pack(fill="x", padx=20, pady=(20, 10))
        
        self.save_btn = ctk.CTkButton(self.sidebar, text="Save Dashboard", command=self.save_data, fg_color="#2CC985", hover_color="#229966", height=40, font=("Segoe UI", 14, "bold"))
        self.save_btn.pack(fill="x", padx=20, pady=(0, 20))
        
        settings_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        settings_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        ctk.CTkOptionMenu(settings_frame, values=["System", "Light", "Dark"], command=ctk.set_appearance_mode).pack(fill="x", pady=5)

    def setup_dashboard(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_area, corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True)
        container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=40)

        header_row = ctk.CTkFrame(container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))
        self.date_display = ctk.CTkLabel(header_row, text=self.current_date_str, font=("Segoe UI", 36, "bold"))
        self.date_display.pack(side="left")
        ctk.CTkLabel(header_row, text=" |  Focus on what matters.", font=("Segoe UI", 20), text_color="gray").pack(side="left", padx=10, pady=10)

        self.progress_bar = ctk.CTkProgressBar(container, height=15, corner_radius=8, progress_color="#2ECC71")
        self.progress_bar.pack(fill="x", pady=(0, 20))
        self.progress_bar.set(0)

        self.goal_card = ctk.CTkFrame(container, fg_color=("white", "gray20"), corner_radius=15)
        self.goal_card.pack(fill="x", pady=10)
        
        goal_header = ctk.CTkFrame(self.goal_card, fg_color="transparent")
        goal_header.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(goal_header, text="🎯 Top 3 Goals", font=FONT_HEADER).pack(side="left")
        ctk.CTkButton(goal_header, text="🎲 Pick One", width=80, height=28, fg_color="#9B59B6", hover_color="#8E44AD", command=self.pick_random_goal).pack(side="right")

        self.goal_widgets = []
        for i in range(3):
            row = ctk.CTkFrame(self.goal_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(row, text="", variable=var, width=24, height=24, corner_radius=12, command=self.update_progress)
            chk.pack(side="left", padx=(0, 10))
            entry = ctk.CTkEntry(row, placeholder_text=f"오늘의 핵심 목표 {i+1}", font=FONT_NORMAL, height=40, border_width=0, fg_color=("gray95", "gray15"))
            entry.pack(side="left", fill="x", expand=True)
            
            btn_up = ctk.CTkButton(row, text="▲", width=25, height=25, fg_color="transparent", text_color=("black", "white"), font=("Arial", 12, "bold"), command=lambda idx=i: self.move_goal(idx, -1))
            btn_up.pack(side="right", padx=(2, 0))
            btn_down = ctk.CTkButton(row, text="▼", width=25, height=25, fg_color="transparent", text_color=("black", "white"), font=("Arial", 12, "bold"), command=lambda idx=i: self.move_goal(idx, 1))
            btn_down.pack(side="right", padx=(0, 5))

            self.goal_widgets.append({"chk": var, "entry": entry})
        ctk.CTkFrame(self.goal_card, height=10, fg_color="transparent").pack()

        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, pady=10)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        left_col = ctk.CTkFrame(grid_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        right_col = ctk.CTkFrame(grid_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        time_card = ctk.CTkFrame(left_col, fg_color=("white", "gray20"), corner_radius=15)
        time_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(time_card, text="🕒 Time Blocks", font=FONT_HEADER).pack(anchor="w", padx=20, pady=(15, 10))
        self.time_entries = {}
        self.time_entry_widgets = []
        times = ["07-09 AM", "09-11 AM", "11-01 PM", "01-03 PM", "03-05 PM", "05-07 PM", "07-09 PM", "09 PM +"]
        for i, t in enumerate(times):
            row = ctk.CTkFrame(time_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=t, width=80, anchor="w", font=("Segoe UI", 12, "bold"), text_color="gray").pack(side="left")
            entry = ctk.CTkEntry(row, height=32, border_width=0, fg_color=("gray95", "gray15"))
            entry.pack(side="right", fill="x", expand=True)
            self.time_entries[t] = entry
            self.time_entry_widgets.append(entry)
            
            btn_up = ctk.CTkButton(row, text="▲", width=25, height=25, fg_color="transparent", text_color=("black", "white"), font=("Arial", 12, "bold"), command=lambda idx=i: self.move_time_block(idx, -1))
            btn_up.pack(side="right", padx=(2, 0))
            btn_down = ctk.CTkButton(row, text="▼", width=25, height=25, fg_color="transparent", text_color=("black", "white"), font=("Arial", 12, "bold"), command=lambda idx=i: self.move_time_block(idx, 1))
            btn_down.pack(side="right", padx=(0, 5))

        ctk.CTkFrame(time_card, height=15, fg_color="transparent").pack()

        misc_card = ctk.CTkFrame(left_col, fg_color=("white", "gray20"), corner_radius=15)
        misc_card.pack(fill="x")
        ctk.CTkLabel(misc_card, text="🔋 Energy Level", font=FONT_HEADER).pack(anchor="w", padx=20, pady=(15, 5))
        self.energy_var = ctk.StringVar(value="Medium")
        ctk.CTkSegmentedButton(misc_card, values=["HIGH 🔥", "MEDIUM ⚡", "LOW 💤"], variable=self.energy_var, font=("Segoe UI", 12, "bold"), height=35).pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(misc_card, text="💡 아이디어 (Ideas)", font=FONT_HEADER).pack(anchor="w", padx=20, pady=(15, 5))
        self.idea_box = ctk.CTkTextbox(misc_card, height=120, font=FONT_NORMAL, fg_color=("gray95", "gray15"))
        self.idea_box.pack(fill="x", padx=20, pady=(0, 20))

        note_card = ctk.CTkFrame(right_col, fg_color=("white", "gray20"), corner_radius=15)
        note_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(note_card, text="🧠 Brain Dump", font=FONT_HEADER).pack(anchor="w", padx=20, pady=(15, 5))
        self.brain_dump = ctk.CTkTextbox(note_card, height=100, font=FONT_NORMAL, fg_color=("gray95", "gray15"))
        self.brain_dump.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(note_card, text="🏆 Small Wins", font=FONT_HEADER).pack(anchor="w", padx=20, pady=(5, 5))
        self.small_wins = ctk.CTkTextbox(note_card, height=80, font=FONT_NORMAL, fg_color=("gray95", "gray15"))
        self.small_wins.pack(fill="x", padx=20, pady=(0, 20))

        check_card = ctk.CTkFrame(right_col, fg_color=("white", "gray20"), corner_radius=15)
        check_card.pack(fill="x")
        self.routine_list = DynamicChecklist(check_card, "ROUTINE CHECK", default_items=["물 마시기", "스트레칭"], command=self.update_progress)
        self.routine_list.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkFrame(check_card, height=1, fg_color=("gray90", "gray30")).pack(fill="x", padx=20, pady=5)
        self.evening_list = DynamicChecklist(check_card, "EVENING ROUTINE", default_items=["회고하기", "내일 준비"], command=self.update_progress)
        self.evening_list.pack(fill="x", padx=20, pady=(5, 20))

    # --- 기능 로직 ---

    def calculate_live_stats(self):
        if not hasattr(self, 'goal_widgets'): return "로딩 중..."
        goals = self.goal_widgets
        total = len(goals)
        checked = sum(1 for w in goals if w["chk"].get())
        energy = self.energy_var.get()
        return f"Goals: {checked}/{total}  |  Energy: {energy}"

    def move_goal(self, index, direction):
        target_index = index + direction
        if 0 <= target_index < len(self.goal_widgets):
            current_text = self.goal_widgets[index]["entry"].get()
            current_check = self.goal_widgets[index]["chk"].get()
            target_text = self.goal_widgets[target_index]["entry"].get()
            target_check = self.goal_widgets[target_index]["chk"].get()
            self.goal_widgets[index]["entry"].delete(0, "end"); self.goal_widgets[index]["entry"].insert(0, target_text); self.goal_widgets[index]["chk"].set(target_check)
            self.goal_widgets[target_index]["entry"].delete(0, "end"); self.goal_widgets[target_index]["entry"].insert(0, current_text); self.goal_widgets[target_index]["chk"].set(current_check)
            self.update_progress()

    def move_time_block(self, index, direction):
        target_index = index + direction
        if 0 <= target_index < len(self.time_entry_widgets):
            curr_entry = self.time_entry_widgets[index]
            target_entry = self.time_entry_widgets[target_index]
            curr_text = curr_entry.get(); target_text = target_entry.get()
            curr_entry.delete(0, "end"); curr_entry.insert(0, target_text)
            target_entry.delete(0, "end"); target_entry.insert(0, curr_text)

    def move_picked_goal_to_top(self, picked_text):
        for i, w in enumerate(self.goal_widgets):
            if w["entry"].get() == picked_text:
                if i > 0:
                    top_text = self.goal_widgets[0]["entry"].get(); top_chk = self.goal_widgets[0]["chk"].get()
                    self.goal_widgets[0]["entry"].delete(0, "end"); self.goal_widgets[0]["entry"].insert(0, picked_text); self.goal_widgets[0]["chk"].set(w["chk"].get())
                    w["entry"].delete(0, "end"); w["entry"].insert(0, top_text); w["chk"].set(top_chk)
                break
        self.update_progress()

    def minimize_to_tray(self):
        if not TRAY_AVAILABLE: self.quit(); return
        self.withdraw()
        image = create_tray_icon_image()
        menu = (item('Open Dashboard', self.show_window_from_tray), item('Exit App', self.quit_app))
        self.tray_icon = pystray.Icon("name", image, "ADHD Planner", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_app(self, icon, item):
        icon.stop()
        self.quit()

    def update_progress(self):
        if not hasattr(self, 'routine_list') or not hasattr(self, 'evening_list') or not hasattr(self, 'goal_widgets'): return
        total = 3 + len(self.routine_list.items) + len(self.evening_list.items)
        if total == 0: return
        checked = sum(1 for w in self.goal_widgets if w["chk"].get()) + sum(1 for item in self.routine_list.items if item["var"].get()) + sum(1 for item in self.evening_list.items if item["var"].get())
        ratio = checked / total
        self.progress_bar.set(ratio)
        if ratio == 1.0 and self.previous_progress < 1.0: self.trigger_celebration()
        self.previous_progress = ratio
        
        if self.cal.get_date() == datetime.now().strftime("%Y-%m-%d"):
            self.stats_label.configure(text=self.calculate_live_stats())

    def trigger_celebration(self):
        celebration = ConfettiOverlay(self) 
        celebration.start()

    def show_real_random_idea(self):
        all_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
        valid_ideas = []
        for fname in all_files:
            try:
                with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    idea_text = data.get("ideas", "").strip()
                    if idea_text:
                        valid_ideas.append((fname.replace(".json", ""), idea_text))
            except: continue

        if not valid_ideas:
            messagebox.showinfo("알림", "아직 저장된 아이디어가 없습니다. 아이디어를 먼저 기록해보세요!")
            return

        picked_date, picked_text = random.choice(valid_ideas)
        self.create_idea_popup(f"Random Idea - {picked_date}", f"🎲 Random Pick from {picked_date}", picked_text)

    def pick_random_goal(self):
        goals = [w["entry"].get() for w in self.goal_widgets if w["entry"].get().strip()]
        if not goals: messagebox.showinfo("알림", "먼저 목표를 입력해주세요!"); return
        RoulettePopup(self, goals, callback=self.move_picked_goal_to_top)

    def show_weekly_report(self):
        # [NEW] WeeklyReportWindow 호출 (새로운 클래스 사용)
        WeeklyReportWindow(self)

    def switch_to_mini_mode(self):
        self.withdraw()
        active_goal = "모든 목표 달성! 🎉"
        for w in self.goal_widgets:
            if not w["chk"].get() and w["entry"].get().strip(): active_goal = w["entry"].get(); break
        
        self.mini_window = ctk.CTkToplevel(); self.mini_window.geometry("300x180")
        self.mini_window.overrideredirect(True); self.mini_window.attributes('-topmost', True)
        
        drag_frame = ctk.CTkFrame(self.mini_window, corner_radius=10, fg_color=("gray85", "gray25"))
        drag_frame.pack(fill="both", expand=True)
        control_frame = ctk.CTkFrame(self.mini_window, corner_radius=0, fg_color=("gray90", "gray20"), height=60)
        control_frame.pack(fill="x", side="bottom")

        for w in [drag_frame, ctk.CTkLabel(drag_frame, text="🔥 Current Focus", font=("Segoe UI", 12, "bold"), text_color="gray"), ctk.CTkLabel(drag_frame, text=active_goal, font=("Segoe UI", 16, "bold"), wraplength=280)]:
            w.pack(pady=(10,0)) if isinstance(w, ctk.CTkLabel) else None
            w.bind("<Button-1>", self.start_move); w.bind("<B1-Motion>", self.do_move)

        slider = ctk.CTkSlider(control_frame, from_=0.1, to=1.0, number_of_steps=10, width=150, command=lambda v: self.mini_window.attributes('-alpha', v))
        slider.set(1.0); slider.pack(pady=(10, 5))
        ctk.CTkButton(control_frame, text="Expand", command=self.restore_main_window, width=80, height=24).pack(pady=(0, 10))

    def start_move(self, event): self.x, self.y = event.x, event.y
    def do_move(self, event): self.mini_window.geometry(f"+{self.mini_window.winfo_x() + event.x - self.x}+{self.mini_window.winfo_y() + event.y - self.y}")
    def restore_main_window(self): self.mini_window.destroy(); self.deiconify()

    def on_date_select(self, date_obj):
        selected_date = date_obj.strftime("%Y-%m-%d")
        file_path = os.path.join(DATA_DIR, f"{selected_date}.json")
        self.preview_date_label.configure(text=f"{selected_date}")
        
        if selected_date == datetime.now().strftime("%Y-%m-%d"):
            self.stats_label.configure(text=self.calculate_live_stats())
            has_idea = len(self.idea_box.get("1.0", "end-1c").strip()) > 0
            self.selected_date_ideas = self.idea_box.get("1.0", "end-1c")
        else:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                goals = data.get("goals", [])
                done = sum(1 for g in goals if g.get("done", False))
                self.selected_date_ideas = data.get("ideas", "")
                self.stats_label.configure(text=f"Goals: {done}/{len(goals)}  |  Energy: {data.get('energy', '-')}")
                has_idea = len(self.selected_date_ideas) > 0
            else:
                self.stats_label.configure(text="기록 없음")
                has_idea = False
                self.selected_date_ideas = ""
        
        self.day_idea_btn.configure(state="normal" if has_idea else "disabled", fg_color="#008000" if has_idea else "transparent", hover_color="#006400" if has_idea else ("gray70", "gray30"))

    def show_day_idea(self): self.create_idea_popup(f"Idea - {self.cal.get_date()}", f"💡 Ideas from {self.cal.get_date()}", self.selected_date_ideas)
    
    def create_idea_popup(self, title, header, content):
        top = ctk.CTkToplevel(self); top.title(title); top.geometry("400x350")
        top.lift(); top.attributes('-topmost', True); top.focus_force()
        ctk.CTkLabel(top, text=header, font=FONT_HEADER).pack(pady=10)
        txt = ctk.CTkTextbox(top, font=FONT_NORMAL, fg_color=("gray95", "gray15"))
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 20)); txt.insert("1.0", content); txt.configure(state="disabled")

    def load_selected_dashboard(self): self.load_date_data(self.cal.get_date())

    def save_data(self):
        data = {
            "goals": [{"text": w["entry"].get(), "done": w["chk"].get()} for w in self.goal_widgets],
            "time_blocks": {t: entry.get() for t, entry in self.time_entries.items()},
            "energy": self.energy_var.get(), "ideas": self.idea_box.get("1.0", "end-1c"),
            "brain_dump": self.brain_dump.get("1.0", "end-1c"), "small_wins": self.small_wins.get("1.0", "end-1c"),
            "routines": self.routine_list.get_data(), "evening": self.evening_list.get_data()
        }
        with open(os.path.join(DATA_DIR, f"{self.current_date_str}.json"), "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
        if self.cal.get_date() == self.current_date_str: self.on_date_select(datetime.strptime(self.current_date_str, "%Y-%m-%d").date())
        messagebox.showinfo("Saved", "대시보드가 저장되었습니다.")

    def load_date_data(self, date_str):
        self.current_date_str = date_str; self.date_display.configure(text=date_str)
        path = os.path.join(DATA_DIR, f"{date_str}.json")
        for w in self.goal_widgets: w["entry"].delete(0, "end"); w["chk"].set(False)
        for entry in self.time_entries.values(): entry.delete(0, "end")
        self.idea_box.delete("1.0", "end"); self.brain_dump.delete("1.0", "end"); self.small_wins.delete("1.0", "end")
        self.energy_var.set("Medium"); self.progress_bar.set(0)

        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                for w, g_data in zip(self.goal_widgets, data.get("goals", [])): w["entry"].insert(0, g_data.get("text", "")); w["chk"].set(g_data.get("done", False))
                for t, text in data.get("time_blocks", {}).items(): 
                    if t in self.time_entries: self.time_entries[t].insert(0, text)
                self.energy_var.set(data.get("energy", "Medium")); self.idea_box.insert("1.0", data.get("ideas", ""))
                self.brain_dump.insert("1.0", data.get("brain_dump", "")); self.small_wins.insert("1.0", data.get("small_wins", ""))
                self.routine_list.load_data(data.get("routines", [])); self.evening_list.load_data(data.get("evening", []))
                self.update_progress()
            except: pass
        else:
            # [기능 추가] 가장 최근 데이터 불러오기 (루틴 지속성)
            found_recent = False
            try:
                # 날짜 형식(YYYY-MM-DD.json)인 파일만 필터링하여 정렬
                valid_files = []
                for f in os.listdir(DATA_DIR):
                    if f.endswith(".json"):
                        try:
                            # 파일명에서 날짜 파싱 시도
                            datetime.strptime(f[:-5], "%Y-%m-%d")
                            valid_files.append(f)
                        except ValueError:
                            pass
                
                valid_files.sort() # 날짜순 정렬

                if valid_files:
                    last_file = valid_files[-1] # 가장 최근 날짜 파일
                    with open(os.path.join(DATA_DIR, last_file), "r", encoding="utf-8") as f:
                        prev_data = json.load(f)
                    
                    routines = prev_data.get("routines", [])
                    evening = prev_data.get("evening", [])
                    
                    # 체크 상태 초기화 (내용은 유지하되 체크만 해제)
                    for item in routines: item["done"] = False
                    for item in evening: item["done"] = False

                    self.routine_list.load_data(routines)
                    self.evening_list.load_data(evening)
                    found_recent = True
            except Exception as e:
                print(f"Error loading previous data: {e}")

            if not found_recent:
                # 이전 데이터가 없으면 기본값 로드
                self.routine_list.load_data([{"text": "물 마시기"}, {"text": "덤벨 들기"}])
                self.evening_list.load_data([{"text": "플래너 정리하기"}, {"text": "내일 계획 준비"}])
            
            self.update_progress()
        
        self.on_date_select(datetime.strptime(date_str, "%Y-%m-%d").date())

if __name__ == "__main__":
    app = ADHDPlannerApp()
    app.mainloop()