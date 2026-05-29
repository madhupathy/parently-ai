"""Weekly Parently ops report — emails business metrics to the operator.

What it reports:
  - Total users, new users this week
  - Digest count this week
  - LLM cost this week (real number, from llm_usage table)
  - Infra costs (read from INFRA_COSTS_YAML — operator updates monthly when bills arrive)
  - Runway estimate

Why this design:
  Railway, Neon, and most domain registrars don't expose convenient billing
  APIs for a single-developer SaaS. Manually maintained monthly figures
  in a YAML file are honest and reliable; LLM cost is pulled from our
  own LLMUsage table which is the most volatile number.

Usage:
    python apps/backend/scripts/weekly_report.py
    python apps/backend/scripts/weekly_report.py --dry-run   # print to stdout, don't send

Env (in addition to standard SMTP_* + BACKEND_DATABASE_URL):
    REPORT_RECIPIENT_EMAIL   (required) where to send
    INFRA_COSTS_YAML         (optional) path to costs file; defaults to
                             apps/backend/config/infra_costs.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import aiosmtplib  # noqa: E402
from sqlalchemy import func  # noqa: E402

from config import get_settings  # noqa: E402
from storage import get_db  # noqa: E402
from storage.models import Digest, LLMUsage, User, UserEntitlement  # noqa: E402

logger = logging.getLogger("weekly_report")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_infra_costs() -> Dict[str, float]:
    """Read monthly infra costs from YAML. Returns dollars per month per service."""
    path = Path(os.getenv("INFRA_COSTS_YAML") or REPO_ROOT / "config" / "infra_costs.yaml")
    if not path.exists():
        logger.warning("infra costs YAML not found at %s — infra costs will be $0", path)
        return {}
    try:
        import yaml
    except ImportError:
        logger.error("PyYAML not installed; cannot read %s. Run: pip install pyyaml", path)
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    costs: Dict[str, float] = {}
    for key, raw in data.items():
        try:
            costs[str(key)] = float(raw)
        except (TypeError, ValueError):
            logger.warning("ignoring non-numeric cost entry %r=%r", key, raw)
    return costs


def _collect_metrics() -> Dict[str, Any]:
    db = get_db()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    with db.session_scope() as session:
        total_users = session.query(func.count(User.id)).scalar() or 0
        new_users = session.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0
        digests_this_week = (
            session.query(func.count(Digest.id)).filter(Digest.created_at >= week_ago).scalar() or 0
        )
        llm_cost_this_week = (
            session.query(func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0))
            .filter(LLMUsage.created_at >= week_ago)
            .scalar()
            or 0.0
        )
        llm_cost_lifetime = (
            session.query(func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0)).scalar() or 0.0
        )
        premium_users = (
            session.query(func.count(UserEntitlement.id))
            .filter(UserEntitlement.premium_active.is_(True))
            .scalar()
            or 0
        )
    return {
        "as_of": now.isoformat(timespec="seconds"),
        "total_users": int(total_users),
        "new_users_week": int(new_users),
        "premium_users": int(premium_users),
        "digests_week": int(digests_this_week),
        "llm_cost_week_usd": float(llm_cost_this_week),
        "llm_cost_lifetime_usd": float(llm_cost_lifetime),
    }


def _build_report(metrics: Dict[str, Any], infra_costs: Dict[str, float]) -> Dict[str, str]:
    infra_monthly_total = sum(infra_costs.values())
    infra_weekly_total = infra_monthly_total / 4.0
    total_weekly_cost = infra_weekly_total + metrics["llm_cost_week_usd"]
    mrr_estimate = metrics["premium_users"] * 5.0  # current target subscription
    runway_weeks: str
    if total_weekly_cost <= 0:
        runway_weeks = "infinite"
    elif mrr_estimate <= 0:
        runway_weeks = "no revenue yet"
    else:
        # very rough — burn vs incoming
        weekly_revenue = mrr_estimate / 4.0
        net_burn = total_weekly_cost - weekly_revenue
        runway_weeks = "profitable" if net_burn <= 0 else f"burn ${net_burn:.2f}/week"

    rows = []
    rows.append(f"<tr><td>Total users</td><td>{metrics['total_users']}</td></tr>")
    rows.append(f"<tr><td>New users (last 7d)</td><td>{metrics['new_users_week']}</td></tr>")
    rows.append(f"<tr><td>Premium users</td><td>{metrics['premium_users']}</td></tr>")
    rows.append(f"<tr><td>Digests run (last 7d)</td><td>{metrics['digests_week']}</td></tr>")
    rows.append(f"<tr><td>LLM cost (last 7d)</td><td>${metrics['llm_cost_week_usd']:.2f}</td></tr>")
    rows.append(f"<tr><td>LLM cost (lifetime)</td><td>${metrics['llm_cost_lifetime_usd']:.2f}</td></tr>")
    rows.append("<tr><td colspan=2><strong>Infra costs (monthly)</strong></td></tr>")
    for service, cost in sorted(infra_costs.items()):
        rows.append(f"<tr><td>&nbsp;&nbsp;{service}</td><td>${cost:.2f}/mo</td></tr>")
    rows.append(f"<tr><td>Infra total</td><td>${infra_monthly_total:.2f}/mo (≈ ${infra_weekly_total:.2f}/wk)</td></tr>")
    rows.append(f"<tr><td><strong>This week total cost</strong></td><td><strong>${total_weekly_cost:.2f}</strong></td></tr>")
    rows.append(f"<tr><td>MRR estimate (premium × $5)</td><td>${mrr_estimate:.2f}</td></tr>")
    rows.append(f"<tr><td>Status</td><td>{runway_weeks}</td></tr>")
    table_html = "<table style='border-collapse:collapse'>" + "".join(rows) + "</table>"

    text_lines = [
        f"Parently weekly report — {metrics['as_of']}",
        "",
        f"Users:       {metrics['total_users']}  (+{metrics['new_users_week']} this week)",
        f"Premium:     {metrics['premium_users']}",
        f"Digests:     {metrics['digests_week']}",
        f"LLM cost:    ${metrics['llm_cost_week_usd']:.2f} this week  /  ${metrics['llm_cost_lifetime_usd']:.2f} lifetime",
        "",
        "Infra (monthly):",
    ]
    for service, cost in sorted(infra_costs.items()):
        text_lines.append(f"  - {service:20s}  ${cost:.2f}/mo")
    text_lines.extend([
        f"  Infra total          ${infra_monthly_total:.2f}/mo  (≈${infra_weekly_total:.2f}/wk)",
        "",
        f"Total this week:  ${total_weekly_cost:.2f}",
        f"MRR estimate:     ${mrr_estimate:.2f}",
        f"Status:           {runway_weeks}",
    ])
    return {"html": table_html, "text": "\n".join(text_lines)}


async def _send_email(subject: str, html: str, text_body: str, recipient: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError("SMTP_HOST and SMTP_FROM must be set to send the report")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_secure,
        start_tls=not settings.smtp_secure,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print to stdout instead of sending email")
    args = parser.parse_args()

    metrics = _collect_metrics()
    infra = _load_infra_costs()
    report = _build_report(metrics, infra)
    subject = f"Parently weekly — {metrics['total_users']} users, ${metrics['llm_cost_week_usd']:.2f} LLM this week"

    if args.dry_run:
        print(report["text"])
        return 0

    recipient = os.getenv("REPORT_RECIPIENT_EMAIL")
    if not recipient:
        logger.error("REPORT_RECIPIENT_EMAIL not set; printing instead")
        print(report["text"])
        return 1

    asyncio.run(_send_email(subject, report["html"], report["text"], recipient))
    logger.info("weekly report sent to %s", recipient)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
