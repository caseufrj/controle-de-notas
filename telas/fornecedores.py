# telas/fornecedores.py
import tkinter as tk
from tkinter import ttk, messagebox
import banco


class TelaFornecedores(tk.Frame):
    def __init__(self, master):
        # >>> IMPORTANTE: herda de tk.Frame e chama super().__init__
        super().__init__(master, bg="white")

        # Cria/atualiza schema do banco (pode manter aqui ou mover para main.py)
        try:
            banco.criar_tabelas()
        except Exception as e:
            messagebox.showerror("Banco de dados", f"Não foi possível preparar o banco:\n{e}")

        # ----- Lado esquerdo: lista + busca -----
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
        cabecas = ("ID","Nome","E-mail","Telefone","Município","Estado")
        larguras = (60,220,200,120,120,80)
        for c, t, w in zip(cols, cabecas, larguras):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, anchor="w")
        self.tv.column("id", anchor="center")
        self.tv.pack(fill="both", expand=True, pady=(8,0))
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._carregar_form())

        # ----- Lado direito: formulário -----
        right = tk.Frame(self, bg="white")
        right.pack(side="left", fill="y", padx=12, pady=12)

        def row(lbl):
            f = tk.Frame(right, bg="white")
            f.pack(fill="x", pady=3)
            tk.Label(f, text=lbl, width=16, anchor="w", bg="white").pack(side="left")
            e = ttk.Entry(f, width=40)
            e.pack(side="left")
            return e

        self._id_var = tk.StringVar()  # guarda id atual (se edição)

        tk.Label(right, text="Cadastro de Fornecedores",
                 font=("Segoe UI", 12, "bold"), bg="white").pack(anchor="w", pady=(0,8))

        self.e_nome = row("Razão Social*:")
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
        tk.Label(f_obs, text="Observação:", width=16, anchor="w",
                 bg="white").pack(side="left", anchor="n")
        self.txt_obs = tk.Text(f_obs, width=40, height=6)
        self.txt_obs.pack(side="left")

        btns = tk.Frame(right, bg="white")
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Salvar", command=self._salvar).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpar", command=self._novo).pack(side="left", padx=4)

        # Carrega lista inicial
        self._carregar_lista()

    # ----------------- Lista/Busca -----------------
    def _carregar_lista(self, busca: str = ""):
        for i in self.tv.get_children():
            self.tv.delete(i)
        try:
            fornecedores = banco.fornecedores_listar(busca)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao listar fornecedores:\n{e}")
            fornecedores = []

        for f in fornecedores:
            self.tv.insert("", "end", values=(
                f.get("id",""),
                f.get("nome",""),
                f.get("email",""),
                f.get("telefone",""),
                f.get("municipio",""),
                f.get("estado",""),
            ))

    def _filtrar(self):
        self._carregar_lista(self.ent_busca.get().strip())

    # ----------------- Formulário -----------------
    def _novo(self):
        """Limpa o formulário para novo cadastro."""
        self._id_var.set("")
        for e in (self.e_nome, self.e_rua, self.e_numero, self.e_compl,
                  self.e_bairro, self.e_municipio, self.e_estado,
                  self.e_email, self.e_tel):
            e.delete(0, "end")
        self.txt_obs.delete("1.0", "end")
        # foco no nome
        self.e_nome.focus_set()

    def _carregar_form(self):
        sel = self.tv.selection()
        if not sel:
            return
        vals = self.tv.item(sel[0], "values")
        if not vals:
            return
        try:
            id_ = int(vals[0])
        except Exception:
            return

        d = banco.fornecedor_obter(id_)
        if not d:
            return

        self._novo()
        self._id_var.set(str(d["id"]))
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
            "observacao": self.txt_obs.get("1.0", "end").strip(),
            # campos extras, se quiser expor depois
            "cnpj": None,
            "contato_vendedor": None,
        }

    def _salvar(self):
        d = self._coletar_form()
        if not d["nome"]:
            messagebox.showwarning("Validação", "Informe o nome do fornecedor.")
            self.e_nome.focus_set()
            return

        id_txt = self._id_var.get().strip()
        try:
            if id_txt:
                banco.fornecedor_atualizar(int(id_txt), d)
                messagebox.showinfo("OK", "Fornecedor atualizado.")
            else:
                novo_id = banco.fornecedor_inserir(d)
                self._id_var.set(str(novo_id))
                messagebox.showinfo("OK", "Fornecedor cadastrado.")
            self._carregar_lista(self.ent_busca.get().strip())
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar fornecedor:\n{e}")

    def _excluir(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um fornecedor.")
            return
        vals = self.tv.item(sel[0], "values")
        try:
            id_ = int(vals[0])
        except Exception:
            return

        if not messagebox.askyesno("Confirmar",
                                   "Excluir fornecedor selecionado?\n"
                                   "(As notas/itens vinculados serão removidos)"):
            return
        try:
            banco.fornecedor_excluir(id_)
            self._novo()
            self._carregar_lista(self.ent_busca.get().strip())
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir:\n{e}")
