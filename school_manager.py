"""
School Management System (Console based)
----------------------------------------
Features
  1. Student data      - add / view / search / update / delete
  2. Teacher data      - add / view / search / update / delete
  3. Subjects          - add / view / delete
  4. School timings    - school open time, close time, period length, break
  5. Time table        - period wise (subject + teacher) for every class, day wise
  6. Attendance        - mark student present/absent subject (period) wise, reports

Data is saved automatically in  school_data.json  (same folder as this file).
Run:  python school_manager.py
"""

import json
import os
from datetime import datetime, timedelta, date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_data.json")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ----------------------------------------------------------------------------
# Data load / save
# ----------------------------------------------------------------------------
def default_data():
    return {
        "settings": {
            "school_name": "My School",
            "open_time": "08:00",
            "close_time": "14:00",
            "period_minutes": 40,
            "break_after_period": 4,
            "break_minutes": 20,
        },
        "students": {},     # "S001": {name, class, roll, phone, parent}
        "teachers": {},     # "T001": {name, subject, phone, qualification}
        "subjects": [],     # ["Maths", "English", ...]
        "timetable": {},    # class -> day -> period(str) -> {subject, teacher_id}
        "attendance": {},   # date -> class -> period(str) -> {subject, records{sid: P/A}}
    }


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            base = default_data()
            for key, value in base.items():
                data.setdefault(key, value)
            for key, value in base["settings"].items():
                data["settings"].setdefault(key, value)
            return data
        except (json.JSONDecodeError, OSError):
            print("! Data file is damaged. Starting with empty data.")
    return default_data()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# Input helpers
# ----------------------------------------------------------------------------
def ask(prompt, required=True, default=None):
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if not value and default is not None:
            return str(default)
        if value or not required:
            return value
        print("  This field cannot be empty.")


def ask_int(prompt, minimum=None, maximum=None, default=None):
    while True:
        raw = ask(prompt, default=default)
        try:
            num = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if minimum is not None and num < minimum:
            print(f"  Minimum value is {minimum}.")
            continue
        if maximum is not None and num > maximum:
            print(f"  Maximum value is {maximum}.")
            continue
        return num


def ask_time(prompt, default=None):
    while True:
        raw = ask(prompt + " (HH:MM, 24 hour)", default=default)
        try:
            return datetime.strptime(raw, "%H:%M").strftime("%H:%M")
        except ValueError:
            print("  Wrong format. Example: 08:30 or 14:00")


def ask_date(prompt, default=None):
    while True:
        raw = ask(prompt + " (YYYY-MM-DD)", default=default)
        try:
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("  Wrong format. Example: 2026-11-16")


def confirm(prompt):
    return input(f"{prompt} (y/n): ").strip().lower() in ("y", "yes")


def pause():
    input("\nPress Enter to continue...")


def header(title):
    print("\n" + "=" * 64)
    print(f" {title}")
    print("=" * 64)


def new_id(prefix, existing):
    n = 1
    while f"{prefix}{n:03d}" in existing:
        n += 1
    return f"{prefix}{n:03d}"


