"""
Global entity mapper for consistent anonymization.

Ensures that the same entity value (e.g., "Acme Corp") always maps to the
same fake value (e.g., "FakeCo Industries") across all columns and sheets.
"""

from typing import Dict
from faker import Faker


class EntityMapper:
    """
    Maintains global mappings for entities across all columns/sheets.

    Example:
        mapper = EntityMapper()

        # First occurrence of "Acme Corp"
        fake1 = mapper.get_or_create("ORGANIZATION", "Acme Corp")  # → "FakeCo Industries"

        # Second occurrence of "Acme Corp" (different column/sheet)
        fake2 = mapper.get_or_create("ORGANIZATION", "Acme Corp")  # → "FakeCo Industries" (same!)
    """

    def __init__(self, seed: int | None = None):
        """
        Initialize entity mapper.

        Args:
            seed: Random seed for reproducible fake data generation
        """
        self.fake = Faker()

        if seed is not None:
            # Seed the instance directly for reproducibility across mapper instances.
            # Faker.seed() is class-level and shared across all instances, so creating
            # a new Faker() after Faker.seed() consumes state differently each time.
            # seed_instance() seeds this specific instance's RNG deterministically.
            self.fake.seed_instance(seed)

        # Store mappings: entity_type -> {original_value -> fake_value}
        self.mappings: Dict[str, Dict[str, str]] = {}

    def get_or_create(self, entity_type: str, original_value: str) -> str:
        """
        Get existing mapping or create new one.

        Args:
            entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
            original_value: Original value to anonymize

        Returns:
            Fake value (consistent across calls)
        """
        if entity_type not in self.mappings:
            self.mappings[entity_type] = {}

        if original_value not in self.mappings[entity_type]:
            self.mappings[entity_type][original_value] = self._generate_fake(
                entity_type
            )

        return self.mappings[entity_type][original_value]

    def _generate_fake(self, entity_type: str) -> str:
        """
        Generate fake value for entity type.

        Supported entity types:
        - PERSON: Full names
        - PERSON_FIRST_NAME: First names only
        - PERSON_LAST_NAME: Last names only
        - ORGANIZATION: Company names
        - EMAIL_ADDRESS: Email addresses
        - PHONE_NUMBER: Phone numbers
        - PROJECT_NAME: Project names
        - PROJECT_DESCRIPTION: Short descriptions
        - LOCATION: Office/branch locations
        """
        if entity_type == "PERSON":
            return self.fake.name()
        elif entity_type == "PERSON_FIRST_NAME":
            return self.fake.first_name()
        elif entity_type == "PERSON_LAST_NAME":
            return self.fake.last_name()
        elif entity_type == "ORGANIZATION":
            return self.fake.company()
        elif entity_type == "EMAIL_ADDRESS":
            return self.fake.email()
        elif entity_type == "PHONE_NUMBER":
            return self.fake.phone_number()
        elif entity_type == "PROJECT_NAME":
            return f"Project {self.fake.word().title()}"
        elif entity_type == "PROJECT_DESCRIPTION":
            return self.fake.catch_phrase()
        elif entity_type == "LOCATION":
            return f"{self.fake.city()}, {self.fake.state_abbr()}"
        else:
            return f"<{entity_type}:{self.fake.word()}>"

    def to_dict(self) -> dict:
        """Export mappings for audit trail"""
        return {
            "entity_types": list(self.mappings.keys()),
            "total_mappings": sum(len(m) for m in self.mappings.values()),
            "mappings": self.mappings,
        }
