import logging

from test.open_ai_tests import OpenAiTests

logging.root.setLevel(logging.DEBUG)

if __name__ == "__main__":
    OpenAiTests()