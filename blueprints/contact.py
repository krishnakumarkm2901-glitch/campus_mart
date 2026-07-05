"""Contact form API: persist enquiries and notify support by email."""
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import smtplib

from flask import Blueprint, current_app, jsonify, request, session

from utils.db import get_db


contact_bp = Blueprint("contact", __name__)


def _valid_email(value):
    parsed = parseaddr(value)[1]
    return parsed == value and "@" in parsed and "." in parsed.rsplit("@", 1)[-1]


def _send_contact_email(contact):
    config = current_app.config
    if not config["MAIL_SERVER"] or not config["CONTACT_EMAIL"] or not config["MAIL_FROM"]:
        raise RuntimeError("SMTP email is not configured")

    message = EmailMessage()
    message["Subject"] = f"CampusMart contact: {contact['subject']}"
    message["From"] = config["MAIL_FROM"]
    message["To"] = config["CONTACT_EMAIL"]
    message["Reply-To"] = contact["email"]
    message.set_content(
        "New CampusMart contact message\n\n"
        f"Name: {contact['name']}\n"
        f"Email: {contact['email']}\n"
        f"Subject: {contact['subject']}\n\n"
        f"Message:\n{contact['message']}\n"
    )

    smtp_class = smtplib.SMTP_SSL if config["MAIL_USE_SSL"] else smtplib.SMTP
    with smtp_class(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=15) as smtp:
        if config["MAIL_USE_TLS"] and not config["MAIL_USE_SSL"]:
            smtp.starttls()
        if config["MAIL_USERNAME"]:
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        smtp.send_message(message)


@contact_bp.route("/api/contact", methods=["POST"])
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    subject = str(data.get("subject", "")).strip() or "General enquiry"
    message = str(data.get("message", "")).strip()

    if not name or not email or not message:
        return jsonify({"error": "Name, email and message are required."}), 400
    if not _valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(name) > 100 or len(email) > 254 or len(subject) > 150 or len(message) > 5000:
        return jsonify({"error": "One or more fields exceed the allowed length."}), 400
    if "\r" in subject or "\n" in subject:
        return jsonify({"error": "Subject contains invalid characters."}), 400

    now = datetime.now(timezone.utc)
    contact = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
        "user_id": session.get("user", {}).get("id"),
        "status": "new",
        "email_status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    db = get_db()
    result = db.contact_messages.insert_one(contact)

    try:
        _send_contact_email(contact)
        db.contact_messages.update_one(
            {"_id": result.inserted_id},
            {"$set": {"email_status": "sent", "email_sent_at": datetime.now(timezone.utc)}},
        )
    except Exception as exc:
        current_app.logger.exception("Contact email delivery failed")
        db.contact_messages.update_one(
            {"_id": result.inserted_id},
            {"$set": {"email_status": "failed", "email_error": str(exc)[:500]}},
        )

    return jsonify({
        "success": True,
        "message": "Your message has been received. We'll get back to you soon.",
    }), 201
