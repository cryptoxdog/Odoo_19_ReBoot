import hashlib


def make_packet_id(intake_id: int, packet_version: str) -> str:
    raw = f"intake:{intake_id}:v:{packet_version}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
