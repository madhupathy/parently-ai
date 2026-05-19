"""Async email delivery service for Parently digest notifications.

Uses aiosmtplib for non-blocking SMTP and Jinja2 for HTML rendering.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

import aiosmtplib
from jinja2 import Environment, select_autoescape

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inline HTML template (avoids a templates/ directory dependency)
# ---------------------------------------------------------------------------

_DIGEST_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ subject }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f8fafc; margin: 0; padding: 0; color: #1e293b; }
    .wrapper { max-width: 600px; margin: 32px auto; background: #ffffff;
               border-radius: 12px; overflow: hidden;
               box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .header { background: #6366f1; padding: 28px 32px; color: #ffffff; }
    .header h1 { margin: 0; font-size: 22px; font-weight: 700; }
    .header p { margin: 4px 0 0; font-size: 14px; opacity: 0.85; }
    .body { padding: 28px 32px; }
    .section-title { font-size: 13px; font-weight: 600; text-transform: uppercase;
                     letter-spacing: 0.06em; color: #6366f1; margin: 20px 0 8px; }
    .digest-prose { font-size: 15px; line-height: 1.7; white-space: pre-wrap; }
    .action-items { list-style: none; padding: 0; margin: 0; }
    .action-items li { padding: 10px 14px; margin-bottom: 8px; border-radius: 8px;
                       background: #f1f5f9; font-size: 14px; }
    .action-items li.high { border-left: 4px solid #ef4444; }
    .action-items li.medium { border-left: 4px solid #f59e0b; }
    .action-items li.low { border-left: 4px solid #10b981; }
    .due-date { font-size: 12px; color: #64748b; margin-top: 2px; }
    .event-items { list-style: none; padding: 0; margin: 0; }
    .event-items li { padding: 10px 14px; margin-bottom: 8px; border-radius: 8px;
                      background: #f0fdf4; border-left: 4px solid #22c55e; font-size: 14px; }
    .footer { padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0;
              text-align: center; font-size: 12px; color: #94a3b8; }
    .footer a { color: #6366f1; text-decoration: none; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>📚 {{ child_name }}'s School Update</h1>
      <p>{{ digest_date }}</p>
    </div>
    <div class="body">
      {% if action_items %}
      <div class="section-title">Action Items</div>
      <ul class="action-items">
        {% for item in action_items %}
        <li class="{{ item.priority or 'low' }}">
          <strong>{{ item.title }}</strong>
          {% if item.summary %}<br />{{ item.summary }}{% endif %}
          {% if item.due_at %}<div class="due-date">Due: {{ item.due_at }}</div>{% endif %}
        </li>
        {% endfor %}
      </ul>
      {% endif %}

      {% if event_items %}
      <div class="section-title">Upcoming Events</div>
      <ul class="event-items">
        {% for item in event_items %}
        <li>
          <strong>{{ item.title }}</strong>
          {% if item.due_at %}<div class="due-date">{{ item.due_at }}</div>{% endif %}
        </li>
        {% endfor %}
      </ul>
      {% endif %}

      {% if digest_prose %}
      <div class="section-title">Full Digest</div>
      <div class="digest-prose">{{ digest_prose }}</div>
      {% endif %}
    </div>
    <div class="footer">
      <p>You're receiving this because you enabled email notifications in Parently.</p>
      <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> &nbsp;|&nbsp;
         <a href="{{ app_url }}">Open Parently</a></p>
    </div>
  </div>
</body>
</html>
"""

# Jinja2 environment used for rendering the inline template via from_string().
_jinja_env = Environment(autoescape=select_autoescape(["html"]))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def send_digest_email(user_email: str, digest: Dict[str, Any], child_name: str) -> bool:
    """Send digest via SMTP. Returns True on success, False on failure.

    Args:
        user_email: Recipient address.
        digest: Dict containing at minimum ``digest_markdown`` and ``items_json``.
        child_name: First child's name, used in the subject line.

    Environment variables consumed:
        SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL (or SMTP_FROM),
        SMTP_FROM_NAME, FRONTEND_APP_URL.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_FROM", "noreply@parently.app")
    from_name = os.environ.get("SMTP_FROM_NAME", "Parently")
    app_url = os.environ.get("FRONTEND_APP_URL", "https://parently-ai.com")

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning("SMTP not configured — skipping email for %s", user_email)
        return False

    today_str: str = digest.get("digest_date") or date.today().isoformat()
    subject = f"📚 {child_name}'s School Update — {today_str}"
    unsubscribe_url = f"{app_url}/settings/notifications"

    # Parse items from JSON
    raw_items: List[Dict[str, Any]] = []
    items_json = digest.get("items_json", "[]")
    if isinstance(items_json, str):
        try:
            raw_items = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            raw_items = []
    elif isinstance(items_json, list):
        raw_items = items_json

    action_items = [i for i in raw_items if i.get("type") != "event"]
    event_items = [i for i in raw_items if i.get("type") == "event"]

    # Render HTML
    tmpl_source = _jinja_env.from_string(_DIGEST_HTML_TEMPLATE)
    html_body = tmpl_source.render(
        subject=subject,
        child_name=child_name,
        digest_date=today_str,
        action_items=action_items,
        event_items=event_items,
        digest_prose=digest.get("digest_markdown", ""),
        unsubscribe_url=unsubscribe_url,
        app_url=app_url,
    )

    # Plain-text fallback
    text_body = _build_plaintext(child_name, today_str, action_items, event_items, digest, app_url)

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = user_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Send
    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        logger.info("Digest email sent to %s", user_email)
        return True
    except Exception as exc:
        logger.error("Failed to send digest email to %s: %s", user_email, exc)
        return False


def _build_plaintext(
    child_name: str,
    today_str: str,
    action_items: List[Dict[str, Any]],
    event_items: List[Dict[str, Any]],
    digest: Dict[str, Any],
    app_url: str,
) -> str:
    """Build a readable plain-text version of the digest email."""
    lines: List[str] = [
        f"School Update for {child_name} — {today_str}",
        "=" * 50,
        "",
    ]

    if action_items:
        lines.append("ACTION ITEMS")
        lines.append("-" * 30)
        for item in action_items:
            priority = (item.get("priority") or "low").upper()
            lines.append(f"[{priority}] {item.get('title', '')}")
            if item.get("summary"):
                lines.append(f"  {item['summary']}")
            if item.get("due_at"):
                lines.append(f"  Due: {item['due_at']}")
            lines.append("")

    if event_items:
        lines.append("UPCOMING EVENTS")
        lines.append("-" * 30)
        for item in event_items:
            lines.append(f"• {item.get('title', '')}")
            if item.get("due_at"):
                lines.append(f"  {item['due_at']}")
            lines.append("")

    prose = digest.get("digest_markdown", "").strip()
    if prose:
        lines.append("FULL DIGEST")
        lines.append("-" * 30)
        lines.append(prose)
        lines.append("")

    lines += [
        "-" * 50,
        f"Open Parently: {app_url}",
        f"Manage notifications: {app_url}/settings/notifications",
    ]
    return "\n".join(lines)
