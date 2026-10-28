"""Build the SRS, the System Design and the project report as Word documents.

Usage:  python tools/build_docs.py
Writes the .docx files listed in DOCS_TO_BUILD; tools/export_pdf.ps1 turns them
into PDFs with Microsoft Word. Arabic documents (lang "ar") are laid out right to left.
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

UNIVERSITY = "Syrian Private University"
PROJECT = "SPU Dental Clinic System"
AUTHORS = ["Hamza Almawla", "Zeannab Alhommsi"]
SUPERVISORS = "Dr. Mouhib Alnoukari, Amer Khourshed"

ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x59, 0x59, 0x59)
BODY_FONT = "Calibri"
ARABIC_FONT = "Arial"
MONO_FONT = "Consolas"

LABELS = {
    "en": {"toc": "Table of Contents", "page": "Page ", "of": " of ",
           "toc_hint": "Right-click and choose Update Field to build the table of contents."},
    "ar": {"toc": "المحتويات", "page": "صفحة ", "of": " من ",
           "toc_hint": "انقر بالزر الأيمن واختر تحديث الحقل لبناء جدول المحتويات."},
}

_SPEC_COVER = {
    "lang": "en",
    "top": [UNIVERSITY.upper(), "Faculty of Dentistry"],
    "kicker": PROJECT,
    "rows": lambda date: [("Prepared by", ", ".join(AUTHORS)), ("Date", date), ("Status", "Draft for review")],
}
_REPORT_EN = {
    "lang": "en",
    "top": [UNIVERSITY.upper(), "Faculty of Computer and Informatics Engineering"],
    "kicker": PROJECT,
    "subtitle": "Problem and objectives · State of the art · Proposed solution\nChapter 1: Theoretical Study",
    "rows": lambda date: [("Prepared by", ", ".join(AUTHORS)), ("Supervised by", SUPERVISORS),
                          ("Beneficiary", "Faculty of Dentistry, SPU"), ("Academic year", "2026–2027"),
                          ("Date", date)],
    "header": f"{PROJECT} — Graduation Project Report, Part 1",
}
_REPORT_AR = {
    "lang": "ar",
    "top": ["الجامعة السورية الخاصة", "كلية هندسة الحاسوب والمعلوماتية"],
    "kicker": "نظام عيادات كلية طب الأسنان",
    "subtitle": "المشكلة والأهداف · الدراسة المرجعية · الحل المقترح\nالفصل الأول: الدراسة النظرية",
    "rows": lambda date: [("إعداد", ", ".join(AUTHORS)), ("إشراف", SUPERVISORS),
                          ("الجهة المستفيدة", "كلية طب الأسنان، الجامعة السورية الخاصة"),
                          ("العام الدراسي", "2026–2027"), ("التاريخ", date)],
    "header": "نظام عيادات كلية طب الأسنان — تقرير مشروع التخرج، الجزء الأول",
}

# (source, output, title, cover settings)
DOCS_TO_BUILD = [
    ("SRS.md", "SPU-Dental-SRS.docx", "Software Requirements Specification", _SPEC_COVER),
    ("system-design.md", "SPU-Dental-System-Design.docx", "System Design Document", _SPEC_COVER),
    ("report/part1-en.md", "report/SPU-Dental-Report-Part1-EN.docx", "Graduation Project Report — Part 1", _REPORT_EN),
    ("report/part1-ar.md", "report/SPU-Dental-Report-Part1-AR.docx", "تقرير مشروع التخرج — الجزء الأول", _REPORT_AR),
]

# headings that start on a new page in the report
NEW_PAGE_HEADINGS = ("Chapter 1", "References", "الفصل الأول", "المراجع")


# ---------- low-level helpers ----------

def set_cell_shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def set_cell_margins(table, top=60, bottom=60, left=100, right=100):
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def set_table_borders(table, color="A6A6A6", size=4):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def no_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def add_field(paragraph, instr, placeholder=""):
    """Insert a Word field (PAGE, NUMPAGES, TOC ...)."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run._r.append(begin)
    run = paragraph.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    run._r.append(it)
    run = paragraph.add_run()
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run._r.append(sep)
    paragraph.add_run(placeholder)
    run = paragraph.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(end)


def bottom_border(paragraph, color="1F3A5F", size=8):
    p_pr = paragraph._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(size))
    b.set(qn("w:space"), "4")
    b.set(qn("w:color"), color)
    bdr.append(b)
    p_pr.append(bdr)


