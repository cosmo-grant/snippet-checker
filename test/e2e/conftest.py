from anki.storage import Collection
from pytest import fixture


@fixture
def anki_config(tmp_path):
    (tmp_path / "snippet-checker").mkdir()
    config_path = tmp_path / "snippet-checker" / "snippet-checker.toml"
    config_path.write_text(f"""\
collection_path = "{tmp_path / "test_collection.anki2"}"

[[notes]]
note_type = "Basic"

[notes.code_field]
name = "Front"
pattern = "(?s)^(?P<target>.*)$"

[notes.output_field]
name = "Back"
pattern = "(?s)^(?P<target>.*)$"
""")


@fixture
def anki_collection(tmp_path):
    collection = Collection(tmp_path / "test_collection.anki2")
    deck = collection.decks.by_name("Default")
    model = collection.models.by_name("Basic")

    python_note = collection.new_note(model)
    python_note.fields[0] = "print(1 + 1)\n"
    python_note.fields[1] = "2\n"
    python_note.tags = ["check_me", "snip:image:python:3.13"]
    collection.add_note(python_note, deck["id"])
