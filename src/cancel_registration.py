"""
DELETE /registration/{id}

Cancels (soft-deletes) a registration by its registrationId.
"""

import os
import logging

import boto3
from botocore.exceptions import ClientError

from common.response import build_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
registrations_table = dynamodb.Table(os.environ["REGISTRATIONS_TABLE"])


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    registration_id = path_params.get("id")

    if not registration_id:
        return error_response(400, "Registration id path parameter is required.")

    try:
        existing = registrations_table.get_item(Key={"registrationId": registration_id}).get("Item")
    except ClientError as exc:
        logger.error("DynamoDB get_item failed: %s", exc)
        return error_response(500, "Could not look up the registration right now.")

    if not existing:
        return error_response(404, f"No registration found with id '{registration_id}'.")

    try:
        registrations_table.update_item(
            Key={"registrationId": registration_id},
            UpdateExpression="SET #s = :cancelled",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":cancelled": "CANCELLED"},
        )
    except ClientError as exc:
        logger.error("DynamoDB update_item failed: %s", exc)
        return error_response(500, "Could not cancel the registration right now.")

    return build_response(200, {"message": f"Registration {registration_id} cancelled."})