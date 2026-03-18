# telas/orcamento.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import banco
import utils  # <--- adicionar
import tempfile  # usamos para gerar o anexo Excel


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
        
        self.btn_salvar = ttk.Button(rod, text="Salvar orçamento", command=self._salvar_orcamento)
        self.btn_salvar.pack(side="left")
        
        self.btn_email = ttk.Button(rod, text="Enviar por e-mail", command=self._enviar_email)
        self.btn_email.pack(side="right", padx=6)
        
        self.btn_export = ttk.Button(rod, text="Exportar para Excel", command=self._exportar_excel)
        self.btn_export.pack(side="right", padx=6)

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
    def _salvar_orcamento_linhas(self, linhas: list[int] | list[dict]) -> int:
        """
        Salva no banco cada linha do orçamento que está na Treeview.
        Retorna a quantidade de registros inseridos.
        """
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            raise RuntimeError("Selecione o fornecedor.")
    
        # resolve fornecedor_id
        fornecedor_id = None
        for f in banco.fornecedores_listar():
            if f["nome"] == forn_nome:
                fornecedor_id = f["id"]
                break
        if not fornecedor_id:
            raise RuntimeError("Fornecedor não encontrado no cadastro.")
    
        mensagem = self.txt_msg.get("1.0", "end").strip()
    
        salvos = 0
        for l in linhas:
            # l vem do self.tv.item(...,"values")
            # ordem: ("cod","nome","qt","vu","emp","obs","vl_total")
            try:
                banco.orcamento_inserir({
                    "fornecedor_id": fornecedor_id,
                    "cod_aghu": l[0],
                    "nome_item": l[1],
                    "qtde": float(str(l[2]).replace(",", ".")),
                    "vl_unit": float(str(l[3]).replace(",", ".")),
                    "numero_empenho": l[4],
                    "observacao": l[5],
                    "mensagem_email": mensagem
                })
                salvos += 1
            except Exception:
                # se uma linha falhar, segue nas demais (mas reporta depois)
                continue
        return salvos
        
    def _exportar_excel(self):
        # Coleta linhas da tabela
        valores = []
        for iid in self.tv.get_children():
            valores.append(self.tv.item(iid, "values"))
    
        if not valores:
            messagebox.showinfo("Exportação", "Não há itens na tabela para exportar.")
            return
    
        # 1) SALVAR no banco ANTES de exportar
        try:
            salvos = self._salvar_orcamento_linhas(valores)
            if salvos == 0:
                # não impede exportar, só informa
                print("Aviso: nenhuma linha foi salva (verifique os dados).")
        except Exception as e:
            # não bloqueia exportação, mas informa
            messagebox.showwarning("Salvar orçamento", f"Não foi possível salvar no banco antes de exportar:\n{e}")
    
        # 2) Montar DataFrame e exportar
        linhas_df = []
        for v in valores:
            linhas_df.append({
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
            df = utils.tabela_para_dataframe(linhas_df, [
                "Cód AGHU","Nome","Qtde","Valor Unitário","Valor Total","Nº Empenho","Observação"
            ])
            utils.exportar_excel({"Orcamento": df}, arq)
            messagebox.showinfo("Exportação", f"Planilha salva em:\n{arq}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar para Excel: {e}")
            

    def _enviar_email(self):
        forn_nome = self.cb_fornec.get()
        if not forn_nome:
            messagebox.showwarning("Validação", "Selecione o fornecedor.")
            return
    
        # Buscar fornecedor para pegar e-mail
        fornecedor = None
        for f in banco.fornecedores_listar():
            if f["nome"] == forn_nome:
                fornecedor = f
                break
        if not fornecedor:
            messagebox.showwarning("Validação", "Fornecedor não encontrado no cadastro.")
            return
    
        destinatario = (fornecedor.get("email") or "").strip()
        if not destinatario:
            messagebox.showwarning("Validação", "O fornecedor selecionado não possui e-mail cadastrado.")
            return
    
        # Coleta linhas da tabela
        valores = []
        for iid in self.tv.get_children():
            valores.append(self.tv.item(iid, "values"))
        if not valores:
            messagebox.showinfo("E-mail", "Não há itens na tabela para enviar.")
            return
    
        # 1) SALVAR no banco ANTES de enviar
        try:
            salvos = self._salvar_orcamento_linhas(valores)
            if salvos == 0:
                print("Aviso: nenhuma linha foi salva (verifique os dados).")
        except Exception as e:
            messagebox.showwarning("Salvar orçamento", f"Não foi possível salvar no banco antes de enviar:\n{e}")
    
        # 2) Montar corpo HTML e anexo
        linhas = []
        total_geral = 0.0
        for v in valores:
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
    
        # 3) Enviar (com CC opcional)
        try:
            cfg = utils.carregar_config()
            destinatarios = [destinatario]
            if cfg.get("email_alerta"):
                destinatarios.append(cfg["email_alerta"])
    
            utils.enviar_email(
                destinatarios=destinatarios,
                assunto=f"Orçamento - {forn_nome}",
                corpo_html=corpo_html,
                anexos=anexos
            )
            messagebox.showinfo("E-mail", f"E-mail enviado com sucesso para: {', '.join(destinatarios)}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar e-mail: {e}")
