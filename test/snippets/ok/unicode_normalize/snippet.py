from unicodedata import normalize

s1 = "ca\N{LATIN SMALL LETTER N WITH TILDE}a"
s2 = "can\N{COMBINING TILDE}a"
print(s1, s2)
print(len(s1), len(s2))
print(len(normalize("NFC", s1)), len(normalize("NFC", s2)))
