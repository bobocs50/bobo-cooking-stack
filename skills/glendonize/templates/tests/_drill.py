"""The pass/fail line every drill prints; shared so the copies cannot drift."""


def expect(label, condition):
    print(("  ok   " if condition else "  FAIL ") + label)
    return condition
