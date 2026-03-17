# telas/fornecedores.py

import tkinter as tk
from tkinter import ttk, messagebox
import banco

class TelaFornecedores(tk.Frame):           # <<< herda de tk.Frame
    def __init__(self, master):
        super().__init__(master, bg="white")  # <<< inicializa o Frame
        banco.criar_tabelas()

        # Esquerda: Lista / Busca
        left = tk.Frame(self, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        barra = tk.Frame(left, bg="white")
        barra.pack(fill="x")
        tk.Label(barra, text="Buscar:", bg="white").pack(side="left")
        self.ent_busca = ttk.Entry(barra, width=40)
        self.ent_busca.pack(side="left", padx=6)
        ttk.Button(barra, text="Filtrar", command=self._filtrar).pack(side="left", padx=4)
        ttk.Button(barra, text="Novo", command=self._novo).pack(side="left", padx=4)
        ttk.Button(barra, text="Excluir", command=self._excluir).pack(side="left", padx=4)

        cols = ("id","nome","email","telefone","municipio","estado")
        self.tv = ttk.Treeview(left, columns=cols, show="headings", height=18)
        for c in cols:
            self.tv.heading(c, text=c)
            self.tv.column(c, width=120, anchor="w")
        self.tv.column("id", width=60, anchor="center")
        self.tv.pack(fill="both", expand=True, pady=(8,0))
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._carregar_form())

        # Direita: Form
        right = tk.Frame(self, bg="white")
        right.pack(side="left", fill="y", padx=12, pady=12)

        def row(lbl):
            f = tk.Frame(right, bg="white")
            f.pack(fill="x", pady=3)
            tk.Label(f, text=lbl, width=16, anchor="w", bg="white").pack(side="left")
            e = ttk.Entry(f, width=40)
            e.pack(side="left")
            return e

        self.ent_id = tk.StringVar()
        tk.Label(right, text="Cadastro de Fornecedores", font=("Segoe UI", 12, "bold"), bg="white").pack(anchor="w", pady=(0,8))

        self.e_nome = row("Nome*:")
        self.e_rua = row("Rua:")
        self.e_numero = row("Número:")
        self.e_compl = row("Complemento:")
        self.e_bairro = row("Bairro:")
        self.e_municipio = row("Município:")
        self.e_estado = row("Estado:")
        self.e_email = row("E-mail:")
        self.e_tel = row("Telefone:")

        f_obs = tk.Frame(right, bg="white")
        f_obs.pack(fill="both", expand=True, pady=3)
        tk.Label(f_obs, text="Observação:", width=16, anchor="w", bg="white").pack(side="left", anchor="n")
        self.txt_obs = tk.Text(f_obs, width=40, height=6)
        self.txt_obs.pack(side="left")

        btns = tk.Frame(right, bg="white")
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Salvar", command=self._salvar).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpar", command=self._limpar_form).pack(side="left", padx=4)

        self._carregar_lista()

    # ---- Lista ----
    def _carregar_lista(self, busca=""):
        for i in self.tv.get_children():
            self.tv.delete(i)
        for f in banco.fornecedores_listar(busca):
            self.tv.insert("", "end", values=(
                f["id"], f.get("nome",""), f.get("email",""), f.get("telefone",""),
                f.get("municipio",""), f.get("estado","")
            ))

    def _filtrar(self):
        self._carregar_lista(self.ent_busca.get().strip())

    # ---- Form ----
    def _limpar_form(self):
        self.ent_id.set("")
        for e in (self.e_nome, self.e_rua, self.e_numero, self.e_compl, self.e_bairro,
                  self.e_municipio, self.e_estado, self.e_email, self.e_tel):
            e.delete(0, "end")
        self.txt_obs.delete("1.0", "end")

    def _carregar_form(self):
        sel = self.tv.selection()
        if not sel:
            return
        vals = self.tv.item(sel[0], "values")
        id_ = int(vals[0])
        d = banco.fornecedor_obter(id_)
        if not d:
            return
        self._limpar_form()
        self.ent_id.set(str(d["id"]))
        self.e_nome.insert(0, d.get("nome",""))
        self.e_rua.insert(0, d.get("rua",""))
        self.e_numero.insert(0, d.get("numero",""))
        self.e_compl.insert(0, d.get("complemento",""))
        self.e_bairro.insert(0, d.get("bairro",""))
        self.e_municipio.insert(0, d.get("municipio",""))
        self.e_estado.insert(0, d.get("estado",""))
        self.e_email.insert(0, d.get("email",""))
        self.e_tel.insert(0, d.get("telefone",""))
        self.txt_obs.insert("1.0", d.get("observacao",""))

    def _coletar_form(self):
        return {
            "nome": self.e_nome.get().strip(),
            "rua": self.e_rua.get().strip(),
            "numero": self.e_numero.get().strip(),
            "complemento": self.e_compl.get().strip(),
            "bairro": self.e_bairro.get().strip(),
            "municipio": self.e_municipio.get().strip(),
            "estado": self.e_estado.get().strip(),
            "email": self.e_email.get().strip(),
            "telefone": self.e_tel.get().strip(),
            "observacao": self.txt_obs.get("1.0","end").strip(),
            "cnpj": None,  # pode adicionar ao formulário depois
            "contato_vendedor": None
        }

    def _salvar(self):
        d = self._coletar_form()
        if not d["nome"]:
            messagebox.showwarning("Validação", "Informe o nome do fornecedor.")
            return
        id_txt = self.ent_id.get().strip()
        if id_txt:
            banco.fornecedor_atualizar(int(id_txt), d)
            messagebox.showinfo("OK", "Fornecedor atualizado.")
        else:
            novo_id = banco.fornecedor_inserir(d)
            self.ent_id.set(str(novo_id))
            messagebox.showinfo("OK", "Fornecedor cadastrado.")
        self._carregar_lista()
        self._filtrar()

    def _excluir(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um fornecedor.")
            return
        vals = self.tv.item(sel[0], "values")
        id_ = int(vals[0])
        if messagebox.askyesno("Confirmar", "Excluir fornecedor selecionado? (as notas/itens vinculados serão removidos)"):
            banco.fornecedor_excluir(id_)
            self._limpar_form()
            self._carregar_lista()
