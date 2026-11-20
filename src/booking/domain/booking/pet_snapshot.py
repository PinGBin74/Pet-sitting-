"""PetSnapshot: pet data copied into the booking at request time."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class Species(StrEnum):
    CAT = "cat"
    DOG = "dog"


@dataclass(frozen=True, slots=True)
class PetSnapshot:
    """A copy, not a reference to the pet card.

    The host agrees to take this exact pet. Editing the card after confirmation
    must not silently change what the host agreed to (docs/domain/aggregates.md).
    """

    pet_id: UUID
    species: Species
    breed: str
    weight_kg: Decimal
    vaccinated_on: date | None
    notes: str = ""
