#!/usr/bin/env python3
"""
delete_instances.py — Delete FOLIO instance records by UUID.

Performs a full cascade delete for each UUID:
  1. Preceding/succeeding title relationships
  2. Source Record Storage (SRS) record
  3. Items under each holdings record
  4. Holdings records
  5. Instance record itself

Credentials are read from a .env file via --creds-file, with environment
variables as a fallback for any missing keys.

.env format (KEY=VALUE, # comments supported):
  FOLIO_OKAPI_URL=https://okapi.example.edu
  FOLIO_OKAPI_TENANT_ID=mytenant
  FOLIO_OKAPI_USER=myuser
  FOLIO_OKAPI_PASSWORD=mypassword

Usage:
  python delete_instances.py uuids.txt --creds-file folio.env
  python delete_instances.py uuids.txt --creds-file folio.env --dry-run
  python delete_instances.py uuids.txt --creds-file folio.env \
      --backup-dir ./backups --checkpoint-file progress.txt
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# Refresh the access token when fewer than this many seconds remain.
_REFRESH_BUFFER_SECONDS = 300


class FolioClient:
    """Thin FOLIO HTTP client that logs in and refreshes its token automatically."""

    def __init__(self, url, tenant_id):
        self.url = url.rstrip('/')
        self.tenant_id = tenant_id
        self.token = None
        self._refresh_token = None
        self._access_expires = None   # ISO 8601 string
        self._refresh_expires = None  # ISO 8601 string
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, user, password):
        """POST to /authn/login-with-expiry and store the resulting tokens."""
        payload = json.dumps({'tenant': self.tenant_id, 'username': user, 'password': password})
        resp = requests.post(
            self.url + '/authn/login-with-expiry',
            data=payload,
            headers=self._base_headers(),
            timeout=30,
        )
        if resp.status_code != 201:
            sys.exit(f"Login failed (HTTP {resp.status_code}): {resp.text[:500]}")

        self.token = self._extract_access_token(resp)
        self._refresh_token = self._extract_refresh_token(resp)
        try:
            body = resp.json()
            self._access_expires = body.get('accessTokenExpiration')
            self._refresh_expires = body.get('refreshTokenExpiration')
        except Exception:
            pass

        if not self.token:
            sys.exit("Login succeeded but no access token found in response")

        self._update_session_token()
        log.info(f"Logged in successfully. Access token expires: {self._access_expires}")

    def _base_headers(self):
        return {
            'x-okapi-tenant': self.tenant_id,
            'content-type': 'application/json',
            'User-Agent': 'folio-delete-script',
            'X-Forwarded-For': '127.0.0.1',
        }

    def _update_session_token(self):
        assert self.token is not None
        self._session.headers.update({
            'x-okapi-token': self.token,
            'x-okapi-tenant': self.tenant_id,
            'content-type': 'application/json',
        })

    @staticmethod
    def _extract_access_token(resp):
        # FOLIO returns the token in a header on older versions, or a cookie on newer ones.
        token = resp.headers.get('x-okapi-token')
        if token:
            return token
        return resp.cookies.get('folioAccessToken')

    @staticmethod
    def _extract_refresh_token(resp):
        return resp.cookies.get('folioRefreshToken')

    @staticmethod
    def _seconds_until(iso_timestamp):
        """Return seconds until the given ISO 8601 timestamp, or None if unparseable."""
        if not iso_timestamp:
            return None
        try:
            expiration = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return (expiration - datetime.now(timezone.utc)).total_seconds()
        except Exception:
            return None

    def _refresh_if_needed(self):
        if not self._refresh_token:
            return

        secs_left = self._seconds_until(self._access_expires)
        # If expiry is known and we have plenty of time, nothing to do.
        if secs_left is not None and secs_left > _REFRESH_BUFFER_SECONDS:
            return
        # If expiry is completely unknown, don't attempt a speculative refresh.
        if secs_left is None:
            return

        refresh_secs = self._seconds_until(self._refresh_expires)
        if refresh_secs is not None and refresh_secs <= 0:
            log.warning("Refresh token is expired — continuing with current access token")
            return

        log.info(f"Access token expiring in {int(secs_left)}s; refreshing...")
        headers = self._base_headers()
        headers['Cookie'] = f'folioRefreshToken={self._refresh_token}'
        resp = requests.post(self.url + '/authn/refresh', headers=headers, timeout=30)

        if resp.status_code != 201:
            log.warning(f"Token refresh failed (HTTP {resp.status_code}) — continuing with current token")
            return

        new_token = self._extract_access_token(resp)
        new_refresh = self._extract_refresh_token(resp)
        try:
            body = resp.json()
            self._access_expires = body.get('accessTokenExpiration') or self._access_expires
            self._refresh_expires = body.get('refreshTokenExpiration') or self._refresh_expires
        except Exception:
            pass

        if new_token:
            self.token = new_token
            self._update_session_token()
            log.info(f"Token refreshed. New expiry: {self._access_expires}")
        if new_refresh:
            self._refresh_token = new_refresh

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def get(self, endpoint, params=None):
        self._refresh_if_needed()
        resp = self._session.get(self.url + endpoint, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def delete(self, endpoint, label=''):
        self._refresh_if_needed()
        log.info(f"  DELETE {label or endpoint}")
        resp = self._session.delete(self.url + endpoint, timeout=30)
        if resp.status_code == 404:
            log.warning(f"  404 not found: {label or endpoint} — skipping")
            return False
        resp.raise_for_status()
        return True


# ------------------------------------------------------------------
# Credentials loading
# ------------------------------------------------------------------

def load_credentials(creds_file=None):
    """Read credentials from a .env file, with env vars as fallback."""
    data = {}

    if creds_file:
        path = Path(creds_file)
        if not path.exists():
            sys.exit(f"Credentials file not found: {creds_file}")
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, _, v = line.partition('=')
                data[k.strip()] = v.strip().strip('"').strip("'")

    # Fill in anything not found in the file from environment variables
    for key in ('FOLIO_OKAPI_URL', 'FOLIO_OKAPI_TENANT_ID',
                'FOLIO_OKAPI_USER', 'FOLIO_OKAPI_PASSWORD'):
        if key not in data and key in os.environ:
            data[key] = os.environ[key]

    return data


# ------------------------------------------------------------------
# Deletion logic
# ------------------------------------------------------------------

def save_backup(data, backup_dir, instance_uuid, label):
    if not backup_dir:
        return
    dest = Path(backup_dir) / instance_uuid
    dest.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    path = dest / f"{label}-{ts}.json"
    path.write_text(json.dumps(data, indent=2))
    log.debug(f"  backed up to {path}")


def delete_instance(client, uuid, dry_run=False, backup_dir=None):
    log.info(f"--- instance {uuid} ---")
    errors = []

    # Step 1: preceding/succeeding title relationships
    try:
        pst_query = f"precedingInstanceId=={uuid} or succeedingInstanceId=={uuid}"
        pst_data = client.get("/preceding-succeeding-titles",
                              params={"query": f"({pst_query})", "limit": 1000})
        pst_records = pst_data.get("precedingSucceedingTitles", [])
        if pst_records:
            log.info(f"  {len(pst_records)} preceding/succeeding title relationship(s)")
            for pst in pst_records:
                pst_id = pst["id"]
                if dry_run:
                    log.info(f"  [dry-run] would delete PST {pst_id}")
                else:
                    save_backup(pst, backup_dir, uuid, f"pst-{pst_id}")
                    client.delete(f"/preceding-succeeding-titles/{pst_id}", f"PST {pst_id}")
        else:
            log.info("  no preceding/succeeding title relationships")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            log.info("  no preceding/succeeding title relationships (404)")
        else:
            log.error(f"  PST lookup failed: {e}")
            errors.append(f"PST: {e}")

    # Step 2: Source Record Storage
    try:
        srs_data = client.get(f"/source-storage/records/{uuid}/formatted",
                              params={"idType": "INSTANCE"})
        if srs_data and srs_data.get("matchedId"):
            srs_id = srs_data["id"]
            log.info(f"  SRS record {srs_id}")
            if dry_run:
                log.info(f"  [dry-run] would delete SRS record {srs_id}")
            else:
                save_backup(srs_data, backup_dir, uuid, f"srs-{srs_id}")
                client.delete(f"/source-storage/records/{srs_id}", f"SRS {srs_id}")
        else:
            log.info("  no SRS record (instance has no MARC record)")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            log.info("  no SRS record (404)")
        else:
            log.error(f"  SRS lookup failed: {e}")
            errors.append(f"SRS: {e}")

    # Step 3: items then holdings (FOLIO requires items deleted before holdings)
    try:
        holdings_data = client.get("/holdings-storage/holdings",
                                   params={"query": f"instanceId=={uuid}", "limit": 1000})
        holdings_records = holdings_data.get("holdingsRecords", [])
        total_holdings = holdings_data.get("totalRecords", 0)
        if total_holdings > 1000:
            log.warning(f"  {total_holdings} holdings found but only fetched 1000 — re-run after partial delete")
        log.info(f"  {len(holdings_records)} holdings record(s)")

        for h in holdings_records:
            h_id = h["id"]
            items_data = client.get("/item-storage/items",
                                    params={"query": f"holdingsRecordId=={h_id}", "limit": 1000})
            items = items_data.get("items", [])
            total_items = items_data.get("totalRecords", 0)
            if total_items > 1000:
                log.warning(f"  holdings {h_id} has {total_items} items but only fetched 1000")
            log.info(f"  holdings {h_id}: {len(items)} item(s)")

            for item in items:
                item_id = item["id"]
                if dry_run:
                    log.info(f"    [dry-run] would delete item {item_id}")
                else:
                    save_backup(item, backup_dir, uuid, f"item-{item_id}")
                    client.delete(f"/item-storage/items/{item_id}", f"item {item_id}")

            if dry_run:
                log.info(f"    [dry-run] would delete holdings {h_id}")
            else:
                save_backup(h, backup_dir, uuid, f"holdings-{h_id}")
                client.delete(f"/holdings-storage/holdings/{h_id}", f"holdings {h_id}")

    except requests.HTTPError as e:
        log.error(f"  holdings/items failed: {e}")
        errors.append(f"holdings/items: {e}")

    # Step 4: instance record — skipped if any earlier step errored
    if errors:
        log.error(f"  skipping instance deletion due to earlier errors: {errors}")
        return False

    try:
        if dry_run:
            log.info(f"  [dry-run] would delete instance {uuid}")
        else:
            try:
                inst_data = client.get(f"/instance-storage/instances/{uuid}")
                save_backup(inst_data, backup_dir, uuid, f"instance-{uuid}")
            except Exception as e:
                log.warning(f"  could not back up instance record: {e}")
            client.delete(f"/instance-storage/instances/{uuid}", f"instance {uuid}")
            log.info("  done")
    except requests.HTTPError as e:
        log.error(f"  instance deletion failed: {e}")
        return False

    return True


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def read_uuids(path):
    lines = Path(path).read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def load_checkpoint(checkpoint_file):
    """Return the set of UUIDs already recorded as successfully deleted."""
    if not checkpoint_file:
        return set()
    path = Path(checkpoint_file)
    if not path.exists():
        return set()
    return {ln.strip() for ln in path.read_text().splitlines() if ln.strip()}


def record_checkpoint(checkpoint_file, uuid):
    """Append a UUID to the checkpoint file immediately after successful deletion."""
    if not checkpoint_file:
        return
    with open(checkpoint_file, 'a') as f:
        f.write(uuid + '\n')


def main():
    parser = argparse.ArgumentParser(
        description="Delete FOLIO instance records by UUID (full cascade)."
    )
    parser.add_argument("uuid_file",
                        help="File with one instance UUID per line")
    parser.add_argument("--creds-file", metavar="FILE",
                        help=".env file with FOLIO credentials (KEY=VALUE, # comments supported)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log what would be deleted without making any changes")
    parser.add_argument("--backup-dir", metavar="DIR",
                        help="Save JSON backups of each deleted record to this directory")
    parser.add_argument("--checkpoint-file", metavar="FILE",
                        help="File to record each successfully deleted UUID; on restart, any UUID "
                             "already in this file is skipped")
    parser.add_argument("--stop-on-error", action="store_true",
                        help="Halt on first failure instead of continuing to the next UUID")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    creds = load_credentials(args.creds_file)

    missing = [k for k in ("FOLIO_OKAPI_URL", "FOLIO_OKAPI_TENANT_ID",
                            "FOLIO_OKAPI_USER", "FOLIO_OKAPI_PASSWORD")
               if not creds.get(k)]
    if missing:
        sys.exit("Error: missing required credentials: " + ", ".join(missing)
                 + "\nProvide them via --creds-file or as environment variables.")

    client = FolioClient(creds["FOLIO_OKAPI_URL"], creds["FOLIO_OKAPI_TENANT_ID"])
    client.login(creds["FOLIO_OKAPI_USER"], creds["FOLIO_OKAPI_PASSWORD"])

    uuids = read_uuids(args.uuid_file)
    log.info(f"Loaded {len(uuids)} UUID(s) from {args.uuid_file}")

    completed = load_checkpoint(args.checkpoint_file)
    if completed:
        log.info(f"Checkpoint: skipping {len(completed)} already-deleted UUID(s)")

    if args.dry_run:
        log.info("DRY RUN — no records will be modified")

    succeeded, failed = [], []
    for i, uuid in enumerate(uuids, 1):
        if uuid in completed:
            continue
        log.info(f"[{i}/{len(uuids)}]")
        ok = delete_instance(client, uuid, dry_run=args.dry_run, backup_dir=args.backup_dir)
        (succeeded if ok else failed).append(uuid)
        if ok and not args.dry_run:
            record_checkpoint(args.checkpoint_file, uuid)
        if not ok and args.stop_on_error:
            log.error("Stopping due to --stop-on-error")
            break

    log.info(f"Finished: {len(succeeded)} succeeded, {len(failed)} failed.")
    if failed:
        log.warning("Failed UUIDs:")
        for uuid in failed:
            log.warning(f"  {uuid}")
        sys.exit(1)


if __name__ == "__main__":
    main()
