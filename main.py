# main.py
"""
Ponto de entrada do SICONAE.
- Funciona tanto em build DEBUG (com console) quanto RELEASE (windowed, sem console).
- Grava logs em %USERPROFILE%\\controle_notas_erro.log
- Ativa faulthandler mesmo sem stderr (redireciona para arquivo).
"""

import os
import sys
import traceback
import logging
import faulthandler
import tkinter as tk
from tkinter import messagebox

from telas.tela_inicial import montar_tela_inicial

# Caminho padrão de log do usuário
LOG_PATH = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")

# Mantemos referência do arquivo do faulthandler para não fechar
_FAULT_FILE = None


def install_crash_logger():
    """
    Configura logging para arquivo (sempre) e para console quando disponível.
    Define sys.excepthook para registrar qualquer exceção não tratada.
    Também habilita o faulthandler corretamente em ambiente windowed.
    """
    global _FAULT_FILE

    # Handlers do logging: sempre arquivo; console apenas se existir stdout
    handlers = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    logging.getLogger("bootstrap").debug("logger iniciado; LOG_PATH=%s", LOG_PATH)

    # Faulthandler: ativa no stderr (se houver) ou num arquivo
    try:
        if sys.stderr is not None:
            faulthandler.enable()
        else:
            # Em --windowed, stderr é None; direcione para arquivo
            _FAULT_FILE = open(LOG_PATH, "a", buffering=1)
            faulthandler.enable(_FAULT_FILE)
    except Exception as e:
        logging.getLogger("bootstrap").warning("falha ao ativar faulthandler: %s", e)

    # Registrar exceções não tratadas
    def excepthook(exc_type, exc, tb):
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 80 + "\n")
                traceback.print_exception(exc_type, exc, tb, file=f)
        finally:
            # tenta mostrar mensagem se já houver Tk rodando
            try:
                messagebox.showerror("Erro inesperado", f"{exc}\n\nLog: {LOG_PATH}")
            except Exception:
                # sem Tk disponível: apenas escreve no arquivo/console
                print("ERRO não tratado:", exc, file=sys.stderr or sys.stdout)

    sys.excepthook = excepthook


def main():
    # Aviso de segurança (apenas no console se houver)
    if not os.environ.get("APP_PEPPER"):
        try:
            print("[AVISO] APP_PEPPER não definido. Configure uma variável do ambiente segura.")
        except Exception:
            # Em windowed, print não aparece; sem problemas
            pass

    install_crash_logger()

    print("[DEBUG] Boot: criando Tk()") if sys.stdout else None
    root = tk.Tk()
    root.title("SICONAE — Sistema de Controle de Atas e Empenhos")
    root.geometry("920x540")
    root.minsize(760, 460)

    print("[DEBUG] Montando tela inicial…") if sys.stdout else None
    montar_tela_inicial(root)

    print("[DEBUG] Chamando mainloop()") if sys.stdout else None
    root.mainloop()
    print("[DEBUG] mainloop() terminou") if sys.stdout else None


if __name__ == "__main__":
    main()
