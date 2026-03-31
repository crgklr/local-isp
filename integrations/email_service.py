"""Marcus email service - sends scored suggestions and receives replies.

Supports SendGrid (preferred) with SMTP fallback. Inbound reply parsing via IMAP.
"""

from __future__ import annotations

import email
import imaplib
import json
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx
from config.settings import (
    SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO,
    IMAP_HOST, IMAP_USER, IMAP_PASSWORD,
)


def send_suggestions_email(report: dict) -> dict:
    clusters = report.get("clusters", [])
    scan_date = report.get("scan_date", datetime.now().strftime("%Y-%m-%d"))
    top_pick = report.get("top_pick", {})
    subject = f"Marcus: Content opportunities for {scan_date}"
    html_body = _build_suggestions_html(clusters, top_pick, scan_date)
    text_body = _build_suggestions_text(clusters, top_pick, scan_date)
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(subject, html_body, text_body)
    return _send_via_smtp(subject, html_body, text_body)


def _build_suggestions_html(clusters: list, top_pick: dict, scan_date: str) -> str:
    html = f"""<html><body style="font-family: Arial, sans-serif; max-width: 680px; margin: 0 auto; color: #333;">
<h2 style="color: #1a5276;">Marcus here. Your daily content opportunities for {scan_date}.</h2>
<p style="color: #666; font-size: 14px;">I scanned the competitive landscape and scored each opportunity by how much it would help DWC's distributor customers.
Reply with the <strong>number</strong> of the topic you'd like me to write.</p>"""

    if top_pick and top_pick.get("title"):
        tp_score = top_pick.get("value_score", top_pick.get("total_score", "?"))
        html += f"""
<div style="background: #eaf2f8; border-left: 4px solid #2980b9; padding: 16px; margin: 20px 0;">
<p style="margin: 0 0 4px 0; font-size: 12px; color: #2980b9; font-weight: bold;">MY TOP PICK (Value: {tp_score}/100)</p>
<p style="margin: 0; font-size: 16px; font-weight: bold;">{top_pick.get('title', '')}</p>
<p style="margin: 4px 0 0 0; font-size: 13px; color: #666;">
Keyword: <strong>{top_pick.get('primary_keyword', '')}</strong> |
Volume: {top_pick.get('volume', '?')} |
KD: {top_pick.get('difficulty', '?')} |
Traffic Potential: {top_pick.get('traffic_potential', '?')}</p></div>"""

    for i, cluster in enumerate(clusters, 1):
        rec = cluster.get("recommended_topic", {})
        existing = cluster.get("existing_dwc_content", [])
        additional = cluster.get("additional_keywords", [])
        existing_str = f'<br><span style="font-size: 12px; color: #888;">Expands cluster with: {", ".join(existing[:3])}</span>' if existing else ""
        additional_str = f'<br><span style="font-size: 12px; color: #888;">Also targets: {", ".join(additional[:4])}</span>' if additional else ""

        value_score = rec.get("value_score", rec.get("total_score", 0))
        if value_score >= 75:
            badge_color = "#27ae60"
            badge_label = "HIGH VALUE"
        elif value_score >= 50:
            badge_color = "#f39c12"
            badge_label = "MEDIUM VALUE"
        else:
            badge_color = "#e74c3c"
            badge_label = "LOW VALUE"
        value_badge = f'<span style="background: {badge_color}; color: white; font-size: 11px; padding: 2px 8px; border-radius: 3px; margin-left: 8px;">{badge_label} ({value_score}/100)</span>'

        html += f"""
<div style="border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 12px 0;">
<p style="margin: 0 0 2px 0; font-size: 12px; color: #999; text-transform: uppercase;">{cluster.get('cluster_name', '')}</p>
<p style="margin: 0; font-size: 16px;">
<strong style="color: #2980b9; font-size: 20px; margin-right: 8px;">{i}.</strong>
<strong>{rec.get('title', 'Untitled')}</strong>{value_badge}</p>
<p style="margin: 6px 0 0 0; font-size: 13px; color: #555;">
Keyword: <strong>{rec.get('primary_keyword', '')}</strong> |
Volume: {rec.get('volume', '?')} | KD: {rec.get('difficulty', '?')} | TP: {rec.get('traffic_potential', '?')}</p>
<p style="margin: 6px 0 0 0; font-size: 13px; color: #555; font-style: italic;">{rec.get('rationale', '')}</p>
{existing_str}{additional_str}</div>"""

    html += """
<div style="background: #f9f9f9; padding: 16px; margin-top: 24px; border-radius: 6px;">
<p style="margin: 0; font-size: 14px; color: #555;">
<strong>To pick a topic:</strong> Reply with just the number (e.g., "2")
or the number followed by notes (e.g., "3 - focus on NEC compliance angle").</p></div>
<p style="margin-top: 16px; font-size: 12px; color: #999;">- Marcus</p>
</body></html>"""
    return html


