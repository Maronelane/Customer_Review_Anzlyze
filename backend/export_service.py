"""
Export service: Generate professional, business-grade PDF and Excel reports
from analysis results. All styling uses the AnZlyze brand palette
(primary #6C5CE7, positive #00D2A0, negative #FF6B6B, neutral #FECA57) so every
export feels on-brand and ready to present to real stakeholders.
"""
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie as RLPie
from reportlab.graphics.charts.legends import Legend

# Brand palette
PRIMARY = "#6C5CE7"
PRIMARY_LIGHT = "#A78BFA"
POSITIVE = "#00D2A0"
NEGATIVE = "#FF6B6B"
NEUTRAL = "#FECA57"
INK = "#1E293B"
SLATE = "#64748B"
BG_ALT = "#F8FAFC"
WHITE = "#FFFFFF"

POSITIVE_STYLE = PatternFill("solid", fgColor="EFFDF7")
NEGATIVE_STYLE = PatternFill("solid", fgColor="FFF1F1")
NEUTRAL_STYLE = PatternFill("solid", fgColor="FFFBE8")


def _color(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip("#")
    r, g, b = [int(hex_str[i:i + 2], 16) for i in (0, 2, 4)]
    return colors.Color(r / 255.0, g / 255.0, b / 255.0, alpha=alpha)


def _fmt_labels(cell, *, bold=False, size=10, color=INK, center=False, wrap=False):
    rgb = str(color).lstrip("#")
    cell.font = Font(bold=bold, size=size, color=rgb, name="Calibri")
    if center or wrap:
        cell.alignment = Alignment(
            horizontal="center" if center else "left",
            vertical="center",
            wrap_text=wrap,
        )


def _apply_table_borders(ws, min_row, max_row, min_col, max_col, color="E2E8F0"):
    side = Side(style="thin", color=color)
    border = Border(left=side, right=side, top=side, bottom=side)
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            cell.border = border


def _severity_fill(severity):
    return {
        "critical": PatternFill("solid", fgColor="FEE2E2"),
        "high": PatternFill("solid", fgColor="FDECEC"),
        "medium": PatternFill("solid", fgColor="FFFBE8"),
        "low": PatternFill("solid", fgColor="EFFDF7"),
    }.get((severity or "").lower(), PatternFill("solid", fgColor="F8FAFC"))


def generate_excel(results_data: dict) -> bytes:
    analysis = results_data.get("analysis", {})
    results = results_data.get("results", {})
    dist = results.get("sentiment_distribution", {})
    total = dist.get("total", 0)
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    neu = dist.get("neutral", 0)
    pos_pct = pos / max(total, 1) * 100
    neg_pct = neg / max(total, 1) * 100
    neu_pct = neu / max(total, 1) * 100

    header_font = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
    header_fill = PatternFill("solid", fgColor="6C5CE7")
    border_body = Border(
        left=Side(style="thin", color="E2E8F0"), right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"), bottom=Side(style="thin", color="E2E8F0"),
    )

    def add_header_row(ws, cols, start_row=1):
        for ci, name in enumerate(cols, 1):
            c = ws.cell(row=start_row, column=ci, value=name)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_body
        ws.row_dimensions[start_row].height = 24

    def polish_sheet(ws, freeze="A4", tab_color="6C5CE7"):
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = freeze
        ws.sheet_properties.tabColor = tab_color
        ws.auto_filter.ref = ws.dimensions
        return ws

    wb = Workbook()

    # ── COVER ──────────────────────────────────────────────
    ws_cover = wb.active
    ws_cover.title = "Report"
    ws_cover.sheet_view.showGridLines = False
    ws_cover.merge_cells("B4:F4")
    ws_cover["B4"] = "AnZlyze"
    _fmt_labels(ws_cover["B4"], bold=True, size=34, color=PRIMARY)
    ws_cover.merge_cells("B5:F5")
    ws_cover["B5"] = "Customer Review Intelligence Report"
    _fmt_labels(ws_cover["B5"], bold=True, size=15, color=INK)
    ws_cover.merge_cells("B6:F6")
    ws_cover["B6"] = analysis.get("filename", "")
    _fmt_labels(ws_cover["B6"], size=12, color=SLATE)

    info_rows = [
        ("Date", datetime.now().strftime("%B %d, %Y")),
        ("Reviews Analyzed", str(total)),
        ("Text Column", analysis.get("text_column") or "—"),
        ("Rating Column", analysis.get("rating_column") or "—"),
        ("Best Model", (results.get("best_model") or "").replace("_", " ").title()),
        ("Model Accuracy", f"{results.get('best_accuracy', 0) * 100:.1f}%"),
        ("Overall Sentiment", results.get("recommendations", {}).get("overall_sentiment", "—").title()),
    ]
    for i, (k, v) in enumerate(info_rows):
        r = 14 + i
        ws_cover.merge_cells(f"A{r}:C{r}")
        ws_cover[f"A{r}"] = k.upper()
        _fmt_labels(ws_cover[f"A{r}"], bold=True, size=9, color=SLATE)
        ws_cover.merge_cells(f"D{r}:F{r}")
        ws_cover[f"D{r}"] = v
        _fmt_labels(ws_cover[f"D{r}"], bold=True, size=11, color=INK)

    # Prepared for/by + disclaimer footer
    ws_cover.merge_cells("A23:F23")
    ws_cover["A23"] = "PREPARED FOR: CUSTOMER EXPERIENCE TEAM"
    _fmt_labels(ws_cover["A23"], bold=True, size=9, color=SLATE)
    ws_cover.merge_cells("A24:F24")
    ws_cover["A24"] = "PREPARED BY: ANZLYZE — CUSTOMER REVIEW INTELLIGENCE PLATFORM"
    _fmt_labels(ws_cover["A24"], bold=True, size=8, color=SLATE)
    ws_cover.merge_cells("A26:F28")
    ws_cover["A26"] = ("This report was generated automatically by AnZlyze based on machine-learning "
                       "analysis of the uploaded review dataset. Figures are for planning purposes and "
                       "should be validated against primary sources before strategic decisions.")
    _fmt_labels(ws_cover["A26"], size=8, color=SLATE, wrap=True)
    ws_cover.row_dimensions[26].height = 36

    for col, w in zip("ABCDEF", [6, 12, 18, 16, 20, 22]):
        ws_cover.column_dimensions[col].width = w
    for r in range(12, 24):
        ws_cover.row_dimensions[r].height = 22

    # ── EXECUTIVE SUMMARY ──────────────────────────────────
    ws_exec = wb.create_sheet("Executive Summary")
    polish_sheet(ws_exec, freeze="A7", tab_color="00D2A0")
    ws_exec.merge_cells("A1:F1")
    ws_exec["A1"] = "Executive Summary"
    _fmt_labels(ws_exec["A1"], bold=True, size=16, color=PRIMARY)
    ws_exec.row_dimensions[1].height = 26

    # KPI band
    kpis = [
        ("Positive", pos, f"{pos / max(total, 1) * 100:.1f}%", POSITIVE, POSITIVE_STYLE),
        ("Negative", neg, f"{neg / max(total, 1) * 100:.1f}%", NEGATIVE, NEGATIVE_STYLE),
        ("Neutral", neu, f"{neu / max(total, 1) * 100:.1f}%", NEUTRAL, NEUTRAL_STYLE),
        ("Total Reviews", total, "", INK, PatternFill("solid", fgColor="EDE9FE")),
        ("Spam Flagged", results.get("spam_summary", {}).get("total_flagged", 0),
         f"{results.get('spam_summary', {}).get('flagged_percentage', 0)}%", SLATE, PatternFill("solid", fgColor="F1F5F9")),
    ]
    kpi_start = 3
    for i, (label, value, sub, color, fill) in enumerate(kpis):
        c1 = kpi_start + i
        for rr in (3, 4, 5):
            ws_exec[f"{get_column_letter(c1)}{rr}"].fill = fill
        ws_exec[f"{get_column_letter(c1)}3"] = str(value)
        _fmt_labels(ws_exec[f"{get_column_letter(c1)}3"], bold=True, size=20, color=color, center=True)
        ws_exec[f"{get_column_letter(c1)}4"] = label + (f"  ({sub})" if sub else "")
        _fmt_labels(ws_exec[f"{get_column_letter(c1)}4"], bold=True, size=9, color=SLATE, center=True)
    for i in range(len(kpis)):
        ws_exec.column_dimensions[get_column_letter(kpi_start + i)].width = 15
    ws_exec.row_dimensions[3].height = 26
    ws_exec.row_dimensions[4].height = 20
    ws_exec.row_dimensions[5].height = 18

    exec_text = results.get("recommendations", {}).get("summary") or ""
    r = 7
    for line in exec_text.split("\n"):
        line = line.strip()
        if not line:
            r += 1
            continue
        ws_exec.merge_cells(f"A{r}:F{r}")
        ws_exec[f"A{r}"] = line
        _fmt_labels(ws_exec[f"A{r}"], bold=(line.startswith("Executive") or line.endswith(":")),
                    size=10, color=INK, wrap=True)
        ws_exec[f"A{r}"].alignment = Alignment(vertical="top", wrap_text=True, horizontal="left")
        ws_exec.row_dimensions[r].height = 18 if len(line) < 110 else 30
        r += 1

    ws_exec.column_dimensions["F"].width = 15

    # ── SENTIMENT DISTRIBUTION ─────────────────────────────
    ws_sent = wb.create_sheet("Sentiment Analysis")
    polish_sheet(ws_sent, tab_color="FECA57")
    ws_sent.merge_cells("A1:C1")
    ws_sent["A1"] = "Overall Sentiment Distribution"
    _fmt_labels(ws_sent["A1"], bold=True, size=16, color=PRIMARY)
    ws_sent.row_dimensions[1].height = 26
    add_header_row(ws_sent, ["Sentiment", "Count", "Percentage"], 3)
    row_fills = {
        "positive": POSITIVE_STYLE,
        "negative": NEGATIVE_STYLE,
        "neutral": NEUTRAL_STYLE,
    }
    for i, sent in enumerate(["positive", "negative", "neutral"]):
        rr = 4 + i
        count = dist.get(sent, 0)
        pct = count / max(total, 1) * 100
        ws_sent.cell(row=rr, column=1, value=sent.capitalize()).fill = row_fills[sent]
        ws_sent.cell(row=rr, column=2, value=count).fill = row_fills[sent]
        ws_sent.cell(row=rr, column=3, value=f"{pct:.1f}%").fill = row_fills[sent]
        _fmt_labels(ws_sent.cell(row=rr, column=1), size=10, color=INK)
        _fmt_labels(ws_sent.cell(row=rr, column=2), size=10, color=INK, center=True)
        _fmt_labels(ws_sent.cell(row=rr, column=3), size=10, color=INK, center=True)
    _apply_table_borders(ws_sent, 3, 6, 1, 3)

    # Summary band beneath the table (plain cells, no charts/pictures)
    ws_sent.merge_cells("A8:C8")
    ws_sent["A8"] = "SUMMARY"
    _fmt_labels(ws_sent["A8"], bold=True, size=9, color=SLATE)
    ws_sent.merge_cells("A9:C9")
    ws_sent["A9"] = (f"Of {total} reviews analyzed, {pos_pct:.1f}% were positive, "
                     f"{neg_pct:.1f}% were negative and {neu_pct:.1f}% neutral.")
    _fmt_labels(ws_sent["A9"], size=10, color=INK, wrap=True)
    ws_sent.row_dimensions[9].height = 30

    ws_sent.column_dimensions["A"].width = 22
    ws_sent.column_dimensions["B"].width = 12
    ws_sent.column_dimensions["C"].width = 14

    # ── TOP PROBLEMS ───────────────────────────────────────
    ws_prob = wb.create_sheet("Problems")
    polish_sheet(ws_prob, tab_color="FF6B6B")
    ws_prob.merge_cells("A1:E1")
    ws_prob["A1"] = "Detected Problem Categories"
    _fmt_labels(ws_prob["A1"], bold=True, size=16, color=PRIMARY)
    ws_prob.row_dimensions[1].height = 26
    add_header_row(ws_prob, ["Category", "Severity", "Frequency", "% of Negative", "Example Review"], 3)
    problems = results.get("problems", {}).get("problems", [])
    neg_total = problems and max(results.get("problems", {}).get("total_negative", 1), 1) or 1
    for i, p in enumerate(problems):
        rr = 4 + i
        ws_prob.cell(row=rr, column=1, value=p.get("category", ""))
        ws_prob.cell(row=rr, column=2, value=(p.get("severity") or "").upper())
        ws_prob.cell(row=rr, column=3, value=p.get("frequency", 0))
        ws_prob.cell(row=rr, column=4, value=f"{p.get('percentage', 0)}%")
        ex = (p.get("examples") or [""])[0][:180]
        ws_prob.cell(row=rr, column=5, value=ex)
        for ci in range(1, 6):
            ws_prob.cell(row=rr, column=ci).fill = _severity_fill(p.get("severity"))
            _fmt_labels(ws_prob.cell(row=rr, column=ci), size=10, color=INK, wrap=(ci == 5))
            if ci in (2, 3, 4):
                ws_prob.cell(row=rr, column=ci).alignment = Alignment(horizontal="center", vertical="center")
        ws_prob.row_dimensions[rr].height = 30
    _apply_table_borders(ws_prob, 3, 3 + len(problems), 1, 5)
    ws_prob.column_dimensions["A"].width = 24
    ws_prob.column_dimensions["B"].width = 12
    ws_prob.column_dimensions["C"].width = 12
    ws_prob.column_dimensions["D"].width = 16
    ws_prob.column_dimensions["E"].width = 60

    if problems:
        # A plain summary note replaces what used to be a floating chart.
        ws_prob.merge_cells("A8:E8")
        ws_prob["A8"] = "SUMMARY"
        _fmt_labels(ws_prob["A8"], bold=True, size=9, color=SLATE)
        top_problem = problems[0].get("category", "") if problems else ""
        ws_prob.merge_cells("A9:E9")
        ws_prob["A9"] = (f"The most frequent problem is '{top_problem}' appearing in "
                         f"{problems[0].get('percentage', 0)}% of negative reviews.")
        _fmt_labels(ws_prob["A9"], size=10, color=INK, wrap=True)
        ws_prob.row_dimensions[9].height = 30

    # ── RECOMMENDATIONS ────────────────────────────────────
    ws_rec = wb.create_sheet("Recommendations")
    polish_sheet(ws_rec, tab_color="6C5CE7")
    ws_rec.merge_cells("A1:E1")
    ws_rec["A1"] = "Strategic Recommendations"
    _fmt_labels(ws_rec["A1"], bold=True, size=16, color=PRIMARY)
    ws_rec.row_dimensions[1].height = 26
    add_header_row(ws_rec, ["Priority", "Action", "Problem Category", "Impact", "Suggested Steps"], 3)
    recs = results.get("recommendations", {}).get("recommendations", [])
    priority_fill = {
        "critical": PatternFill("solid", fgColor="FEE2E2"),
        "high": PatternFill("solid", fgColor="FDECEC"),
        "medium": PatternFill("solid", fgColor="FFFBE8"),
        "low": PatternFill("solid", fgColor="EFFDF7"),
    }
    for i, r in enumerate(recs):
        rr = 4 + i
        ws_rec.cell(row=rr, column=1, value=(r.get("priority") or "").upper())
        ws_rec.cell(row=rr, column=2, value=r.get("title", ""))
        ws_rec.cell(row=rr, column=3, value=r.get("problem_category", ""))
        ws_rec.cell(row=rr, column=4, value=r.get("impact", ""))
        steps = "\n".join(f"• {s}" for s in (r.get("suggestions") or [])[:4])
        ws_rec.cell(row=rr, column=5, value=steps)
        for ci in range(1, 6):
            c = ws_rec.cell(row=rr, column=ci)
            c.fill = priority_fill.get((r.get("priority") or "").lower(), PatternFill("solid", fgColor="F8FAFC"))
            _fmt_labels(c, size=10, color=INK, wrap=True)
        ws_rec.cell(row=rr, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws_rec.row_dimensions[rr].height = 42
    _apply_table_borders(ws_rec, 3, 3 + len(recs), 1, 5)
    ws_rec.column_dimensions["A"].width = 12
    ws_rec.column_dimensions["B"].width = 34
    ws_rec.column_dimensions["C"].width = 20
    ws_rec.column_dimensions["D"].width = 44
    ws_rec.column_dimensions["E"].width = 50

    # ── MODEL COMPARISON ───────────────────────────────────
    ws_model = wb.create_sheet("Model Comparison")
    polish_sheet(ws_model, tab_color="8B5CF6")
    ws_model.merge_cells("A1:C1")
    ws_model["A1"] = "Model Performance Comparison"
    _fmt_labels(ws_model["A1"], bold=True, size=16, color=PRIMARY)
    ws_model.row_dimensions[1].height = 26
    add_header_row(ws_model, ["Model", "Accuracy", "Relative Rank"], 3)
    model_results = results.get("model_results", {})
    sorted_models = sorted(model_results.items(), key=lambda x: x[1].get("accuracy", 0), reverse=True)
    best_acc = sorted_models[0][1].get("accuracy", 0) if sorted_models else 1
    for i, (name, info) in enumerate(sorted_models):
        rr = 4 + i
        acc = info.get("accuracy", 0)
        ws_model.cell(row=rr, column=1, value=name.replace("_", " ").title())
        ws_model.cell(row=rr, column=2, value=f"{acc * 100:.1f}%")
        ws_model.cell(row=rr, column=3, value=f"{acc / max(best_acc, 1e-9) * 100:.1f}% of best")
        for ci in range(1, 4):
            ws_model.cell(row=rr, column=ci).fill = (
                PatternFill("solid", fgColor="DCFCE7") if i == 0
                else PatternFill("solid", fgColor="F8FAFC"))
            _fmt_labels(ws_model.cell(row=rr, column=ci), size=10, color=INK)
            ws_model.cell(row=rr, column=2).alignment = Alignment(horizontal="center")
    _apply_table_borders(ws_model, 3, 3 + len(sorted_models), 1, 3)
    ws_model.column_dimensions["A"].width = 26
    ws_model.column_dimensions["B"].width = 14
    ws_model.column_dimensions["C"].width = 16

    # ── CLUSTER THEMES ─────────────────────────────────────
    clusters = results.get("cluster_summary", []) or []
    if clusters:
        ws_cl = wb.create_sheet("Review Themes")
        polish_sheet(ws_cl, tab_color="A78BFA")
        ws_cl.merge_cells("A1:C1")
        ws_cl["A1"] = "Emerging Review Themes"
        _fmt_labels(ws_cl["A1"], bold=True, size=16, color=PRIMARY)
        ws_cl.row_dimensions[1].height = 26
        add_header_row(ws_cl, ["Theme", "# Reviews", "Share"], 3)
        total_cl = sum(c.get("count", 0) for c in clusters)
        for i, c in enumerate(clusters):
            rr = 4 + i
            cnt = c.get("count", 0)
            ws_cl.cell(row=rr, column=1, value=c.get("label") or c.get("cluster") or "Theme")
            ws_cl.cell(row=rr, column=2, value=cnt)
            ws_cl.cell(row=rr, column=3, value=f"{cnt / max(total_cl, 1) * 100:.1f}%")
            for ci in range(1, 4):
                ws_cl.cell(row=rr, column=ci).fill = PatternFill("solid", fgColor="F5F3FF")
                _fmt_labels(ws_cl.cell(row=rr, column=ci), size=10, color=INK)
                ws_cl.cell(row=rr, column=2).alignment = Alignment(horizontal="center")
        _apply_table_borders(ws_cl, 3, 3 + len(clusters), 1, 3)
        ws_cl.column_dimensions["A"].width = 30
        ws_cl.column_dimensions["B"].width = 12
        ws_cl.column_dimensions["C"].width = 14

    # ── SPAM INSIGHT ───────────────────────────────────────
    spam = results.get("spam_summary", {})
    if spam:
        ws_spam = wb.create_sheet("Data Quality")
        polish_sheet(ws_spam, tab_color="94A3B8")
        ws_spam.merge_cells("A1:C1")
        ws_spam["A1"] = "Data Quality & Spam Profile"
        _fmt_labels(ws_spam["A1"], bold=True, size=16, color=PRIMARY)
        ws_spam.row_dimensions[1].height = 26
        spam_rows = [
            ("Total Reviews Scanned", spam.get("total_reviews", 0)),
            ("Flagged as Spam", spam.get("total_flagged", 0)),
            ("Spam Percentage", f"{spam.get('flagged_percentage', 0)}%"),
            ("Clean Reviews", max(spam.get("total_reviews", 0) - spam.get("total_flagged", 0), 0)),
        ]
        for i, (k, v) in enumerate(spam_rows):
            rr = 3 + i
            ws_spam.merge_cells(f"A{rr}:B{rr}")
            ws_spam[f"A{rr}"] = k
            _fmt_labels(ws_spam[f"A{rr}"], size=10, color=INK)
            ws_spam.merge_cells(f"C{rr}:C{rr}")
            ws_spam[f"C{rr}"] = v
            _fmt_labels(ws_spam[f"C{rr}"], bold=True, size=11, color=INK, center=True)
            ws_spam[f"A{rr}"].fill = PatternFill("solid", fgColor="F8FAFC")
            ws_spam[f"C{rr}"].fill = PatternFill("solid", fgColor="EDE9FE")
        _apply_table_borders(ws_spam, 3, 2 + len(spam_rows), 1, 3)
        ws_spam.column_dimensions["A"].width = 26
        ws_spam.column_dimensions["B"].width = 10
        ws_spam.column_dimensions["C"].width = 16

    # Final polish: freeze header rows + enable autofilter on every data sheet
    # (applied now so dimensions reflect the fully-written content).
    freeze_map = {
        "Executive Summary": "A7",
        "Sentiment Analysis": "A4",
        "Problems": "A4",
        "Recommendations": "A4",
        "Model Comparison": "A4",
    }
    for name, ws in wb._sheets.items() if isinstance(wb._sheets, dict) else [(ws.title, ws) for ws in wb.worksheets]:
        if name == "Report":
            continue
        try:
            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = freeze_map.get(name, "A4")
        except Exception:
            pass

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════════════════

def _pdf_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(_color(PRIMARY))
    canvas.rect(0, doc.pagesize[1] - 0.4 * inch, doc.pagesize[0], 0.4 * inch, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.5 * inch, doc.pagesize[1] - 0.27 * inch, "AnZlyze  •  Customer Review Intelligence")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(doc.pagesize[0] - 0.5 * inch, doc.pagesize[1] - 0.27 * inch,
                           f"{datetime.now().strftime('%B %d, %Y')}")
    canvas.setFillColor(_color(SLATE))
    canvas.roundRect(0.5 * inch, 0.35 * inch, doc.pagesize[0] - 1.0 * inch, 0.12 * inch, 3, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(0.6 * inch, 0.39 * inch,
                      f"Generated by AnZlyze  •  Page {canvas.getPageNumber()}")
    canvas.setFillColor(_color(PRIMARY_LIGHT))
    canvas.setFont("Helvetica", 6.5)
    canvas.drawRightString(doc.pagesize[0] - 0.6 * inch, 0.39 * inch,
                           "Proprietary & confidential")
    canvas.restoreState()


def _pdf_blank_page(canvas, doc):
    """Clean cover page — no header/footer so the logo never overlaps lettering."""
    pass


def generate_pdf(results_data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title="AnZlyze Analysis Report", author="AnZlyze",
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=24, textColor=_color(INK),
                        spaceAfter=2, spaceBefore=0)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=15, textColor=_color(PRIMARY),
                        spaceBefore=10, spaceAfter=8)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11.5, textColor=_color(INK),
                        spaceBefore=14, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=14, textColor=_color(INK))
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=11, textColor=_color(SLATE))
    white_bold = ParagraphStyle("whiteBold", parent=styles["Normal"], fontSize=9.5,
                                textColor=WHITE, fontName="Helvetica-Bold")
    muted = ParagraphStyle("muted", parent=styles["Normal"], fontSize=9, textColor=_color(SLATE))

    analysis = results_data.get("analysis", {})
    results = results_data.get("results", {})
    dist = results.get("sentiment_distribution", {})
    total = dist.get("total", 0)
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    neu = dist.get("neutral", 0)

    # ── COVERSHEET ─────────────────────────────────────────
    elements = []
    elements.append(Spacer(1, 1.0 * inch))
    elements.append(Paragraph("AnZlyze", ParagraphStyle(
        "c_over", parent=h1, fontSize=42, leading=54, textColor=_color(PRIMARY),
        spaceAfter=6, spaceBefore=0)))
    elements.append(Paragraph("Customer Review Intelligence Report",
                              ParagraphStyle("c_sub", parent=h1, fontSize=16, leading=24,
                                             textColor=_color(INK), spaceAfter=12)))
    elements.append(Spacer(1, 0.06 * inch))
    elements.append(HRFlowable(width="100%", thickness=2, color=_color(PRIMARY_LIGHT)))
    elements.append(Spacer(1, 0.5 * inch))

    cover_info = [
        ("Dataset", analysis.get("filename", "")),
        ("Reviews Analyzed", str(total)),
        ("Text Column", analysis.get("text_column") or "—"),
        ("Rating Column", analysis.get("rating_column") or "—"),
        ("Generated On", datetime.now().strftime("%B %d, %Y at %H:%M")),
        ("Prepared For", "Customer Experience Team"),
    ]
    cover_rows = [[Paragraph(k, muted), Paragraph(v, styles["Normal"])] for k, v in cover_info]
    cover_tbl = Table(cover_rows, colWidths=[1.6 * inch, 4.6 * inch])
    cover_tbl.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _color("E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(cover_tbl)

    # Overall verdict callout on the cover
    overall = (results.get("recommendations", {}).get("overall_sentiment") or "neutral").title()
    overall_color = {"Positive": POSITIVE, "Negative": NEGATIVE, "Neutral": NEUTRAL}.get(overall, SLATE)
    verdict = Table(
        [[Paragraph(
            f'<font size="10" color="{SLATE}">Overall customer sentiment</font><br/>'
            f'<font size="15" color="{overall_color}" fontName="Helvetica-Bold">{overall}</font>',
            body)]],
        colWidths=[6.2 * inch],
    )
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _color("F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, _color("E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(Spacer(1, 16))
    elements.append(verdict)
    elements.append(Paragraph(
        "This report was generated automatically by AnZlyze based on machine-learning "
        "analysis of the uploaded review dataset. Figures are for planning purposes and "
        "should be validated against primary sources before strategic decisions.",
        ParagraphStyle("discl", parent=muted, fontSize=7.5, leading=10, textColor=_color("94A3B8"))),
    )
    elements.append(PageBreak())

    # ── EXECUTIVE SUMMARY ─────────────────────────────────
    elements.append(Paragraph("Executive Summary", h1))
    elements.append(Spacer(1, 10))

    # KPI band
    kpis = [
        ("Positive", pos, f"{pos / max(total, 1) * 100:.1f}%", _color(POSITIVE)),
        ("Negative", neg, f"{neg / max(total, 1) * 100:.1f}%", _color(NEGATIVE)),
        ("Neutral", neu, f"{neu / max(total, 1) * 100:.1f}%", _color(NEUTRAL)),
        ("Total Reviews", total, "", _color(PRIMARY)),
    ]
    kpi_cells = []
    for label, value, sub, accent in kpis:
        inner_tbl = Table([
            [Paragraph(str(value), ParagraphStyle("v", parent=styles["Normal"], fontSize=18,
                                                  textColor=accent, fontName="Helvetica-Bold"))],
            [Paragraph(label, ParagraphStyle("l", parent=styles["Normal"], fontSize=8, textColor=_color(SLATE)))],
            [Paragraph(sub, ParagraphStyle("s", parent=styles["Normal"], fontSize=7.5, textColor=_color(SLATE)))],
        ], colWidths=[1.7 * inch])
        inner_tbl.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("BACKGROUND", (0, 0), (-1, -1), _color(BG_ALT)),
        ]))
        kpi_cells.append(inner_tbl)
    kpi_band = Table([kpi_cells], colWidths=[1.7 * inch] * 4)
    kpi_band.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_band)
    elements.append(Spacer(1, 14))

    exec_text = results.get("recommendations", {}).get("summary") or ""
    elements.append(Paragraph("Key Findings", h2))
    for line in exec_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") or line.startswith("Executive"):
            elements.append(Paragraph(f"<b>{line}</b>", body))
        else:
            elements.append(Paragraph(f"• &nbsp;{line}", body))
        elements.append(Spacer(1, 3))
    elements.append(Spacer(1, 8))

    # Sentiment bar chart
    elements.append(Paragraph("Sentiment Breakdown", h2))
    draw = Drawing(400, 200)
    pie = RLPie()
    pie.x = 40
    pie.y = 20
    pie.width = 150
    pie.height = 150
    pie.data = [pos, neg, neu]
    pie.labels = [f"Positive {p/1.0}%" for p in []]
    pie.slices.strokeWidth = 1
    pie.slices[0].fillColor = _color(POSITIVE)
    pie.slices[1].fillColor = _color(NEGATIVE)
    pie.slices[2].fillColor = _color(NEUTRAL)
    pie.slices[0].strokeColor = colors.white
    pie.slices[1].strokeColor = colors.white
    pie.slices[2].strokeColor = colors.white
    pie.slices.labelRadius = 0.72
    pie.simpleLabels = 0
    draw.add(pie)

    # legend
    leg = Legend()
    leg.x = 230
    leg.y = 150
    leg.alignment = "right"
    leg.dx = 8
    leg.dy = 12
    leg.fontName = "Helvetica"
    leg.fontSize = 9
    leg.strokeWidth = 0
    leg.colorNamePairs = [
        (_color(POSITIVE), f"Positive  {pos}  ({pos / max(total, 1) * 100:.1f}%)"),
        (_color(NEGATIVE), f"Negative  {neg}  ({neg / max(total, 1) * 100:.1f}%)"),
        (_color(NEUTRAL), f"Neutral  {neu}  ({neu / max(total, 1) * 100:.1f}%)"),
    ]
    draw.add(leg)
    elements.append(draw)
    elements.append(Spacer(1, 10))

    # ── SUMMARY TABLE ─────────────────────────────────────
    summary_data = [
        [Paragraph("<b>Metric</b>", white_bold), Paragraph("<b>Value</b>", white_bold)],
        ["Dataset", analysis.get("filename", "")],
        ["Total Reviews", str(total)],
        ["Best Model", (results.get("best_model") or "").replace("_", " ").title()],
        ["Model Accuracy", f"{results.get('best_accuracy', 0) * 100:.1f}%"],
        ["Overall Sentiment", (results.get("recommendations", {}).get("overall_sentiment") or "—").title()],
        ["Spam Flagged", f"{results.get('spam_summary', {}).get('total_flagged', 0)}"
                         f" ({results.get('spam_summary', {}).get('flagged_percentage', 0)}%)"],
    ]
    st = Table(summary_data, colWidths=[2.2 * inch, 4.0 * inch])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _color(PRIMARY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, _color("E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, _color(BG_ALT)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 1), (-1, -1), 9.5),
    ]))
    elements.append(st)
    elements.append(PageBreak())

    # ── PROBLEMS ──────────────────────────────────────────
    problems = results.get("problems", {}).get("problems", [])
    if problems:
        elements.append(Paragraph("Detected Problem Categories", h1))
        elements.append(Spacer(1, 6))
        prob_data = [[Paragraph("<b>Category</b>", white_bold),
                      Paragraph("<b>Severity</b>", white_bold),
                      Paragraph("<b>Frequency</b>", white_bold),
                      Paragraph("<b>% Negative</b>", white_bold),
                      Paragraph("<b>Example Review</b>", white_bold)]]
        for p in problems:
            ex = (p.get("examples") or [""])[0][:140]
            prob_data.append([
                Paragraph(p.get("category", ""), body),
                Paragraph((p.get("severity") or "").upper(),
                          ParagraphStyle("sev", parent=body, textColor=_color(
                              NEGATIVE if (p.get("severity") in ("high", "critical")) else
                              (NEUTRAL if p.get("severity") == "medium" else POSITIVE)))),
                Paragraph(str(p.get("frequency", 0)), body),
                Paragraph(f"{p.get('percentage', 0)}%", body),
                Paragraph(ex, small),
            ])
        pt = Table(prob_data, colWidths=[1.5 * inch, 0.8 * inch, 0.9 * inch, 0.9 * inch, 2.1 * inch])
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _color(PRIMARY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.4, _color("E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, _color(BG_ALT)]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(pt)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            "* Severity is derived from how often a category appears across negative reviews.", small))
        elements.append(PageBreak())

    # ── RECOMMENDATIONS ───────────────────────────────────
    recs = results.get("recommendations", {}).get("recommendations", [])
    if recs:
        elements.append(Paragraph("Strategic Recommendations", h1))
        elements.append(Spacer(1, 8))
        for r in recs:
            prio = (r.get("priority") or "").upper()
            prio_color = {"CRITICAL": NEGATIVE, "HIGH": NEGATIVE, "MEDIUM": NEUTRAL, "LOW": POSITIVE}.get(prio, SLATE)
            badge = Table([[Paragraph(f"{prio}", ParagraphStyle(
                "prio", parent=white_bold, textColor=_color(prio_color)))]], colWidths=[0.9 * inch])
            badge.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _color(prio_color)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            title_tbl = Table([[badge, Paragraph(f"<b>{r.get('title', '')}</b>", h3)]],
                              colWidths=[1.0 * inch, 5.2 * inch])
            title_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
            elements.append(title_tbl)
            elements.append(Paragraph(f"<font color='{SLATE}'><i>{r.get('impact', '')}</i></font>", body))
            for s in (r.get("suggestions") or [])[:4]:
                elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;• &nbsp;{s}", body))
            elements.append(Spacer(1, 10))

    # ── CLUSTER THEMES ────────────────────────────────────
    clusters = results.get("cluster_summary", []) or []
    if clusters:
        elements.append(PageBreak())
        elements.append(Paragraph("Emerging Review Themes", h1))
        elements.append(Spacer(1, 6))
        cl_data = [[Paragraph("<b>Theme</b>", white_bold),
                    Paragraph("<b>Reviews</b>", white_bold),
                    Paragraph("<b>Share</b>", white_bold)]]
        total_cl = sum(c.get("count", 0) for c in clusters)
        for c in clusters:
            cnt = c.get("count", 0)
            cl_data.append([
                Paragraph(str(c.get("label") or c.get("cluster") or "Theme"), body),
                Paragraph(str(cnt), body),
                Paragraph(f"{cnt / max(total_cl, 1) * 100:.1f}%", body),
            ])
        ct = Table(cl_data, colWidths=[3.4 * inch, 1.4 * inch, 1.4 * inch])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _color(PRIMARY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.4, _color("E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, _color(BG_ALT)]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 8))

    # ── MODEL COMPARISON ──────────────────────────────────
    model_results = results.get("model_results", {})
    if model_results:
        elements.append(Paragraph("Model Performance Comparison", h1))
        elements.append(Spacer(1, 6))
        m_data = [[Paragraph("<b>Model</b>", white_bold), Paragraph("<b>Accuracy</b>", white_bold)]]
        for name, info in sorted(model_results.items(), key=lambda x: x[1].get("accuracy", 0), reverse=True):
            acc = info.get("accuracy", 0)
            m_data.append([Paragraph(name.replace("_", " ").title(), body),
                           Paragraph(f"{acc * 100:.1f}%", body)])
        mt = Table(m_data, colWidths=[4.0 * inch, 2.0 * inch])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _color(PRIMARY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.4, _color("E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, _color(BG_ALT)]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(mt)

    doc.build(elements, onFirstPage=_pdf_blank_page, onLaterPages=_pdf_header_footer)
    buf.seek(0)
    return buf.read()
