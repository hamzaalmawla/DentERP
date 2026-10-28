"""Generate erd.svg and lifecycles.svg, then render every SVG here to docs/figures/*.png.

Usage:  python tools/figures/make_figures.py
Rendering uses headless Microsoft Edge (or Chrome) at 2x scale.
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "docs" / "figures"
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

NAVY, GREY, TEXT = "#1F3A5F", "#44546A", "#333333"
HEAD = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Segoe UI, Calibri, Arial, sans-serif">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#44546A"/></marker></defs>
<rect width="{w}" height="{h}" fill="#ffffff"/>
"""


# ---------- ERD ----------

BOX_W, BOX_H, COL, ROW, X0, Y0 = 200, 78, 260, 135, 20, 20

ENTITIES = {
    # name: (col, row, key fields)
    "Patient": (0, 0, ["file_no, national_id", "full_name, phone"]),
    "Diagnosis": (1, 0, ["patient, student, supervisor", "status, version"]),
    "PlanItem": (2, 0, ["diagnosis, treatment_type", "teeth, status"]),
    "Referral": (3, 0, ["from_clinic, to_clinic", "status, assigned_student"]),
    "Enrollment": (0, 1, ["student, course, term"]),
    "WorkCard": (1, 1, ["enrollment, card_no"]),
    "Case": (2, 1, ["work_card, patient, tooth", "referral, status"]),
    "Clinic": (3, 1, ["number, type", "department"]),
    "Course": (0, 2, ["code, type, term", "students_per_chair"]),
    "StepTemplate": (1, 2, ["course, order, name", "grading_scheme"]),
    "StepRecord": (2, 2, ["case, order, status", "grade, supervisor"]),
    "Chair": (3, 2, ["clinic, number, status"]),
    "MediaFile": (2, 3, ["file, kind (photo, xray)", "patient, case, step"]),
    "Ticket": (3, 3, ["chair, category, status", "opened_by, resolved_by"]),
}

# (from, to, card_from, card_to)
RELATIONS = [
    ("Patient", "Diagnosis", "1", "*"),
    ("Diagnosis", "PlanItem", "1", "*"),
    ("PlanItem", "Referral", "*", "*"),
    ("Referral", "Clinic", "*", "1"),
    ("Referral", "Case", "1", "0..1"),
    ("Enrollment", "WorkCard", "1", "1"),
    ("WorkCard", "Case", "1", "*"),
    ("Clinic", "Chair", "1", "*"),
    ("Chair", "Ticket", "1", "*"),
    ("Course", "Enrollment", "1", "*"),
    ("Course", "StepTemplate", "1", "*"),
    ("StepTemplate", "StepRecord", "1", "*"),
    ("Case", "StepRecord", "1", "*"),
    ("StepRecord", "MediaFile", "1", "*"),
]


def box_xy(name):
    c, r, _ = ENTITIES[name]
    return X0 + c * COL, Y0 + r * ROW


def anchor(a, b):
    """Points on the facing edges of boxes a and b."""
    ax, ay = box_xy(a)
    bx, by = box_xy(b)
    ca, ra, _ = ENTITIES[a]
    cb, rb, _ = ENTITIES[b]
    if ra == rb:  # same row
        if ca < cb:
            return (ax + BOX_W, ay + BOX_H / 2), (bx, by + BOX_H / 2)
        return (ax, ay + BOX_H / 2), (bx + BOX_W, by + BOX_H / 2)
    if ca == cb:  # same column
        if ra < rb:
            return (ax + BOX_W / 2, ay + BOX_H), (bx + BOX_W / 2, by)
        return (ax + BOX_W / 2, ay), (bx + BOX_W / 2, by + BOX_H)
    # diagonal: bottom of upper box to top of lower box
    if ra < rb:
        return (ax + 30, ay + BOX_H), (bx + BOX_W - 30, by)
    return (ax + BOX_W - 30, ay), (bx + 30, by + BOX_H)


