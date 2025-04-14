import flet as ft
from datetime import datetime, timedelta
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

LEAVE_TYPES = {
    "sick": "ลาป่วย",
    "vacation": "ลาพักร้อน",
    "personal": "ลากิจ"
}

COLOR_MAP = {
    "sick": ft.Colors.RED_200,
    "vacation": ft.Colors.GREEN_200,
    "personal": ft.Colors.YELLOW_200,
    "holiday": ft.Colors.BLUE_200,
    "today": ft.Colors.PURPLE_300,
    "selected": ft.Colors.ORANGE_200
}

NOTE_COLORS = {
    "blue": ft.Colors.BLUE_100,
    "green": ft.Colors.GREEN_100,
    "yellow": ft.Colors.YELLOW_100,
    "pink": ft.Colors.PINK_100
}


def get_month_label(month):
    month_th = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    return month_th[month - 1]



class NotePopup(ft.AlertDialog):
    def __init__(self, notes, on_submit):
        self.new_note = ft.TextField(label="ข้อความโน้ต", multiline=True)
        self.color_picker = ft.Dropdown(
            label="เลือกสี",
            options=[ft.dropdown.Option(k, text=k.title()) for k in NOTE_COLORS]
        )

        note_list = ft.Column(
            [
                ft.Container(
                    content=ft.Text(note["content"]),
                    bgcolor=note["color"],
                    padding=10,
                    border_radius=6,
                    width=float("inf"),
                    height=60  # ความสูงคงที่ต่อ note
                ) for note in notes
            ],
            spacing=10
        )

        scrollable_notes = ft.Container(
            content=ft.ListView(
                controls=note_list.controls,
                expand=True,
                spacing=10,
                padding=0,
                auto_scroll=False
            ),
            expand=True
        )

        note_input_area = ft.Column([
            self.color_picker,
            self.new_note,
        ])

        super().__init__(
            modal=True,
            title=ft.Text("Note"),
            content=ft.Column(
                controls=[
                    scrollable_notes,  # จะขยายเต็มพื้นที่ที่เหลือ
                    note_input_area    # ส่วนป้อนโน้ตใหม่
                ],
                expand=True,
                height=400,
                tight=True
            ),
            actions=[
                ft.TextButton("บันทึก", on_click=lambda e: on_submit(self.new_note.value, self.color_picker.value)),
                ft.TextButton("ยกเลิก", on_click=self.close_popup)
            ]
        )

    def close_popup(self, e=None):
        self.open = False
        self.update()

