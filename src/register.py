"""
POST /register

Registers an attendee for an event.

Expected JSON body:
{
    "eventId": "evt-001",
    "name": "Emmanuella Martey",
    "email": "ella@example.com"
}
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from common.response import build_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")

EVENTS_TABLE = os.environ["EVENTS_TABLE"]
REGISTRATIONS_TABLE = os.environ["REGISTRATIONS_TABLE"]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

events_table = dynamodb.Table(EVENTS_TABLE)
registrations_table = dynamodb.Table(REGISTRATIONS_TABLE)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def handler(event, context):
    logger.info("Received registration request: %s", json.dumps(event.get("body", "")))

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON.")

    event_id = (body.get("eventId") or "").strip()
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()

    # --- Input validation -------------------------------------------------
    if not event_id or not name or not email:
        return error_response(400, "eventId, name and email are all required.")

    if not EMAIL_RE.match(email):
        return error_response(400, "Please provide a valid email address.")

    if len(name) > 100 or len(event_id) > 100:
        return error_response(400, "name/eventId exceed maximum allowed length.")

    # --- Confirm the event exists and has capacity -------------------------
    try:
        event_item = events_table.get_item(Key={"eventId": event_id}).get("Item")
    except ClientError as exc:
        logger.error("DynamoDB get_item failed: %s", exc)
        return error_response(500, "Could not verify the event right now.")

    if not event_item:
        return error_response(404, f"No event found with id '{event_id}'.")

    if event_item.get("status") == "SOLD_OUT":
        return error_response(409, "This event is sold out.")

    registration_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    item = {
        "registrationId": registration_id,
        "eventId": event_id,
        "email": email,
        "name": name,
        "status": "CONFIRMED",
        "createdAt": timestamp,
    }

    try:
        # Prevent the same email registering twice for the same event.
        registrations_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(registrationId)",
        )
    except ClientError as exc:
        logger.error("DynamoDB put_item failed: %s", exc)
        return error_response(500, "Could not save the registration right now.")

    _publish_confirmation(email, name, event_item)

    return build_response(201, {"message": "Registration confirmed.", "registration": item})


def _publish_confirmation(email: str, name: str, event_item: dict) -> None:
    """Best-effort SNS notification; failures here must never fail the request."""
    if not SNS_TOPIC_ARN:
        return
    try:
        sns = boto3.client("sns")
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Registration confirmed: {event_item.get('name', 'Event')}",
            Message=(
                f"Hi {name},\n\n"
                f"You're confirmed for {event_item.get('name', 'the event')} "
                f"on {event_item.get('date', 'TBC')}.\n\nSee you there!"
            ),
            MessageAttributes={"email": {"DataType": "String", "StringValue": email}},
        )
    except ClientError as exc:
        logger.warning("SNS publish failed (non-fatal): %s", exc)