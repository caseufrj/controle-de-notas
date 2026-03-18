# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import banco
import utils
import tempfile

class TelaOrcamento(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # ---------- Topo: fornecedor ----------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        tk.Label(topo, text="Fornecedor:", bg="white").pack(side="left")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.pack(side="left", padx=6)
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: self._carregar_salvos())

        # ---------- Formulário de lançamento ----------
        form = ttk.LabelFrame(self, text="Lançar itens para Orçamento")
        form.pack(fill="x", padx=12, pady=8)

        def campo(lbl, col, row, width=28):
            tk.Label(form, text=lbl).grid(column=col, row=row, sticky="w", padx=6, pady=3)
            e = ttk.Entry(form, width=width)
            e.grid(column=col+1, row=row, sticky="w", padx=6, pady=3)
            return e

        self.e_cod = campo("Cód AGHU*:", 0, 0)
        self.e_nome = campo("Nome item*:", 0, 1, 40)
        self.e_qt = campo("Qtde*:", 2, 0, 12)
        self.e_vu = campo("Vlr Unit*:", 2, 1, 12)
        self.e_emp = campo("Nº Empenho:", 4, 0)
        tk.Label(form, text="Observação:").grid(column=4, row=1, sticky="w", padx=6, pady=3)
        self.e_obs = ttk.Entry(form, width=40)
        self.e_obs.grid(column=5, row=1, sticky="w", padx=6, pady=3)

        tk.Label(form, text="Mensagem p/ e-mail:").grid(column=0, row=3, sticky="nw", padx=6, pady=3)
        self.txt_msg = tk.Text(form, width=80, height=4)
        self.txt_msg.grid(column=1, row=3, columnspan=5, sticky="w", padx=6, pady=3)

        btns_form = tk.Frame(form, bg="white")
        btns_form.grid(column=5, row=0, rowspan=2, sticky="e", padx=6)
        ttk.Button(btns_form, text="Add", command=self._adicionar).pack(side="top", pady=2)

        # ---------- Grade: Itens em rascunho (memória) ----------
        lf_rasc = ttk.LabelFrame(self, text="Itens em rascunho (não salvos)")
        lf_rasc.pack(fill="both", expand=True, padx=12, pady=(4, 2))

        cols = ("cod","nome","qt","vu","emp","obs","vl_total")
        heads = ("Cód AGHU","Nome","Qtde","Vlr Unit","Nº Empenho","Obs","Vlr Total")
        widths = (100,260,60,90,120,260,100)
        self.tv = ttk.Treeview(lf_rasc, columns=cols, show="headings", height=6)
        for c, h, w in zip(cols, heads, widths):
            self.tv.heading(c, text=h)
            self.tv.column(c, width=w, anchor="w")
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)

        # ---------- Rodapé: ações ----------
        rod = tk.Frame(self, bg="white")
        rod.pack(fill="x", padx=12, pady=8)
        self.btn_email = ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email)
        self.btn_email.pack(side="right", padx=6)
        self.btn_export = ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel)
        self.btn_export.pack(side="right", padx=6)

        # ---------- Grade: Orçamentos já salvos ----------
        lf_hist = ttk.LabelFrame(self, text="Orçamentos já salvos (no banco) — por fornecedor")
        lf_hist.pack(fill="both", expand=True, padx=12, pady=(2, 10))

        cols_s = ("id","criado_em","cod_aghu","nome_item","qtde","vl_unit","vl_total","numero_empenho","observacao")
        heads_s = ("ID","Criado em","Cód AGHU","Item","Qtde","Vlr Unit","Vlr Total","Nº Empenho","Obs")
        widths_s = (60,140,100,260,70,90,100,120,260)
        self.tv_salvos = ttk.Treeview(lf_hist, columns=cols_s, show="headings", height=8)
        for c, h, w in zip(cols_s, heads_s, widths_s):
            self.tv_salvos.heading(c, text=h)
            self.tv_salvos.column(c, width=w, anchor="w")
        self.tv_salvos.pack(fill="both", expand=True, padx=6, pady=(6,2))

        barra_hist = tk.Frame(lf_hist, bg="white")
        barra_hist.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(barra_hist, text="Atualizar", command=self._carregar_salvos).pack(side="left")
        ttk.Button(barra_hist, text="Excluir selecionado", command=self._excluir_salvo).pack(side="left", padx=6)
        tip = tk.Label(barra_hist, text="Dica: selecione o fornecedor no topo para ver os orçamentos salvos.",
                       bg="white", fg="#7f8c8d")
        tip.pack(side="left", padx=12)

        # Estado
        self.map_fornec = {}

        # Carrega fornecedores e histórico inicial
        self._carregar_fornecedores()
        self._carregar_salvos()

    # ----------------- Utilidades -----------------
    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs:
            if not self.cb_fornec.get():
                self.cb_fornec.current(0)

    def _fornecedor_id_atual(self):
        nome = self.cb_fornec.get()
        if not nome:
            return None
        return self.map_fornec.get(nome)

    def _adicionar(self):
        # validação e inserção no rascunho
        try:
            qt = float(str(self.e_qt.get() or 0).replace(",", "."))
            vu = float(str(self.e_vu.get() or 0).replace(",", "."))
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

    # ---------- Persistência ----------
    def _salvar_orcamento_linhas(self, values_rows) -> int:
        """
        Salva cada linha (values) do rascunho no banco, para o fornecedor atual.
        Retorna a quantidade salva.
        """
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            raise RuntimeError("Selecione o fornecedor.")

        mensagem = self.txt_msg.get("1.0", "end").strip()
        salvos = 0
        for v in values_rows:
            try:
                banco.orcamento_inserir({
                    "fornecedor_id": forn_id,
                    "cod_aghu": v[0],
                    "nome_item": v[1],
                    "qtde": float(str(v[2]).replace(",", ".")),
                    "vl_unit": float(str(v[3]).replace(",", ".")),
                    "numero_empenho": v[4],
                    "observacao": v[5],
                    "mensagem_email": mensagem
                })
                salvos += 1
            except Exception:
                continue
        return salvos

    def _carregar_salvos(self):
        """Recarrega a tabela de orçamentos salvos para o fornecedor atual."""
        forn_id = self._fornecedor_id_atual()
        for i in self.tv_salvos.get_children():
            self.tv_salvos.delete(i)
        if not forn_id:
            return
        try:
            rows = banco.orcamentos_listar(fornecedor_id=forn_id)
            for r in rows:
                self.tv_salvos.insert("", "end", values=(
                    r.get("id",""),
                    r.get("criado_em",""),
                    r.get("cod_aghu",""),
                    r.get("nome_item",""),
                    r.get("qtde",0),
                    f'{r.get("vl_unit",0):.2f}',
                    f'{(r.get("qtde",0) or 0) * (r.get("vl_unit",0) or 0):.2f}',
                    r.get("numero_empenho","") or "",
                    r.get("observacao","") or ""
                ))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar orçamentos salvos:\n{e}")

    def _excluir_salvo(self):
        sel = self.tv_salvos.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma linha salva para excluir.")
            return
        vals = self.tv_salvos.item(sel[0], "values")
        try:
            id_ = int(vals[0])
        except Exception:
            return
        if not messagebox.askyesno("Confirmar", "Excluir o orçamento selecionado?"):
            return
        try:
            banco.orcamento_excluir(id_)
            self._carregar_salvos()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir: {e}")

    # ---------- Exportar / Enviar (salva automaticamente ANTES) ----------
    def _exportar_excel(self):
        # coleta valores do rascunho
        values_rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not values_rows:
            messagebox.showinfo("Exportação", "Não há itens no rascunho para exportar.")
            return

        # 1) SALVA no banco
        try:
            salvos = self._salvar_orcamento_linhas(values_rows)
            if salvos == 0:
                print("Aviso: nenhuma linha foi salva (verifique os dados).")
        except Exception as e:
            messagebox.showwarning("Salvar orçamento", f"Não foi possível salvar no banco antes de exportar:\n{e}")

        # 2) Monta DF para exportar
        linhas = []
        for v in values_rows:
            linhas.append({
                "Cód AGHU": v[0],
                "Nome": v[1],
                "Qtde": float(str(v[2]).replace(",", ".")),
                "Valor Unitário": float(str(v[3]).replace(",", ".")),
                "Nº Empenho": v[4],
                "Observação": v[5],
                "Valor Total": float(str(v[6]).replace(",", "."))
            })

        arq = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Salvar orçamento"
        )
        if not arq:
            return

        try:
            df = utils.tabela_para_dataframe(linhas, [
                "Cód AGHU","Nome","Qtde","Valor Unitário","Valor Total","Nº Empenho","Observação"
            ])
            utils.exportar_excel({"Orcamento": df}, arq)
            messagebox.showinfo("Exportação", f"Planilha salva em:\n{arq}")
            # limpa rascunho e recarrega salvos
            for i in self.tv.get_children():
                self.tv.delete(i)
            self._carregar_salvos()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar para Excel: {e}")

    def _enviar_email(self):
        forn_id = self._fornecedor_id_atual()
        if not forn_id:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return

        # pega e-mail do fornecedor
        fornecedor = None
        for f in banco.fornecedores_listar():
            if f["id"] == forn_id:
                fornecedor = f
                break
        if not fornecedor:
            messagebox.showwarning("Validação", "Fornecedor não encontrado no cadastro.")
            return
        destinatario = (fornecedor.get("email") or "").strip()
        if not destinatario:
            messagebox.showwarning("Validação", "O fornecedor selecionado não possui e-mail cadastrado.")
            return

        values_rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not values_rows:
            messagebox.showinfo("E-mail", "Não há itens no rascunho para enviar.")
            return

        # 1) SALVA no banco
        try:
            salvos = self._salvar_orcamento_linhas(values_rows)
            if salvos == 0:
                print("Aviso: nenhuma linha foi salva (verifique os dados).")
        except Exception as e:
            messagebox.showwarning("Salvar orçamento", f"Não foi possível salvar no banco antes de enviar:\n{e}")

        # 2) Monta HTML e anexo
        linhas = []
        total_geral = 0.0
        for v in values_rows:
            l = {
                "cod": v[0],
                "nome": v[1],
                "qt": float(str(v[2]).replace(",", ".")),
                "vu": float(str(v[3]).replace(",", ".")),
                "emp": v[4],
                "obs": v[5],
                "vt": float(str(v[6]).replace(",", "."))
            }
            linhas.append(l)
            total_geral += l["vt"]

        msg_user = self.txt_msg.get("1.0", "end").strip()
        html_rows = ""
        for l in linhas:
            html_rows += f"""
                <tr>
                  <td>{l['cod']}</td>
                  <td>{l['nome']}</td>
                  <td style="text-align:right">{l['qt']}</td>
                  <td style="text-align:right">{l['vu']:.2f}</td>
                  <td style="text-align:right">{l['vt']:.2f}</td>
                  <td>{l['emp']}</td>
                  <td>{l['obs']}</td>
                </tr>
            """

        corpo_html = f"""
        <html>
          <body>
            <p>Prezados,</p>
            <p>{msg_user or 'Segue orçamento conforme itens abaixo.'}</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:Segoe UI,Arial,sans-serif;font-size:12px;">
              <thead style="background:#eee;">
                <tr>
                  <th>Cód AGHU</th>
                  <th>Nome</th>
                  <th>Qtde</th>
                  <th>Valor Unitário</th>
                  <th>Valor Total</th>
                  <th>Nº Empenho</th>
                  <th>Observação</th>
                </tr>
              </thead>
              <tbody>
                {html_rows}
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="4" style="text-align:right"><b>Total geral</b></td>
                  <td style="text-align:right"><b>{total_geral:.2f}</b></td>
                  <td colspan="2"></td>
                </tr>
              </tfoot>
            </table>
            <p>Atenciosamente,</p>
          </body>
        </html>
        """

        anexos = []
        try:
            tmp = tempfile.NamedTemporaryFile(prefix="orcamento_", suffix=".xlsx", delete=False)
            tmp.close()
            df = utils.tabela_para_dataframe(
                [
                    {
                        "Cód AGHU": l["cod"],
                        "Nome": l["nome"],
                        "Qtde": l["qt"],
                        "Valor Unitário": l["vu"],
                        "Valor Total": l["vt"],
                        "Nº Empenho": l["emp"],
                        "Observação": l["obs"]
                    } for l in linhas
                ],
                ["Cód AGHU","Nome","Qtde","Valor Unitário","Valor Total","Nº Empenho","Observação"]
            )
            utils.exportar_excel({"Orcamento": df}, tmp.name)
            anexos.append(tmp.name)
        except Exception as e:
            print("Falha ao gerar anexo Excel:", e)

        # 3) Envio com CC (email_alerta)
        try:
            cfg = utils.carregar_config()
            destinatarios = [destinatario]
            if cfg.get("email_alerta"):
                destinatarios.append(cfg["email_alerta"])

            utils.enviar_email(
                destinatarios=destinatarios,
                assunto=f"Orçamento - {self.cb_fornec.get()}",
                corpo_html=corpo_html,
                anexos=anexos
            )
            messagebox.showinfo("E-mail", f"E-mail enviado com sucesso para: {', '.join(destinatarios)}")
            # limpa rascunho e recarrega salvos
            for i in self.tv.get_children():
                self.tv.delete(i)
            self._carregar_salvos()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar e-mail: {e}")
