# main.py
import os
import sys
import tkinter as tk

# Corrige caminho quando vira EXE (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_PATH = os.path.dirname(__file__)

from telas.tela_inicial import montar_tela_inicial

def main():
    if not os.environ.get("APP_PEPPER"):
        print("[AVISO] APP_PEPPER não definido. Configure uma variável de ambiente segura.")

    root = tk.Tk()
    root.title("SICONAE — Sistema de Controle de Atas e Empenhos")
    root.geometry("920x540")
    root.minsize(760, 460)

    montar_tela_inicial(root)

    root.mainloop()

if __name__ == "__main__":
    main()
