"""
GET /events

Returns all events, optionally filtered with ?status=AVAILABLE
"""

import os
import logging

import boto3
from botocore.exceptions import ClientError

from common.response import build_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
events_table = dynamodb.Table(os.environ["EVENTS_TABLE"])


def handler(event, context):
    query_params = event.get("queryStringParameters") or {}
    status_filter = (query_params.get("status") or "").strip().upper()

    try:
        result = events_table.scan()
        items = result.get("Items", [])

        # Paginate through the full table (fine at this scale; swap for a
        # Query on a GSI if the table grows large).
        while "LastEvaluatedKey" in result:
            result = events_table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
            items.extend(result.get("Items", []))

    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return error_response(500, "Could not retrieve events right now.")

    if status_filter:
        items = [i for i in items if i.get("status", "").upper() == status_filter]

    items.sort(key=lambda i: i.get("date", ""))

    return build_response(200, {"count": len(items), "events": items})