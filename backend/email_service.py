"""
Email service: Send polished, business-grade analysis reports via email.
Builds a responsive branded HTML body and attaches the generated PDF / Excel
reports so recipients get a ready-to-share deliverable.
"""
import os
import smtplib
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from export_service import generate_pdf, generate_excel

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_NAME = os.environ.get("FROM_NAME", "AnZlyze")

# Brand palette (matches the app + Excel/PDF)
PRIMARY = "#6C5CE7"
PRIMARY_LIGHT = "#A78BFA"
POSITIVE = "#00D2A0"
NEGATIVE = "#FF6B6B"
NEUTRAL = "#FECA57"


def _pct(count, total):
    return round(count / max(total, 1) * 100, 1)


def build_html_body(results_data: dict) -> str:
    analysis = results_data.get("analysis", {})
    results = results_data.get("results", {})
    dist = results.get("sentiment_distribution", {})
    total = dist.get("total", 0)
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    neu = dist.get("neutral", 0)
    pos_pct = _pct(pos, total)
    neg_pct = _pct(neg, total)
    neu_pct = _pct(neu, total)

    filename = analysis.get("filename", "Analysis")
    best_model = (results.get("best_model") or "").replace("_", " ").title()
    accuracy = results.get("best_accuracy", 0) * 100
    spam = results.get("spam_summary", {})
    recs_data = results.get("recommendations", {})
    overall = (recs_data.get("overall_sentiment") or "neutral").title()
    recs = recs_data.get("recommendations", [])
    problems = results.get("problems", {}).get("problems", [])

    # Sentiment horizontal bars
    def _bar(pct, color, label):
        return f"""
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;font-size:13px;color:#475569;margin-bottom:5px;">
            <span style="font-weight:600;">{label}</span>
            <span style="font-weight:700;color:{color};">{pct}%</span>
          </div>
          <div style="background:#EEF2F7;border-radius:8px;height:10px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:8px;"></div>
          </div>
        </div>"""

    # KPI stat card
    def _stat(label, value, sub, color):
        return f"""
        <td style="padding:6px;width:25%;">
          <div style="background:#FFFFFF;border:1px solid #EAE5FF;border-radius:12px;padding:14px 8px;text-align:center;">
            <div style="font-size:26px;font-weight:800;color:{color};line-height:1.1;">{value}</div>
            <div style="font-size:11px;font-weight:700;color:#334155;margin-top:2px;letter-spacing:.3px;">{label}</div>
            <div style="font-size:10px;color:#94A3B8;margin-top:2px;">{sub}</div>
          </div>
        </td>"""

    problem_html = ""
    if problems:
        problem_items = ""
        for p in problems[:6]:
            sev = (p.get("severity") or "medium").upper()
            sev_col = {
                "CRITICAL": NEGATIVE, "HIGH": NEGATIVE,
                "MEDIUM": NEUTRAL, "LOW": POSITIVE,
            }.get(sev, "#94A3B8")
            ex = (p.get("examples") or [""])[0][:160]
            problem_items += f"""
            <tr style="border-bottom:1px solid #EEF2F7;">
              <td style="padding:12px 6px;font-size:13px;color:#1E293B;font-weight:600;">{p.get('category','')}</td>
              <td style="padding:12px 6px;text-align:center;">
                <span style="background:{sev_col}1A;color:{sev_col};font-size:11px;font-weight:700;padding:3px 8px;border-radius:20px;">{sev}</span>
              </td>
              <td style="padding:12px 6px;text-align:center;font-size:13px;color:#475569;">{p.get('frequency',0)}</td>
              <td style="padding:12px 6px;text-align:center;font-size:13px;color:#475569;">{p.get('percentage',0)}%</td>
            </tr>"""
        problem_html = f"""
        <h2 style="color:#1E293B;font-size:17px;margin:28px 0 12px;">Key Problem Areas</h2>
        <table style="width:100%;border-collapse:collapse;background:#FFFFFF;border-radius:12px;overflow:hidden;border:1px solid #EEF2F7;">
          <tr style="background:#6C5CE7;color:#FFFFFF;">
            <th style="padding:10px 6px;font-size:12px;text-align:left;">Category</th>
            <th style="padding:10px 6px;font-size:12px;">Severity</th>
            <th style="padding:10px 6px;font-size:12px;">Freq</th>
            <th style="padding:10px 6px;font-size:12px;">% Neg</th>
          </tr>
          {problem_items}
        </table>"""

    rec_html = ""
    if recs:
        rec_items = ""
        for r in recs[:5]:
            prio = (r.get("priority") or "medium").upper()
            rec_items += f"""
            <div style="background:#FFFFFF;border-left:4px solid {PRIMARY};border-radius:10px;padding:14px 16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
              <div style="font-size:13px;color:#64748B;margin-bottom:4px;">
                <span style="background:{PRIMARY};color:#FFFFFF;font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;letter-spacing:.5px;">{prio}</span>
                <span style="margin-left:8px;font-weight:600;color:{PRIMARY};">{r.get('problem_category','')}</span>
              </div>
              <div style="font-size:14px;font-weight:700;color:#1E293B;">{r.get('title','')}</div>
              <div style="font-size:12.5px;color:#475569;margin-top:5px;line-height:1.5;">{r.get('impact','')}</div>
            </div>"""
        rec_html = f"""
        <h2 style="color:#1E293B;font-size:17px;margin:28px 0 12px;">Recommended Actions</h2>
        {rec_items}"""

    spam_line = ""
    if spam.get("total_flagged"):
        spam_line = f"""<tr>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#64748B;">Reviews Flagged as Spam</td>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#1E293B;font-weight:700;text-align:right;">
              {spam.get('total_flagged',0)} ({spam.get('flagged_percentage',0)}%)</td></tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>AnZlyze Report: {filename}</title></head>
<body style="margin:0;padding:0;background:#F4F6FB;">
  <!-- Preheader (invisible) -->
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">
    Sentiment {pos_pct}% positive • {neg_pct}% negative • {total} reviews analyzed. Ready to share with your team.
  </div>
  <div style="max-width:600px;margin:0 auto;background:#FFFFFF;font-family:'Segoe UI',Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#6C5CE7 0%,#8B7CF7 50%,#A78BFA 100%);padding:34px 32px;text-align:center;">
      <div style="display:inline-block;background:#FFFFFF;border-radius:14px;padding:6px 18px;margin-bottom:14px;">
        <span style="font-size:22px;font-weight:800;background:linear-gradient(90deg,#6C5CE7,#00D2A0);-webkit-background-clip:text;background-clip:text;color:transparent;">AnZlyze</span>
      </div>
      <div style="font-size:22px;font-weight:800;color:#FFFFFF;">Customer Review Intelligence Report</div>
      <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px;">{filename}</div>
      <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:16px;">Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}</div>
    </div>

    <!-- KPI band -->
    <div style="margin:-26px 20px 0;background:#FFFFFF;border-radius:16px;box-shadow:0 8px 24px rgba(108,92,231,.12);border:1px solid #EEF2F7;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          {_stat("Positive", pos, f"{pos_pct}%", POSITIVE)}
          {_stat("Negative", neg, f"{neg_pct}%", NEGATIVE)}
          {_stat("Neutral", neu, f"{neu_pct}%", NEUTRAL)}
          {_stat("Total", total, "reviews", PRIMARY)}
        </tr>
      </table>
    </div>

    <div style="padding:24px 32px 30px;">

      <!-- Overall verdict highlight -->
      <div style="background:#F8F9FE;border:1px solid #E6E1FF;border-radius:12px;padding:16px 18px;margin-top:6px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div>
          <div style="font-size:12px;font-weight:700;color:#64748B;letter-spacing:.4px;">OVERALL CUSTOMER SENTIMENT</div>
          <div style="font-size:18px;font-weight:800;color:#1E293B;margin-top:2px;">{overall}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12px;color:#64748B;">Best model</div>
          <div style="font-size:15px;font-weight:800;color:{PRIMARY};">{best_model} &middot; {accuracy:.1f}%</div>
        </div>
      </div>

      <!-- Summary -->
      <h2 style="color:#1E293B;font-size:17px;margin:24px 0 4px;">Executive Summary</h2>
      <div style="font-size:13.5px;color:#475569;line-height:1.65;margin-top:8px;">{ (recs_data.get('summary') or '').replace(chr(10), '<br>') }</div>

      <h2 style="color:#1E293B;font-size:17px;margin:24px 0 4px;">Sentiment Breakdown</h2>
      <div style="background:#F8F9FE;border-radius:12px;padding:18px 18px 10px;margin-top:8px;">
        {_bar(pos_pct, POSITIVE, "Positive")}
        {_bar(neg_pct, NEGATIVE, "Negative")}
        {_bar(neu_pct, NEUTRAL, "Neutral")}
      </div>

      {problem_html}
      {rec_html}

      <!-- Report details -->
      <h2 style="color:#1E293B;font-size:17px;margin:24px 0 12px;">Report Details</h2>
      <table style="width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #EEF2F7;border-radius:12px;overflow:hidden;">
        <tr><td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#64748B;background:#F8F9FE;">Best Model</td>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#1E293B;font-weight:700;text-align:right;">{best_model}</td></tr>
        <tr><td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#64748B;background:#F8F9FE;">Model Accuracy</td>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#1E293B;font-weight:700;text-align:right;">{accuracy:.1f}%</td></tr>
        <tr><td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#64748B;background:#F8F9FE;">Overall Sentiment</td>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#1E293B;font-weight:700;text-align:right;">{overall}</td></tr>
        <tr><td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#64748B;background:#F8F9FE;">Reviews Analyzed</td>
            <td style="padding:9px 14px;border-bottom:1px solid #EEF2F7;font-size:13px;color:#1E293B;font-weight:700;text-align:right;">{total}</td></tr>{spam_line}
      </table>

      <!-- CTA -->
      <div style="text-align:center;margin:30px 0 10px;">
        <a href="#" style="display:inline-block;background:linear-gradient(135deg,#6C5CE7,#8B7CF7);color:#FFFFFF;font-size:14px;font-weight:700;padding:13px 34px;border-radius:30px;text-decoration:none;">View Full Report</a>
      </div>

      <!-- Footer / confidentiality -->
      <div style="border-top:1px solid #EEF2F7;margin-top:24px;padding-top:16px;color:#94A3B8;font-size:11px;line-height:1.6;">
        <p style="margin:0 0 6px;">This message was generated by <strong>AnZlyze</strong> and includes attached PDF &amp; Excel reports ready for sharing and presentation.</p>
        <p style="margin:0 0 6px;"><strong>Confidentiality notice:</strong> This e-mail and any attachments are confidential and intended solely for the addressee. If you are not the intended recipient, please notify the sender and delete this message.</p>
        <p style="margin:0;">&copy; {datetime.now().year} AnZlyze &middot; Customer Review Intelligence Platform</p>
      </div>
    </div>
  </div>
</body>
</html>
"""


