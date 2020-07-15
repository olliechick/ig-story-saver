def write_to_file(filename, contents, mode='w+', encoding="utf-8", errors='ignore'):
    """ Writes contents to file filename """
    out_file = open(filename, mode, encoding=encoding, errors=errors)
    out_file.write(contents)
    out_file.close()


def read_file(filename, mode='r', encoding="utf-8", errors='ignore'):
    """ Returns the contents of the file filename"""
    in_file = open(filename, mode, encoding=encoding, errors=errors)
    lines = in_file.readlines()
    in_file.close()
    return lines
