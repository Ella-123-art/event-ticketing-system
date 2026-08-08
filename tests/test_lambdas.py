"""
Unit tests for the ticketing Lambda functions, using moto to mock DynamoDB
and SNS so tests run without any real AWS resources.

Run with:  pytest tests/ -v
"""

import os
import json
import importlib

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("EVENTS_TABLE", "test-events")
os.environ.setdefault("REGISTRATIONS_TABLE", "test-registrations")
os.environ.setdefault("SNS_TOPIC_ARN", "")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-1")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def aws_setup():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

        dynamodb.create_table(
            TableName="test-events",
            KeySchema=[{"AttributeName": "eventId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "eventId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        dynamodb.create_table(
            TableName="test-registrations",
            KeySchema=[{"AttributeName": "registrationId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "registrationId", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "email-index",
                    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        events_table = dynamodb.Table("test-events")
        events_table.put_item(
            Item={"eventId": "evt-001", "name": "Test Event", "date": "2026-05-15", "status": "AVAILABLE"}
        )

        yield dynamodb


def test_list_events_returns_seeded_event(aws_setup):
    list_events = importlib.import_module("list_events")
    result = list_events.handler({"queryStringParameters": None}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["count"] == 1
    assert body["events"][0]["eventId"] == "evt-001"


def test_register_success(aws_setup):
    register = importlib.import_module("register")
    event = {
        "body": json.dumps({"eventId": "evt-001", "name": "Ella Martey", "email": "ella@example.com"})
    }
    result = register.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 201
    assert body["registration"]["email"] == "ella@example.com"


def test_register_rejects_invalid_email(aws_setup):
    register = importlib.import_module("register")
    event = {"body": json.dumps({"eventId": "evt-001", "name": "Ella Martey", "email": "not-an-email"})}
    result = register.handler(event, None)

    assert result["statusCode"] == 400


def test_register_rejects_unknown_event(aws_setup):
    register = importlib.import_module("register")
    event = {"body": json.dumps({"eventId": "evt-999", "name": "Ella Martey", "email": "ella@example.com"})}
    result = register.handler(event, None)

    assert result["statusCode"] == 404


def test_cancel_registration_flow(aws_setup):
    register = importlib.import_module("register")
    cancel = importlib.import_module("cancel_registration")

    reg_event = {
        "body": json.dumps({"eventId": "evt-001", "name": "Ella Martey", "email": "ella@example.com"})
    }
    reg_result = register.handler(reg_event, None)
    registration_id = json.loads(reg_result["body"])["registration"]["registrationId"]

    cancel_result = cancel.handler({"pathParameters": {"id": registration_id}}, None)
    assert cancel_result["statusCode"] == 200


def test_get_registrations_by_email(aws_setup):
    register = importlib.import_module("register")
    get_regs = importlib.import_module("get_registrations")

    reg_event = {
        "body": json.dumps({"eventId": "evt-001", "name": "Ella Martey", "email": "ella@example.com"})
    }
    register.handler(reg_event, None)

    result = get_regs.handler({"pathParameters": {"email": "ella@example.com"}}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["count"] == 1