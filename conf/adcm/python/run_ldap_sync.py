def print_hello(file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("Hello")


file = 'test.txt'
print_hello(file)
