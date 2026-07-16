import random

from app.engine.seed_schedule import SEED_SCHEDULE_ALGORITHM, derive_run_seed, seed_schedule


def test_gm020_known_seed_fixture_is_exact() -> None:
    assert SEED_SCHEDULE_ALGORITHM == "sha256_first_64_bits"
    assert [derive_run_seed(42, index) for index in range(5)] == [
        6085284259181818738,
        278651779053087998,
        14840890843343779510,
        11043869433078333928,
        8217744721944257512,
    ]


def test_gm020_seed_prefix_is_stable_and_unique() -> None:
    first_50 = seed_schedule(42, 50)
    first_100 = seed_schedule(42, 100)

    assert first_100[:50] == first_50
    assert len(set(seed_schedule(42, 500))) == 500


def test_seed_schedule_does_not_consume_rng_state() -> None:
    generator = random.Random(20250715)
    before = generator.getstate()
    seed_schedule(42, 100)

    assert generator.getstate() == before