def _build_suggestions_text(clusters: list, top_pick: dict, scan_date: str) -> str:
    lines = [f"Marcus here. Content opportunities for {scan_date}.", "=" * 50, "",
             "Reply with the NUMBER of the topic you'd like me to write.", ""]
    if top_pick and top_pick.get("title"):
        tp_score = top_pick.get("value_score", top_pick.get("total_score", "?"))
        lines.extend([f"MY TOP PICK (Value: {tp_score}/100): {top_pick.get('title', '')}",
                       f"  Keyword: {top_pick.get('primary_keyword', '')} | Vol: {top_pick.get('volume', '?')} | KD: {top_pick.get('difficulty', '?')}", ""])
    for i, cluster in enumerate(clusters, 1):
        rec = cluster.get("recommended_topic", {})
        score = rec.get("value_score", rec.get("total_score", "?"))
        lines.extend([f"{i}. [{cluster.get('cluster_name', '')}] {rec.get('title', 'Untitled')} (Value: {score}/100)",
                       f"   Keyword: {rec.get('primary_keyword', '')} | Vol: {rec.get('volume', '?')} | KD: {rec.get('difficulty', '?')}",
                       f"   {rec.get('rationale', '')}", ""])
    lines.extend(["-" * 50, "Reply with just a number (e.g., '2') to select a topic.", "", "- Marcus"])
    return "\n".join(lines)


def _send_via_sendgrid(subject: str, html: str, text: str) -> dict:
    with httpx.Client(timeout=15) as c:
        resp = c.post("https://api.sendgrid.com/v3/mail/send",
                       headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
                       json={"personalizations": [{"to": [{"email": EMAIL_TO}]}],
                             "from": {"email": EMAIL_FROM, "name": "Marcus by DWC"},
                             "subject": subject,
                             "content": [{"type": "text/plain", "value": text}, {"type": "text/html", "value": html}]})
    return {"status": "sent" if resp.status_code in (200, 202) else "failed", "status_code": resp.status_code, "method": "sendgrid"}


def _send_via_smtp(subject: str, html: str, text: str) -> dict:
    if not IMAP_HOST or not IMAP_USER:
        return {"status": "skipped", "reason": "No email credentials configured"}
    smtp_host = IMAP_HOST.replace("imap.", "smtp.")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Marcus by DWC <{EMAIL_FROM}>"
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL(smtp_host, 465) as server:
            server.login(IMAP_USER, IMAP_PASSWORD)
            server.send_message(msg)
        return {"status": "sent", "method": "smtp"}
    except Exception as e:
        return {"status": "failed", "error": str(e), "method": "smtp"}


def send_completion_email(article_title: str, article_slug: str, contentful_result: dict) -> dict:
    entry_id = contentful_result.get("entry_id", "N/A")
    status = contentful_result.get("status", "unknown")
    subject = f"Marcus: Draft ready for review - {article_title}"
    html = f"""<html><body style="font-family: Arial, sans-serif; max-width: 680px; margin: 0 auto;">
<h2 style="color: #27ae60;">Marcus here. Your article draft is ready.</h2>
<div style="background: #eafaf1; border-left: 4px solid #27ae60; padding: 16px; margin: 20px 0;">
<p style="margin: 0; font-size: 18px; font-weight: bold;">{article_title}</p>
<p style="margin: 8px 0 0 0; font-size: 14px; color: #555;">
Slug: <code>{article_slug}</code><br>
Contentful Status: <strong>{status}</strong><br>
Entry ID: <code>{entry_id}</code></p></div>
<p style="font-size: 14px; color: #555;">
I've published this as a <strong>draft</strong> in Contentful. Log in to review, edit, and publish when you're ready.</p>
<p style="margin-top: 16px; font-size: 12px; color: #999;">- Marcus</p>
</body></html>"""
    text = f"Marcus here. Draft ready: {article_title}\nSlug: {article_slug}\nContentful: {status} (ID: {entry_id})"
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(subject, html, text)
    return _send_via_smtp(subject, html, text)


def poll_for_reply(since_minutes: int = 30) -> Optional[dict]:
    if not IMAP_HOST or not IMAP_USER:
        return None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")
        since_date = (datetime.now() - timedelta(minutes=since_minutes)).strftime("%d-%b-%Y")
        _, message_ids = mail.search(None, f'(FROM "{EMAIL_TO}" SUBJECT "Re: Marcus" SINCE {since_date})')
        if not message_ids[0]:
            mail.logout()
            return None
        latest_id = message_ids[0].split()[-1]
        _, msg_data = mail.fetch(latest_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        reply_text = re.split(r"\nOn .+wrote:", body)[0].strip()
        lines = []
        for line in reply_text.split("\n"):
            if line.startswith(">"):
                break
            lines.append(line)
        reply_text = "\n".join(lines).strip()
        mail.store(latest_id, "+FLAGS", "\\Seen")
        mail.logout()
        return _parse_reply(reply_text)
    except Exception:
        return None


def _parse_reply(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    match = re.match(r"(\d+)\s*[-:.]?\s*(.*)", text, re.DOTALL)
    if match:
        return {"selection": int(match.group(1)), "notes": match.group(2).strip()}
    numbers = re.findall(r"\b(\d+)\b", text)
    if numbers:
        return {"selection": int(numbers[0]), "notes": text}
    return None
