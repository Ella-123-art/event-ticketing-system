"""Shared helpers for building consistent, CORS-friendly API responses."""

import json
import decimal


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns Decimal types; make them JSON-serialisable."""

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE",
}


def build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def error_response(status_code: int, message: str) -> dict:
    return build_response(status_code, {"error": message})