# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import banco
import utils

class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")

        # ========== TOPO: FORNECEDOR ==========
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=5)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: (
            self._reset_autosave_context(),
            self._carregar_itens_rascunho(),
            self._carregar_salvos(),
            self._carregar_msgs(),
            self._carregar_msgs_enviadas(),
        ))

        self._after_ids = []
        self._anexos_extra = []

        # ========== BLOCO 1: FORMULÁRIO PRINCIPAL ==========
        form = ttk.LabelFrame(self, text="Lançar itens para Orçamento")
        form.pack(fill="x", padx=12, pady=4)
        
        # Container com 2 colunas (ESQUERDA / DIREITA)
        container = tk.Frame(form)
        container.pack(fill="x", expand=True)
        
        # ========= ESQUERDA =========
        left = tk.Frame(container)
        left.pack(side="left", fill="x", expand=True)
        
        # ========= DIREITA =========
        right = tk.Frame(container)
        right.pack(side="right", fill="y", padx=(10, 0))
        
        
        def campo(lbl, col, row, width=22):
            tk.Label(left, text=lbl).grid(column=col, row=row, sticky="w", padx=2, pady=1)
            e = ttk.Entry(left, width=width)
            e.grid(column=col + 1, row=row, sticky="ew", padx=2, pady=1)
            return e
        
        # ===== LINHA 1 =====
        self.e_cod = campo("Cód AGHU*:", 0, 0)
        self.e_qt = campo("Qtde*:", 2, 0, 10)
        self.e_emp = campo("Nº Empenho:", 4, 0)
        
        # ===== LINHA 2 =====
        self.e_nome = campo("Nome item*:", 0, 1, 40)
        self.e_vu = campo("Vlr Unit*:", 2, 1, 10)
        
        tk.Label(left, text="Observação:").grid(column=4, row=1, sticky="w", padx=2, pady=1)
        self.e_obs = ttk.Entry(left, width=30)
        self.e_obs.grid(column=5, row=1, sticky="ew", padx=2, pady=1)
        
        # ===== BOTÃO ADD =====
        ttk.Button(left, text="Add", command=self._adicionar, width=10)\
            .grid(column=5, row=2, sticky="e", padx=2, pady=2)
        
        # ===== MODELO =====
        tk.Label(left, text="Modelo:").grid(column=0, row=2, sticky="w", padx=2, pady=1)
        
        self.cb_modelo = ttk.Combobox(left, state="readonly")
        self.cb_modelo.grid(column=1, row=2, columnspan=3, sticky="ew", padx=2, pady=1)
        
        ttk.Button(left, text="Carregar", command=self._carregar_modelo_rapido)\
            .grid(column=4, row=2, sticky="w", padx=2, pady=1)
        
        # ===== MENSAGEM =====
        tk.Label(left, text="Mensagem p/ e-mail:")\
            .grid(column=0, row=3, sticky="w", padx=2, pady=(4, 0))
        
        # Frame pra agrupar texto + scroll
        frame_msg = tk.Frame(left)
        frame_msg.grid(column=0, row=4, columnspan=4, sticky="nsew", padx=2, pady=2)
        
        # Campo de texto
        self.txt_msg = tk.Text(frame_msg, height=8, width=30, wrap="word")
        self.txt_msg.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scroll = ttk.Scrollbar(frame_msg, orient="vertical", command=self.txt_msg.yview)
        scroll.pack(side="right", fill="y")
        
        # Conectar scrollbar ao Text
        self.txt_msg.config(yscrollcommand=scroll.set)
        
        self._lbl_autosave = tk.Label(left, text="", fg="#2c7")
        self._lbl_autosave.grid(column=0, row=5, columnspan=6, sticky="w", padx=2)
        
        # 🔥 AQUI — ANTES DOS BINDs
        self._autosave_msg_id = None
        self._autosave_job = None
        self._msg_editando_id = None
        self._rascunho_inicializado = False
        
        # Eventos autosave
        self.txt_msg.bind("<KeyRelease>", lambda e: self._agendar_autosave())
        self.txt_msg.bind("<FocusOut>", lambda e: self._autosave_now())
        
        # Responsivo
        for col in [1, 3, 5]:
            left.columnconfigure(col, weight=1)
        
        
        # ========== CAIXA LATERAL (AGORA CORRETA) ==========
        side_box = ttk.LabelFrame(right, text="Mensagem: Modelo / Rascunho")
        side_box.pack(fill="y", expand=True)
        
        tk.Label(side_box, text="Assunto:").pack(anchor="w", padx=6, pady=(4, 0))
        self.e_titulo_msg = ttk.Entry(side_box, width=22)
        self.e_titulo_msg.pack(anchor="w", padx=6, pady=(0, 4))
        
        self.var_msg_forn = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            side_box,
            text="Vincular ao fornecedor atual",
            variable=self.var_msg_forn
        ).pack(anchor="w", padx=6, pady=(0, 4))
        
        btns_msg = tk.Frame(side_box)
        btns_msg.pack(fill="x", padx=6, pady=(0, 4))
        
        ttk.Button(btns_msg, text="Salvar Modelo",
                   command=lambda: self._salvar_mensagem("modelo")).pack(side="left", padx=2)
        
        ttk.Button(btns_msg, text="Salvar Rascunho",
                   command=lambda: self._salvar_mensagem("rascunho")).pack(side="left", padx=2)
        
        ttk.Button(side_box, text="Anexar arquivo",
                   command=self._add_anexo).pack(anchor="w", padx=6, pady=(0, 4))
        
        wrapper_anexos = ttk.LabelFrame(side_box, text="Anexos")
        wrapper_anexos.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        
        self.frm_anexos = tk.Frame(wrapper_anexos, height=50)
        self.frm_anexos.pack(fill="both", expand=True, padx=4, pady=4)
        self.frm_anexos.pack_propagate(False)
        
        self.lbl_sem_anexo = tk.Label(self.frm_anexos, text="Nenhum anexo", fg="#666")
        self.lbl_sem_anexo.pack(anchor="w")

        # ========== ABAS MODELOS/RASCUNHOS ==========
        lf_msg = ttk.LabelFrame(form, text="Mensagens (Modelos e Rascunhos)")
        lf_msg.pack(fill="x", padx=6, pady=5)
        
        # 🔥 BARRA ÚNICA (Editar + Buscar)
        bar_top = tk.Frame(lf_msg)
        bar_top.pack(fill="x", padx=6, pady=4)
        
        # ESQUERDA (Editar)
        ttk.Button(bar_top, text="Editar", command=self._editar_msg).pack(side="left")
        ttk.Button(bar_top, text="Salvar alterações", command=self._salvar_alteracoes_msg).pack(side="left", padx=6)
        
        # 👉 ESPAÇADOR (empurra pra direita)
        tk.Frame(bar_top).pack(side="left", expand=True)
        
        # DIREITA (Buscar)
        tk.Label(bar_top, text="Buscar:").pack(side="left")
        self.e_msg_busca = ttk.Entry(bar_top, width=30)
        self.e_msg_busca.pack(side="left", padx=6)
        ttk.Button(bar_top, text="Filtrar", command=self._carregar_msgs).pack(side="left")
        
        # NOTEBOOK MODELOS / RASCUNHOS
        self.nb_msg = ttk.Notebook(lf_msg)
        self.nb_msg.pack(fill="both", expand=True, padx=6, pady=4)
        
        # -------------------------------------------------------------
        # ABA 1 — MODELOS
        # -------------------------------------------------------------
        aba_modelos = tk.Frame(self.nb_msg)
        self.nb_msg.add(aba_modelos, text="Modelos")
        
        cols_m = ("id", "titulo", "fornecedor_id", "criado_em")
        self.tv_modelos = ttk.Treeview(aba_modelos, columns=cols_m, show="headings", height=5)
        for c, h, w in zip(cols_m, ("ID","Título","Fornecedor","Criado em"), (60,250,120,140)):
            self.tv_modelos.heading(c, text=h)
            self.tv_modelos.column(c, width=w, anchor="w")
        self.tv_modelos.pack(fill="both", expand=True, padx=4, pady=4)
        
        bar_m = tk.Frame(aba_modelos)
        bar_m.pack(fill="x", padx=4, pady=(0,4))
        
        ttk.Button(bar_m, text="Usar", command=lambda: self._usar_msg("modelo")).pack(side="left")
        ttk.Button(bar_m, text="Excluir", command=lambda: self._excluir_msg("modelo")).pack(side="left", padx=6)
        ttk.Button(bar_m, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)
        
        tk.Frame(bar_m).pack(side="left", expand=True)
        
        ttk.Button(bar_m, text="Exportar para Excel", command=self._exportar_excel).pack(side="right", padx=6)
        ttk.Button(bar_m, text="Enviar por e-mail", command=self._enviar_email).pack(side="right", padx=6)
        
        # -------------------------------------------------------------
        # ABA 2 — RASCUNHO
        # -------------------------------------------------------------
        aba_rasc = tk.Frame(self.nb_msg)
        self.nb_msg.add(aba_rasc, text="Rascunhos")
        
        cols_rasc  = ("id", "assunto", "cod_aghu", "nome_item", "fornecedor", "resumo")
        heads_rasc = ("Id", "Assunto", "Cód AGHU", "Nome Item", "Fornecedor", "Resumo da mensagem")
        widths_rasc = (60, 200, 90, 250, 180, 300)
        
        self.tv_rasc = ttk.Treeview(aba_rasc, columns=cols_rasc, show="headings", height=6)
        for c, h, w in zip(cols_rasc, heads_rasc, widths_rasc):
            self.tv_rasc.heading(c, text=h)
            self.tv_rasc.column(c, width=w, anchor="w")
        
        self.tv_rasc.pack(fill="both", expand=True, padx=4, pady=4)
        
        bar_r = tk.Frame(aba_rasc)
        bar_r.pack(fill="x", padx=4, pady=(0, 4))
        
        ttk.Button(bar_r, text="Usar", command=lambda: self._usar_msg("rascunho")).pack(side="left")
        ttk.Button(bar_r, text="Excluir", command=lambda: self._excluir_msg("rascunho")).pack(side="left", padx=6)
        ttk.Button(bar_r, text="Atualizar", command=self._carregar_msgs).pack(side="left", padx=6)
        
        tk.Frame(bar_r).pack(side="left", expand=True)
        
        ttk.Button(bar_r, text="Exportar para Excel", command=self._exportar_excel).pack(side="right", padx=6)
        ttk.Button(bar_r, text="Enviar por e-mail", command=self._enviar_email).pack(side="right", padx=6)

        # ========== NOTEBOOK HISTÓRICO + MENSAGENS ENVIADAS ==========
        notebook_hist = ttk.Notebook(self)
        notebook_hist.pack(fill="both", expand=True, padx=12, pady=5)
        
        # -------------------------------------------------------------
        # ABA 1 — ORÇAMENTOS SALVOS
        # -------------------------------------------------------------
        lf_hist = ttk.Frame(notebook_hist)
        notebook_hist.add(lf_hist, text="Orçamentos")
        
        # --- FILTROS ---
        filtros = tk.Frame(lf_hist)
        filtros.pack(fill="x", padx=6, pady=4)
        
        tk.Label(filtros, text="De:").pack(side="left")
        self.f_data_ini = ttk.Entry(filtros, width=10)
        self.f_data_ini.pack(side="left", padx=4)
        
        tk.Label(filtros, text="Até:").pack(side="left")
        self.f_data_fim = ttk.Entry(filtros, width=10)
        self.f_data_fim.pack(side="left", padx=4)
        
        tk.Label(filtros, text="Termo:").pack(side="left", padx=(12, 0))
        self.f_busca = ttk.Entry(filtros, width=25)
        self.f_busca.pack(side="left", padx=4)
        
        tk.Label(filtros, text="Empenho:").pack(side="left", padx=(12, 0))
        self.f_emp = ttk.Entry(filtros, width=12)
        self.f_emp.pack(side="left", padx=4)
        
        # Botões todos na mesma linha
        ttk.Button(filtros, text="Filtrar", command=self._resetar_paginacao).pack(side="left", padx=6)
        ttk.Button(filtros, text="Limpar", command=self._limpar_filtros).pack(side="left", padx=4)
        
        # 🔥 Botões movidos para a mesma linha:
        ttk.Button(filtros, text="Atualizar", command=self._carregar_salvos).pack(side="left", padx=(20,4))
        ttk.Button(filtros, text="Excluir", command=self._excluir_salvo).pack(side="left", padx=4)
        ttk.Button(filtros, text="Exportar", command=self._exportar_historico).pack(side="left", padx=4)
        
        # --- TABELA ORÇAMENTOS ---
        cols_s = ("id", "criado_em", "cod_aghu", "nome_item", "qtde", "vl_unit", "vl_total", "numero_empenho", "observacao")
        heads_s = ("ID", "Criado em", "Cód AGHU", "Item", "Qtde", "Vlr Unit", "Vlr Total", "Nº Empenho", "Obs")
        widths_s = (50, 120, 90, 200, 60, 80, 90, 110, 200)
        
        self.tv_salvos = ttk.Treeview(lf_hist, columns=cols_s, show="headings", height=5)
        for c, h, w in zip(cols_s, heads_s, widths_s):
            self.tv_salvos.heading(c, text=h)
            self.tv_salvos.column(c, width=w, anchor="w")
        self.tv_salvos.pack(fill="both", expand=True, padx=6, pady=4)
                
        # --- PAGINAÇÃO ORÇAMENTOS ---
        pag = tk.Frame(lf_hist, bg="white")
        pag.pack(fill="x", padx=6, pady=(0, 4))
        
        tk.Label(pag, text="Itens/página:").pack(side="left")
        self.cb_page_size = ttk.Combobox(pag, state="readonly", width=5, values=[20, 50, 100])
        
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
        
        # -------------------------------------------------------------
        # ABA 2 — MENSAGENS ENVIADAS
        # -------------------------------------------------------------
        lf_msgs_env = ttk.Frame(notebook_hist)
        notebook_hist.add(lf_msgs_env, text="Mensagens enviadas")
        
        # --- FILTROS MSG ---
        filtros_msg = tk.Frame(lf_msgs_env)
        filtros_msg.pack(fill="x", padx=6, pady=4)
        
        tk.Label(filtros_msg, text="De:").pack(side="left")
        self.f_msg_data_ini = ttk.Entry(filtros_msg, width=10)
        self.f_msg_data_ini.pack(side="left", padx=4)
        
        tk.Label(filtros_msg, text="Até:").pack(side="left")
        self.f_msg_data_fim = ttk.Entry(filtros_msg, width=10)
        self.f_msg_data_fim.pack(side="left", padx=4)
        
        tk.Label(filtros_msg, text="Destinatário:").pack(side="left", padx=(12, 0))
        self.f_msg_dest = ttk.Entry(filtros_msg, width=25)
        self.f_msg_dest.pack(side="left", padx=4)
        
        ttk.Button(filtros_msg, text="Filtrar", command=self._resetar_paginacao_msgs).pack(side="left", padx=6)
        ttk.Button(filtros_msg, text="Limpar", command=self._limpar_filtros_msgs).pack(side="left")
        
        # --- TABELA MSG ENVIADAS ---
        cols_msg = ("id", "enviado_em", "destinatario", "assunto", "fornecedor")
        heads_msg = ("ID", "Enviado em", "Destinatário", "Assunto", "Fornecedor")
        widths_msg = (50, 120, 180, 250, 150)
        
        self.tv_msgs_enviadas = ttk.Treeview(lf_msgs_env, columns=cols_msg, show="headings", height=5)
        for c, h, w in zip(cols_msg, heads_msg, widths_msg):
            self.tv_msgs_enviadas.heading(c, text=h)
            self.tv_msgs_enviadas.column(c, width=w, anchor="w")
        self.tv_msgs_enviadas.pack(fill="both", expand=True, padx=6, pady=4)
        
        # --- PAGINAÇÃO MSG ---
        pag_msg = tk.Frame(lf_msgs_env, bg="white")
        pag_msg.pack(fill="x", padx=6, pady=(0, 4))
        
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

        # Inicializa
        self._page = 1
        self._total = 0
        self._page_msg = 1
        self._total_msg = 0
        self.map_fornec = {}
        self._modelos_cache = []

        self._carregar_fornecedores()
        self._carregar_salvos()
        self._carregar_msgs()
        self._carregar_msgs_enviadas()

        self.tv_rasc.bind("<<TreeviewSelect>>", self._ao_selecionar_rascunho)


    # ==================== MÉTODOS DE SUPORTE ====================

    def _add_anexo(self):
        arq = filedialog.askopenfilename(title="Selecionar anexo", filetypes=[("Todos os arquivos", "*.*")])
        if not arq:
            return
        self._anexos_extra.append(arq)
        self._atualizar_lista_anexos()

    def _atualizar_lista_anexos(self):
        for w in self.frm_anexos.winfo_children():
            w.destroy()
        if not self._anexos_extra:
            self.lbl_sem_anexo = tk.Label(self.frm_anexos, text="Nenhum anexo", bg="white", fg="#666")
            self.lbl_sem_anexo.pack(anchor="w")
            return
        for idx, path in enumerate(self._anexos_extra, start=1):
            nome = os.path.basename(path)
            linha = tk.Frame(self.frm_anexos, bg="white")
            linha.pack(anchor="w", fill="x", pady=1)
            tk.Label(linha, text=f"{idx}. {nome}", bg="white").pack(side="left", padx=(2, 6))
            ttk.Button(linha, text="X", width=3, command=lambda p=path: self._remover_anexo(p)).pack(side="left")

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
        self._msg_editando_id = None

    def _agendar_autosave(self):
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(1000, self._autosave_now)

    def _autosave_now(self):
        import json
        titulo = self.e_titulo_msg.get().strip()
        conteudo = self.txt_msg.get("1.0", "end").strip()
    
        # cria título automático se vazio
        if not titulo:
            titulo = f"Rascunho {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
        # montar dados completos do rascunho
        d = {
            "tipo": "rascunho",
            "titulo": titulo,
            "conteudo": conteudo,
            "fornecedor_id": self._fornecedor_id_atual(),
            "cod_aghu": self.e_cod.get().strip(),
            "nome_item": self.e_nome.get().strip(),
            "fornecedor_nome": self.cb_fornec.get() if self.var_msg_forn.get() else "",
            "vl_unit": self.e_vu.get().strip(),
            "numero_empenho": self.e_emp.get().strip(),
            "anexos": json.dumps(self._anexos_extra)
        }
    
        # ===================== CRIAR RASCUNHO =====================
        if not self._autosave_msg_id and not self._msg_editando_id:
            try:
                novo_id = banco.mensagem_inserir(d)
                self._autosave_msg_id = novo_id
                self._msg_editando_id = novo_id
    
                # atualizar campo do título
                self.e_titulo_msg.delete(0, "end")
                self.e_titulo_msg.insert(0, titulo)
    
            except Exception as e:
                print("Erro ao criar rascunho automático:", e)
                return
    
        # ===================== ATUALIZAR RASCUNHO =====================
        else:
            try:
                banco.mensagem_atualizar(
                    self._msg_editando_id,
                    titulo,
                    conteudo,
                    cod_aghu=self.e_cod.get().strip(),
                    nome_item=self.e_nome.get().strip(),
                    fornecedor_nome=self.cb_fornec.get() if self.var_msg_forn.get() else "",
                    vl_unit=self.e_vu.get().strip(),
                    numero_empenho=self.e_emp.get().strip(),
                    qtde=self.e_qt.get().strip(),
                    observacao=self.e_obs.get().strip(),
                    anexos=json.dumps(self._anexos_extra)
                )
            except Exception as e:
                print("Erro ao atualizar rascunho automático:", e)
    
        # ===================== FEEDBACK =====================
        self._lbl_autosave.config(text="Rascunho salvo automaticamente")
        self.after(2000, lambda: self._lbl_autosave.config(text=""))
        
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
    
        # gerar resumo da mensagem
        conteudo = self.txt_msg.get("1.0", "end").strip()
        resumo = (conteudo[:60] + "...") if len(conteudo) > 60 else conteudo
        
        self.tv_rasc.insert(
            "",
            "end",
            values=(
                self.e_cod.get().strip(),
                self.e_nome.get().strip(),
                f"{qt}",
                self.cb_fornec.get(),
                resumo
            )
        )    
        try:
            banco.itens_rascunho_inserir({
                "fornecedor_id": self._fornecedor_id_atual(),
                "cod_aghu": self.e_cod.get().strip(),
                "nome_item": self.e_nome.get().strip(),
                "qtde": qt,
                "vl_unit": vu,
                "numero_empenho": self.e_emp.get().strip(),
                "observacao": self.e_obs.get().strip(),
                #"mensagem_email": self.txt_msg.get("1.0", "end").strip()
            })
        except Exception as e:
            messagebox.showwarning("Rascunho", f"Erro ao salvar rascunho:\n{e}")
    
        for e in (self.e_cod, self.e_nome, self.e_qt, self.e_vu, self.e_emp, self.e_obs):
            e.delete(0, "end")

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

    def _limpar_filtros(self):
        self.f_data_ini.delete(0, "end")
        self.f_data_fim.delete(0, "end")
        self.f_busca.delete(0, "end")
        self.f_emp.delete(0, "end")
        self._resetar_paginacao()

    def _filtros_atual(self):
        di = self.f_data_ini.get().strip() or None
        df = self.f_data_fim.get().strip() or None
        termo = self.f_busca.get().strip()
        nem = self.f_emp.get().strip()
        return di, df, termo, nem

    def _carregar_modelo_rapido(self):
        titulo = self.cb_modelo.get()
        if not titulo:
            return
        for m in self._modelos_cache:
            if m["titulo"] == titulo:
                msg = banco.mensagem_obter(m["id"])
                if msg:
                    self.txt_msg.delete("1.0", "end")
                    self.txt_msg.insert("1.0", msg.get("conteudo", ""))
                    self.e_titulo_msg.delete(0, "end")
                    self.e_titulo_msg.insert(0, msg.get("titulo", ""))
                    self._autosave_msg_id = None
                break

    def _carregar_salvos(self):
        forn_id = self._fornecedor_id_atual()
        for i in self.tv_salvos.get_children():
            self.tv_salvos.delete(i)
        if not forn_id:
            self._total = 0
            self._page = 1
            self.lbl_pag.config(text="Página 1/1")
            return
        di, df, termo, nem = self._filtros_atual()
        page_size = int(self.cb_page_size.get() or 50)
        offset = (self._page - 1) * page_size
        try:
            res = banco.orcamentos_filtrar_paginado(
                fornecedor_id=forn_id, data_ini=di, data_fim=df,
                termo=termo, numero_empenho=nem, limit=page_size, offset=offset,
            )
            rows, self._total = res["rows"], res["total"]
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar histórico:\n{e}")
            return
        for r in rows:
            qt = float(r.get("qtde", 0) or 0)
            vu = float(r.get("vl_unit", 0) or 0)
            self.tv_salvos.insert("", "end", values=(
                r.get("id", ""), r.get("criado_em", ""), r.get("cod_aghu", ""),
                r.get("nome_item", ""), f"{qt}", f"{vu:.2f}", f"{qt * vu:.2f}",
                r.get("numero_empenho", "") or "", r.get("observacao", "") or "",
            ))
        total_pages = max(1, (self._total + page_size - 1) // page_size)
        self._page = min(self._page, total_pages)
        self.lbl_pag.config(text=f"Página {self._page}/{total_pages} — {self._total} registro(s)")

    def _exportar_historico(self):
        fornecedor_id = self._fornecedor_id_atual()
        if not fornecedor_id:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return
        di, df, termo, nem = self._filtros_atual()
        try:
            rows = banco.orcamentos_filtrar(fornecedor_id=fornecedor_id, data_ini=di, data_fim=df, termo=termo, numero_empenho=nem)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao filtrar histórico:\n{e}")
            return
        if not rows:
            messagebox.showinfo("Histórico", "Nenhum registro encontrado.")
            return
        arq = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Salvar histórico de orçamentos")
        if not arq:
            return
        import pandas as pd
        dados = []
        for r in rows:
            qt = float(r.get("qtde", 0) or 0)
            vu = float(r.get("vl_unit", 0) or 0)
            dados.append({"Criado em": r.get("criado_em", ""), "Cód AGHU": r.get("cod_aghu", ""),
                "Item": r.get("nome_item", ""), "Qtde": qt, "Vlr Unit": vu, "Vlr Total": qt * vu,
                "Nº Empenho": r.get("numero_empenho", "") or "", "Obs": r.get("observacao", "") or ""})
        df = pd.DataFrame(dados)
        utils.exportar_excel({"Histórico": df}, arq)
        messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{arq}")

    def _exportar_excel(self):
        values_rows = [self.tv_rasc.item(iid, "values") for iid in self.tv_rasc.get_children()]
        if not values_rows:
            messagebox.showinfo("Exportação", "Não há itens no rascunho para exportar.")
            return
        try:
            self._salvar_orcamento_linhas(values_rows)
        except Exception as e:
            messagebox.showwarning("Salvar orçamento", f"Não foi possível salvar no banco antes de exportar:\n{e}")
        linhas = []
        for v in values_rows:
            linhas.append({"Cód AGHU": v[0], "Nome": v[1], "Qtde": float(str(v[2]).replace(",", ".")),
                "Valor Unitário": float(str(v[3]).replace(",", ".")), "Nº Empenho": v[4],
                "Observação": v[5], "Valor Total": float(str(v[6]).replace(",", "."))})
        arq = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Salvar orçamento")
        if not arq:
            return
        try:
            df = utils.tabela_para_dataframe(linhas, ["Cód AGHU", "Nome", "Qtde", "Valor Unitário", "Valor Total", "Nº Empenho", "Observação"])
            utils.exportar_excel({"Orcamento": df}, arq)
            messagebox.showinfo("Exportação", f"Planilha salva em:\n{arq}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar para Excel:\n{e}")

    def _excluir_salvo(self):
        sel = self.tv_salvos.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um orçamento salvo para excluir.")
            return
        vals = self.tv_salvos.item(sel[0], "values")
        try:
            id_ = int(vals[0])
        except Exception:
            messagebox.showwarning("Erro", "Não foi possível identificar o ID do registro.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir o orçamento selecionado?"):
            return
        try:
            banco.orcamento_excluir(id_)
            self._carregar_salvos()
            messagebox.showinfo("OK", "Registro excluído com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir: {e}")

    def _usar_msg(self, tipo: str):
        tv = self.tv_modelos if tipo == "modelo" else self.tv_rasc
        sel = tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem.")
            return
    
        vals = tv.item(sel[0], "values")
        try:
            mid = int(vals[0])
        except:
            return
    
        msg = banco.mensagem_obter(mid)
        if not msg:
            return
    
        # guardar id
        self._msg_editando_id = mid
        self._autosave_msg_id = mid if msg.get("tipo") == "rascunho" else None
    
        # preencher campos da direita
        self.e_titulo_msg.delete(0, "end")
        self.e_titulo_msg.insert(0, msg.get("titulo", ""))
    
        self.txt_msg.delete("1.0", "end")
        self.txt_msg.insert("1.0", msg.get("conteudo", ""))
    
        # preencher CAMPOS DO ORÇAMENTO 🔥
        self.e_cod.delete(0, "end")
        self.e_cod.insert(0, msg.get("cod_aghu", ""))
    
        self.e_nome.delete(0, "end")
        self.e_nome.insert(0, msg.get("nome_item", ""))
    
        self.e_vu.delete(0, "end")
        self.e_vu.insert(0, msg.get("vl_unit", ""))
    
        self.e_emp.delete(0, "end")
        self.e_emp.insert(0, msg.get("numero_empenho", ""))
    
        # fornecedor (nome)
        if msg.get("fornecedor_nome"):
            self.cb_fornec.set(msg.get("fornecedor_nome"))
    
        # anexos
        import json
        anexos = msg.get("anexos")
        try:
            self._anexos_extra = json.loads(anexos) if anexos else []
        except:
            self._anexos_extra = []
    
        self._atualizar_lista_anexos()
    
        self.txt_msg.focus_set()

    def _carregar_msgs(self):
        forn_id = self._fornecedor_id_atual()
        busca = self.e_msg_busca.get().strip() if hasattr(self, "e_msg_busca") else ""
    
        # limpar modelos e rascunhos
        if hasattr(self, "tv_modelos"):
            for i in self.tv_modelos.get_children():
                self.tv_modelos.delete(i)
    
        if hasattr(self, "tv_rasc"):
            for i in self.tv_rasc.get_children():
                self.tv_rasc.delete(i)
    
        if hasattr(self, "cb_modelo"):
            self.cb_modelo.set("")
            self.cb_modelo["values"] = []
    
        # função auxiliar interna
        def _safe_listar(tipo: str, fornecedor_id):
            try:
                base = banco.mensagens_listar(tipo=tipo, fornecedor_id=fornecedor_id, busca=busca) or []
            except:
                base = []
    
            if fornecedor_id is not None:
                try:
                    glb = banco.mensagens_listar(tipo=tipo, fornecedor_id=None, busca=busca) or []
                except:
                    glb = []
    
                usados = set(m.get("id") for m in base)
                for g in glb:
                    if g.get("id") not in usados:
                        base.append(g)
    
            try:
                base.sort(key=lambda m: (m.get("criado_em") or "", m.get("id") or 0), reverse=True)
            except:
                pass
    
            return base
    
        # ===============================================
        #   MODELOS
        # ===============================================
        modelos = _safe_listar("modelo", forn_id)
        self._modelos_cache = modelos[:]
    
        if hasattr(self, "cb_modelo"):
            self.cb_modelo["values"] = [m.get("titulo", "") for m in modelos]
    
        for m in modelos:
            escopo = "Global" if m.get("fornecedor_id") in (None, "") else f"Forn {m['fornecedor_id']}"
            self.tv_modelos.insert(
                "",
                "end",
                values=(
                    m.get("id", ""),
                    m.get("titulo", ""),
                    escopo,
                    m.get("criado_em", "")
                )
            )
    
        # ===============================================
        #   RASCUNHOS — versão corrigida
        # ===============================================
        rasc = _safe_listar("rascunho", forn_id)
    
        for m in rasc:
    
            # resumo da mensagem (conteúdo)
            conteudo = m.get("conteudo") or ""
            resumo = (conteudo[:60] + "...") if len(conteudo) > 60 else conteudo
    
            # inserir na grid SOMENTE o que deve aparecer
            self.tv_rasc.insert(
                "",
                "end",
                values=(
                    m.get("id", ""),                 # ID
                    m.get("titulo", ""),             # ASSUNTO
                    m.get("cod_aghu", ""),           # CÓD AGHU
                    m.get("nome_item", ""),          # NOME DO ITEM
                    m.get("fornecedor_nome", ""),    # FORNECEDOR
                    resumo                           # RESUMO
                )
            )

    def _editar_msg(self):
        aba_atual = self.nb_msg.index(self.nb_msg.select())
    
        # 0 = Modelos
        # 1 = Rascunhos
        if aba_atual == 0:
            tv = self.tv_modelos
            tipo = "modelo"
        else:
            tv = self.tv_rasc
            tipo = "rascunho"
    
        sel = tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem.")
            return
    
        vals = tv.item(sel[0], "values")
    
        try:
            mid = int(vals[0])
        except:
            messagebox.showerror("Erro", "ID inválido.")
            return
    
        msg = banco.mensagem_obter(mid)
        if not msg:
            messagebox.showerror("Erro", "Mensagem não encontrada.")
            return
    
        self._msg_editando_id = mid
        self._autosave_msg_id = mid if tipo == "rascunho" else None
    
        # título
        self.e_titulo_msg.delete(0, "end")
        self.e_titulo_msg.insert(0, msg.get("titulo", ""))
    
        # conteúdo
        self.txt_msg.delete("1.0", "end")
        self.txt_msg.insert("1.0", msg.get("conteudo", ""))
    
        # --- CAMPOS DO ORÇAMENTO ---
        self.e_cod.delete(0, "end")
        self.e_cod.insert(0, msg.get("cod_aghu", ""))
    
        self.e_nome.delete(0, "end")
        self.e_nome.insert(0, msg.get("nome_item", ""))
    
        self.e_vu.delete(0, "end")
        self.e_vu.insert(0, msg.get("vl_unit", ""))
    
        self.e_emp.delete(0, "end")
        self.e_emp.insert(0, msg.get("numero_empenho", ""))

        # carregar qtde
        self.e_qt.delete(0, "end")
        self.e_qt.insert(0, msg.get("qtde", ""))
        
        # carregar observação
        self.e_obs.delete(0, "end")
        self.e_obs.insert(0, msg.get("observacao", ""))
    
        # --- FORNECEDOR ---
        if msg.get("fornecedor_nome"):
            self.cb_fornec.set(msg.get("fornecedor_nome"))
            self.var_msg_forn.set(True)   # 🔥 CORREÇÃO IMPORTANTE
        else:
            self.var_msg_forn.set(False)
    
        # --- ANEXOS ---
        import json
        anexos = msg.get("anexos")
        try:
            self._anexos_extra = json.loads(anexos) if anexos else []
        except:
            self._anexos_extra = []
    
        self._atualizar_lista_anexos()
        self.txt_msg.focus_set()

    def _salvar_alteracoes_msg(self):
        if not self._msg_editando_id:
            messagebox.showwarning("Edição", "Nenhuma mensagem carregada para edição.")
            return
    
        titulo = (self.e_titulo_msg.get() or "").strip()
        conteudo = self.txt_msg.get("1.0", "end").strip()
    
        if not conteudo:
            messagebox.showwarning("Validação", "Conteúdo não pode ser vazio.")
            return
    
        # Obter info do banco para descobrir se é modelo ou rascunho
        msg_atual = banco.mensagem_obter(self._msg_editando_id)
        tipo_msg = msg_atual.get("tipo", "rascunho")
    
        # MODELO → exige título
        if tipo_msg == "modelo" and not titulo:
            messagebox.showwarning("Validação", "Título é obrigatório para modelos.")
            return
    
        # RASCUNHO → título não obrigatório
        if tipo_msg == "rascunho" and not titulo:
            titulo = f"Rascunho {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
        try:
            banco.mensagem_atualizar(
                self._msg_editando_id,
                titulo,
                conteudo,
                cod_aghu=self.e_cod.get().strip(),
                nome_item=self.e_nome.get().strip(),
                fornecedor_nome=self.cb_fornec.get() if self.var_msg_forn.get() else "",
                vl_unit=self.e_vu.get().strip(),
                numero_empenho=self.e_emp.get().strip(),
                qtde=self.e_qt.get().strip(),
                observacao=self.e_obs.get().strip(),
                anexos=json.dumps(self._anexos_extra)
            )
            self._carregar_msgs()
            messagebox.showinfo("OK", "Mensagem atualizada com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar mensagem:\n{e}")

    def _excluir_msg(self, tipo: str):
        tv = self.tv_modelos if tipo == "modelo" else self.tv_rasc
        sel = tv.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma mensagem para excluir.")
            return
        vals = tv.item(sel[0], "values")
        try:
            mid = int(vals[0])
        except:
            messagebox.showerror("Erro", "ID inválido.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir a mensagem selecionada?"):
            return
        try:
            banco.mensagem_excluir(mid)
            self._msg_editando_id = None
            self._autosave_msg_id = None
            self._carregar_msgs()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir mensagem:\n{e}")

    def _salvar_mensagem(self, tipo):
        import json
    
        titulo = self.e_titulo_msg.get().strip()
        conteudo = self.txt_msg.get("1.0", "end").strip()
    
        # ================= VALIDAÇÕES =================
        if tipo == "modelo":
            if not titulo or not conteudo:
                messagebox.showwarning("Validação", "Título e conteúdo são obrigatórios para modelos.")
                return
    
        if tipo == "rascunho":
            # Rascunho pode ser salvo SEM mensagem
            if not conteudo:
                conteudo = ""   # permite rascunho vazio

            # título automático se vazio
            if not titulo:
                titulo = f"Rascunho {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
        fornecedor_id = self._fornecedor_id_atual() if self.var_msg_forn.get() else None
    
        try:
            # ================= ATUALIZAR =================
            if self._msg_editando_id:
                banco.mensagem_atualizar(
                    self._msg_editando_id,
                    titulo,
                    conteudo,
                    cod_aghu=self.e_cod.get().strip(),
                    nome_item=self.e_nome.get().strip(),
                    fornecedor_nome=self.cb_fornec.get() if self.var_msg_forn.get() else "",
                    vl_unit=self.e_vu.get().strip(),
                    numero_empenho=self.e_emp.get().strip(),
                    qtde=self.e_qt.get().strip(),
                    observacao=self.e_obs.get().strip(),
                    anexos=json.dumps(self._anexos_extra)
                )
    
            # ================= INSERIR =================
            else:
                novo_id = banco.mensagem_inserir({
                    "tipo": tipo,
                    "titulo": titulo,
                    "conteudo": conteudo,
            
                    # respeitar o checkbox
                    "fornecedor_id": self._fornecedor_id_atual() if self.var_msg_forn.get() else None,
            
                    # salvar todos os campos
                    "cod_aghu": self.e_cod.get().strip(),
                    "nome_item": self.e_nome.get().strip(),
                    "fornecedor_nome": self.cb_fornec.get() if self.var_msg_forn.get() else "",
                    "vl_unit": self.e_vu.get().strip(),
                    "numero_empenho": self.e_emp.get().strip(),
                    "qtde": self.e_qt.get().strip(),
                    "observacao": self.e_obs.get().strip(),
                    "anexos": json.dumps(self._anexos_extra)
                })
            
                self._msg_editando_id = novo_id
                self._autosave_msg_id = novo_id
    
                # 🔥 importante pro autosave não criar outro
                self._msg_editando_id = novo_id
                self._autosave_msg_id = novo_id
    
            # ================= PÓS-SALVAMENTO =================
            self._carregar_msgs()
            messagebox.showinfo("OK", f"{tipo.capitalize()} salvo com sucesso.")
    
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar mensagem:\n{e}")

    def _salvar_orcamento_linhas(self, values_rows):
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            raise Exception("Selecione o fornecedor")
        for v in values_rows:
            banco.orcamento_inserir({
                "fornecedor_id": forn_id, "cod_aghu": v[0], "nome_item": v[1],
                "qtde": float(str(v[2]).replace(",", ".")),
                "vl_unit": float(str(v[3]).replace(",", ".")),
                "numero_empenho": v[4], "observacao": v[5]
            })

    def _enviar_email(self):
        values_rows = [self.tv_rasc.item(iid, "values") for iid in self.tv_rasc.get_children()]
        if not values_rows:
            messagebox.showwarning("Atenção", "Não há itens para enviar.")
            return
        try:
            self._salvar_orcamento_linhas(values_rows)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar orçamento:\n{e}")
            return
        try:
            banco.mensagem_enviada_registrar({
                "fornecedor_id": self._fornecedor_id_atual(),
                "destinatario": "cliente@email.com",
                "assunto": "Orçamento",
                "conteudo": self.txt_msg.get("1.0", "end")
            })
        except Exception as e:
            print(f"Erro ao registrar msg enviada: {e}")
        messagebox.showinfo("Sucesso", "Orçamento enviado com sucesso!")
        self._carregar_msgs_enviadas()

    def _carregar_itens_rascunho(self):
        for i in self.tv_rasc.get_children():
            self.tv_rasc.delete(i)
    
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            return
    
        try:
            rows = banco.itens_rascunho_listar(fornecedor_id=forn_id)
            for r in rows:
                qt = float(r.get("qtde", 0) or 0)
                vu = float(r.get("vl_unit", 0) or 0)
                vt = qt * vu
    
                # gerar resumo baseado no campo mensagem_email (se você gravou isso no salvamento)
                msg = r.get("mensagem_email", "") or ""
                resumo = (msg[:60] + "...") if len(msg) > 60 else msg
                
                self.tv_rasc.insert("", "end", values=(
                    r["cod_aghu"],
                    r["nome_item"],
                    f"{qt}",
                    nome_forn,
                    resumo
                ))
        except Exception as e:
            print("Erro ao carregar rascunho:", e)

    def _ao_selecionar_rascunho(self, event):
        sel = self.tv_rasc.selection()
        if not sel:
            return
    
        item = self.tv_rasc.item(sel[0])
        cod_aghu = item["values"][0]
        nome_item = item["values"][1]
    
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            return
    
        try:
            rows = banco.itens_rascunho_listar(fornecedor_id=forn_id)
    
            for r in rows:
                if r["cod_aghu"] == cod_aghu and r["nome_item"] == nome_item:
                    msg = r.get("mensagem_email", "") or ""
    
                    # 🔥 carregar mensagem completa
                    self.txt_msg.delete("1.0", "end")
                    self.txt_msg.insert("1.0", msg)
    
                    break
    
        except Exception as e:
            print("Erro ao carregar mensagem completa:", e)

    def _carregar_msgs_enviadas(self):
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
            res = banco.mensagens_enviadas_filtrar_paginado(
                fornecedor_id=forn_id, data_ini=data_ini, data_fim=data_fim,
                destinatario=destinatario, limit=page_size, offset=offset
            )
            rows, self._total_msg = res["rows"], res["total"]
        except Exception as e:
            print(f"Erro ao carregar msgs enviadas: {e}")
            return
        for r in rows:
            self.tv_msgs_enviadas.insert("", "end", values=(
                r.get("id", ""), r.get("enviado_em", ""), r.get("destinatario", ""),
                r.get("assunto", ""), r.get("fornecedor_nome", "")
            ))
        total_pages = max(1, (self._total_msg + page_size - 1) // page_size)
        self._page_msg = min(self._page_msg, total_pages)
        self.lbl_pag_msg.config(text=f"Página {self._page_msg}/{total_pages}")
