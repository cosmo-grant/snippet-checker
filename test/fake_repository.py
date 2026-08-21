from snippet_checker.repository import Repository


class FakeRepository(Repository):
    def __init__(self, questions):
        self.questions = questions

    def get(self):
        return self.questions

    def write_output(self, question, output):
        super().write_output(question, output)

    def write_code(self, question, code):
        super().write_code(question, code)

    def add_tag(self, question, tag):
        super().add_tag(question, tag)
