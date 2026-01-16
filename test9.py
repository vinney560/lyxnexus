import os
def _reverse(word) -> str:
    _reversed = word[::-1]
    return _reversed
def _split_word(word):
    name, ext = os.path.splitext(word)
    
    print(f"{name} {ext}")

word = 'Lyxin'

_split_word(word)