def set_run_fonts(run, name, cs=ARABIC_FONT):
    run.font.name = name
    r_pr = run._r.get_or_add_rPr()
    fonts = r_pr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        fonts.set(qn(attr), name)
    fonts.set(qn("w:cs"), cs)


# ---------- inline markdown ----------

INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))")


def add_inline(paragraph, text, size=None, bold=False, color=None):
    text = text.replace("\\_", "_").replace("\\*", "*")
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            # non-breaking spaces keep a code span on one line
            run = paragraph.add_run(part[1:-1].replace(" ", " "))
            set_run_fonts(run, MONO_FONT)
            run.font.size = Pt((size or 11) - 1.5)
            run.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
            if bold:
                run.bold = True
            continue
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        if bold:
            run.bold = True
        if size:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color


# ---------- document setup ----------

def setup_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:cs"), ARABIC_FONT)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15

    for name, size, before, after in (
        ("Heading 1", 16, 18, 8),
        ("Heading 2", 13, 14, 6),
        ("Heading 3", 11.5, 10, 4),
    ):
        st = styles[name]
        st.font.name = BODY_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = ACCENT
        rpr = st.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fonts.set(qn(attr), BODY_FONT if attr != "w:cs" else ARABIC_FONT)
        for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if fonts.get(qn(theme_attr)) is not None:
                del fonts.attrib[qn(theme_attr)]
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number"):
        st = styles[name]
        st.font.name = BODY_FONT
        st.font.size = Pt(11)
        st.paragraph_format.space_after = Pt(3)

    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.left_margin = sec.right_margin = Cm(2.3)


def centered(doc, text, size, color, bold=False, space_after=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, line in enumerate(text.split("\n")):
        r = p.add_run(line)
        r.bold = bold
        r.font.size = Pt(size)
        r.font.color.rgb = color
        if i < len(text.split("\n")) - 1:
            r.add_break()
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def cover_page(doc, title, date_text, cover):
    for _ in range(3):
        doc.add_paragraph()
    centered(doc, cover["top"][0], 15, ACCENT, bold=True, space_after=2)
    for line in cover["top"][1:]:
        centered(doc, line, 13, GREY)

    for _ in range(4):
        doc.add_paragraph()
    centered(doc, cover["kicker"], 18, GREY)
    p = centered(doc, title, 26, ACCENT, bold=True)
    bottom_border(p, size=12)
    if cover.get("subtitle"):
        centered(doc, cover["subtitle"], 12.5, GREY)

    rows = cover["rows"](date_text)
    for _ in range(9 - len(rows)):
        doc.add_paragraph()
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(rows):
        c0, c1 = table.rows[i].cells
        c0.width, c1.width = Cm(4.2), Cm(9)
        c0.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = c0.paragraphs[0].add_run(k)
        r.bold = True
        r.font.color.rgb = ACCENT
        c1.paragraphs[0].add_run(v)
        for c in (c0, c1):
            c.paragraphs[0].paragraph_format.space_after = Pt(3)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def toc_page(doc, labels):
    p = doc.add_paragraph()
    r = p.add_run(labels["toc"])
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = ACCENT
    p.paragraph_format.space_after = Pt(12)
    add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u', labels["toc_hint"])


def header_footer(section, header_text, labels, rtl=False):
    hp = section.header.paragraphs[0]
    hp.text = ""
    r = hp.add_run(header_text)
    r.font.size = Pt(9)
    r.font.color.rgb = GREY
    # in a right-to-left paragraph Word reads "left" as the leading (right) edge
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT if rtl else WD_ALIGN_PARAGRAPH.RIGHT
    bottom_border(hp, color="BFBFBF", size=4)

    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for piece in (labels["page"], "PAGE", labels["of"], "SECTIONPAGES"):
        if piece in ("PAGE", "SECTIONPAGES"):
            add_field(fp, piece, "1")
        else:
            fp.add_run(piece)
    for r in fp.runs:
        r.font.size = Pt(9)
        r.font.color.rgb = GREY


# ---------- block markdown ----------

def parse_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)]


