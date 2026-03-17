import tkinter as tk
from telas.dashboard import Dashboard
from telas.fornecedores import TelaFornecedores
import sys
import os

# Corrige caminho quando vira EXE
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

sys.path.append(base_path)

class Sistema(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Controle de Notas e Empenhos")
        self.geometry("1000x600")

        self.menu_lateral()
        self.area_trabalho()

    def menu_lateral(self):

        menu = tk.Frame(self, width=200, bg="#2c3e50")
        menu.pack(side="left", fill="y")

        tk.Button(menu, text="Dashboard", command=self.abrir_dashboard).pack(fill="x")
        tk.Button(menu, text="Fornecedores", command=self.abrir_fornecedores).pack(fill="x")

    def area_trabalho(self):

        self.container = tk.Frame(self)
        self.container.pack(side="right", expand=True, fill="both")

    def limpar(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def abrir_dashboard(self):
        self.limpar()
        tela = Dashboard(self.container)
        tela.pack(fill="both", expand=True)
        
    def abrir_fornecedores(self):
        self.limpar()
        TelaFornecedores(self.container)


if __name__ == "__main__":
    app = Sistema()
    app.mainloop()
