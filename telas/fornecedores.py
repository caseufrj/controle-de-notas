# telas/fornecedores.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import urllib.request
import urllib.error
import banco


class TelaFornecedores(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        try:
            banco.criar_tabelas()
        except Exception as e:
            messagebox.showerror("Banco de dados", f"Não foi possível preparar o banco:\n{e}")

        # ----------------- Estado interno (paginação e endereço) -----------------
        self.page_size = 20
        self.page = 1
        self._dados_filtrados = []
        self._endereco_editavel = False  # <--- NOVO: controla se rua/bairro/município/estado podem ser editados

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
        self.tv = ttk.Treeview(left, columns=cols, show="headings", height=16)
        cabecas = ("ID","Nome","E-mail","Telefone","Município","Estado")
        larguras = (60,220,200,120,120,80)
        for c, t, w in zip(cols, cabecas, larguras):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, anchor="w")
        self.tv.column("id", anchor="center")
        self.tv.pack(fill="both", expand=True, pady=(8,0))
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._carregar_form())

        # ---- Paginação (controles) ----
        pag = tk.Frame(left, bg="white")
        pag.pack(fill="x", pady=(6, 0))

        self.lbl_pag = tk.Label(pag, text="", bg="white")
        self.lbl_pag.pack(side="left")

        tk.Label(pag, text="Itens por página:", bg="white").pack(side="right", padx=(8, 2))
        self.cb_page_size = ttk.Combobox(pag, values=[10, 20, 50], width=4, state="readonly")
        self.cb_page_size.set(self.page_size)
        self.cb_page_size.pack(side="right")
        self.cb_page_size.bind("<<ComboboxSelected>>", self._on_change_page_size)

        self.btn_prev = ttk.Button(pag, text="⟨ Anterior", command=self._pagina_anterior)
        self.btn_prev.pack(side="left", padx=(8, 4))
        self.btn_next = ttk.Button(pag, text="Próxima ⟩", command=self._proxima_pagina)
        self.btn_next.pack(side="left")

        # ----- Lado direito: formulário -----
        right = tk.Frame(self, bg="white")
        right.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        def row(lbl):
            f = tk.Frame(right, bg="white")
            f.pack(fill="x", pady=3)
            tk.Label(f, text=lbl, width=16, anchor="w", bg="white").pack(side="left")
            e = ttk.Entry(f, width=40)
            e.pack(side="left", fill="x", expand=True)
            return e

        self._id_var = tk.StringVar()

        tk.Label(right, text="Cadastro de Fornecedores",
                 font=("Segoe UI", 12, "bold"), bg="white").pack(anchor="w", pady=(0,8))

        self.e_nome = row("Razão Social*:")

        # CEP acima do endereço
        self.e_cep = row("CEP:")
        self.e_cep.bind("<FocusOut>", self._buscar_cep_event)
        self.e_cep.bind("<KeyRelease>", self._buscar_cep_quando_completo)

        self.e_rua = row("Endereço:")
        self.e_numero = row("Número:")
        self.e_compl = row("Complemento:")
        self.e_bairro = row("Bairro:")
        self.e_municipio = row("Município:")
        self.e_estado = row("Estado:")
        self.e_email = row("E-mail:")
        self.e_tel = row("Telefone:")

        # Campos de endereço iniciam bloqueados
        for ent in (self.e_rua, self.e_bairro, self.e_municipio, self.e_estado):
            ent.config(state="readonly")

        # Observação com borda visível
        lf_obs = ttk.LabelFrame(right, text="Observação:")
        lf_obs.pack(fill="both", expand=True, pady=6)
        self.txt_obs = tk.Text(lf_obs, width=40, height=6, wrap="word",
                               bd=1, relief="solid", highlightthickness=0)
        self.txt_obs.pack(fill="both", expand=True, padx=6, pady=6)

        btns = tk.Frame(right, bg="white")
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Salvar", command=self._salvar).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpar", command=self._novo).pack(side="left", padx=4)

        # Carrega lista inicial
        self._carregar_lista()

    # ----------------- Helpers internos -----------------
    def _entry_set_readonly(self, entry: ttk.Entry, value: str):
        """Define texto em Entry mesmo que esteja readonly."""
        cur_state = str(entry.cget("state"))
        try:
            entry.config(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value or "")
        finally:
            entry.config(state=cur_state)

    def _somente_digitos(self, s: str) -> str:
        return "".join(ch for ch in s if ch.isdigit())

    def _set_endereco_editavel(self, editavel: bool):
        """Ativa/Desativa edição manual de rua/bairro/município/estado."""
        self._endereco_editavel = editavel
        state = "normal" if editavel else "readonly"
        for ent in (self.e_rua, self.e_bairro, self.e_municipio, self.e_estado):
            # preserva o texto e só muda o state
            cur = ent.get()
            ent.config(state="normal")
            ent.delete(0, "end")
            ent.insert(0, cur)
            ent.config(state=state)

    # ----------------- ViaCEP (CEP -> endereço) -----------------
    def _buscar_cep(self, cep: str):
        """Consulta ViaCEP e preenche endereço/bairro/município/estado."""
        cep_digits = self._somente_digitos(cep)
        if len(cep_digits) != 8:
            return  # CEP incompleto; sem alertar

        url = f"https://viacep.com.br/ws/{cep_digits}/json/"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read().decode("utf-8")
            j = json.loads(data)
        except urllib.error.URLError as e:
            messagebox.showwarning("CEP", f"Não foi possível consultar o CEP (conexão?):\n{e}")
            return
        except Exception as e:
            messagebox.showwarning("CEP", f"Falha ao ler resposta do ViaCEP:\n{e}")
            return

        if j.get("erro"):
            # CEP não encontrado -> pergunta se deseja cadastrar manualmente
            if messagebox.askyesno("CEP não encontrado",
                                   "CEP não encontrado.\nDeseja cadastrar o endereço manualmente?"):
                # libera edição manual
                self._set_endereco_editavel(True)
                # limpa campos para digitação
                for ent in (self.e_rua, self.e_bairro, self.e_municipio, self.e_estado):
                    ent.config(state="normal")
                    ent.delete(0, "end")
                self.e_rua.focus_set()
            else:
                # mantém bloqueado e não altera nada
                self._set_endereco_editavel(False)
            return

        # CEP válido: preenche e bloqueia
        logradouro = j.get("logradouro", "")
        bairro = j.get("bairro", "")
        localidade = j.get("localidade", "")
        uf = j.get("uf", "")

        self._entry_set_readonly(self.e_rua, logradouro)
        self._entry_set_readonly(self.e_bairro, bairro)
        self._entry_set_readonly(self.e_municipio, localidade)
        self._entry_set_readonly(self.e_estado, uf)

        # garante bloqueio (modo automático)
        self._set_endereco_editavel(False)

        # Foco natural no Número
        self.e_numero.focus_set()

    def _buscar_cep_event(self, _evt):
        self._buscar_cep(self.e_cep.get())

    def _buscar_cep_quando_completo(self, _evt):
        if len(self._somente_digitos(self.e_cep.get())) == 8:
            self._buscar_cep(self.e_cep.get())

    # ----------------- Lista/Busca -----------------
    def _carregar_lista(self, busca: str = ""):
        try:
            fornecedores = banco.fornecedores_listar(busca)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao listar fornecedores:\n{e}")
            fornecedores = []

        self._dados_filtrados = fornecedores
        self.page = 1
        self._mostrar_pagina_atual()

    def _mostrar_pagina_atual(self):
        for i in self.tv.get_children():
            self.tv.delete(i)

        total = len(self._dados_filtrados)
        if total == 0:
            self.lbl_pag.config(text="Nenhum registro.")
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            return

        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page > total_pages:
            self.page = total_pages

        start = (self.page - 1) * self.page_size
        end = min(start + self.page_size, total)
        for f in self._dados_filtrados[start:end]:
            self.tv.insert("", "end", values=(
                f.get("id",""),
                f.get("nome",""),
                f.get("email",""),
                f.get("telefone",""),
                f.get("municipio",""),
                f.get("estado",""),
            ))

        self.lbl_pag.config(text=f"Página {self.page} de {total_pages} • Registros: {total}")
        self.btn_prev.config(state=("normal" if self.page > 1 else "disabled"))
        self.btn_next.config(state=("normal" if self.page < total_pages else "disabled"))

    def _filtrar(self):
        self._carregar_lista(self.ent_busca.get().strip())

    def _on_change_page_size(self, _evt):
        try:
            self.page_size = int(self.cb_page_size.get())
        except Exception:
            self.page_size = 20
        self.page = 1
        self._mostrar_pagina_atual()

    def _pagina_anterior(self):
        if self.page > 1:
            self.page -= 1
            self._mostrar_pagina_atual()

    def _proxima_pagina(self):
        total = len(self._dados_filtrados)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.page < total_pages:
            self.page += 1
            self._mostrar_pagina_atual()

    # ----------------- Formulário -----------------
    def _novo(self):
        """Limpa o formulário para novo cadastro."""
        self._id_var.set("")
        for e in (self.e_nome, self.e_cep, self.e_numero, self.e_compl,
                  self.e_email, self.e_tel):
            e.delete(0, "end")

        # limpa campos de endereço e volta ao bloqueio padrão
        self._set_endereco_editavel(False)
        for ent in (self.e_rua, self.e_bairro, self.e_municipio, self.e_estado):
            self._entry_set_readonly(ent, "")

        self.txt_obs.delete("1.0", "end")
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
        self._id_var.set(str(d.get("id","")))
        self.e_nome.insert(0, d.get("nome",""))

        cep_val = d.get("cep","")
        self.e_cep.insert(0, cep_val)

        # Preenche endereço (mantém bloqueado)
        self._entry_set_readonly(self.e_rua, d.get("rua",""))
        self.e_numero.insert(0, d.get("numero",""))
        self.e_compl.insert(0, d.get("complemento",""))
        self._entry_set_readonly(self.e_bairro, d.get("bairro",""))
        self._entry_set_readonly(self.e_municipio, d.get("municipio",""))
        self._entry_set_readonly(self.e_estado, d.get("estado",""))
        self.e_email.insert(0, d.get("email",""))
        self.e_tel.insert(0, d.get("telefone",""))
        self.txt_obs.insert("1.0", d.get("observacao",""))

    def _coletar_form(self):
        return {
            "nome": self.e_nome.get().strip(),
            # "cep": self.e_cep.get().strip(),  # <-- Ative se o banco suportar salvar CEP
            "rua": self.e_rua.get().strip(),
            "numero": self.e_numero.get().strip(),
            "complemento": self.e_compl.get().strip(),
            "bairro": self.e_bairro.get().strip(),
            "municipio": self.e_municipio.get().strip(),
            "estado": self.e_estado.get().strip(),
            "email": self.e_email.get().strip(),
            "telefone": self.e_tel.get().strip(),
            "observacao": self.txt_obs.get("1.0", "end").strip(),
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
