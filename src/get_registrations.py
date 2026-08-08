"""
GET /registrations/{email}

Returns every registration made with the given email address.
Requires a GSI named "email-index" on the registrations table
(partition key: email).
"""

import os
import logging
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError

from common.response import build_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
registrations_table = dynamodb.Table(os.environ["REGISTRATIONS_TABLE"])


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    raw_email = path_params.get("email")

    if not raw_email:
        return error_response(400, "email path parameter is required.")

    email = unquote(raw_email).strip().lower()

    try:
        result = registrations_table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": email},
        )
    except ClientError as exc:
        logger.error("DynamoDB query failed: %s", exc)
        return error_response(500, "Could not retrieve registrations right now.")

    items = result.get("Items", [])

    return build_response(200, {"email": email, "count": len(items), "registrations": items})