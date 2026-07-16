import hashlib
from typing import Literal

SEED_SCHEDULE_ALGORITHM: Literal["sha256_first_64_bits"] = "sha256_first_64_bits"


def derive_run_seed(base_seed: int, run_index: int) -> int:
    """Derive one platform-stable unsigned 64-bit child seed."""
    digest = hashlib.sha256(f"{base_seed}:{run_index}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def seed_schedule(base_seed: int, run_count: int) -> list[int]:
    return [derive_run_seed(base_seed, index) for index in range(run_count)]
