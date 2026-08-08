"""
One-off helper to load sample events into the Events table.

Usage:
    python scripts/seed_events.py <events-table-name> [--region eu-west-1]
"""

import sys
import argparse

import boto3

SAMPLE_EVENTS = [
    {
        "eventId": "evt-001",
        "name": "AWS Workshop Accra 2026",
        "date": "2026-05-15",
        "location": "Accra, Ghana",
        "capacity": 100,
        "status": "AVAILABLE",
    },
    {
        "eventId": "evt-002",
        "name": "Cloud Solutions Summit",
        "date": "2026-06-28",
        "location": "Tema, Ghana",
        "capacity": 50,
        "status": "LIMITED",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("table_name")
    parser.add_argument("--region", default="eu-west-1")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(args.table_name)

    with table.batch_writer() as batch:
        for item in SAMPLE_EVENTS:
            batch.put_item(Item=item)
            print(f"Seeded: {item['eventId']} — {item['name']}")


if __name__ == "__main__":
    sys.exit(main())