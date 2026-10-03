from app import should_save_memory
from src.memory import build_memory_entries


def test_memory_requires_approved_hil():
    assert should_save_memory("hassan", "approve")
    assert should_save_memory("hassan", "edit")
    assert not should_save_memory("hassan", "reject")
    assert not should_save_memory("hassan", "pending")
    assert not should_save_memory(None, "approve")


def test_property_search_memory_entries():
    entries = build_memory_entries(
        "Find three apartments in New Cairo under 5M EGP.",
        ["property_search"],
    )

    assert entries == [
        "Episodic conversation summary: Find three apartments in New Cairo under 5M EGP.",
        "Client preferences: Find three apartments in New Cairo under 5M EGP.",
    ]


def test_scheduling_memory_entries():
    entries = build_memory_entries(
        "Schedule listing_001 for Hassan tomorrow at 15:00.",
        ["scheduling"],
    )

    assert entries == [
        "Episodic conversation summary: Schedule listing_001 for Hassan tomorrow at 15:00.",
        "Ongoing deal: Schedule listing_001 for Hassan tomorrow at 15:00.",
    ]


def test_combined_memory_entries():
    entries = build_memory_entries(
        "Find an apartment and schedule a viewing.",
        ["property_search", "scheduling"],
    )

    assert len(entries) == 3
    assert entries[0].startswith("Episodic conversation summary:")
    assert entries[1].startswith("Client preferences:")
    assert entries[2].startswith("Ongoing deal:")


def test_generic_memory_entry():
    entries = build_memory_entries(
        "Draft a follow-up message for Hassan.",
        ["communication"],
    )

    assert entries == [
        "Episodic conversation summary: Draft a follow-up message for Hassan."
    ]