class QuotaPopup(ft.AlertDialog):
    def __init__(self, quotas, on_submit):
        self.inputs = [(q["type"], ft.TextField(label=f"{LEAVE_TYPES[q['type']]} (วัน)", value=str(q["total"]))) for q in quotas]

        # Header row with close button
        header_row = ft.Row(
            controls=[
                ft.Text("อัปเดตโควต้าการลา", size=16, weight="bold", expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, on_click=self._close)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        super().__init__(
            modal=True,
            content=ft.Column([header_row] + [inp[1] for inp in self.inputs], tight=True),
            actions=[
                ft.TextButton("ยืนยัน", on_click=lambda e: on_submit(self.inputs)),
                ft.TextButton("ยกเลิก", on_click=self._close)
            ]
        )

    def _close(self, e=None):
        self.open = False
        if hasattr(self, "page"):
            self.page.update()


class LeaveApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.today = datetime.today()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.selected_date = ft.Text("")
        self.selected_date_detail = ft.Text("")

        self.leaves = []
        self.holidays = []
        self.quotas = []
        self.notes = []

        self.data_loaded = False
        self.calendar_rows = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.leave_summary = ft.Row(wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        self.header_text = ft.Text(size=16)
        self.leave_type_dd = ft.Dropdown(label="ประเภทการลา", options=[ft.dropdown.Option(k, text=v) for k, v in LEAVE_TYPES.items()])
        self.reason_tf = ft.TextField(label="เหตุผล", expand=True)
        self.holiday_name = ft.TextField(label="ชื่อวันหยุด", expand=True)
        self.note_button = ft.ElevatedButton("Note", icon=ft.Icons.EVENT_NOTE, on_click=self.show_note_popup)

    def fetch_table(self, table):
        return supabase.table(table).select("*").execute().data

    def load_data(self):
        if not self.data_loaded:
            self.leaves = self.fetch_table("leaves")
            self.holidays = self.fetch_table("holidays")
            self.quotas = self.fetch_table("leave_quota")
            self.notes = self.fetch_table("notes")
            self.data_loaded = True

    def reload_data(self):
        self.leaves = self.fetch_table("leaves")
        self.holidays = self.fetch_table("holidays")
        self.quotas = self.fetch_table("leave_quota")
        self.notes = self.fetch_table("notes")


    def save_leave(self, date, leave_type, reason):
        supabase.table("leaves").insert({
            "date": date.isoformat(),
            "type": leave_type,
            "reason": reason
        }).execute()
        # self.load_data()
        self.reload_data()

    def save_holiday(self, date, name):
        supabase.table("holidays").insert({
            "date": date.isoformat(),
            "name": name
        }).execute()
        # self.load_data()
        self.reload_data()

    def update_quota(self, type_, total):
        existing = supabase.table("leave_quota").select("*").eq("type", type_).execute().data
        if existing:
            supabase.table("leave_quota").update({"total": total}).eq("type", type_).execute()
        else:
            supabase.table("leave_quota").insert({"type": type_, "total": total}).execute()

    def build_calendar(self):

        self.calendar_rows.controls.clear()
        first_day = datetime(self.current_year, self.current_month, 1)
        start_day = first_day - timedelta(days=(first_day.weekday() + 1) % 7)

        day_size = (self.page.width - 6 * 10 - 40) / 7

        header = [
            ft.Container(
                content=ft.Text("อา.", size=12, text_align=ft.TextAlign.CENTER, color=ft.Colors.RED_300, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("จ.", size=12, text_align=ft.TextAlign.CENTER, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("อ.", size=12, text_align=ft.TextAlign.CENTER, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("พ.", size=12, text_align=ft.TextAlign.CENTER, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("พฤ.", size=12, text_align=ft.TextAlign.CENTER, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("ศ.", size=12, text_align=ft.TextAlign.CENTER, width=day_size),
                alignment=ft.alignment.center,
                width=day_size),
            ft.Container(
                content=ft.Text("ส.", size=12, text_align=ft.TextAlign.CENTER, width=day_size, color=ft.Colors.RED_300),
                alignment=ft.alignment.center,
                width=day_size)
        ]
        self.calendar_rows.controls.append(ft.Row(header, spacing=10, alignment=ft.MainAxisAlignment.CENTER))

        for week in range(6):
            row = []
            for i in range(7):
                day = start_day + timedelta(days=week * 7 + i)
                if day.month == self.current_month:
                    is_today = day.date() == self.today.date()
                    is_selected = self.selected_date.value == day.strftime("%Y-%m-%d")
                    is_leave = False
                    is_holiday = False
                    tooltip = ""
                    bg_color = None
                    date_detail = ''

                    for l in self.leaves:
                        if l["date"] == day.strftime("%Y-%m-%d"):
                            is_leave = True
                            tooltip = f"{LEAVE_TYPES.get(l['type'], '')}: {l['reason']}"
                            bg_color = COLOR_MAP.get(l["type"], ft.Colors.GREY_300)
                            date_detail = l['reason']

                    for h in self.holidays:
                        if h["date"] == day.strftime("%Y-%m-%d"):
                            is_holiday = True
                            tooltip = f"วันหยุด: {h['name']}"
                            bg_color = COLOR_MAP["holiday"]
                            date_detail = h['name']

                    if is_today:
                        bg_color = COLOR_MAP["today"]
                    if is_selected:
                        bg_color = COLOR_MAP["selected"]
                        

                    btn = ft.Container(
                        content=ft.Text(str(day.day), size=12),
                        bgcolor=bg_color if bg_color else ft.Colors.TRANSPARENT,
                        border_radius=day_size / 2,
                        tooltip=tooltip,
                        padding=0,
                        width=day_size,
                        height=day_size,
                        alignment=ft.alignment.center,
                        on_click=lambda e, d=day, date_detail=date_detail: self.on_date_click(d, date_detail)
                    )
                else:
                    btn = ft.Container(content=ft.Text(""), width=day_size, height=day_size)
                row.append(btn)
            self.calendar_rows.controls.append(ft.Row(row, spacing=10, alignment=ft.MainAxisAlignment.CENTER))

        self.header_text.value = f"{get_month_label(self.current_month)} {self.current_year}"

    def build_summary(self):

        self.leave_summary = ft.Column(
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        counts = {lt: 0 for lt in LEAVE_TYPES}
        for l in self.leaves:
            if l["type"] in counts:
                counts[l["type"]] += 1

        for q in self.quotas:
            used = counts.get(q["type"], 0)
            remaining = q["total"] - used

            leave_layout = ft.Row([
                ft.Column([
                    ft.Text(f"{LEAVE_TYPES[q['type']]}", size=18, weight="bold"),
                    ft.Text("วันลาคงเหลือ", size=12)], 
                    expand=True),
                ft.Text(f"{remaining} วัน", text_align=ft.TextAlign.RIGHT)]
                )

            self.leave_summary.controls.append(
                ft.Container(
                    content=leave_layout,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=10,
                    border_radius=8,
                    alignment=ft.alignment.center,
                    theme=ft.Theme(color_scheme_seed=ft.Colors.INDIGO),
                    theme_mode=ft.ThemeMode.DARK,
                    # border=ft.border.all(2, ft.Colors.BLACK),
                )
            )

    def on_date_click(self, d, date_detail):

        txt = ''
        if date_detail:
            txt = date_detail

        self.selected_date.value = d.strftime("%Y-%m-%d")
        self.selected_date_detail.value = txt

        self.refresh()

    def on_add_leave(self, e):
        if self.selected_date.value and self.leave_type_dd.value:
            self.save_leave(datetime.fromisoformat(self.selected_date.value), self.leave_type_dd.value, self.reason_tf.value)
            self.refresh()

    def on_add_holiday(self, e):
        if self.selected_date.value and self.holiday_name.value:
            self.save_holiday(datetime.fromisoformat(self.selected_date.value), self.holiday_name.value)
            self.refresh()

    def show_quota_popup(self, e):
        popup = QuotaPopup(self.quotas, 
                        on_submit=self.on_quota_submit)
        self.page.dialog = popup
        popup.open = True
        self.page.open(popup)
        self.page.update()

    def on_quota_submit(self, inputs):
        for type_, field in inputs:
            self.update_quota(type_, int(field.value))

        self.page.dialog.open = False
        self.page.update()
        self.refresh()

    def change_month(self, direction):
        self.current_month += direction
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        elif self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.refresh()

    def show_note_popup(self, e):
        if not self.selected_date:
            return
        
        date_str = self.selected_date.value
        day_notes = [n for n in self.notes if n["date"] == date_str]

        popup = NotePopup(day_notes, lambda content, color: self.add_note(date_str, content, color))
        self.page.dialog = popup
        popup.open = True
        self.page.open(popup)
        self.page.update()

    def add_note(self, date_str, content, color):
        data = {
            "date": date_str,
            "content": content,
            "color": color
        }
        supabase.table("notes").insert(data).execute()
        self.load_data()
        self.page.dialog.open = False
        self.page.update()

    def refresh(self):
        # self.load_data()
        self.build_calendar()
        self.build_summary()
        self.page.update()

    def main(self):

        self.page.title = "ระบบบันทึกวันลา"
        self.page.scroll = ft.ScrollMode.HIDDEN

        self.load_data()
        self.build_calendar()
        self.build_summary()

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("ระบบบันทึกวันลา", size=20, weight="bold", text_align=ft.TextAlign.LEFT, expand=True),
                        ft.Container(content=self.note_button, alignment=ft.alignment.center_right)]) ,
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self.change_month(-1)),
                                self.header_text,
                                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self.change_month(1)),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            self.calendar_rows,
                        ]),
                        padding=20,
                        alignment=ft.alignment.center,
                        width=float("inf")
                    ),
                    ft.Text("วันที่เลือก:", text_align=ft.TextAlign.CENTER),
                    ft.Row([
                        self.selected_date,
                        self.selected_date_detail,
                    ]),
                    ft.Row([
                        self.leave_type_dd,
                        self.reason_tf,
                        ft.ElevatedButton("บันทีก", on_click=self.on_add_leave)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text("วันหยุด", size=12, weight="bold", text_align=ft.TextAlign.LEFT, expand=True),
                    ft.Row([
                        self.holiday_name,
                        ft.ElevatedButton("บันทึก", on_click=self.on_add_holiday)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(),
                    ft.Row([
                        ft.Text("วันลาคงเหลือ", 
                                size=20, 
                                weight="bold", 
                                text_align=ft.TextAlign.LEFT,
                                expand=True),
                        ft.ElevatedButton("อัปเดตโควต้าการลา", 
                                on_click=self.show_quota_popup, 
                                icon=ft.Icons.EDIT_CALENDAR),
                    ]),
                    ft.Container(
                        content=self.leave_summary,
                        padding=10,
                        alignment=ft.alignment.center,
                        width=float("inf")
                    ),
                    
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
        )


def main(page: ft.Page):
    app = LeaveApp(page)
    app.main()


if __name__ == "__main__":

    # import asyncio
    # import sys
    # if sys.platform.startswith("win"):
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import flet as ft
    ft.app(target=main)
