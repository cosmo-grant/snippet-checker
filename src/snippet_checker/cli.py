from argparse import ArgumentParser
from pathlib import Path

from .check_snippets import check_formatting, check_output
from .repository import AnkiRepository, DirectoryRepository
from .snippet import Snippet

parser = ArgumentParser()
parser.add_argument("target", help="directory or anki tag of the questions you want to check")
subparsers = parser.add_subparsers(required=True)

check_output_parser = subparsers.add_parser("check-output", help="check snippet output")
check_output_parser.add_argument(
    "-i", "--interactive", action="store_true", help="get user input for whether to fix, ignore in future, or leave as is"
)
check_output_parser.set_defaults(func=check_output)

check_formatting_parser = subparsers.add_parser("check-formatting", help="check snippet formatting")
check_formatting_parser.add_argument(
    "--interactive", action="store_true", help="get user input for whether to fix, ignore in future, or leave as is"
)
check_formatting_parser.set_defaults(func=check_formatting)


def app() -> None:
    args = parser.parse_args()

    # TODO: how to tell if the target is meant to be taken as a directory or an anki tag?
    # i take a simple, risky approach: take it as a directory if a same-named directory exists, else an anki tag
    maybe_dir = Path(args.target)
    repository = DirectoryRepository(maybe_dir) if maybe_dir.is_dir() else AnkiRepository(args.target)

    try:
        args.func(repository, args.interactive)
    finally:
        Snippet.cleanup()


if __name__ == "__main__":
    app()
