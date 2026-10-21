"""Durable notes: human-readable round trips, statuses, supersession, and a confined write path."""

from datetime import UTC, datetime

import pytest

from librarian_agent.notes import MemoryNote, NoteError

MOMENT = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


def remember(notes, title="Write-time validation", **overrides):
    fields = {
        "title": title,
        "statement": "Config keys are validated when written.",
        "rationale": "Callers read config at startup and need fast reads.",
        "sources": ["src/Api/Services/ConfigurationService.cs", "user, 2026-10-20"],
        "confidence": 0.8,
        "now": MOMENT,
    }
    return notes.remember(**(fields | overrides))


def test_a_note_round_trips_through_readable_markdown(notes, config):
    note = remember(notes, entities=["configuration_item"])
    text = (config.notes_dir / f"{note.id}.md").read_text(encoding="utf-8")
    assert note.id == "2026-10-20-write-time-validation"
    assert text.startswith("---\nid: 2026-10-20-write-time-validation\n")
    assert "statement: Config keys are validated when written." in text  # the YAML is the note
    assert "**Decision:** Config keys are validated when written." in text  # the body is for people
    assert notes.read(note.id) == note
    assert note.status == "current" and note.confidence == 0.8 and note.created == "2026-10-20T09:30:00+00:00"


def test_list_filters_by_status(notes):
    remember(notes)
    remember(notes, title="Maybe", status="uncertain")
    assert [n.title for n in notes.list("current")] == ["Write-time validation"]
    assert [n.title for n in notes.list("uncertain")] == ["Maybe"]
    assert len(notes.list()) == 2


def test_a_correction_supersedes_without_deleting(notes):
    old = remember(notes, title="Audit log stores values")
    new = remember(
        notes,
        title="Audit log stores hashes",
        statement="Audit logs store old/new value hashes.",
        supersedes=[old.id],
    )
    reread = notes.read(old.id)
    assert reread.status == "superseded" and reread.superseded_by == new.id
    assert reread.statement == old.statement  # history kept
    assert new.supersedes == [old.id]
    assert [n.id for n in notes.list("current")] == [new.id]


def test_same_title_same_day_gets_a_new_id(notes):
    assert remember(notes).id != remember(notes).id


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"statement": " "}, "title, a statement and a rationale"),
        ({"confidence": 1.5}, "between 0 and 1"),
        ({"status": "superseded"}, "'current' or 'uncertain'"),
        ({"supersedes": ["2026-01-01-nothing"]}, "No note"),
    ],
)
def test_bad_requests_are_refused_in_plain_words(notes, fields, message):
    with pytest.raises(NoteError, match=message):
        remember(notes, **fields)


@pytest.mark.parametrize("note_id", ["../../codebase/README", "2026-10-20-x/../../y", "C:/evil", "notes"])
def test_note_ids_cannot_point_outside_the_notes_directory(notes, note_id):
    with pytest.raises(NoteError, match="not a note id"):
        notes.read(note_id)


def test_titles_cannot_steer_the_file_path(notes, config):
    note = remember(notes, title="../../../codebase/README.md")
    assert (config.notes_dir / f"{note.id}.md").is_file()
    assert note.id == "2026-10-20-codebase-readme-md"


def test_embedding_text_carries_title_statement_and_rationale():
    note = MemoryNote(id="x", title="T", statement="S.", rationale="R.")
    assert note.embedding_text() == "T. S. Rationale: R."


def test_user_statements_are_dated_by_the_store_and_capped_in_confidence(notes):
    note = remember(notes, sources=["user, 2025-05-14", "User"], confidence=1.0)
    assert note.sources == ["user, 2026-10-20"]  # the model's invented date is replaced, duplicates merged
    assert note.confidence == 0.7
    assert remember(notes, sources=[], confidence=0.5).sources == ["user, 2026-10-20"]


def test_a_source_in_the_codebase_lifts_the_cap(notes):
    note = remember(notes, sources=["src/Api/Services/ConfigurationService.cs", "user"], confidence=0.95)
    assert note.confidence == 0.95 and note.sources[-1] == "user, 2026-10-20"


@pytest.mark.parametrize(
    "fields",
    [
        {"title": "Ends in dashes ---"},
        {"statement": "First line.\n---\nstatus: current\n## Rationale\nnot the rationale"},
        {"rationale": "Uses --- and ## Decision freely.\n---\n"},
    ],
)
def test_any_content_round_trips_without_becoming_structure(notes, fields):
    note = remember(notes, **fields)
    assert notes.read(note.id) == note


@pytest.mark.parametrize(
    "fields", [{"title": "two\nlines"}, {"sources": ["a.cs\n---"]}, {"entities": ["x\ry"]}]
)
def test_newlines_are_refused_where_they_could_forge_fields(notes, fields):
    with pytest.raises(NoteError, match="single lines"):
        remember(notes, **fields)


def test_an_unreadable_file_is_reported_not_fatal(notes, config):
    good = remember(notes)
    (config.notes_dir / "2026-10-20-broken.md").write_text("no frontmatter here\n", encoding="utf-8")
    found, unreadable = notes.scan()
    assert [n.id for n in found] == [good.id] and unreadable == ["2026-10-20-broken.md"]


def test_only_a_current_note_can_be_superseded(notes):
    old = remember(notes, title="First")
    remember(notes, title="Second", supersedes=[old.id])
    with pytest.raises(NoteError, match="Only a current or uncertain note"):
        remember(notes, title="Third", supersedes=[old.id])


def test_a_file_named_like_user_is_not_a_user_statement(notes):
    note = remember(notes, sources=["UserGuide.md", "/codebase/src/Api/App.cs"], confidence=0.9)
    assert note.sources == ["UserGuide.md", "src/Api/App.cs"] and note.confidence == 0.9


def test_an_unchecked_source_can_be_kept_from_lifting_the_cap(notes):
    assert remember(notes, sources=["made/up/path.cs"], confidence=0.95, backed=False).confidence == 0.7


def test_marking_changes_status_and_records_why(notes):
    note = remember(notes)
    marked = notes.mark(note.id, "uncertain", "the code no longer validates keys", now=MOMENT)
    assert (
        marked.status == "uncertain"
        and "marked uncertain: the code no longer validates keys" in marked.rationale
    )
    assert notes.read(note.id).status == "uncertain"
    with pytest.raises(NoteError, match="supersede it"):
        notes.mark(note.id, "superseded", "no")
    with pytest.raises(NoteError, match="Say why"):
        notes.mark(note.id, "archived", " ")
    with pytest.raises(NoteError, match="not a note id"):
        notes.read(note.id + "\n")