def card_label(p, q, text, along=14):
    """Cardinality text placed just off point p, toward q."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    x, y = p[0] + ux * along, p[1] + uy * along
    # push the label sideways off the line
    x += -uy * 10 + 2
    y += ux * 10 + 4
    return f'<text x="{x:.0f}" y="{y:.0f}" font-size="12" font-weight="700" fill="{GREY}" text-anchor="middle">{text}</text>'


def erd():
    w = X0 * 2 + COL * 3 + BOX_W
    h = Y0 + ROW * 3 + BOX_H + 30
    parts = [HEAD.format(w=w, h=h)]
    for a, b, ca, cb in RELATIONS:
        p, q = anchor(a, b)
        parts.append(f'<line x1="{p[0]:.0f}" y1="{p[1]:.0f}" x2="{q[0]:.0f}" y2="{q[1]:.0f}" stroke="{GREY}" stroke-width="1.5"/>')
        diagonal = p[0] != q[0] and p[1] != q[1]
        along = 40 if diagonal else 14
        parts.append(card_label(p, q, ca, along))
        parts.append(card_label(q, p, cb, along))
    for name, (c, r, fields) in ENTITIES.items():
        x, y = box_xy(name)
        parts.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="6" fill="#fff" stroke="{NAVY}" stroke-width="1.5"/>')
        parts.append(f'<path d="M{x},{y + 26} H{x + BOX_W}" stroke="{NAVY}" stroke-width="1"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="26" rx="6" fill="{NAVY}"/>')
        parts.append(f'<rect x="{x}" y="{y + 16}" width="{BOX_W}" height="10" fill="{NAVY}"/>')
        parts.append(f'<text x="{x + BOX_W / 2}" y="{y + 18}" text-anchor="middle" font-size="14" font-weight="700" fill="#fff">{name}</text>')
        for i, f in enumerate(fields):
            parts.append(f'<text x="{x + 10}" y="{y + 45 + i * 18}" font-size="12" fill="{TEXT}">{f}</text>')
    note_y = Y0 + 3 * ROW + 20
    parts.append(f'<text x="{X0}" y="{note_y}" font-size="12" fill="#666">1 = one, * = many, 0..1 = optional.</text>')
    parts.append(f'<text x="{X0}" y="{note_y + 18}" font-size="12" fill="#666">Every table also links to User (created_by,</text>')
    parts.append(f'<text x="{X0}" y="{note_y + 36}" font-size="12" fill="#666">student, supervisor); those links are not drawn.</text>')
    parts.append(f'<text x="{X0}" y="{note_y + 54}" font-size="12" fill="#666">PlanItem–Referral uses the ReferralItem table.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# ---------- lifecycles ----------

PILL_W, PILL_H, STEP, LX, ROW_H = 122, 38, 192, 160, 150

LIFECYCLES = [
    # title, main states, extra states {name: col}, extra arrows
    ("Diagnosis", ["Draft", "Submitted", "Approved"], {"Returned": 1},
     [("Submitted", "Returned", "return"), ("Returned", "Submitted", "resubmit")]),
    ("Referral", ["Sent", "Accepted", "Assigned", "In treatment", "Completed"], {"Rejected": 0},
     [("Sent", "Rejected", "reject")]),
    ("Step", ["Pending", "Submitted", "Approved"], {"Returned": 1},
     [("Submitted", "Returned", "return"), ("Returned", "Submitted", "resubmit")]),
    ("Ticket", ["Open", "In progress", "External repair", "Resolved"], {},
     [("In progress", "Resolved", "repaired in house")]),
]
MAIN_LABELS = {
    "Diagnosis": ["submit", "approve"],
    "Referral": ["accept", "assign", "first step", "complete"],
    "Step": ["submit", "approve"],
    "Ticket": ["start", "send out", "repaired"],
}


def pill(x, y, text, fill, stroke, color):
    return (f'<rect x="{x}" y="{y}" width="{PILL_W}" height="{PILL_H}" rx="19" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{x + PILL_W / 2}" y="{y + 24}" text-anchor="middle" font-size="13" font-weight="600" fill="{color}">{text}</text>')


def lifecycles():
    w = LX + STEP * 4 + PILL_W + 20
    h = ROW_H * len(LIFECYCLES) + 10
    parts = [HEAD.format(w=w, h=h)]
    for i, (title, main, extra, arrows) in enumerate(LIFECYCLES):
        top = 15 + i * ROW_H
        y = top + 20
        if i:
            parts.append(f'<path d="M15,{top - 8} H{w - 15}" stroke="#D9D9D9" stroke-width="1"/>')
        parts.append(f'<text x="20" y="{y + 25}" font-size="16" font-weight="700" fill="{NAVY}">{title}</text>')
        pos = {}
        for c, s in enumerate(main):
            x = LX + c * STEP
            pos[s] = (x, y)
            final = c == len(main) - 1
            parts.append(pill(x, y, s, NAVY if final else "#EAF0F7", NAVY, "#fff" if final else NAVY))
        for s, c in extra.items():
            x, yy = LX + c * STEP, y + 72
            pos[s] = (x, yy)
            parts.append(pill(x, yy, s, "#FBF1E6", "#B5651D", "#8A4A10"))
        # forward arrows with action labels
        for c in range(len(main) - 1):
            x1 = LX + c * STEP + PILL_W
            x2 = LX + (c + 1) * STEP
            parts.append(f'<path d="M{x1 + 2},{y + 19} L{x2 - 2},{y + 19}" stroke="{GREY}" stroke-width="1.6" marker-end="url(#a)"/>')
            parts.append(f'<text x="{(x1 + x2) / 2}" y="{y + 12}" text-anchor="middle" font-size="11" fill="{GREY}">{MAIN_LABELS[title][c]}</text>')
        for a, b, label in arrows:
            (ax, ay), (bx, by) = pos[a], pos[b]
            if ax == bx:  # vertical pair, offset left/right
                down = by > ay
                off = -22 if down else 22
                x = ax + PILL_W / 2 + off
                y1, y2 = (ay + PILL_H, by) if down else (ay, by + PILL_H)
                parts.append(f'<path d="M{x},{y1 + 2} L{x},{y2 - 2 if down else y2 + 2}" stroke="#B5651D" stroke-width="1.6" marker-end="url(#a)"/>')
                tx = x - 6 if down else x + 6
                anchor_ = "end" if down else "start"
                parts.append(f'<text x="{tx}" y="{(y1 + y2) / 2 + 4}" text-anchor="{anchor_}" font-size="11" fill="#8A4A10">{label}</text>')
            else:  # curve below the row
                x1, x2 = ax + PILL_W / 2, bx + PILL_W / 2
                yb = ay + PILL_H
                parts.append(f'<path d="M{x1},{yb + 2} C{x1},{yb + 60} {x2},{yb + 60} {x2},{yb + 3}" fill="none" stroke="#B5651D" stroke-width="1.6" marker-end="url(#a)"/>')
                parts.append(f'<text x="{(x1 + x2) / 2}" y="{yb + 58}" text-anchor="middle" font-size="11" fill="#8A4A10">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# ---------- shared shapes for the report figures ----------

def text_lines(cx, cy, text, size=13, weight="400", color=TEXT, gap=17):
    lines = text.split("\n")
    top = cy - (len(lines) - 1) * gap / 2 + size * 0.35
    return "".join(
        f'<text x="{cx}" y="{top + i * gap:.0f}" text-anchor="middle" font-size="{size}" font-weight="{weight}" fill="{color}">{line}</text>'
        for i, line in enumerate(lines))


def box(x, y, w, h, label, fill="#fff", stroke=NAVY, color=NAVY, size=13, weight="600", rx=7):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            + text_lines(x + w / 2, y + h / 2, label, size, weight, color))


def arrow(d, color=GREY, dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#a)"/>'


def label(x, y, text, color=GREY, anchor="middle", size=11.5, weight="400"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}">{text}</text>'


# ---------- block diagram ----------

def block_diagram():
    w, h = 1100, 580
    p = [HEAD.format(w=w, h=h)]
    heads = [(105, "Users"), (335, "Interfaces"), (640, "Backend"), (965, "Outputs")]
    for x, t in heads:
        p.append(label(x, 32, t, NAVY, size=15, weight="700"))

    users = ["Student", "Maintenance\ntechnician", "Supervisor", "Reception", "Super admin and\nmanagement"]
    for i, u in enumerate(users):
        p.append(box(20, 60 + i * 100, 170, 64, u, fill="#EAF0F7"))

    # interfaces
    p.append(f'<rect x="240" y="60" width="190" height="250" rx="8" fill="#fff" stroke="{NAVY}" stroke-width="2"/>')
    p.append(text_lines(335, 86, "Mobile app", 14, "700", NAVY))
    p.append(text_lines(335, 106, "Android and iOS", 11.5, "400", "#666"))
    for i, t in enumerate(["Student interface", "Supervisor interface", "Maintenance interface"]):
        p.append(box(255, 130 + i * 58, 160, 44, t, fill="#DDE6F1", stroke="#DDE6F1", size=12.5))
    p.append(f'<rect x="240" y="350" width="190" height="200" rx="8" fill="#fff" stroke="{NAVY}" stroke-width="2"/>')
    p.append(text_lines(335, 376, "Web dashboard", 14, "700", NAVY))
    for i, t in enumerate(["Super admin", "Reception", "Supervisor", "Management (read-only)"]):
        p.append(text_lines(335, 410 + i * 34, t, 12.5, "400", TEXT))

    # user -> interface arrows (students, technicians and supervisors use the app;
    # supervisors, reception and admin use the dashboard)
    for y in (92, 192, 284):
        p.append(arrow(f"M190,{y} L238,{y}"))
    p.append(arrow("M190,302 C218,302 214,368 238,368"))
    for y in (392, 492):
        p.append(arrow(f"M190,{y} L238,{y}"))

    # backend
    p.append(f'<rect x="480" y="50" width="320" height="500" rx="10" fill="#FAFBFC" stroke="{NAVY}" stroke-width="2"/>')
    p.append(box(495, 65, 290, 40, "REST API  ·  dashboard screens", fill="#DDE6F1", stroke="#DDE6F1", size=12.5))
    mods = ["Patients and\ndiagnosis", "Referrals", "Work cards\nand grading", "Scheduling and\nattendance",
            "Chair maintenance", "Notifications", "Reports", "Users and\nconfiguration"]
    for i, m in enumerate(mods):
        x = 495 + (i % 2) * 150
        y = 118 + (i // 2) * 62
        p.append(box(x, y, 140, 52, m, fill=NAVY, stroke=NAVY, color="#fff", size=12.5))
    p.append(box(495, 372, 290, 40, "Security: roles, scope, audit log", fill="#C9D6E8", stroke="#C9D6E8", size=12.5))
    p.append(box(495, 430, 140, 100, "PostgreSQL\ndatabase\n\nall records", fill="#F3F6EA", stroke="#5B7B2A", color="#3E5A16", size=12.5))
    p.append(box(645, 430, 140, 100, "Photo storage\n(S3)\n\nphotos, X-rays", fill="#F3F6EA", stroke="#5B7B2A", color="#3E5A16", size=12.5))
    p.append(arrow("M432,185 L478,185"))
    p.append(arrow("M432,450 L478,450"))

    # outputs
    outs = ["Complete patient\narchive", "Work cards, grades\nand logbook", "Daily reports\n(F6, F8, F9, F18)",
            "Referral and\nmaintenance boards", "Statistics for\nmanagement"]
    for i, o in enumerate(outs):
        y = 60 + i * 100
        p.append(box(880, y, 200, 64, o, fill="#FBF1E6", stroke="#B5651D", color="#8A4A10"))
        p.append(arrow(f"M802,{300} C840,300 840,{y + 32} 878,{y + 32}"))
    p.append("</svg>")
    return "\n".join(p)


# ---------- flowchart ----------

FW, FH = 300, 52  # process box
DW, DH = 240, 78  # decision diamond


def fbox(cx, cy, text, kind="process"):
    if kind == "terminal":
        return box(cx - FW / 2, cy - 22, FW, 44, text, fill=NAVY, stroke=NAVY, color="#fff", rx=22)
    return box(cx - FW / 2, cy - FH / 2, FW, FH, text, fill="#EAF0F7")


def diamond(cx, cy, text):
    pts = f"{cx},{cy - DH / 2} {cx + DW / 2},{cy} {cx},{cy + DH / 2} {cx - DW / 2},{cy}"
    return (f'<polygon points="{pts}" fill="#FBF1E6" stroke="#B5651D" stroke-width="1.5"/>'
            + text_lines(cx, cy, text, 12.5, "600", "#8A4A10", gap=15))


def flowchart():
    w, h = 1000, 900
    L, R = 250, 720
    p = [HEAD.format(w=w, h=h)]
    p.append(label(L, 30, "Diagnosis phase", NAVY, size=15, weight="700"))
    p.append(label(R, 30, "Treatment phase", NAVY, size=15, weight="700"))

    left = [(70, "Patient arrives at the clinic", "terminal"),
            (150, "Reception registers the patient\n(file number generated)", "process"),
            (230, "Patient waits in a diagnosis\nclinic's queue", "process"),
            (310, "Supervisor assigns the patient\nto a student", "process"),
            (390, "Student fills in the diagnosis (F1)\nin the app and submits it", "process")]
    for cy, t, k in left:
        p.append(fbox(L, cy, t, k))
    for (a, _, ka), (b, _, _) in zip(left, left[1:]):
        top = a + (22 if ka == "terminal" else FH / 2)
        p.append(arrow(f"M{L},{top} L{L},{b - FH / 2 - 2}"))
    p.append(diamond(L, 490, "Supervisor\napproves?"))
    p.append(arrow(f"M{L},{390 + FH / 2} L{L},{490 - DH / 2 - 2}"))
    p.append(fbox(L, 590, "Diagnosis locked;\ntreatment plan items created"))
    p.append(arrow(f"M{L},{490 + DH / 2} L{L},{590 - FH / 2 - 2}"))
    p.append(label(L + 12, 548, "Yes", anchor="start", weight="600"))
    p.append(fbox(L, 670, "Supervisor refers a plan item\nto a department clinic"))
    p.append(arrow(f"M{L},{590 + FH / 2} L{L},{670 - FH / 2 - 2}"))
    # return loop on the diagnosis
    p.append(arrow(f"M{L - DW / 2},490 L30,490 L30,390 L{L - FW / 2 - 2},390", "#B5651D"))
    p.append(label(38, 436, "No:", "#8A4A10", anchor="start"))
    p.append(label(38, 451, "returned", "#8A4A10", anchor="start"))

    # link to the treatment column
    p.append(arrow(f"M{L + FW / 2},664 L480,664 L480,90 L{R},90 L{R},{150 - DH / 2 - 2}"))

    p.append(diamond(R, 150, "Receiving clinic\naccepts?"))
    p.append(box(860, 124, 130, 52, "Rejected: item\nstays in the plan", fill="#fff", stroke="#B5651D", color="#8A4A10", size=12, weight="400"))
    p.append(arrow(f"M{R + DW / 2},150 L858,150", "#B5651D"))
    p.append(label(849, 140, "No", "#8A4A10", weight="600"))
    p.append(fbox(R, 250, "Supervisor assigns an eligible student;\ncase added to the work card"))
    p.append(arrow(f"M{R},{150 + DH / 2} L{R},{250 - FH / 2 - 2}"))
    p.append(label(R + 10, 212, "Yes", anchor="start", weight="600"))
    p.append(fbox(R, 340, "Student records a step\nwith photos"))
    p.append(arrow(f"M{R},{250 + FH / 2} L{R},{340 - FH / 2 - 2}"))
    p.append(diamond(R, 440, "Supervisor\napproves and grades?"))
    p.append(arrow(f"M{R},{340 + FH / 2} L{R},{440 - DH / 2 - 2}"))
    p.append(arrow(f"M{R + DW / 2},440 L930,440 L930,340 L{R + FW / 2 + 2},340", "#B5651D"))
    p.append(label(936, 400, "No:", "#8A4A10", anchor="start"))
    p.append(label(936, 415, "returned", "#8A4A10", anchor="start"))
    p.append(diamond(R, 550, "Last step\nof the case?"))
    p.append(arrow(f"M{R},{440 + DH / 2} L{R},{550 - DH / 2 - 2}"))
    p.append(label(R + 10, 504, "Yes", anchor="start", weight="600"))
    p.append(arrow(f"M{R - DW / 2},550 L540,550 L540,346 L{R - FW / 2 - 2},346"))
    p.append(label(546, 470, "No: next", anchor="start"))
    p.append(label(546, 485, "step", anchor="start"))
    p.append(fbox(R, 650, "Case complete: referral closed,\nplan item done, student credited"))
    p.append(arrow(f"M{R},{550 + DH / 2} L{R},{650 - FH / 2 - 2}"))
    p.append(label(R + 10, 606, "Yes", anchor="start", weight="600"))
    p.append(diamond(R, 750, "More plan\nitems?"))
    p.append(arrow(f"M{R},{650 + FH / 2} L{R},{750 - DH / 2 - 2}"))
    p.append(arrow(f"M{R - DW / 2},750 L520,750 L520,680 L{L + FW / 2 + 2},680"))
    p.append(label(512, 708, "Yes: refer", anchor="end"))
    p.append(label(512, 723, "the next item", anchor="end"))
    p.append(fbox(R, 850, "Full record kept in the patient archive", "terminal"))
    p.append(arrow(f"M{R},{750 + DH / 2} L{R},{850 - 22 - 2}"))
    p.append(label(R + 10, 808, "No", anchor="start", weight="600"))
    p.append("</svg>")
    return "\n".join(p)


# ---------- render ----------

def render(svg_path):
    text = svg_path.read_text(encoding="utf-8")
    w = re.search(r'width="(\d+)"', text).group(1)
    h = re.search(r'height="(\d+)"', text).group(1)
    browser = next(b for b in BROWSERS if Path(b).exists())
    png = OUT / (svg_path.stem + ".png")
    subprocess.run([
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2", f"--window-size={w},{h}",
        f"--screenshot={png}", svg_path.as_uri(),
    ], check=True, capture_output=True)
    print("rendered", png)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "erd.svg").write_text(erd(), encoding="utf-8")
    (HERE / "lifecycles.svg").write_text(lifecycles(), encoding="utf-8")
    (HERE / "block-diagram.svg").write_text(block_diagram(), encoding="utf-8")
    (HERE / "flowchart.svg").write_text(flowchart(), encoding="utf-8")
    for svg in sorted(HERE.glob("*.svg")):
        render(svg)
