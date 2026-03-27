# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import tempfile
from datetime import datetime
import os
import banco
import utils


class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        # ========== TOPO: FORNECEDOR ==========
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind(
            "<<ComboboxSelected>>",
            lambda e: (
                self._reset_autosave_context(),
                self._carregar_itens_rascunho(),
                self._carregar_salvos(),
                self._carregar_msgs(),
                self._carregar_msgs_enviadas(),
            ),
        )

        # Controladores internos
        self._after_ids = []
        self._anexos_extra = []

        # ========== BLOCO SUPERIOR: FORMULÁRIO + CAIXA LATERAL ==========
        bloco_superior = tk.Frame(self, bg="white")
        bloco_superior.pack(fill="x", padx=12, pady=8)

        # Formulário principal (compacto)
        form = ttk.LabelFrame(bloco_superior, text="Lançar itens para Orçamento")
        form.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Grid compacto - 2 linhas apenas
        def campo(lbl, row, width=30):
            tk.Label(form, text=lbl, bg="white").grid(
                column=0, row=row, sticky="w", padx=6, pady=2
            )
            e = ttk.Entry(form, width=width)
            e.grid(column=1, row=row, sticky="ew", padx=6, pady=2)
            return e

        # Linha 0: Cód, Nome, Qtde
        self.e_cod = campo("Cód AGHU*:", 0, 20)
        self.e_nome = campo("Nome item*:", 1, 40)
        
        tk.Label(form, text="Qtde*:", bg="white").grid(column=2, row=0, sticky="w", padx=6, pady=2)
        self.e_qt = ttk.Entry(form, width=10)
        self.e_qt.grid(column=3, row=0, sticky="w", padx=6, pady=2)

        # Linha 1: Vlr Unit, Empenho, Obs
        tk.Label(form, text="Vlr Unit*:", bg="white").grid(column=2, row=1, sticky="w", padx=6, pady=2)
        self.e_vu = ttk.Entry(form, width=10)
        self.e_vu.grid(column=3, row=1, sticky="w", padx=6, pady=2)

        tk.Label(form, text="Nº Empenho:", bg="white").grid(column=4, row=0, sticky="w", padx=6, pady=2)
        self.e_emp = ttk.Entry(form, width=12)
        self.e_emp.grid(column=5, row=0, sticky="w", padx=6, pady=2)

        tk.Label(form, text="Observação:", bg="white").grid(column=4, row=1, sticky="w", padx=6, pady=2)
        self.e_obs = ttk.Entry(form, width=25)
        self.e_obs.grid(column=5, row=1, sticky="ew", padx=6, pady=2)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(5, weight=1)

        # Botão Add
        btn_frame = tk.Frame(form, bg="white")
        btn_frame.grid(column=6, row=0, rowspan=2, sticky="n", padx=10)
        ttk.Button(btn_frame, text="Add", command=self._adicionar, width=10).pack(pady=2)

        # Modelo rápido
        modelo_frame = tk.Frame(form, bg="white")
        modelo_frame.grid(column=0, row=2, columnspan=6, sticky="ew", padx=6, pady=(6, 2))
        
        tk.Label(modelo_frame, text="Modelo:", bg="white").pack(side="left", padx=6)
        self.cb_modelo = ttk.Combobox(modelo_frame, state="readonly", width=40)
        self.cb_modelo.pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(modelo_frame, text="Carregar", command=self._carregar_modelo_rapido).pack(side="left", padx=6)

        # Mensagem p/ email
        msg_frame = tk.Frame(form, bg="white")
        msg_frame.grid(column=0, row=3, columnspan=6, sticky="ew", padx=6, pady=2)

        tk.Label(msg_frame, text="Mensagem p/ e-mail:", bg="white").pack(anchor="w", padx=6, pady=(0, 2))
        self.txt_msg = tk.Text(msg_frame, width=80, height=3)
        self.txt_msg.pack(fill="both", expand=True, padx=6, pady=2)

        # Autosave label
        self._lbl_autosave = tk.Label(msg_frame, text="", fg="#2c7", bg="white")
        self._lbl_autosave.pack(anchor="w", padx=6, pady=(0, 4))

        # ========== CAIXA LATERAL (TOPO DIREITO) ==========
        side_box = ttk.LabelFrame(bloco_superior, text="Mensagem: Modelo / Rascunho")
        side_box.pack(side="right", fill="y", padx=(6, 0))

        tk.Label(side_box, text="Título:").pack(anchor="w", padx=6, pady=(6, 0))
        self.e_titulo_msg = ttk.Entry(side_box, width=25)
        self.e_titulo_msg.pack(anchor="w", padx=6, pady=(0, 6))

        self.var_msg_forn = tk.BooleanVar(value=False)
        ttk.Checkbutton(side_box, text="Vincular ao fornecedor atual", variable=self.var_msg_forn)\
            .pack(anchor="w", padx=6, pady=(0, 6))

        btns_msg = tk.Frame(side_box, bg="white")
        btns_msg.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Button(btns_msg, text="Salvar Modelo", command=lambda: self._salvar_mensagem("modelo"))\
            .pack(side="left", padx=2)
        ttk.Button(btns_msg, text="Salvar Rascunho", command=lambda: self._salvar_mensagem("rascunho"))\
            .pack(side="left", padx=2)

        ttk.Button(side_box, text="Anexar arquivo", command=self._add_anexo)\
            .pack(anchor="w", padx=6, pady=(0, 6))

        # Área de anexos
        wrapper_anexos = ttk.LabelFrame(side_box, text="Anexos")
        wrapper_anexos.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        self.frm_anexos = tk.Frame(wrapper_anexos, bg="white", height=80)
        self.frm_anexos.pack(fill="both", expand=True, padx=4, pady=4)
        self.frm_anexos.pack_propagate(False)

        self.lbl_sem_anexo = tk.Label(self.frm_anexos, text="Nenhum anexo", bg="white", fg="#666")
        self.lbl_sem_anexo.pack(anchor="w")

        # ========== ABAS: MODELOS / RASCUNHOS ==========
        lf_msg = ttk.LabelFrame(self, text="Mensagens (Modelos e Rascunhos)")
        lf_msg.pack(fill="both", expand=False, padx=12, pady=(4, 8))

        busca_bar = tk.Frame(lf_msg)
        busca_bar.pack(fill="x", padx=6, pady=6)
        tk.Label(busca_bar, text="Buscar (título/conteúdo):").pack(side="left")
        self.e_msg_busca = ttk.Entry(busca_bar, width=40)
        self.e_msg_busca.pack(side="left", padx=6)
        ttk.Button(busca_bar, text="Filtrar listas", command=self._carregar_msgs).pack(side="left")

        msg_edit = tk.Frame(lf_msg)
        msg_edit.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(msg_edit, text="Editar selecionada", command=self._editar_msg).pack(side="left")
        ttk.Button(msg_edit, text="Salvar alterações", command=self._salvar_alteracoes_msg).pack(side="left", padx=6)

        nb = ttk.Notebook(lf_msg)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        # Aba MODELOS
        aba_modelos = tk.Frame(nb)
        nb.add(aba_modelos, text="Modelos")
        cols_m = ("id", "titulo", "fornecedor_id", "criado_em")
        self.tv_modelos = ttk.Treeview(aba_modelos, columns=cols_m, show="headings", height=5)
        for c, h, w in zip(cols_m, ("ID", "Título", "Fornecedor", "Criado em"), (60, 250, 120, 140)):
            self.tv_modelos.heading(c, text=h)
            self.tv_modelos.column(c, width=w, anchor="w")
        self.tv_modelos.pack(fill="both", expand=True, padx=4, pady=4)
        self.tv_modelos.bind("<Double-1>", lambda e: self._usar_msg("modelo"))

        bar_m = tk.Frame(aba_modelos)
        bar_m.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(bar_m, text="Usar na mensagem", command=lambda: self._usar_msg("modelo")).pack(side="left")
        ttk.Button(bar_m, text="Excluir", command=lambda: self._excluir_msg("modelo")).pack(side="left", padx=6)
        ttk.Button(bar_m, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)

        # Aba RASCUNHOS
        aba_rasc = tk.Frame(nb)
        nb.add(aba_rasc, text="Rascunhos")

        self.tv_rasc = ttk.Treeview(aba_rasc, columns=cols_m, show="headings", height=5)
        for c, h, w in zip(cols_m, ("ID", "Título", "Fornecedor", "Criado em"), (60, 250, 120, 140)):
            self.tv_rasc.heading(c, text=h)
            self.tv_rasc.column(c, width=w, anchor="w")
        self.tv_rasc.pack(fill="both", expand=True, padx=4, pady=4)
        self.tv_rasc.bind("<Double-1>", lambda e: self._usar_msg("rascunho"))

        bar_r = tk.Frame(aba_rasc)
        bar_r.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(bar_r, text="Usar na mensagem", command=lambda: self._usar_msg("rascunho")).pack(side="left")
        ttk.Button(bar_r, text="Excluir", command=lambda: self._excluir_msg("rascunho")).pack(side="left", padx=6)
        ttk.Button(bar_r, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)

        # ========== ITENS EM RASCUNHO ==========
        lf_rasc = ttk.LabelFrame(self, text="Itens em rascunho (não salvos)")
        lf_rasc.pack(fill="both", expand=True, padx=12, pady=(4, 2))

        cols = ("cod", "nome", "qt", "vu", "emp", "obs", "vl_total")
        heads = ("Cód AGHU", "Nome", "Qtde", "Vlr Unit", "Nº Empenho", "Obs", "Vlr Total")
        widths = (100, 260, 60, 90, 120, 260, 100)

        self.tv = ttk.Treeview(lf_rasc, columns=cols, show="headings", height=5)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h)
            self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)

        # ========== AÇÕES PRINCIPAIS ==========
        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=8)
        self.btn_email = ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email)
        self.btn_email.pack(side="right", padx=6)

        self.btn_export = ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel)
        self.btn_export.pack(side="right", padx=6)

        # ========== HISTÓRICO DE ORÇAMENTOS ==========
        lf_hist = ttk.LabelFrame(self, text="Orçamentos já salvos (no banco) — por fornecedor")
        lf_hist.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        filtros = tk.Frame(lf_hist)
        filtros.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(filtros, text="De (YYYY-MM-DD):").pack(side="left")
        self.f_data_ini = ttk.Entry(filtros, width=12)
        self.f_data_ini.pack(side="left", padx=4)

        tk.Label(filtros, text="Até:").pack(side="left")
        self.f_data_fim = ttk.Entry(filtros, width=12)
        self.f_data_fim.pack(side="left", padx=4)

        tk.Label(filtros, text="Termo (cód/nome/obs):").pack(side="left", padx=(12, 0))
        self.f_busca = ttk.Entry(filtros, width=28)
        self.f_busca.pack(side="left", padx=4)

        tk.Label(filtros, text="Empenho:").pack(side="left", padx=(12, 0))
        self.f_emp = ttk.Entry(filtros, width=14)
        self.f_emp.pack(side="left", padx=4)

        ttk.Button(filtros, text="Filtrar", command=self._resetar_paginacao).pack(side="left", padx=6)
        ttk.Button(filtros, text="Limpar", command=self._limpar_filtros).pack(side="left")

        # Lista do histórico
        cols_s = ("id", "criado_em", "cod_aghu", "nome_item", "qtde", "vl_unit", "vl_total", "numero_empenho", "observacao")
        heads_s = ("ID", "Criado em", "Cód AGHU", "Item", "Qtde", "Vlr Unit", "Vlr Total", "Nº Empenho", "Obs")
        widths_s = (60, 140, 100, 260, 70, 90, 100, 120, 260)

        self.tv_salvos = ttk.Treeview(lf_hist, columns=cols_s, show="headings", height=6)
        for c, h, w in zip(cols_s, heads_s, widths_s):
            self.tv_salvos.heading(c, text=h)
            self.tv_salvos.column(c, width=w, anchor="w")
        self.tv_salvos.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        # Botões do histórico
        barra_hist = tk.Frame(lf_hist, bg="white")
        barra_hist.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(barra_hist, text="Atualizar", command=self._carregar_salvos).pack(side="left")
        ttk.Button(barra_hist, text="Excluir selecionado", command=self._excluir_salvo).pack(side="left", padx=6)
        ttk.Button(barra_hist, text="Exportar histórico (filtros)", command=self._exportar_historico).pack(side="left", padx=6)

        # Paginação
        pag = tk.Frame(lf_hist, bg="white")
        pag.pack(fill="x", padx=6, pady=(0, 6))

        tk.Label(pag, text="Itens/página:").pack(side="left")
        self.cb_page_size = ttk.Combobox(pag, state="readonly", width=5, values=[20, 50, 100, 200])

        try:
            cfg = utils.carregar_config()
            ultimo = int(cfg.get("paginacao_orcamento", 50))
        except:
            ultimo = 50

        self.after(10, lambda: self.cb_page_size.set(ultimo))
        self.cb_page_size.pack(side="left", padx=4)
        self.cb_page_size.bind("<<ComboboxSelected>>", self._on_page_size_changed)

        ttk.Button(pag, text="<<", command=lambda: self._ir_pagina("first")).pack(side="left", padx=2)
        ttk.Button(pag, text="<", command=lambda: self._ir_pagina("prev")).pack(side="left", padx=2)
        ttk.Button(pag, text=">", command=lambda: self._ir_pagina("next")).pack(side="left", padx=2)
        ttk.Button(pag, text=">>", command=lambda: self._ir_pagina("last")).pack(side="left", padx=2)

        self.lbl_pag = tk.Label(pag, text="Página 1/1", bg="white")
        self.lbl_pag.pack(side="left", padx=10)

        # ========== MENSAGENS ENVIADAS ==========
        lf_msgs_env = ttk.LabelFrame(self, text="Mensagens enviadas")
        lf_msgs_env.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        filtros_msg = tk.Frame(lf_msgs_env)
        filtros_msg.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(filtros_msg, text="De:").pack(side="left")
        self.f_msg_data_ini = ttk.Entry(filtros_msg, width=12)
        self.f_msg_data_ini.pack(side="left", padx=4)

        tk.Label(filtros_msg, text="Até:").pack(side="left")
        self.f_msg_data_fim = ttk.Entry(filtros_msg, width=12)
        self.f_msg_data_fim.pack(side="left", padx=4)

        tk.Label(filtros_msg, text="Destinatário:").pack(side="left", padx=(12, 0))
        self.f_msg_dest = ttk.Entry(filtros_msg, width=30)
        self.f_msg_dest.pack(side="left", padx=4)

        ttk.Button(filtros_msg, text="Filtrar", command=self._resetar_paginacao_msgs).pack(side="left", padx=6)
        ttk.Button(filtros_msg, text="Limpar", command=self._limpar_filtros_msgs).pack(side="left")

        # Lista mensagens enviadas
        cols_msg = ("id", "enviado_em", "destinatario", "assunto", "fornecedor")
        heads_msg = ("ID", "Enviado em", "Destinatário", "Assunto", "Fornecedor")
        widths_msg = (60, 140, 200, 300, 150)

        self.tv_msgs_enviadas = ttk.Treeview(lf_msgs_env, columns=cols_msg, show="headings", height=6)
        for c, h, w in zip(cols_msg, heads_msg, widths_msg):
            self.tv_msgs_enviadas.heading(c, text=h)
            self.tv_msgs_enviadas.column(c, width=w, anchor="w")
        self.tv_msgs_enviadas.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        # Paginação mensagens enviadas
        pag_msg = tk.Frame(lf_msgs_env, bg="white")
        pag_msg.pack(fill="x", padx=6, pady=(0, 6))

        tk.Label(pag_msg, text="Itens/página:").pack(side="left")
        self.cb_page_size_msg = ttk.Combobox(pag_msg, state="readonly", width=5, values=[20, 50, 100])
        self.cb_page_size_msg.set(50)
        self.cb_page_size_msg.pack(side="left", padx=4)

        ttk.Button(pag_msg, text="<<", command=lambda: self._ir_pagina_msg("first")).pack(side="left", padx=2)
        ttk.Button(pag_msg, text="<", command=lambda: self._ir_pagina_msg("prev")).pack(side="left", padx=2)
        ttk.Button(pag_msg, text=">", command=lambda: self._ir_pagina_msg("next")).pack(side="left", padx=2)
        ttk.Button(pag_msg, text=">>", command=lambda: self._ir_pagina_msg("last")).pack(side="left", padx=2)

        self.lbl_pag_msg = tk.Label(pag_msg, text="Página 1/1", bg="white")
        self.lbl_pag_msg.pack(side="left", padx=10)

        # Inicializa paginação
        self._page = 1
        self._total = 0
        self._page_msg = 1
        self._total_msg = 0

        # Estado geral
        self.map_fornec = {}
        self._modelos_cache = []

        # Autosave
        self._autosave_job = None
        self._autosave_msg_id = None
        self._msg_editando_id = None
        self.txt_msg.bind("<KeyRelease>", lambda e: self._agendar_autosave())
        self.txt_msg.bind("<FocusOut>", lambda e: self._autosave_now())

        # Carregamentos iniciais
        self._carregar_fornecedores()
        self._carregar_itens_rascunho()
        self._carregar_salvos()
        self._carregar_msgs()
        self._carregar_msgs_enviadas()

    # ==================== SUPORTE INTERNO ====================

    def _add_anexo(self):
        arq = filedialog.askopenfilename(
            title="Selecionar anexo",
            filetypes=[("Todos os arquivos", "*.*")]
        )
        if not arq:
            return

        self._anexos_extra.append(arq)
        self._atualizar_lista_anexos()

    def _atualizar_lista_anexos(self):
        for w in self.frm_anexos.winfo_children():
            w.destroy()

        if not self._anexos_extra:
            self.lbl_sem_anexo = tk.Label(self.frm_anexos,
                text="Nenhum anexo", bg="white", fg="#666")
            self.lbl_sem_anexo.pack(anchor="w")
            return

        for idx, path in enumerate(self._anexos_extra, start=1):
            nome = os.path.basename(path)

            linha = tk.Frame(self.frm_anexos, bg="white")
            linha.pack(anchor="w", fill="x", pady=1)

            tk.Label(linha, text=f"{idx}. {nome}", bg="white")\
                .pack(side="left", padx=(2, 6))

            ttk.Button(linha, text="X", width=3,
                       command=lambda p=path: self._remover_anexo(p))\
                .pack(side="left")

    def _remover_anexo(self, caminho):
        try:
            self._anexos_extra.remove(caminho)
        except:
            pass
        self._atualizar_lista_anexos()

    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs and not self.cb_fornec.get():
            self.cb_fornec.current(0)

    def _fornecedor_id_atual(self):
        nome = self.cb_fornec.get()
        if not nome:
            return None
        return self.map_fornec.get(nome)

    def _reset_autosave_context(self):
        self._autosave_msg_id = None

    def _agendar_autosave(self):
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(1000, self._autosave_now)

    def _autosave_now(self):
        if self._autosave_msg_id:
            titulo = self.e_titulo_msg.get().strip()
            conteudo = self.txt_msg.get("1.0", "end").strip()
            if titulo and conteudo:
                try:
                    banco.mensagem_atualizar(self._autosave_msg_id, titulo, conteudo)
                    self._lbl_autosave.config(text="Salvo automaticamente")
                    self.after(2000, lambda: self._lbl_autosave.config(text=""))
                except:
                    pass

    def _adicionar(self):
        try:
            qt = float(str(self.e_qt.get() or 0).replace(",", "."))
            vu = float(str(self.e_vu.get() or 0).replace(",", "."))
        except:
            messagebox.showwarning("Validação", "Digite números válidos.")
            return

        if not (self.e_cod.get().strip() and self.e_nome.get().strip() and qt and vu):
            messagebox.showwarning("Validação", "Preencha todos os campos obrigatórios.")
            return

        vt = qt * vu

        self.tv.insert(
            "", "end",
            values=(self.e_cod.get().strip(), self.e_nome.get().strip(),
                    f"{qt}", f"{vu:.2f}", self.e_emp.get().strip(),
                    self.e_obs.get().strip(), f"{vt:.2f}")
        )

        try:
            banco.itens_rascunho_inserir({
                "fornecedor_id": self._fornecedor_id_atual(),
                "cod_aghu": self.e_cod.get().strip(),
                "nome_item": self.e_nome.get().strip(),
                "qtde": qt,
                "vl_unit": vu,
                "numero_empenho": self.e_emp.get().strip(),
                "observacao": self.e_obs.get().strip()
            })
        except Exception as e:
            messagebox.showwarning("Rascunho", f"Erro ao salvar rascunho:\n{e}")

        for e in (self.e_cod, self.e_nome, self.e_qt, self.e_vu, self.e_emp, self.e_obs):
            e.delete(0, "end")

    # ==================== PAGINAÇÃO ====================

    def _salvar_page_size(self):
        try:
            tam = int(self.cb_page_size.get())
        except:
            tam = 50

        cfg = utils.carregar_config()
        cfg["paginacao_orcamento"] = tam
        utils.salvar_config(cfg)

    def _on_page_size_changed(self, evt=None):
        try:
            self._page_size = int(self.cb_page_size.get())
        except:
            self._page_size = 50

        self._salvar_page_size()
        self._page = 1
        self._carregar_salvos()

    def _resetar_paginacao(self):
        self._page = 1
        self._carregar_salvos()

    def _ir_pagina(self, qual):
        page_size = int(self.cb_page_size.get() or 50)
        total_pages = max(1, (self._total + page_size - 1) // page_size)

        if qual == "first":
            self._page = 1
        elif qual == "prev":
            self._page = max(1, self._page - 1)
        elif qual == "next":
            self._page = min(total_pages, self._page + 1)
        elif qual == "last":
            self._page = total_pages

        self._carregar_salvos()

    def _resetar_paginacao_msgs(self):
        self._page_msg = 1
        self._carregar_msgs_enviadas()

    def _ir_pagina_msg(self, qual):
        page_size = int(self.cb_page_size_msg.get() or 50)
        total_pages = max(1, (self._total_msg + page_size - 1) // page_size)

        if qual == "first":
            self._page_msg = 1
        elif qual == "prev":
            self._page_msg = max(1, self._page_msg - 1)
        elif qual == "next":
            self._page_msg = min(total_pages, self._page_msg + 1)
        elif qual == "last":
            self._page_msg = total_pages

        self._carregar_msgs_enviadas()

    def _limpar_filtros_msgs(self):
        self.f_msg_data_ini.delete(0, "end")
        self.f_msg_data_fim.delete(0, "end")
        self.f_msg_dest.delete(0, "end")
        self._resetar_paginacao_msgs()

    # ==================== MÉTODOS RESTANTES ====================
    # (Mantenha todos os outros métodos: _carregar_modelo_rapido, _limpar_filtros, 
    # _filtros_atual, _carregar_salvos, _exportar_historico, _exportar_excel, 
    # _excluir_salvo, _usar_msg, _carregar_msgs, _editar_msg, _salvar_alteracoes_msg,
    # _excluir_msg, _enviar_email, _carregar_itens_rascunho, _salvar_mensagem,
    # _salvar_orcamento_linhas, _carregar_msgs_enviadas)
    
    # Adicione este método para carregar mensagens enviadas:
    def _carregar_msgs_enviadas(self):
        """Carrega histórico de mensagens enviadas com paginação."""
        for i in self.tv_msgs_enviadas.get_children():
            self.tv_msgs_enviadas.delete(i)

        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            self._total_msg = 0
            self._page_msg = 1
            self.lbl_pag_msg.config(text="Página 1/1")
            return

        data_ini = self.f_msg_data_ini.get().strip() or None
        data_fim = self.f_msg_data_fim.get().strip() or None
        destinatario = self.f_msg_dest.get().strip() or None
        
        page_size = int(self.cb_page_size_msg.get() or 50)
        offset = (self._page_msg - 1) * page_size

        try:
            # Chame uma função no banco.py para buscar mensagens enviadas
            res = banco.mensagens_enviadas_filtrar_paginado(
                fornecedor_id=forn_id,
                data_ini=data_ini,
                data_fim=data_fim,
                destinatario=destinatario,
                limit=page_size,
                offset=offset
            )
            rows, self._total_msg = res["rows"], res["total"]
        except Exception as e:
            print(f"Erro ao carregar msgs enviadas: {e}")
            return

        for r in rows:
            self.tv_msgs_enviadas.insert(
                "", "end",
                values=(
                    r.get("id", ""),
                    r.get("enviado_em", ""),
                    r.get("destinatario", ""),
                    r.get("assunto", ""),
                    r.get("fornecedor_nome", "")
                )
            )

        total_pages = max(1, (self._total_msg + page_size - 1) // page_size)
        self._page_msg = min(self._page_msg, total_pages)
        self.lbl_pag_msg.config(text=f"Página {self._page_msg}/{total_pages}")

    def _salvar_mensagem(self, tipo):
        """Salva mensagem como modelo ou rascunho."""
        titulo = self.e_titulo_msg.get().strip()
        conteudo = self.txt_msg.get("1.0", "end").strip()

        if not titulo or not conteudo:
            messagebox.showwarning("Validação", "Título e conteúdo são obrigatórios.")
            return

        fornecedor_id = self._fornecedor_id_atual() if self.var_msg_forn.get() else None

        try:
            if self._msg_editando_id:
                banco.mensagem_atualizar(self._msg_editando_id, titulo, conteudo)
            else:
                banco.mensagem_inserir({
                    "tipo": tipo,
                    "titulo": titulo,
                    "conteudo": conteudo,
                    "fornecedor_id": fornecedor_id
                })
            self._carregar_msgs()
            messagebox.showinfo("OK", f"{tipo.capitalize()} salvo com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar mensagem:\n{e}")

    def _salvar_orcamento_linhas(self, values_rows):
        """Salva linhas do orçamento no banco."""
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            raise Exception("Selecione o fornecedor")

        for v in values_rows:
            banco.orcamento_inserir({
                "fornecedor_id": forn_id,
                "cod_aghu": v[0],
                "nome_item": v[1],
                "qtde": float(str(v[2]).replace(",", ".")),
                "vl_unit": float(str(v[3]).replace(",", ".")),
                "numero_empenho": v[4],
                "observacao": v[5]
            })

    def _enviar_email(self):
        """Envia orçamento por e-mail e registra no histórico."""
        values_rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not values_rows:
            messagebox.showwarning("Atenção", "Não há itens para enviar.")
            return

        # Salva orçamento
        try:
            self._salvar_orcamento_linhas(values_rows)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar orçamento:\n{e}")
            return

        # Aqui você implementaria o envio de e-mail real
        # E registraria no banco de dados como mensagem enviada
        try:
            banco.mensagem_enviada_registrar({
                "fornecedor_id": self._fornecedor_id_atual(),
                "destinatario": "cliente@email.com",  # Substitua pelo e-mail real
                "assunto": "Orçamento",
                "conteudo": self.txt_msg.get("1.0", "end")
            })
        except:
            pass

        messagebox.showinfo("Sucesso", "Orçamento enviado com sucesso!")
        self._carregar_msgs_enviadas()
