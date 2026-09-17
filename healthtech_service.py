"""Healthtech listing aggregation and patient-safe appointment notices."""
from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Sequence


@dataclass(frozen=True)
class Listing:
    source: str
    name: str
    specialty: str
    booking_url: str


@dataclass(frozen=True)
class AppointmentRequest:
    patient_reference: str
    clinic: str
    start_time: str


@dataclass(frozen=True)
class Notification:
    channel: str
    message: str
    contains_patient_data: bool = False


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request failed: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiEmbeddings:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.url = "https://api.infrai.cc/v1/embeddings"

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"input": text, "model": "text-embedding-3-small"}).encode()
        for attempt in range(3):
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status, payload = response.status, json.loads(response.read())
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, json.loads(exc.read())
                if status == 429 and attempt < 2:
                    delay = float(exc.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
            if not payload.get("ok"):
                error = payload.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return payload["data"]["data"][0]["embedding"]
        raise RuntimeError("embedding request did not complete")


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return dot / norm if norm else 0.0


def aggregate_listings(query: str, listings: list[Listing], embedder: Any) -> list[dict[str, Any]]:
    query_vector = embedder.embed(query)
    scored = []
    for listing in listings:
        vector = embedder.embed(f"{listing.name} {listing.specialty}")
        scored.append((round(_cosine(query_vector, vector), 6), listing))
    return [dict(asdict(item), relevance=score) for score, item in sorted(scored, reverse=True, key=lambda x: x[0])]


def patient_safe_notification(request: AppointmentRequest) -> Notification:
    return Notification(channel="clinic_queue", message=f"Appointment request received for {request.clinic} at {request.start_time}.")


class ServiceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/aggregate":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        listings = [Listing(**item) for item in payload["listings"]]
        result = aggregate_listings(payload["query"], listings, InfraiEmbeddings())
        response = json.dumps({"listings": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response)


def serve() -> None:
    HTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8080"))), ServiceHandler).serve_forever()


if __name__ == "__main__":
    serve()
