from argparse import ArgumentParser
from pathlib import Path

from .check_snippets import check_formatting, check_output
from .repository import AnkiRepository, DirectoryRepository
from .snippet import Snippet

parser = ArgumentParser()
parser.add_argument("target", help="directory or anki tag of the questions you want to check")
parser.add_argument("--anki-profile", "-p", help="name of anki profile to use, if relevant")
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
    repository = AnkiRepository(args.anki_profile, args.target) if args.anki_profile is not None else DirectoryRepository(Path(args.target))

    try:
        args.func(repository, args.interactive)
    finally:
        Snippet.cleanup()


if __name__ == "__main__":
    app()
