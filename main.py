# main.py
import os
import sys
import tkinter as tk
from tkinter import messagebox
import traceback

from telas.tela_inicial import montar_tela_inicial

def install_crash_logger():
    """
    Captura qualquer exceção não tratada, grava em um log no perfil do usuário
    e mostra uma mensagem. Evita o efeito de 'abre e fecha' silencioso.
    """
    def excepthook(exc_type, exc, tb):
        try:
            log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n" + "="*80 + "\n")
                traceback.print_exception(exc_type, exc, tb, file=f)

            # Tenta mostrar mensagem (se o Tk existir)
            try:
                messagebox.showerror("Erro inesperado",
                                     f"{exc}\n\nUm log foi salvo em:\n{log_path}")
            except Exception:
                pass
        finally:
            # Não mata o processo aqui — deixa o Tk decidir
            pass

    sys.excepthook = excepthook

def main():
    if not os.environ.get("APP_PEPPER"):
        print("[AVISO] APP_PEPPER não definido. Configure uma variável de ambiente segura.")

    install_crash_logger()

    root = tk.Tk()
    root.title("SICONAE — Sistema de Controle de Atas e Empenhos")
    root.geometry("920x540")
    root.minsize(760, 460)

    montar_tela_inicial(root)
    root.mainloop()

if __name__ == "__main__":
    main()
