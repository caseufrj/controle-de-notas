# main.py
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import sys
import os

import traceback
from tkinter import messagebox

# Importa as telas
from telas.dashboard import Dashboard
from telas.fornecedores import TelaFornecedores
from telas.atas_empenhos import TelaAtasEmpenhos
from telas.notas import TelaNotas
from telas.orcamento import TelaOrcamento

# Corrige caminho quando vira EXE (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_PATH = os.path.dirname(__file__)

sys.path.append(BASE_PATH)


class Sistema(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Controle de Notas e Empenhos")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._estilos()
        self._menu_lateral()
        self._area_trabalho()

        # Tela inicial
        self.abrir_dashboard()

    def _estilos(self):
        """
        Opção A: configura a fonte padrão via TkDefaultFont (evita o erro 'expected integer but got "UI"').
        """
        # Ajusta a fonte padrão de toda a aplicação
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.option_add("*Font", default_font)

        # Tema ttk
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _menu_lateral(self):
        self.menu = tk.Frame(self, width=200, bg="#2c3e50")
        self.menu.pack(side="left", fill="y")

        def btn(text, cmd):
            b = tk.Button(
                self.menu,
                text=text,
                command=cmd,
                bg="#34495e",
                fg="white",
                bd=0,
                padx=12,
                pady=12,
                activebackground="#3d566e",
                activeforeground="white",
                anchor="w",
            )
            b.pack(fill="x")
            return b

        self.btn_dash = btn("Dashboard", self.abrir_dashboard)
        self.btn_forn = btn("Fornecedores", self.abrir_fornecedores)
        self.btn_atas = btn("Ata / Empenho", self.abrir_atas_empenhos)
        self.btn_notas = btn("Notas Fiscais", self.abrir_notas)
        self.btn_orc = btn("Orçamento", self.abrir_orcamento)

    def _area_trabalho(self):
        self.container = tk.Frame(self, bg="#ecf0f1")
        self.container.pack(side="right", expand=True, fill="both")

    def limpar(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --------- Navegação ----------
    
    def _abrir_tela(self, classe_tela, nome_log="tela"):
            self.limpar()
            try:
                tela = classe_tela(self.container)
                tela.pack(fill="both", expand=True)
            except Exception as e:
                # Loga em arquivo para análise
                log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("\n" + "="*80 + "\n")
                    f.write(f"Erro ao abrir {nome_log}:\n")
                    f.write(traceback.format_exc())
    
                messagebox.showerror(
                    "Erro",
                    f"Ocorreu um erro ao abrir a tela '{nome_log}'.\n\n"
                    f"{e}\n\n"
                    f"Um log foi salvo em:\n{log_path}"
                )
    
    def abrir_dashboard(self):
        self._abrir_tela(Dashboard, "Dashboard")

    def abrir_fornecedores(self):
        self._abrir_tela(TelaFornecedores, "Fornecedores")

    def abrir_atas_empenhos(self):
        self._abrir_tela(TelaAtasEmpenhos, "Ata/Empenho")

    def abrir_notas(self):
        self._abrir_tela(TelaNotas, "Notas")

    def abrir_orcamento(self):
        self._abrir_tela(TelaOrcamento, "Orçamento")


if __name__ == "__main__":
    app = Sistema()
    app.mainloop()
