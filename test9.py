import os
def _reverse(word) -> str:
    _reversed = word[::-1]
    return _reversed
def _split_word(word):
    name, ext = os.path.splitext(word)
    
    print(f"Name: {name} | Ext: {ext}")

word = 'Lyxin.lyx'

output = _reverse(word)
print(output)
_split_word(word)