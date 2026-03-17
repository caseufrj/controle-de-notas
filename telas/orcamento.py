# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import banco


class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)

        self._carregar_fornecedores()

        form = ttk.LabelFrame(self, text="Lançar itens para Orçamento")
        form.pack(fill="x", padx=12, pady=8)

        def r(lbl, col, row, width=28):
            tk.Label(form, text=lbl).grid(column=col, row=row, sticky="w", padx=6, pady=3)
            e = ttk.Entry(form, width=width)
            e.grid(column=col+1, row=row, sticky="w", padx=6, pady=3)
            return e

        self.e_cod = r("Cód AGHU*:", 0, 0)
        self.e_nome = r("Nome item*:", 0, 1, 40)
        self.e_qt = r("Qtde*:", 2, 0, 12)
        self.e_vu = r("Vlr Unit*:", 2, 1, 12)
        self.e_emp = r("Nº Empenho:", 4, 0)
        tk.Label(form, text="Observação:").grid(column=4, row=1, sticky="w", padx=6, pady=3)
        self.e_obs = ttk.Entry(form, width=40)
        self.e_obs.grid(column=5, row=1, sticky="w", padx=6, pady=3)

        tk.Label(form, text="Mensagem p/ e-mail:").grid(column=0, row=3, sticky="nw", padx=6, pady=3)
        self.txt_msg = tk.Text(form, width=80, height=4)
        self.txt_msg.grid(column=1, row=3, columnspan=5, sticky="w", padx=6, pady=3)

        btns = tk.Frame(form)
        btns.grid(column=5, row=0, rowspan=2, sticky="e", padx=6)
        ttk.Button(btns, text="Adicionar", command=self._adicionar).pack(side="top", pady=2)

        # Tabela temporária
        cols = ("cod","nome","qt","vu","emp","obs","vl_total")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=12)
        heads = ("Cód AGHU","Nome","Qtde","Vlr Unit","Nº Empenho","Obs","Vlr Total")
        widths = (100,260,60,90,120,180,100)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h)
            self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=12, pady=6)

        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=10)
        ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel).pack(side="right", padx=6)
        ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email).pack(side="right", padx=6)

    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs:
            self.cb_fornec.current(0)

    def _adicionar(self):
        try:
            qt = float(self.e_qt.get() or 0)
            vu = float(self.e_vu.get() or 0)
        except ValueError:
            messagebox.showwarning("Validação","Digite números válidos em Qtde/Valor.")
            return
        if not (self.e_cod.get().strip() and self.e_nome.get().strip() and qt and vu):
            messagebox.showwarning("Validação","Preencha código, nome, qtde e valor unitário.")
            return
        vt = qt * vu
        self.tv.insert("", "end", values=(
            self.e_cod.get().strip(),
            self.e_nome.get().strip(),
            f"{qt}",
            f"{vu:.2f}",
            self.e_emp.get().strip(),
            self.e_obs.get().strip(),
            f"{vt:.2f}"
        ))
        # limpa campos
        for e in (self.e_cod, self.e_nome, self.e_qt, self.e_vu, self.e_emp, self.e_obs):
            e.delete(0, "end")

    # ---------- Placeholders a implementar ----------
    def _exportar_excel(self):
        # Próxima etapa: gerar .xlsx com pandas
        arq = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Salvar orçamento")
        if not arq:
            return
        # Aqui vamos montar um DataFrame e salvar — implemento quando você der o OK.
        messagebox.showinfo("Exportação", f"Planilha será salva em:\n{arq}\n(Implementaremos na próxima etapa)")

    def _enviar_email(self):
        # Próxima etapa: enviar via smtplib, usando e-mail do fornecedor (cadastro) e a mensagem.
        messagebox.showinfo("E-mail", "Envio por e-mail será implementado na próxima etapa.\nIncluiremos configuração SMTP e corpo da mensagem.")
