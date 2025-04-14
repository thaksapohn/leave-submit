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
    "sick": ft.colors.RED_200,
    "vacation": ft.colors.GREEN_200,
    "personal": ft.colors.YELLOW_200,
    "holiday": ft.colors.BLUE_200,
    "today": ft.colors.PURPLE_300,
    "selected": ft.colors.ORANGE_200
}

def get_month_label(month):
    month_th = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    return month_th[month - 1]

def main(page: ft.Page):
    today = datetime.today()
    current_year = today.year
    current_month = today.month

    selected_date = ft.Text("")
    calendar_rows = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    leave_summary = ft.Row(wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    header_text = ft.Text(f"{get_month_label(current_month)} {current_year}", size=16)
    
    # Cache
    leaves = []
    holidays = []
    quotas = []

    leave_type_dd = ft.Dropdown(
        label="ประเภทการลา",
        options=[ft.dropdown.Option(k, text=v) for k, v in LEAVE_TYPES.items()]
    )
    reason_tf = ft.TextField(label="เหตุผล")
    holiday_name = ft.TextField(label="ชื่อวันหยุด")

    def fetch_table(table):
        return supabase.table(table).select("*").execute().data

    def load_data():
        nonlocal leaves, holidays, quotas
        leaves = fetch_table("leaves")
        holidays = fetch_table("holidays")
        quotas = fetch_table("leave_quota")

    def save_leave(date, leave_type, reason):
        supabase.table("leaves").insert({
            "date": date.isoformat(),
            "type": leave_type,
            "reason": reason
        }).execute()
        load_data()

    def save_holiday(date, name):
        supabase.table("holidays").insert({
            "date": date.isoformat(),
            "name": name
        }).execute()
        load_data()

    def update_quota(type_, total):
        supabase.table("leave_quota").upsert({"type": type_, "total": total}).execute()
        load_data()

    def build_calendar(year, month):
        calendar_rows.controls.clear()
        first_day = datetime(year, month, 1)
        start_day = first_day - timedelta(days=(first_day.weekday() + 1) % 7)

        day_size = (page.width - 6 * 10 - 40) / 7

        header = [
            ft.Container(
                content=ft.Text("อา.", size=12, text_align=ft.TextAlign.CENTER, color=ft.colors.RED_300, width=day_size),
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
                content=ft.Text("ส.", size=12, text_align=ft.TextAlign.CENTER, width=day_size, color=ft.colors.RED_300),
                alignment=ft.alignment.center,
                width=day_size)
        ]
        calendar_rows.controls.append(ft.Row(header, spacing=10, alignment=ft.MainAxisAlignment.CENTER))

        for week in range(6):
            row = []
            for i in range(7):
                day = start_day + timedelta(days=week * 7 + i)
                if day.month == month:
                    is_today = day.date() == today.date()
                    is_selected = selected_date.value == day.strftime("%Y-%m-%d")
                    is_leave = False
                    is_holiday = False
                    tooltip = ""
                    bg_color = None

                    for l in leaves:
                        if l["date"] == day.strftime("%Y-%m-%d"):
                            is_leave = True
                            tooltip = f"{LEAVE_TYPES.get(l['type'], '')}: {l['reason']}"
                            bg_color = COLOR_MAP.get(l["type"], ft.colors.GREY_300)

                    for h in holidays:
                        if h["date"] == day.strftime("%Y-%m-%d"):
                            is_holiday = True
                            tooltip = f"วันหยุด: {h['name']}"
                            bg_color = COLOR_MAP["holiday"]

                    if is_today:
                        bg_color = COLOR_MAP["today"]
                    if is_selected:
                        bg_color = COLOR_MAP["selected"]

                    btn = ft.Container(
                        content=ft.Text(str(day.day), size=12),
                        bgcolor=bg_color if bg_color else ft.colors.TRANSPARENT,
                        border_radius=day_size / 2,
                        tooltip=tooltip,
                        padding=0,
                        width=day_size,
                        height=day_size,
                        alignment=ft.alignment.center,
                        on_click=lambda e, d=day: on_date_click(d)
                    )
                else:
                    btn = ft.Container(content=ft.Text(""), width=day_size, height=day_size)
                row.append(btn)
            calendar_rows.controls.append(ft.Row(row, spacing=10, alignment=ft.MainAxisAlignment.CENTER))

    def on_date_click(d):
        selected_date.value = d.strftime("%Y-%m-%d")
        refresh()

    def refresh():
        build_calendar(current_year, current_month)
        build_summary()
        header_text.value = f"{get_month_label(current_month)} {current_year}"
        page.update()

    def build_summary():
        leave_summary.controls.clear()
        counts = {lt: 0 for lt in LEAVE_TYPES}
        for l in leaves:
            if l["type"] in counts:
                counts[l["type"]] += 1
        for q in quotas:
            used = counts.get(q["type"], 0)
            remaining = q["total"] - used
            leave_summary.controls.append(ft.Container(
                content=ft.Text(f"{LEAVE_TYPES[q['type']]} เหลือ {remaining} วัน", size=12),
                bgcolor=ft.colors.GREY_200,
                padding=10,
                border_radius=8
            ))

    def show_quota_popup(e):
        inputs = []
        for q in quotas:
            tf = ft.TextField(label=f"{LEAVE_TYPES[q['type']]} (วัน)", value=str(q["total"]))
            inputs.append((q["type"], tf))

        def close_popup(e=None):
            page.dialog.open = False
            page.update()

        content = ft.Stack([
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("อัปเดตโควต้าการลา", size=16, weight="bold"),
                        ft.IconButton(ft.icons.CLOSE, on_click=close_popup, tooltip="ปิด", style=ft.ButtonStyle(padding=5))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Column([inp[1] for inp in inputs], tight=True),
                ]),
                padding=20,
                bgcolor=ft.colors.WHITE,
                border_radius=10,
                width=400
            )
        ])

        page.dialog = ft.AlertDialog(
            modal=True,
            content=content,
            actions=[
                ft.TextButton("ยืนยัน", on_click=lambda e: [update_quota(t, int(f.value)) for t, f in inputs] or close_popup()),
            ]
        )
        page.dialog.open = True
        page.update()



    def on_add_leave(e):
        if selected_date.value and leave_type_dd.value:
            save_leave(datetime.fromisoformat(selected_date.value), leave_type_dd.value, reason_tf.value)
            refresh()

    def on_add_holiday(e):
        if selected_date.value and holiday_name.value:
            save_holiday(datetime.fromisoformat(selected_date.value), holiday_name.value)
            refresh()

    def change_month(direction):
        nonlocal current_month, current_year
        current_month += direction
        if current_month > 12:
            current_month = 1
            current_year += 1
        elif current_month < 1:
            current_month = 12
            current_year -= 1
        refresh()

    page.scroll = ft.ScrollMode.ALWAYS
    load_data()
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("ระบบบันทึกวันลา", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.IconButton(ft.icons.CHEVRON_LEFT, on_click=lambda e: change_month(-1)),
                            header_text,
                            ft.IconButton(ft.icons.CHEVRON_RIGHT, on_click=lambda e: change_month(1)),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        calendar_rows,
                    ]),
                    padding=20,
                    alignment=ft.alignment.center,
                    expand=False,
                    width=float("inf")
                ),
                ft.Text("วันที่เลือก:", text_align=ft.TextAlign.CENTER),
                selected_date,
                ft.Row([
                    leave_type_dd,
                    reason_tf,
                    ft.ElevatedButton("บันทึกวันลา", on_click=on_add_leave)
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    holiday_name,
                    ft.ElevatedButton("บันทึกวันหยุด", on_click=on_add_holiday)
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Container(leave_summary, padding=10),
                ft.ElevatedButton("อัปเดตโควต้าการลา", on_click=show_quota_popup, icon=ft.icons.EDIT_CALENDAR),
            ], scroll=ft.ScrollMode.AUTO, expand=True, alignment=ft.MainAxisAlignment.CENTER)
        )
    )

    refresh()



if __name__ == '__main__':

    ft.app(target=main, view=ft.WEB_BROWSER)
