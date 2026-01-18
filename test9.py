def get_file_ext(filename: str) -> str:
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return file_ext
print(get_file_ext("example.txt"))  # Output: txt