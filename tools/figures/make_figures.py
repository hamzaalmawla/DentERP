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
    for svg in sorted(HERE.glob("*.svg")):
        render(svg)
