import re


class Fingerprint(list):

    def __init__(self, fingerprint_s) -> None:
        super().__init__()
        for entry in re.findall("................", fingerprint_s):
            self.append(entry)