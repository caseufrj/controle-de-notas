# dashboard.py
import tkinter as tk
from tkinter import ttk
from banco import conectar

BODY_BG = "#efefef"
CARD_BG = "#ffffff"

class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BODY_BG)

        tk.Label(self, text="Dashboard", font=("Segoe UI Semibold", 18), bg=BODY_BG).pack(anchor="w", padx=20, pady=(20, 10))

        cards = tk.Frame(self, bg=BODY_BG)
        cards.pack(anchor="w", padx=20)

        total_fornec = self._scalar("SELECT COUNT(1) FROM fornecedores")
        total_notas  = self._scalar("SELECT COUNT(1) FROM notas")
        total_empenhos = self._scalar("SELECT COUNT(1) FROM empenhos")

        self._card(cards, "Fornecedores", total_fornec).grid(row=0, column=0, padx=(0,12), pady=6)
        self._card(cards, "Notas", total_notas).grid(row=0, column=1, padx=(0,12), pady=6)
        self._card(cards, "Empenhos", total_empenhos).grid(row=0, column=2, padx=(0,12), pady=6)

        # Saldo de exemplos
        sec = tk.LabelFrame(self, text="Saldos (amostra)", bg=BODY_BG)
        sec.pack(fill="x", padx=20, pady=(16, 20))

        cols = ("tipo", "id", "fornecedor", "cod_aghu", "saldo")
        tree = ttk.Treeview(sec, columns=cols, show="headings", height=8)
        for c in cols:
            tree.heading(c, text=c.upper())
            tree.column(c, width=140, stretch=True)
        tree.pack(fill="both", expand=True)

        # Preenche com saldo de ata e empenho (TOP 10)
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 'ATA' AS tipo, a.ata_id AS id, f.nome AS fornecedor, a.cod_aghu,
                       a.qtde_saldo AS saldo
                FROM vw_saldo_ata a
                JOIN fornecedores f ON f.id = a.fornecedor_id
                ORDER BY a.qtde_saldo ASC
                LIMIT 5
            """)
            for r in cur.fetchall():
                tree.insert("", "end", values=r)
            cur.execute("""
                SELECT 'EMPENHO' AS tipo, e.empenho_id AS id, f.nome AS fornecedor, e.cod_aghu,
                       e.valor_saldo AS saldo
                FROM vw_saldo_empenho e
                JOIN fornecedores f ON f.id = e.fornecedor_id
                ORDER BY e.valor_saldo ASC
                LIMIT 5
            """)
            for r in cur.fetchall():
                tree.insert("", "end", values=r)

    def _scalar(self, sql):
        with conectar() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            r = cur.fetchone()
            return r[0] if r else 0

    def _card(self, master, titulo, valor):
        frame = tk.Frame(master, bg=CARD_BG, highlightbackground="#ddd", highlightthickness=1, width=220, height=90)
        frame.grid_propagate(False)
        tk.Label(frame, text=titulo, bg=CARD_BG, fg="#666").grid(row=0, column=0, sticky="w", padx=12, pady=(12,0))
        tk.Label(frame, text=str(valor), bg=CARD_BG, fg="#222", font=("Segoe UI Semibold", 18)).grid(row=1, column=0, sticky="w", padx=12, pady=(6,10))
        return frame  