def send_report_email(to_email: str, analysis_id: str, results_data: dict, formats=("pdf",)) -> bool:
    """Send the branded report email with generated PDF/Excel attachments.

    formats: tuple of one or more of ("pdf", "excel") to attach.
    """
    if not SMTP_USER or not SMTP_PASS:
        raise ValueError("SMTP credentials not configured. Set SMTP_USER and SMTP_PASS in .env")

    analysis = results_data.get("analysis", {})
    results = results_data.get("results", {})

    subject = f"AnZlyze Report: {analysis.get('filename', 'Analysis')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email

    html_body = build_html_body(results_data)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    base_name = (analysis.get("filename") or "analysis").rsplit(".", 1)[0]
    base_name = "".join(c for c in base_name if c.isalnum() or c in " _-")[:40].strip() or "analysis"

    # Attach requested report files as a nested multipart/mixed at top level.
    # Use a top-level MIMEMultipart("mixed") that contains the alternative body.
    mixed = MIMEMultipart("mixed")
    mixed["Subject"] = subject
    mixed["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    mixed["To"] = to_email
    mixed.attach(msg)

    if "pdf" in formats:
        try:
            pdf_bytes = generate_pdf(results_data)
            att_pdf = MIMEApplication(pdf_bytes, _subtype="pdf")
            att_pdf.add_header("Content-Disposition",
                               "attachment",
                               filename=f"{base_name}_report.pdf")
            mixed.attach(att_pdf)
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Failed to generate PDF attachment: {e}") from e

    if "excel" in formats:
        try:
            xlsx_bytes = generate_excel(results_data)
            att_xlsx = MIMEApplication(
                xlsx_bytes,
                _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            att_xlsx.add_header("Content-Disposition",
                                "attachment",
                                filename=f"{base_name}_report.xlsx")
            mixed.attach(att_xlsx)
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Failed to generate Excel attachment: {e}") from e

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], mixed.as_string())

    return True
