# main.py
import os
import sys
import tkinter as tk
from tkinter import messagebox
import traceback

from telas.tela_inicial import montar_tela_inicial

# main.py
import os, sys, traceback, logging, faulthandler
faulthandler.enable()

def install_crash_logger():
    log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8")
        ],
    )
    def excepthook(exc_type, exc, tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n" + "="*80 + "\n")
                traceback.print_exception(exc_type, exc, tb, file=f)
        finally:
            print("ERRO não tratado:", exc, file=sys.stderr)
    sys.excepthook = excepthook

install_crash_logger()

import tkinter as tk
from telas.tela_inicial import montar_tela_inicial

def main():
    if not os.environ.get("APP_PEPPER"):
        print("[AVISO] APP_PEPPER não definido. Configure uma variável do ambiente segura.")

    print("[DEBUG] Boot: criando Tk()")
    root = tk.Tk()
    root.title("SICONAE — Sistema de Controle de Atas e Empenhos")
    root.geometry("920x540")
    root.minsize(760, 460)

    print("[DEBUG] Montando tela inicial…")
    montar_tela_inicial(root)
    print("[DEBUG] Chamando mainloop()")
    root.mainloop()
    print("[DEBUG] mainloop() terminou")

if __name__ == "__main__":
    main()

  
