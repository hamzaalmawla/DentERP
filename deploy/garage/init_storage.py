"""Prepare the development Garage node: layout, access key and bucket.

Runs once on `docker compose up` (service storage-init) and is safe to run again:
each step checks what already exists. Uses Garage's admin API (v2) and the Python
standard library only.

Environment:
  GARAGE_ADMIN_URL       e.g. http://storage:3903
  GARAGE_ADMIN_TOKEN     the node's admin token
  S3_ACCESS_KEY_ID       GK followed by 24 hex characters
  S3_SECRET_ACCESS_KEY   64 hex characters
  S3_BUCKET              bucket name
  GARAGE_CAPACITY_GB     storage capacity given to the node (default 10)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ADMIN_URL = os.environ["GARAGE_ADMIN_URL"].rstrip("/")
ADMIN_TOKEN = os.environ["GARAGE_ADMIN_TOKEN"]
ACCESS_KEY_ID = os.environ["S3_ACCESS_KEY_ID"]
SECRET_ACCESS_KEY = os.environ["S3_SECRET_ACCESS_KEY"]
BUCKET = os.environ["S3_BUCKET"]
CAPACITY_BYTES = int(os.environ.get("GARAGE_CAPACITY_GB", "10")) * 1000**3
KEY_NAME = "spu-dental-dev"


class ApiError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status


def call(endpoint: str, body: dict | None = None, **query: str) -> dict:
    url = f"{ADMIN_URL}/v2/{endpoint}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method="GET" if body is None else "POST",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, exc.read().decode(errors="replace")) from exc
    return json.loads(raw) if raw else {}


def wait_for_garage(attempts: int = 60) -> dict:
    for _ in range(attempts):
        try:
            return call("GetClusterStatus")
        except (urllib.error.URLError, ConnectionError, ApiError):
            time.sleep(1)
    sys.exit("Garage did not answer on its admin API.")


def ensure_layout(status: dict) -> None:
    node = status["nodes"][0]
    if node.get("role"):
        print("Layout: already assigned.")
        return
    layout = call("GetClusterLayout")
    call(
        "UpdateClusterLayout",
        {"roles": [{"id": node["id"], "zone": "dc1", "capacity": CAPACITY_BYTES, "tags": []}]},
    )
    call("ApplyClusterLayout", {"version": layout["version"] + 1})
    print("Layout: assigned and applied.")


def ensure_key() -> None:
    try:
        call("GetKeyInfo", id=ACCESS_KEY_ID)
        print("Access key: already present.")
    except ApiError as exc:
        if exc.status != 404:
            raise
        call(
            "ImportKey",
            {
                "accessKeyId": ACCESS_KEY_ID,
                "secretAccessKey": SECRET_ACCESS_KEY,
                "name": KEY_NAME,
            },
        )
        print("Access key: imported.")


def ensure_bucket() -> str:
    try:
        bucket = call("GetBucketInfo", globalAlias=BUCKET)
        print(f"Bucket {BUCKET}: already present.")
    except ApiError as exc:
        if exc.status != 404:
            raise
        bucket = call("CreateBucket", {"globalAlias": BUCKET})
        print(f"Bucket {BUCKET}: created.")
    return bucket["id"]


def allow_key(bucket_id: str) -> None:
    call(
        "AllowBucketKey",
        {
            "bucketId": bucket_id,
            "accessKeyId": ACCESS_KEY_ID,
            "permissions": {"read": True, "write": True, "owner": True},
        },
    )
    print("Access key: read, write and owner on the bucket.")


def main() -> None:
    status = wait_for_garage()
    ensure_layout(status)
    ensure_key()
    allow_key(ensure_bucket())
    print("Storage ready.")


if __name__ == "__main__":
    main()
