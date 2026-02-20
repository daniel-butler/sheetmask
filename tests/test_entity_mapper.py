from excel_anonymizer.entity_mapper import EntityMapper


def test_same_entity_maps_to_same_fake():
    mapper = EntityMapper(seed=42)
    fake1 = mapper.get_or_create("PERSON", "John Smith")
    fake2 = mapper.get_or_create("PERSON", "John Smith")
    assert fake1 == fake2


def test_different_entities_map_differently():
    mapper = EntityMapper(seed=42)
    fake1 = mapper.get_or_create("PERSON", "John Smith")
    fake2 = mapper.get_or_create("PERSON", "Jane Doe")
    assert fake1 != fake2


def test_seed_produces_reproducible_output():
    mapper1 = EntityMapper(seed=42)
    mapper2 = EntityMapper(seed=42)
    fake1 = mapper1.get_or_create("ORGANIZATION", "Acme Corp")
    fake2 = mapper2.get_or_create("ORGANIZATION", "Acme Corp")
    assert fake1 == fake2


def test_all_entity_types_generate_without_error():
    mapper = EntityMapper(seed=42)
    types = [
        "PERSON", "PERSON_FIRST_NAME", "PERSON_LAST_NAME",
        "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER",
        "PROJECT_NAME", "PROJECT_DESCRIPTION", "LOCATION",
    ]
    for t in types:
        result = mapper.get_or_create(t, "test_value")
        assert isinstance(result, str)
        assert len(result) > 0


def test_to_dict_counts_mappings():
    mapper = EntityMapper(seed=42)
    mapper.get_or_create("PERSON", "Alice")
    mapper.get_or_create("PERSON", "Bob")
    mapper.get_or_create("ORGANIZATION", "Acme")
    report = mapper.to_dict()
    assert report["total_mappings"] == 3
