import pathlib

content = pathlib.Path("content.txt").read_text()
pathlib.Path("src/inventory/infrastructure/repositories/stock.py").write_text(content)
print("done")
