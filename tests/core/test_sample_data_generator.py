from vector_inspector.core.sample_data.text_generator import generate_sample_data


def test_generate_deterministic_stability():
    a = generate_sample_data(20, randomize=False)
    b = generate_sample_data(20, randomize=False)
    assert a == b


def test_generate_large_count_smoke():
    items = generate_sample_data(10000, randomize=False)
    assert len(items) == 10000