def add_table(doc, rows, usable_width_cm):
    header, body = rows[0], rows[1:]
    ncols = len(header)
    table = doc.add_table(rows=1 + len(body), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    set_cell_margins(table)

    # column widths: each column fits its longest single word, the rest of the
    # page width is shared in proportion to content length
    word_cm, lengths = [], []
    for c in range(ncols):
        cells = [r[c] if c < len(r) else "" for r in rows]
        longest_word = max((len(w) for v in cells for w in v.replace("*", "").split()), default=4)
        word_cm.append(longest_word * 0.2 + 0.45)
        lengths.append(min(max(max(len(v) for v in cells), 6), 60))
    spare = max(usable_width_cm - sum(word_cm), 0)
    total = sum(lengths)
    widths = [Cm(word_cm[c] + spare * lengths[c] / total) for c in range(ncols)]

    font_size = 9.5 if ncols <= 4 else 9
    for i, row_vals in enumerate(rows):
        row = table.rows[i]
        no_split(row)
        for c in range(ncols):
            cell = row.cells[c]
            cell.width = widths[c]
            val = row_vals[c] if c < len(row_vals) else ""
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            # never leave a header row alone at the foot of a page; keep small tables whole
            if i == 0 or (len(rows) <= 8 and i < len(rows) - 1):
                para.paragraph_format.keep_with_next = True
            if i == 0:
                set_cell_shading(cell, "1F3A5F")
                add_inline(para, val, size=font_size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
            else:
                if i % 2 == 0:
                    set_cell_shading(cell, "F2F5F9")
                add_inline(para, val, size=font_size)
    repeat_header(table.rows[0])
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def add_code(doc, lines, usable_width_cm):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="D9D9D9")
    set_cell_margins(table, 100, 100, 160, 160)
    cell = table.rows[0].cells[0]
    cell.width = Cm(usable_width_cm)
    set_cell_shading(cell, "F5F5F5")
    para = cell.paragraphs[0]
    para.paragraph_format.space_after = Pt(0)
    para.paragraph_format.line_spacing = 1.0
    for i, line in enumerate(lines):
        run = para.add_run(line)
        set_run_fonts(run, MONO_FONT, cs=MONO_FONT)
        run.font.size = Pt(8.5)
        if i < len(lines) - 1:
            run.add_break()
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_figure(doc, image_path, caption, usable_width_cm):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(str(image_path), width=Cm(usable_width_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    run = cap.add_run(caption)
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = GREY


ARABIC = re.compile(r"[؀-ۿ]")


def apply_rtl(doc):
    """Lay an Arabic document out right to left.

    Paragraphs and tables get bidi direction; runs that contain Arabic are marked
    right-to-left, and every size, bold and italic setting is copied to its
    complex-script twin, which is what Word uses for Arabic text.
    """
    def twin(rpr, tag, cs_tag):
        el = rpr.find(qn(tag))
        if el is not None and rpr.find(qn(cs_tag)) is None:
            new = OxmlElement(cs_tag)
            for k, v in el.attrib.items():
                new.set(k, v)
            el.addnext(new)

    def fix_rpr(rpr):
        twin(rpr, "w:b", "w:bCs")
        twin(rpr, "w:i", "w:iCs")
        twin(rpr, "w:sz", "w:szCs")

    parts = [doc.element.body]
    for sec in doc.sections:
        parts += [sec.header._element, sec.footer._element]
    for part in parts:
        for p in part.iter(qn("w:p")):
            # Latin-only blocks outside tables (references, figures) stay left to right
            text = "".join(t.text or "" for t in p.iter(qn("w:t")))
            in_table = any(a.tag == qn("w:tc") for a in p.iterancestors())
            if part is doc.element.body and not in_table and text.strip() and not ARABIC.search(text):
                continue
            ppr = p.get_or_add_pPr()
            if ppr.find(qn("w:bidi")) is None:
                bidi = OxmlElement("w:bidi")
                # w:bidi must come before spacing/indentation/justification
                anchor = next((ppr.find(qn(t)) for t in ("w:spacing", "w:ind", "w:jc", "w:rPr")
                               if ppr.find(qn(t)) is not None), None)
                if anchor is not None:
                    anchor.addprevious(bidi)
                else:
                    ppr.append(bidi)
        for p in part.iter(qn("w:p")):
            arabic_para = bool(ARABIC.search("".join(t.text or "" for t in p.iter(qn("w:t")))))
            for r in p.iter(qn("w:r")):
                rpr = r.find(qn("w:rPr"))
                text = "".join(t.text or "" for t in r.iter(qn("w:t")))
                # Arabic runs, and runs with no Latin letters (list numbers, spaces)
                # inside Arabic paragraphs, flow right to left; Latin runs keep theirs
                rtl = bool(ARABIC.search(text)) or (
                    arabic_para and text.strip("  ") != "" and not re.search(r"[A-Za-z]", text))
                if rpr is None:
                    if not rtl:
                        continue
                    rpr = OxmlElement("w:rPr")
                    r.insert(0, rpr)
                fix_rpr(rpr)
                if rtl and rpr.find(qn("w:rtl")) is None:
                    rpr.append(OxmlElement("w:rtl"))
        for tbl in part.iter(qn("w:tbl")):
            tbl_pr = tbl.find(qn("w:tblPr"))
            if tbl_pr is not None and tbl_pr.find(qn("w:bidiVisual")) is None:
                tbl_pr.insert(0, OxmlElement("w:bidiVisual"))
    for style in doc.styles:
        rpr = style.element.find(qn("w:rPr"))
        if rpr is not None:
            fix_rpr(rpr)
    # Arabic body text reads better slightly larger than the Latin text around it
    normal_rpr = doc.styles["Normal"].element.get_or_add_rPr()
    sz_cs = normal_rpr.find(qn("w:szCs"))
    if sz_cs is None:
        sz_cs = OxmlElement("w:szCs")
        normal_rpr.append(sz_cs)
    sz_cs.set(qn("w:val"), "24")


def convert(md_path, out_path, title, cover):
    labels = LABELS[cover["lang"]]
    lines = md_path.read_text(encoding="utf-8").splitlines()

    # first H1 and the "date · @author" line go on the cover page
    date_text = ""
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    if lines and "·" in lines[0]:
        date_text = lines[0].split("·")[0].strip()
        lines = lines[1:]

    doc = Document()
    setup_styles(doc)
    sec = doc.sections[0]
    usable = (sec.page_width - sec.left_margin - sec.right_margin) / 360000  # EMU -> cm
    cover_page(doc, title, date_text, cover)
    toc_page(doc, labels)

    # cover and contents stay without header/footer; the body section gets them,
    # with page numbers restarting at 1
    body = doc.add_section(WD_SECTION.NEW_PAGE)
    body.header.is_linked_to_previous = False
    body.footer.is_linked_to_previous = False
    rtl = cover["lang"] == "ar"
    header_footer(body, cover.get("header", f"{PROJECT} — {title}"), labels, rtl)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    body._sectPr.append(pg)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            add_code(doc, code, usable)
            i += 1
            continue

        m = re.match(r"^!\[(.*)\]\((.+)\)$", stripped)
        if m:
            add_figure(doc, md_path.parent / m.group(2), m.group(1), usable)
            i += 1
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = parse_row(lines[i])
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            add_table(doc, rows, usable)
            continue

        m = re.match(r"^(#{2,4})\s+(.*)", stripped)
        if m:
            level = len(m.group(1)) - 1
            new_page = level == 1 and m.group(2).startswith(NEW_PAGE_HEADINGS)
            if new_page and doc.paragraphs and not doc.paragraphs[-1]._p.xpath(".//w:t|.//w:drawing"):
                # an empty spacer before a page break can spill into a blank page
                last = doc.paragraphs[-1]._p
                last.getparent().remove(last)
            h = doc.add_heading(level=level)
            add_inline(h, m.group(2))
            if new_page:
                h.paragraph_format.page_break_before = True
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped):
            indent = len(line) - len(line.lstrip())
            p = doc.add_paragraph(style="List Bullet 2" if indent >= 2 else "List Bullet")
            add_inline(p, re.sub(r"^[-*]\s+", "", stripped))
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            # numbered list: write the number ourselves so each list restarts at 1
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            if rtl:
                # Word applies hanging indents unevenly in right-to-left paragraphs,
                # so Arabic items start at the margin with the number inline
                p.add_run(f"{m.group(1)}.  ")
            else:
                p.paragraph_format.left_indent = Cm(0.9)
                p.paragraph_format.first_line_indent = Cm(-0.6)
                p.add_run(f"{m.group(1)}.\t")
                p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
            add_inline(p, m.group(2))
            i += 1
            continue

        # paragraph (join soft-wrapped lines)
        buf = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#|\||```|[-*]\s|\d+\.\s)", lines[i].strip()
        ):
            buf.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        text = " ".join(buf)
        # a paragraph that is only a bold label acts as a small sub-heading
        if re.fullmatch(r"\*\*[^*]+\*\*", text):
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6)
            add_inline(p, text, color=ACCENT)
        else:
            add_inline(p, text)

    if cover["lang"] == "ar":
        apply_rtl(doc)

    core = doc.core_properties
    core.title = cover.get("header", f"{PROJECT} — {title}")
    core.author = ", ".join(AUTHORS)
    core.subject = UNIVERSITY
    doc.save(out_path)
    print("wrote", out_path)


if __name__ == "__main__":
    for src, out, title, cover in DOCS_TO_BUILD:
        convert(DOCS / src, DOCS / out, title, cover)
