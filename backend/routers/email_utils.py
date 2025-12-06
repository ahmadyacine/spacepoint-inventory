import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import List, Tuple


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))  # STARTTLS
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@spacepoint.ae")


# -------------------------------------------------------
# Convert datetime → ICS format
# -------------------------------------------------------
def _format_dt_as_ics(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.strftime("%Y%m%dT%H%M%SZ")
    return dt.astimezone().strftime("%Y%m%dT%H%M%SZ")


# -------------------------------------------------------
# ICS Calendar Event Builder
# -------------------------------------------------------
def build_workshop_ics(workshop: dict, uid_prefix: str = "spacepoint-workshop") -> str:
    title = workshop.get("title", "SpacePoint Workshop")
    description = workshop.get("description") or ""
    location = workshop.get("location") or "TBD"

    start_dt = workshop["start_date"]
    end_dt = workshop["end_date"]

    dtstart = _format_dt_as_ics(start_dt)
    dtend = _format_dt_as_ics(end_dt)

    uid = f"{uid_prefix}-{workshop['id']}@spacepoint.ae"

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SpacePoint//Workshop//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
SUMMARY:{title}
DTSTART:{dtstart}
DTEND:{dtend}
DESCRIPTION:{description}
LOCATION:{location}
END:VEVENT
END:VCALENDAR
"""


# -------------------------------------------------------
# Beautiful HTML SpacePoint-branded email
# -------------------------------------------------------
def build_workshop_html_email(workshop: dict, recipient_name: str = "there") -> str:
    title = workshop.get("title", "SpacePoint Workshop")
    location = workshop.get("location") or "TBD"
    description = workshop.get("description") or ""

    start_dt = workshop["start_date"]
    end_dt = workshop["end_date"]

    start_str = start_dt.strftime("%A, %d %B %Y · %H:%M")
    end_str = end_dt.strftime("%A, %d %B %Y · %H:%M")

    logo_url = "https://spacepoint.ae/wp-content/uploads/2023/12/space-2d-silver.png"

    return f"""
<!DOCTYPE html>
<html>
  <body style="margin:0; padding:0; background-color:#f3f4f6; font-family:system-ui;">
    <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 0; background:#f3f4f6;">
      <tr><td align="center">
        <table width="600" style="background:#fff; border-radius:16px; overflow:hidden;">

          <tr>
            <td style="background:linear-gradient(135deg,#241134,#653f84); padding:20px;">
              <img src="{logo_url}" height="40">
            </td>
          </tr>

          <tr>
            <td style="padding:24px;">
              <p>Hello {recipient_name},</p>
              <p>You have been assigned to the following <strong>SpacePoint</strong> workshop:</p>

              <div style="background:#f9fafb; padding:14px; border:1px solid #ddd; border-radius:12px;">
                <p><strong>{title}</strong></p>
                <p><strong>Location:</strong> {location}</p>
                <p><strong>Start:</strong> {start_str}</p>
                <p><strong>End:</strong> {end_str}</p>
              </div>

              <p><strong>Workshop Overview:</strong></p>
              <p>{description}</p>

              <p>The calendar invite (.ics) is attached.</p>

              <p>Best regards,<br>SpacePoint Team</p>
            </td>
          </tr>

          <tr>
            <td style="font-size:12px; color:#aaa; padding:16px; background:#f9fafb;">
              © {datetime.utcnow().year} SpacePoint — Auto-generated email.
            </td>
          </tr>

        </table>
      </td></tr>
    </table>
  </body>
</html>
"""


# -------------------------------------------------------
# Send email (HTML + text + ICS)
# -------------------------------------------------------
def send_workshop_email(
    workshop: dict,
    recipients: List[Tuple[str, str]],
    subject_override: str | None = None,
    body_override: str | None = None,
):
    if not recipients:
        return

    title = workshop.get("title", "SpacePoint Workshop")
    location = workshop.get("location") or "TBD"
    description = workshop.get("description") or ""

    start_dt = workshop["start_date"]
    end_dt = workshop["end_date"]

    start_str = start_dt.strftime("%A, %d %B %Y %H:%M")
    end_str = end_dt.strftime("%A, %d %B %Y %H:%M")

    default_subject = f"[SpacePoint] Workshop Invitation – {title}"
    subject = subject_override or default_subject

    default_text = f"""Hello,

You have been assigned to the following SpacePoint workshop:

Title: {title}
Location: {location}
Start: {start_str}
End:   {end_str}

Description:
{description}

Calendar invite attached.

Best regards,
SpacePoint Team
"""

    text_body = body_override or default_text
    ics_content = build_workshop_ics(workshop)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)

        for name, email in recipients:
            if not email:
                continue

            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = email

            msg.set_content(text_body)
            msg.add_alternative(
                build_workshop_html_email(workshop, recipient_name=name),
                subtype="html"
            )

            msg.add_attachment(
                ics_content.encode(),
                maintype="text",
                subtype="calendar",
                filename=f"{title.replace(' ', '_')}.ics",
                params={"method": "REQUEST"},
            )

            server.send_message(msg)
