# fix_entities.py
import os, sys

EXTS = {".py"}  # só corrige .py

# Ordem importa: primeiro os duplamente escapados (&amp;lt;), depois os simples (&lt;)
REPLACEMENTS = [
    ("&amp;lt;&amp;lt;", "<<"),
    ("&amp;gt;&amp;gt;", ">>"),
    ("-&amp;gt;", "->"),
    ("&amp;lt;", "<"),
    ("&amp;gt;", ">"),
    # fallback para escapes simples eventualmente remanescentes
    ("&lt;&lt;", "<<"),
    ("&gt;&gt;", ">>"),
    ("-&gt;", "->"),
    ("&lt;", "<"),
    ("&gt;", ">"),
]

def fix_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            original = f.read()
    new = original
    for src, dst in REPLACEMENTS:
        new = new.replace(src, dst)
    if new != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        return True
    return False

def main():
    root = os.path.abspath(".")
    changed = []
    for dirpath, _, filenames in os.walk(root):
        low = dirpath.lower()
        if any(skip in low for skip in (os.sep+"dist", os.sep+"build", os.sep+"__pycache__")):
            continue
        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext.lower() in EXTS:
                path = os.path.join(dirpath, name)
                if fix_file(path):
                    changed.append(os.path.relpath(path, root))
    if changed:
        print("Arquivos corrigidos:")
        for p in changed:
            print(" -", p)
    else:
        print("Nenhuma substituição necessária.")

if __name__ == "__main__":
    sys.exit(main())
