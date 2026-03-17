# orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from banco import conectar
from utils import exportar_excel, enviar_email

BODY_BG = "#efefef"

def _combo_fornecedores(parent):
    with conectar() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, email FROM fornecedores ORDER BY nome;")
        rows = cur.fetchall()
    mapa = {f"{r[1]} (id {r[0]})": (r[0], r[2] or "") for r in rows}
    var = tk.StringVar()
    cb = ttk.Combobox(parent, state="readonly", values=list(mapa.keys()), width=42, textvariable=var)
    return cb, var, mapa

class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BODY_BG)
        tk.Label(self, text="Orçamento para Fornecedor", font=("Segoe UI Semibold", 16), bg=BODY_BG)\
            .pack(anchor="w", padx=20, pady=(20, 10))

        sec = tk.LabelFrame(self, text="Itens utilizados na cirurgia (preencher)", bg=BODY_BG)
        sec.pack(fill="x", padx=20)

        self.vars = {k: tk.StringVar() for k in ["cod_aghu","nome_item","qtde","vl_unit","numero_empenho","observacao"]}
        cb, self.for_var, self.map_for = _combo_fornecedores(sec)

        tk.Label(sec, text="Fornecedor", bg=BODY_BG).grid(row=0, column=0, sticky="e", padx=(10,6), pady=4)
        cb.grid(row=0, column=1, sticky="w", padx=(0,10), pady=4)

        def row(r, rot, chave, w=30):
            tk.Label(sec, text=rot, bg=BODY_BG).grid(row=r, column=2, sticky="e", padx=(10,6), pady=4)
            tk.Entry(sec, textvariable=self.vars[chave], width=w).grid(row=r, column=3, sticky="w", padx=(0,10), pady=4)

        row(0,"Código AGHU", "cod_aghu", 18)
        row(0,"Nome do item", "nome_item", 40)
        row(1,"Qtde", "qtde", 10)
        row(1,"Valor unitário", "vl_unit", 12)
        row(2,"Número do empenho", "numero_empenho", 20)
        row(2,"Observação", "observacao", 50)

        act = tk.Frame(self, bg=BODY_BG); act.pack(fill="x", padx=20, pady=8)
        tk.Button(act, text="Adicionar", command=self.adicionar).pack(side="left")
        tk.Button(act, text="Remover", command=self.remover).pack(side="left", padx=(8,0))
        tk.Button(act, text="Exportar Excel", command=self.exportar).pack(side="left", padx=(8,0))
        tk.Button(act, text="Enviar por e-mail", command=self.enviar_email_orc).pack(side="left", padx=(8,0))

        cols = ("cod_aghu","nome_item","qtde","vl_unit","vl_total","numero_empenho","observacao")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c.upper()); self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0,20))

        # Mensagem para e-mail
        msgf = tk.LabelFrame(self, text="Mensagem para o fornecedor (e-mail)", bg=BODY_BG)
        msgf.pack(fill="x", padx=20, pady=(0, 20))
        self.msg_txt = tk.Text(msgf, height=6)
        self.msg_txt.pack(fill="x", padx=10, pady=8)

    def adicionar(self):
        try:
            qtde = float(self.vars["qtde"].get() or 0)
            vu = float(self.vars["vl_unit"].get() or 0)
        except Exception:
            messagebox.showwarning("Validação", "Qtde e Valor unitário devem ser números.")
            return
        vt = qtde * vu
        vals = (
            self.vars["cod_aghu"].get().strip(),
            self.vars["nome_item"].get().strip(),
            qtde, vu, vt,
            self.vars["numero_empenho"].get().strip(),
            self.vars["observacao"].get().strip()
        )
        self.tree.insert("", "end", values=vals)
        for v in self.vars.values(): v.set("")

    def remover(self):
        sel = self.tree.selection()
        if sel:
            self.tree.delete(sel[0])

    def _df(self):
        dados = []
        for iid in self.tree.get_children():
            dados.append(self.tree.item(iid)["values"])
        cols = ["Código AGHU","Nome do Item","Qtde","Valor Unitário","Valor Total","Número do Empenho","Observação"]
        return pd.DataFrame(dados, columns=cols)

    def exportar(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "Inclua itens antes de exportar.")
            return
        arq = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")], title="Salvar orçamento")
        if not arq: return
        df = self._df()
        exportar_excel({"Orçamento": df}, arq)
        messagebox.showinfo("OK", f"Arquivo exportado: {arq}")

    def enviar_email_orc(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "Inclua itens antes de enviar.")
            return
        sel_for = self.for_var.get()
        if not sel_for:
            messagebox.showinfo("Info", "Selecione um fornecedor.")
            return
        fornecedor_id, email_for = self.map_for[sel_for]
        if not email_for:
            messagebox.showwarning("Atenção", "Fornecedor sem e-mail cadastrado.")
            return
        # Exporta temporário
        df = self._df()
        tmp = "orcamento_temp.xlsx"
        exportar_excel({"Orçamento": df}, tmp)

        msg = self.msg_txt.get("1.0", "end").strip() or "Segue orçamento para conferência."
        corpo = f"""
        <p>Prezados,</p>
        <p>{msg}</p>
        <p>Att.</p>
        """
        try:
            from utils import enviar_email
            enviar_email([email_for], "Orçamento - OPME", corpo_html=corpo, anexos=[tmp])
            messagebox.showinfo("OK", "E-mail enviado ao fornecedor.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar e-mail: {e}")
        finally:
            try:
                import os; os.remove(tmp)
            except: pass
