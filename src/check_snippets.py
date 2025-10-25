import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Literal

from question import Question, Tag
from repository import AnkiRepository, DirectoryRepository


def get_user_input() -> Literal["REPLACE", "IGNORE", "MOVE ON"]:
    print()
    response = input("Enter 'r' to replace, 'i' to ignore in future, anything else to move on: ")
    if response == "r":
        return "REPLACE"
    elif response == "i":
        return "IGNORE"
    else:
        return "MOVE ON"


def check_output(args) -> int:
    repository = DirectoryRepository() if Path(args.target).is_dir() else AnkiRepository()
    failed: list[Question] = []
    fixed: list[Question] = []
    ignored: list[Question] = []
    repository = repository
    questions = repository.get(args.target)
    questions_to_check = [question for question in questions if question.check_output]
    print("----------")

    for question in questions_to_check:
        if not question.has_ok_output():
            print(f"\N{CROSS MARK} Unexpected output for {question.id}.", end="\n\n")
            print("Code:")
            colour_print(question.snippet.code, colour="cyan", end="\n\n")
            print("Output (normalised):")
            colour_print(question.snippet.output.normalised, colour="green", end="\n\n")
            print("Given (normalised):")
            colour_print(question.output.normalised, colour="red", end="\n\n")
            failed.append(question)
            if args.interactive:
                response = get_user_input()
                if response == "REPLACE":
                    repository.fix_output(question)
                    fixed.append(question)
                    print("\N{SPARKLES} Replaced.", end="\n\n")
                elif response == "IGNORE":
                    repository.add_tag(question, Tag.NO_CHECK_OUTPUT)
                    ignored.append(question)
                    print("\N{SEE-NO-EVIL MONKEY} Will ignore in future.", end="\n\n")
                else:
                    print("\N{FACE WITHOUT MOUTH} Moving on.", end="\n\n")
            print("----------", end="\n\n")

    if failed:
        print(
            f"{len(failed)} questions had bad output "
            "("
            f"{len(fixed)} fixed, "
            f"{len(ignored)} will be ignored in future, "
            f"{len(failed) - len(fixed) - len(ignored)} remaining"
            ")"
        )
        return 1
    else:
        print("\N{WHITE HEAVY CHECK MARK} All good.")
        return 0


def check_formatting(args) -> int:
    repository = DirectoryRepository() if Path(args.target).is_dir() else AnkiRepository()
    failed: list[Question] = []
    fixed: list[Question] = []
    ignored: list[Question] = []
    repository = repository
    questions = repository.get(args.target)
    questions_to_check = [question for question in questions if question.check_formatting]
    print("----------")

    for question in questions_to_check:
        formatted = question.snippet.format(compressed=isinstance(repository, AnkiRepository))  # TODO: hack
        if formatted is None:
            # error when trying to format snippet
            # treat as non-fixable failure
            print(f"\N{CROSS MARK} Error when formatting {question.id}.", end="\n\n")
            print("Given:")
            colour_print(question.snippet.code, colour="red")
            failed.append(question)
            print("----------")
        elif formatted != question.snippet.code:
            print(f"\N{CROSS MARK} Unexpected formatting for {question.id}.", end="\n\n")
            print("Formatted:")
            colour_print(formatted, colour="green", end="\n\n")
            print("Given:")
            colour_print(question.snippet.code, colour="red")
            failed.append(question)
            if args.interactive:
                response = get_user_input()
                if response == "REPLACE":
                    repository.fix_formatting(question)
                    fixed.append(question)
                    print("\N{SPARKLES} Replaced.")
                elif response == "IGNORE":
                    repository.add_tag(question, Tag.NO_CHECK_FORMATTING)
                    ignored.append(question)
                    print("\N{SEE-NO-EVIL MONKEY} Will ignore in future.")
                else:
                    print("\N{FACE WITHOUT MOUTH} Moving on.")
            print("----------")

    if failed:
        print(
            f"{len(failed)} questions had bad formatting "
            "("
            f"{len(fixed)} fixed, "
            f"{len(ignored)} will be ignored in future, "
            f"{len(failed) - len(fixed) - len(ignored)} left"
            ")"
        )
        return 1
    else:
        print("\N{WHITE HEAVY CHECK MARK} All good.")
        return 0


def colour_print(string: str, colour: str, **kwargs) -> None:
    if colour == "green":
        print("\033[92m" + string + "\033[0m", **kwargs)
    elif colour == "red":
        print("\033[91m" + string + "\033[0m", **kwargs)
    elif colour == "cyan":
        print("\033[96m" + string + "\033[0m", **kwargs)
    else:
        raise ValueError(f"unsupported colour: {colour}")


def main() -> int:
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

    args = parser.parse_args()

    exit_code = args.func(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
