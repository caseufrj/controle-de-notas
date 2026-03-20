# main.py
"""
Ponto de entrada do SICONAE/Controle de Notas.
Agora o app inicia pela Tela Inicial (LOGIN/REGISTRO) e, após autenticar,
abre o dashboard/telas principais.

Compatível com PyInstaller (onefile/--windowed).
"""

import os
import sys

# Corrige caminho quando vira EXE (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_PATH = os.path.dirname(__file__)

# Se você usa assets (imagens/logo), pode precisar deste path:
# os.chdir(BASE_PATH)

# Apenas inicia a Tela Inicial; ela cuida do resto (login/registro → dashboard)
from telas.tela_inicial import tela_inicial

def main():
    # Aviso opcional sobre o pepper (segredo de hash de senhas)
    if not os.environ.get("APP_PEPPER"):
        # Não bloqueia execução; apenas alerta no console (útil ao rodar via terminal)
        print("[AVISO] APP_PEPPER não definido. Defina uma variável de ambiente segura para fortalecer o hash de senhas.")

    # Sobe a tela inicial (gradiente + botões LOGIN / REGISTRO)
    tela_inicial()

if __name__ == "__main__":
    main()
