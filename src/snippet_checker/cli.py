import logging
from argparse import ArgumentParser
from pathlib import Path

from .check_snippets import check_formatting, check_output
from .repository import AnkiRepository, DirectoryRepository

parser = ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
parser.add_argument("--anki-profile", "-p", help="Check anki, using the given profile. (Checks a directory by default.)")
mode = parser.add_mutually_exclusive_group()
mode.add_argument("-c", "--check", action="store_const", const="check", dest="mode", help="Check and report failures (default).")
mode.add_argument(
    "-i",
    "--interactive",
    action="store_const",
    const="interactive",
    dest="mode",
    help="Prompt user to fix, ignore in future, or leave as is.",
)
mode.add_argument("-f", "--fix", action="store_const", const="fix", dest="mode", help="Automatically fix fixable failures.")
parser.set_defaults(mode="check")
parser.add_argument("command", choices=["output", "format"], help="Command to run.")
parser.add_argument("target", help="Directory or anki tag of the questions to check.")


def app() -> None:
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    repository = AnkiRepository(args.anki_profile, args.target) if args.anki_profile is not None else DirectoryRepository(Path(args.target))
    func = check_output if args.command == "output" else check_formatting
    func(repository, args.mode)


if __name__ == "__main__":
    app()
