from enum import Enum

from .question import Question, Tag
from .repository import AnkiRepository, Repository


class UserInput(Enum):
    REPLACE = "REPLACE"
    IGNORE = "IGNORE"
    MOVE_ON = "MOVE ON"
    REVIEW = "REVIEW"


def get_user_input() -> UserInput:
    print()
    response = input("Enter 'r' to replace, 'i' to ignore in future, 'v' to tag for review and move on, anything else to just move on: ")
    if response == "r":
        return UserInput("REPLACE")
    elif response == "i":
        return UserInput("IGNORE")
    elif response == "v":
        return UserInput("REVIEW")
    else:
        return UserInput("MOVE ON")


def check_output(repository: Repository, interactive: bool) -> int:
    failed: list[Question] = []
    fixed: list[Question] = []
    ignored: list[Question] = []
    questions = repository.get()
    questions_to_check = [question for question in questions if question.check_output]

    print(f"Found {len(questions)} questions.")
    print(f"Will check {len(questions_to_check)}.")
    print("----------")

    for question in questions_to_check:
        if not question.has_ok_output():
            print(f"\N{CROSS MARK} Bad output for {question.id}.", end="\n\n")
            print("Code:")
            colour_print(question.snippet.code, colour="cyan", end="\n\n")
            print("Output (normalised):")
            colour_print(question.snippet.output.normalised, colour="green", end="\n\n")
            print("Given:")
            colour_print(question.output.raw, colour="red")
            failed.append(question)
            if interactive:
                response = get_user_input()
                if response == UserInput.REPLACE:
                    repository.fix_output(question)
                    fixed.append(question)
                    print("\N{SPARKLES} Replaced.")
                elif response == UserInput.IGNORE:
                    repository.add_tag(question, Tag.NO_CHECK_OUTPUT)
                    ignored.append(question)
                    print("\N{SEE-NO-EVIL MONKEY} Will ignore in future.")
                elif response == UserInput.REVIEW:
                    repository.add_tag(question, Tag.REVIEW)
                    print("\N{RIGHT-POINTING MAGNIFYING GLASS} Added 'review' tag.")
                else:
                    print("\N{FACE WITHOUT MOUTH} Moving on.")
            print("----------")

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


def check_formatting(repository: Repository, interactive: bool) -> int:
    failed: list[Question] = []
    fixed: list[Question] = []
    ignored: list[Question] = []
    questions = repository.get()
    questions_to_check = [question for question in questions if question.check_formatting]

    print(f"Found {len(questions)} questions.")
    print(f"Will check {len(questions_to_check)}.")
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
            print(f"\N{CROSS MARK} Bad formatting for {question.id}.", end="\n\n")
            print("Formatted:")
            colour_print(formatted, colour="green", end="\n\n")
            print("Given:")
            colour_print(question.snippet.code, colour="red")
            failed.append(question)
            if interactive:
                response = get_user_input()
                if response == UserInput.REPLACE:
                    repository.fix_formatting(question)
                    fixed.append(question)
                    print("\N{SPARKLES} Replaced.")
                elif response == UserInput.IGNORE:
                    repository.add_tag(question, Tag.NO_CHECK_FORMATTING)
                    ignored.append(question)
                    print("\N{SEE-NO-EVIL MONKEY} Will ignore in future.")
                elif response == UserInput.REVIEW:
                    repository.add_tag(question, Tag.REVIEW)
                    print("\N{RIGHT-POINTING MAGNIFYING GLASS} Added 'review' tag.")
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