def print_table(headers, rows):
    if not rows:
        print("  (no records)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(line)
    print("| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |")
    print(line)
    for row in rows:
        print("| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)) + " |")
    print(line)


# ----------------------------------------------------------------------------
# School timing  (open / close time and period slots)
# ----------------------------------------------------------------------------
def build_slots(settings):
    """Return list of slots: {'period': int or None, 'start': 'HH:MM', 'end': 'HH:MM'}.
    period=None means the break."""
    fmt = "%H:%M"
    t = datetime.strptime(settings["open_time"], fmt)
    end = datetime.strptime(settings["close_time"], fmt)
    length = timedelta(minutes=int(settings["period_minutes"]))
    brk = timedelta(minutes=int(settings["break_minutes"]))
    slots, n = [], 1
    while t + length <= end:
        slots.append({"period": n, "start": t.strftime(fmt), "end": (t + length).strftime(fmt)})
        t += length
        if n == int(settings["break_after_period"]) and brk.total_seconds() > 0 and t + brk <= end:
            slots.append({"period": None, "start": t.strftime(fmt), "end": (t + brk).strftime(fmt)})
            t += brk
        n += 1
    return slots


def period_count(settings):
    return sum(1 for s in build_slots(settings) if s["period"])


def period_time(settings, period):
    for s in build_slots(settings):
        if s["period"] == int(period):
            return f"{s['start']} - {s['end']}"
    return "?"


def show_school_timing(data):
    s = data["settings"]
    header(f"SCHOOL TIMING - {s['school_name']}")
    print(f"  School opens  : {s['open_time']}")
    print(f"  School closes : {s['close_time']}")
    print(f"  Period length : {s['period_minutes']} minutes")
    print(f"  Break         : {s['break_minutes']} minutes after period {s['break_after_period']}")
    print("\n  Period schedule:")
    rows = []
    for slot in build_slots(s):
        label = f"Period {slot['period']}" if slot["period"] else "BREAK"
        rows.append([label, slot["start"], slot["end"]])
    print_table(["Period", "Start", "End"], rows)
    print(f"  Total periods per day: {period_count(s)}")


def edit_school_timing(data):
    s = data["settings"]
    show_school_timing(data)
    print("\nPress Enter to keep the current value.")
    s["school_name"] = ask("School name", default=s["school_name"])
    s["open_time"] = ask_time("School open time", default=s["open_time"])
    while True:
        close = ask_time("School close time", default=s["close_time"])
        if close > s["open_time"]:
            s["close_time"] = close
            break
        print("  Close time must be after open time.")
    s["period_minutes"] = ask_int("Period length (minutes)", 5, 180, default=s["period_minutes"])
    s["break_after_period"] = ask_int("Break after which period (0 = no break)", 0, 20,
                                      default=s["break_after_period"])
    s["break_minutes"] = ask_int("Break length (minutes)", 0, 120, default=s["break_minutes"])
    save_data(data)
    print("\n✔ School timing saved.")
    show_school_timing(data)
    total = period_count(s)
    # remove timetable/attendance entries of periods that no longer exist
    removed = False
    for cls in data["timetable"].values():
        for day in cls.values():
            for p in list(day.keys()):
                if int(p) > total:
                    del day[p]
                    removed = True
    if removed:
        save_data(data)
        print("  Note: timetable entries beyond the new last period were removed.")


# ----------------------------------------------------------------------------
# Subjects
# ----------------------------------------------------------------------------
def subject_menu(data):
    while True:
        header("SUBJECTS")
        print(" 1. View subjects\n 2. Add subject\n 3. Delete subject\n 0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            print_table(["No", "Subject"], [[i + 1, s] for i, s in enumerate(data["subjects"])])
            pause()
        elif ch == "2":
            name = ask("Subject name").title()
            if name.lower() in [s.lower() for s in data["subjects"]]:
                print("  Subject already exists.")
            else:
                data["subjects"].append(name)
                save_data(data)
                print(f"✔ Subject '{name}' added.")
            pause()
        elif ch == "3":
            name = ask("Subject name to delete").title()
            match = [s for s in data["subjects"] if s.lower() == name.lower()]
            if not match:
                print("  Subject not found.")
            elif confirm(f"Delete '{match[0]}'?"):
                data["subjects"].remove(match[0])
                save_data(data)
                print("✔ Deleted. (Existing timetable entries keep the old name.)")
            pause()
        elif ch == "0":
            return
        else:
            print("  Invalid choice.")


def pick_subject(data, prompt="Subject"):
    """Let user choose a subject by number or type a new one."""
    if data["subjects"]:
        print("  Available subjects: " +
              ", ".join(f"{i + 1}={s}" for i, s in enumerate(data["subjects"])))
    raw = ask(f"{prompt} (number or name)")
    if raw.isdigit() and 1 <= int(raw) <= len(data["subjects"]):
        return data["subjects"][int(raw) - 1]
    name = raw.title()
    if name.lower() not in [s.lower() for s in data["subjects"]]:
        data["subjects"].append(name)
        save_data(data)
        print(f"  (New subject '{name}' added to subject list)")
        return name
    return [s for s in data["subjects"] if s.lower() == name.lower()][0]


# ----------------------------------------------------------------------------
# Students
# ----------------------------------------------------------------------------
def class_list(data):
    return sorted({s["class"] for s in data["students"].values()} | set(data["timetable"].keys()))


def student_rows(students):
    ordered = sorted(students.items(), key=lambda kv: (kv[1]["class"], kv[1].get("roll", 0), kv[0]))
    return [[sid, s["name"], s["class"], s.get("roll", ""), s.get("parent", ""), s.get("phone", "")]
            for sid, s in ordered]


STUDENT_HEADERS = ["ID", "Name", "Class", "Roll", "Parent", "Phone"]


def add_student(data):
    header("ADD STUDENT")
    name = ask("Student name").title()
    cls = ask("Class / Section (e.g. 10-A)").upper()
    while True:
        roll = ask_int("Roll number", 1)
        clash = [s for s in data["students"].values() if s["class"] == cls and s["roll"] == roll]
        if clash:
            print(f"  Roll {roll} already used in class {cls} by {clash[0]['name']}.")
        else:
            break
    parent = ask("Parent / Guardian name", required=False)
    phone = ask("Phone number", required=False)
    sid = new_id("S", data["students"])
    data["students"][sid] = {"name": name, "class": cls, "roll": roll, "parent": parent, "phone": phone}
    save_data(data)
    print(f"\n✔ Student added with ID {sid}")


def find_students(data, text):
    text = text.lower()
    return {sid: s for sid, s in data["students"].items()
            if text in sid.lower() or text in s["name"].lower() or text == s["class"].lower()}


def update_student(data):
    header("UPDATE STUDENT")
    sid = ask("Student ID").upper()
    s = data["students"].get(sid)
    if not s:
        print("  Student not found.")
        return
    print("Press Enter to keep the current value.")
    s["name"] = ask("Name", default=s["name"]).title()
    s["class"] = ask("Class", default=s["class"]).upper()
    while True:
        roll = ask_int("Roll", 1, default=s["roll"])
        clash = [k for k, v in data["students"].items()
                 if k != sid and v["class"] == s["class"] and v["roll"] == roll]
        if clash:
            print("  That roll number is already used in this class.")
        else:
            s["roll"] = roll
            break
    s["parent"] = ask("Parent", required=False, default=s.get("parent", "") or None) if s.get("parent") \
        else ask("Parent", required=False)
    s["phone"] = ask("Phone", required=False, default=s.get("phone", "") or None) if s.get("phone") \
        else ask("Phone", required=False)
    save_data(data)
    print("✔ Student updated.")


def delete_student(data):
    header("DELETE STUDENT")
    sid = ask("Student ID").upper()
    s = data["students"].get(sid)
    if not s:
        print("  Student not found.")
        return
    if confirm(f"Delete {s['name']} ({s['class']})? Attendance records will also be removed"):
        del data["students"][sid]
        for day in data["attendance"].values():
            for cls in day.values():
                for per in cls.values():
                    per["records"].pop(sid, None)
        save_data(data)
        print("✔ Student deleted.")


def student_menu(data):
    while True:
        header("STUDENT DATA")
        print(" 1. Add student\n 2. View all students\n 3. View class students\n"
              " 4. Search student\n 5. Update student\n 6. Delete student\n 0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            add_student(data)
        elif ch == "2":
            print_table(STUDENT_HEADERS, student_rows(data["students"]))
            print(f"  Total students: {len(data['students'])}")
        elif ch == "3":
            cls = ask("Class").upper()
            sub = {k: v for k, v in data["students"].items() if v["class"] == cls}
            print_table(STUDENT_HEADERS, student_rows(sub))
            print(f"  Students in {cls}: {len(sub)}")
        elif ch == "4":
            found = find_students(data, ask("Enter ID / name / class"))
            print_table(STUDENT_HEADERS, student_rows(found))
        elif ch == "5":
            update_student(data)
        elif ch == "6":
            delete_student(data)
        elif ch == "0":
            return
        else:
            print("  Invalid choice.")
            continue
        pause()


# ----------------------------------------------------------------------------
# Teachers
# ----------------------------------------------------------------------------
TEACHER_HEADERS = ["ID", "Name", "Subject", "Qualification", "Phone"]


def teacher_rows(teachers):
    return [[tid, t["name"], t["subject"], t.get("qualification", ""), t.get("phone", "")]
            for tid, t in sorted(teachers.items())]


def add_teacher(data):
    header("ADD TEACHER")
    name = ask("Teacher name").title()
    subject = pick_subject(data, "Main subject")
    qual = ask("Qualification", required=False)
    phone = ask("Phone number", required=False)
    tid = new_id("T", data["teachers"])
    data["teachers"][tid] = {"name": name, "subject": subject, "qualification": qual, "phone": phone}
    save_data(data)
    print(f"\n✔ Teacher added with ID {tid}")


def update_teacher(data):
    header("UPDATE TEACHER")
    tid = ask("Teacher ID").upper()
    t = data["teachers"].get(tid)
    if not t:
        print("  Teacher not found.")
        return
    print("Press Enter to keep the current value.")
    t["name"] = ask("Name", default=t["name"]).title()
    new_sub = ask("Subject", default=t["subject"]).title()
    if new_sub.lower() not in [s.lower() for s in data["subjects"]]:
        data["subjects"].append(new_sub)
    t["subject"] = new_sub
    t["qualification"] = ask("Qualification", required=False, default=t.get("qualification") or None) \
        if t.get("qualification") else ask("Qualification", required=False)
    t["phone"] = ask("Phone", required=False, default=t.get("phone") or None) \
        if t.get("phone") else ask("Phone", required=False)
    save_data(data)
    print("✔ Teacher updated.")


def delete_teacher(data):
    header("DELETE TEACHER")
    tid = ask("Teacher ID").upper()
    t = data["teachers"].get(tid)
    if not t:
        print("  Teacher not found.")
        return
    if confirm(f"Delete {t['name']}? Their timetable slots will be cleared"):
        del data["teachers"][tid]
        for cls in data["timetable"].values():
            for day in cls.values():
                for p in list(day.keys()):
                    if day[p]["teacher_id"] == tid:
                        del day[p]
        save_data(data)
        print("✔ Teacher deleted.")


def teacher_menu(data):
    while True:
        header("TEACHER DATA")
        print(" 1. Add teacher\n 2. View all teachers\n 3. Search teacher\n"
              " 4. Update teacher\n 5. Delete teacher\n 6. View teacher's timetable\n 0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            add_teacher(data)
        elif ch == "2":
            print_table(TEACHER_HEADERS, teacher_rows(data["teachers"]))
            print(f"  Total teachers: {len(data['teachers'])}")
        elif ch == "3":
            text = ask("Enter ID / name / subject").lower()
            found = {k: v for k, v in data["teachers"].items()
                     if text in k.lower() or text in v["name"].lower() or text in v["subject"].lower()}
            print_table(TEACHER_HEADERS, teacher_rows(found))
        elif ch == "4":
            update_teacher(data)
        elif ch == "5":
            delete_teacher(data)
        elif ch == "6":
            show_teacher_timetable(data)
        elif ch == "0":
            return
        else:
            print("  Invalid choice.")
            continue
        pause()


# ----------------------------------------------------------------------------
# Time table
# ----------------------------------------------------------------------------
def teacher_name(data, tid):
    t = data["teachers"].get(tid)
    return t["name"] if t else "(removed)"


def teacher_busy(data, tid, day, period, skip_class=None):
    """Return class name if the teacher already teaches another class in that slot."""
    for cls, days in data["timetable"].items():
        if cls == skip_class:
            continue
        entry = days.get(day, {}).get(str(period))
        if entry and entry["teacher_id"] == tid:
            return cls
    return None


def show_class_timetable(data, cls):
    s = data["settings"]
    header(f"TIME TABLE - CLASS {cls}   ({s['open_time']} to {s['close_time']})")
    tt = data["timetable"].get(cls, {})
    slots = build_slots(s)
    heads = ["Period", "Time"] + [d[:3] for d in DAYS]
    rows = []
    for slot in slots:
        if slot["period"] is None:
            rows.append(["BREAK", f"{slot['start']}-{slot['end']}"] + ["-----"] * len(DAYS))
            continue
        row = [f"P{slot['period']}", f"{slot['start']}-{slot['end']}"]
        for d in DAYS:
            e = tt.get(d, {}).get(str(slot["period"]))
            row.append(f"{e['subject']} ({teacher_name(data, e['teacher_id']).split()[0]})" if e else "")
        rows.append(row)
    print_table(heads, rows)


def show_teacher_timetable(data):
    tid = ask("Teacher ID").upper()
    t = data["teachers"].get(tid)
    if not t:
        print("  Teacher not found.")
        return
    s = data["settings"]
    header(f"TIME TABLE - {t['name']} ({t['subject']})")
    slots = [x for x in build_slots(s) if x["period"]]
    rows = []
    for slot in slots:
        row = [f"P{slot['period']}", f"{slot['start']}-{slot['end']}"]
        for d in DAYS:
            cell = ""
            for cls, days in data["timetable"].items():
                e = days.get(d, {}).get(str(slot["period"]))
                if e and e["teacher_id"] == tid:
                    cell = f"{cls} {e['subject']}"
            row.append(cell)
        rows.append(row)
    print_table(["Period", "Time"] + [d[:3] for d in DAYS], rows)


def set_timetable_slot(data):
    header("SET TIME TABLE PERIOD")
    cls = ask("Class (e.g. 10-A)").upper()
    total = period_count(data["settings"])
    if total == 0:
        print("  No periods available. Check school timing first.")
        return
    print("  Days: " + ", ".join(f"{i + 1}={d}" for i, d in enumerate(DAYS)))
    d_no = ask_int("Day number", 1, len(DAYS))
    day = DAYS[d_no - 1]
    period = ask_int(f"Period number (1-{total})", 1, total)
    print(f"  Period {period} time: {period_time(data['settings'], period)}")
    subject = pick_subject(data)
    print("\n  Teachers:")
    print_table(TEACHER_HEADERS, teacher_rows(data["teachers"]))
    if not data["teachers"]:
        print("  Please add a teacher first.")
        return
    while True:
        tid = ask("Teacher ID").upper()
        if tid not in data["teachers"]:
            print("  Teacher not found.")
            continue
        busy = teacher_busy(data, tid, day, period, skip_class=cls)
        if busy:
            print(f"  ✘ {teacher_name(data, tid)} already teaches class {busy} on {day} period {period}.")
            if not confirm("Choose another teacher?"):
                return
            continue
        break
    data["timetable"].setdefault(cls, {}).setdefault(day, {})[str(period)] = {
        "subject": subject, "teacher_id": tid}
    save_data(data)
    print(f"✔ {cls} | {day} | Period {period} -> {subject} ({teacher_name(data, tid)})")


def clear_timetable_slot(data):
    cls = ask("Class").upper()
    if cls not in data["timetable"]:
        print("  No timetable for this class.")
        return
    d_no = ask_int("Day number (1=Mon ... 6=Sat)", 1, len(DAYS))
    period = ask_int("Period number", 1)
    day = DAYS[d_no - 1]
    if data["timetable"][cls].get(day, {}).pop(str(period), None):
        save_data(data)
        print("✔ Period cleared.")
    else:
        print("  That period is already empty.")


def timetable_menu(data):
    while True:
        header("TIME TABLE")
        print(" 1. View class time table\n 2. Set / change a period\n 3. Clear a period\n"
              " 4. View teacher time table\n 5. View school timing & period times\n"
              " 6. Change school open/close time & period settings\n 0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            show_class_timetable(data, ask("Class").upper())
        elif ch == "2":
            set_timetable_slot(data)
        elif ch == "3":
            clear_timetable_slot(data)
        elif ch == "4":
            show_teacher_timetable(data)
        elif ch == "5":
            show_school_timing(data)
        elif ch == "6":
            edit_school_timing(data)
        elif ch == "0":
            return
        else:
            print("  Invalid choice.")
            continue
        pause()


# ----------------------------------------------------------------------------
# Attendance (subject / period wise)
# ----------------------------------------------------------------------------
def mark_attendance(data):
    header("MARK ATTENDANCE")
    cls = ask("Class (e.g. 10-A)").upper()
    students = {k: v for k, v in data["students"].items() if v["class"] == cls}
    if not students:
        print("  No students in this class.")
        return
    day_str = ask_date("Date", default=date.today().isoformat())
    weekday = datetime.strptime(day_str, "%Y-%m-%d").strftime("%A")
    total = period_count(data["settings"])
    if weekday not in DAYS:
        print(f"  {weekday} is a holiday (school runs Monday-Saturday).")
        if not confirm("Mark anyway?"):
            return
    period = ask_int(f"Period number (1-{total})", 1, total)
    print(f"  Period {period} time: {period_time(data['settings'], period)}")

    entry = data["timetable"].get(cls, {}).get(weekday, {}).get(str(period))
    if entry:
        subject = entry["subject"]
        print(f"  Subject from time table: {subject} (Teacher: {teacher_name(data, entry['teacher_id'])})")
    else:
        print("  No time table entry for this period.")
        subject = pick_subject(data)

    existing = data["attendance"].get(day_str, {}).get(cls, {}).get(str(period))
    if existing and not confirm("Attendance already taken for this period. Overwrite?"):
        return

    ordered = sorted(students.items(), key=lambda kv: kv[1]["roll"])
    print_table(["ID", "Roll", "Name"], [[k, v["roll"], v["name"]] for k, v in ordered])
    print("All students are PRESENT by default.")
    raw = input("Enter ABSENT student IDs or roll numbers separated by comma (Enter = none absent): ")
    absent = set()
    for token in [t.strip().upper() for t in raw.split(",") if t.strip()]:
        if token in students:
            absent.add(token)
        elif token.isdigit():
            hit = [k for k, v in students.items() if v["roll"] == int(token)]
            if hit:
                absent.add(hit[0])
                continue
            print(f"  ! Roll {token} not found - ignored")
        else:
            print(f"  ! '{token}' not found - ignored")

    records = {sid: ("A" if sid in absent else "P") for sid in students}
    data["attendance"].setdefault(day_str, {}).setdefault(cls, {})[str(period)] = {
        "subject": subject, "records": records}
    save_data(data)
    print(f"\n✔ Attendance saved: {len(records) - len(absent)} present, {len(absent)} absent.")
    if absent:
        print("  Absent: " + ", ".join(f"{students[a]['name']} ({a})" for a in sorted(absent)))


def view_day_attendance(data):
    header("DAY ATTENDANCE REPORT")
    cls = ask("Class").upper()
    day_str = ask_date("Date", default=date.today().isoformat())
    periods = data["attendance"].get(day_str, {}).get(cls, {})
    if not periods:
        print("  No attendance recorded for this class on that date.")
        return
    students = {k: v for k, v in data["students"].items() if v["class"] == cls}
    pnums = sorted(periods.keys(), key=int)
    heads = ["Roll", "Name"] + [f"P{p} {periods[p]['subject'][:6]}" for p in pnums]
    rows = []
    for sid, st in sorted(students.items(), key=lambda kv: kv[1]["roll"]):
        rows.append([st["roll"], st["name"]] + [periods[p]["records"].get(sid, "-") for p in pnums])
    print_table(heads, rows)
    for p in pnums:
        rec = periods[p]["records"]
        pres = sum(1 for v in rec.values() if v == "P")
        print(f"  Period {p} ({periods[p]['subject']}): {pres} present / {len(rec) - pres} absent")


def student_attendance_report(data):
    header("STUDENT ATTENDANCE REPORT (subject wise)")
    sid = ask("Student ID").upper()
    st = data["students"].get(sid)
    if not st:
        print("  Student not found.")
        return
    stats = {}   # subject -> [present, total]
    for day, classes in data["attendance"].items():
        for per in classes.get(st["class"], {}).values():
            if sid in per["records"]:
                row = stats.setdefault(per["subject"], [0, 0])
                row[1] += 1
                if per["records"][sid] == "P":
                    row[0] += 1
    print(f"  {st['name']} | Class {st['class']} | Roll {st['roll']}")
    if not stats:
        print("  No attendance recorded yet.")
        return
    rows, tp, tt = [], 0, 0
    for sub, (p, t) in sorted(stats.items()):
        rows.append([sub, p, t - p, t, f"{p * 100 / t:.1f}%"])
        tp += p
        tt += t
    rows.append(["TOTAL", tp, tt - tp, tt, f"{tp * 100 / tt:.1f}%"])
    print_table(["Subject", "Present", "Absent", "Total", "Percent"], rows)
    if tp * 100 / tt < 75:
        print("  ⚠ Attendance is below 75%.")


def class_attendance_summary(data):
    header("CLASS ATTENDANCE SUMMARY")
    cls = ask("Class").upper()
    students = {k: v for k, v in data["students"].items() if v["class"] == cls}
    if not students:
        print("  No students in this class.")
        return
    rows = []
    for sid, st in sorted(students.items(), key=lambda kv: kv[1]["roll"]):
        p = t = 0
        for classes in data["attendance"].values():
            for per in classes.get(cls, {}).values():
                if sid in per["records"]:
                    t += 1
                    p += per["records"][sid] == "P"
        pct = f"{p * 100 / t:.1f}%" if t else "-"
        flag = "LOW" if t and p * 100 / t < 75 else ""
        rows.append([st["roll"], st["name"], p, t - p, t, pct, flag])
    print_table(["Roll", "Name", "Present", "Absent", "Total", "Percent", "Note"], rows)


def attendance_menu(data):
    while True:
        header("ATTENDANCE")
        print(" 1. Mark attendance (period / subject wise)\n 2. View day attendance of a class\n"
              " 3. Student attendance report (subject wise)\n 4. Class attendance summary\n 0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            mark_attendance(data)
        elif ch == "2":
            view_day_attendance(data)
        elif ch == "3":
            student_attendance_report(data)
        elif ch == "4":
            class_attendance_summary(data)
        elif ch == "0":
            return
        else:
            print("  Invalid choice.")
            continue
        pause()


# ----------------------------------------------------------------------------
# Dashboard + main menu
# ----------------------------------------------------------------------------
def dashboard(data):
    s = data["settings"]
    today = date.today()
    header(f"{s['school_name'].upper()} - DASHBOARD")
    print(f"  Today        : {today.strftime('%A, %d %B %Y')}")
    print(f"  School time  : {s['open_time']} to {s['close_time']}  "
          f"({period_count(s)} periods of {s['period_minutes']} min)")
    print(f"  Students     : {len(data['students'])}")
    print(f"  Teachers     : {len(data['teachers'])}")
    print(f"  Subjects     : {len(data['subjects'])}")
    print(f"  Classes      : {', '.join(class_list(data)) or '-'}")
    now = datetime.now().strftime("%H:%M")
    if s["open_time"] <= now <= s["close_time"]:
        print("  Status       : School is OPEN now")
    else:
        print("  Status       : School is CLOSED now")


def main():
    data = load_data()
    while True:
        dashboard(data)
        print("\n MAIN MENU")
        print(" 1. Student data")
        print(" 2. Teacher data")
        print(" 3. Subjects")
        print(" 4. Time table & school timing")
        print(" 5. Attendance")
        print(" 0. Exit")
        ch = input("Choose: ").strip()
        if ch == "1":
            student_menu(data)
        elif ch == "2":
            teacher_menu(data)
        elif ch == "3":
            subject_menu(data)
        elif ch == "4":
            timetable_menu(data)
        elif ch == "5":
            attendance_menu(data)
        elif ch == "0":
            save_data(data)
            print("Data saved. Goodbye!")
            break
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")
