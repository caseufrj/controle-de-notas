# telas/notas.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import re

import banco


# ===========================
#   Utilidades BR (moeda/data)
# ===========================
def _to_decimal_safe(val) -> Decimal:
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    s = str(val or "").strip()
    s = s.replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def formatar_moeda_br(valor, com_prefixo=True) -> str:
    d = _to_decimal_safe(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inteira, frac = f"{d:.2f}".split(".")
    inteira = f"{int(inteira):,}".replace(",", ".")
    s = f"{inteira},{frac}"
    return f"R$ {s}" if com_prefixo else s


def parse_moeda_br(texto) -> Decimal:
    return _to_decimal_safe(texto)


def mascarar_data_ddmmaa(s: str) -> str:
    d = re.sub(r"\D", "", s)[:8]
    if len(d) > 4:
        return f"{d[:2]}/{d[2:4]}/{d[4:]}"
    elif len(d) > 2:
        return f"{d[:2]}/{d[2:]}"
    return d


def validar_data_ddmmaa(s: str) -> bool:
    s = mascarar_data_ddmmaa(s)
    if len(s) != 10:
        return False
    try:
        datetime.strptime(s, "%d/%m/%Y")
        return True
    except ValueError:
        return False


class MoedaEntry(ttk.Entry):
    """
    Entry de moeda BR com digitação fluida:
      • Enquanto DIGITA: sem "R$ " e sem separadores de milhar (apenas validação leve).
      • Ao SAIR do campo (FocusOut): formata bonito (R$ 1.234,56).
    A posição do cursor é preservada mesmo após a normalização.
    """
    def __init__(self, master=None, prefixo=True, **kw):
        super().__init__(master, **kw)
        self._prefixo = prefixo
        self._sv = tk.StringVar()
        self.configure(textvariable=self._sv)
        self._formatando = False
        self._tem_foco = False

        # eventos
        self._sv.trace_add("write", self._on_write)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    # ---------- helpers ----------
    def _texto_para_digitacao(self, s: str) -> str:
        """
        Modo digitação (sem prefixo, sem milhar). Mantém só dígitos e 1 vírgula.
        Converte ponto para vírgula e permite no máx. 2 casas decimais.
        """
        s = (s or "").strip()
        s = s.replace("R$", "").replace(" ", "")
        s = s.replace(".", ",")
        # mantém apenas dígitos e vírgulas
        s = "".join(ch for ch in s if (ch.isdigit() or ch == ","))
        # deixa apenas uma vírgula (a primeira)
        if s.count(",") > 1:
            partes = s.split(",")
            s = partes[0] + "," + "".join(partes[1:]).replace(",", "")
        # limita 2 decimais
        if "," in s:
            inteira, dec = s.split(",", 1)
            dec = dec[:2]
            s = inteira + "," + dec
        return s

    def _formatar_exibicao(self, s: str) -> str:
        """Formata bonitinho para exibição (com prefixo, milhar, vírgula decimal)."""
        if not s.strip():
            return ""
        dec = parse_moeda_br(s)  # aceita "1234,56"
        return formatar_moeda_br(dec, com_prefixo=self._prefixo)

    # ---------- eventos ----------
    def _on_focus_in(self, *_):
        self._tem_foco = True
        # ao focar, tira o "R$" e milhar para digitar leve
        atual = self._sv.get()
        leve = self._texto_para_digitacao(atual)
        self._sv.set(leve)

    def _on_focus_out(self, *_):
        self._tem_foco = False
        # ao sair, formata bonito
        atual = self._sv.get()
        if not atual.strip():
            return
        self._set_text_preservando_cursor(self._formatar_exibicao(atual), force_end=True)

    def _on_write(self, *_):
        if self._formatando:
            return
        self._formatando = True
        try:
            old = self._sv.get()
            # posição antes da mudança
            try:
                old_pos = self.index("insert")
            except Exception:
                old_pos = len(old)
            dist_right = max(0, len(old) - old_pos)

            # durante digitação: normaliza leve (sem "R$" e sem milhar)
            if self._tem_foco:
                novo = self._texto_para_digitacao(old)
            else:
                # fora do foco (caso programático), já deixa bonito
                novo = self._formatar_exibicao(old) if old.strip() else ""

            self._sv.set(novo)
            try:
                new_len = len(novo)
                new_pos = max(0, new_len - dist_right)
                self.icursor(new_pos)
            except Exception:
                pass
        finally:
            self._formatando = False

    # ---------- util ----------
    def _set_text_preservando_cursor(self, texto: str, force_end: bool = False):
        """Seta texto mantendo a posição lógica do cursor."""
        try:
            old = self._sv.get()
            old_pos = self.index("insert")
            dist_right = max(0, len(old) - old_pos)
        except Exception:
            dist_right = 0

        self._sv.set(texto)
        try:
            if force_end:
                self.icursor("end")
            else:
                new_len = len(texto)
                new_pos = max(0, new_len - dist_right)
                self.icursor(new_pos)
        except Exception:
            pass

    # ---------- API ----------
    def value(self) -> Decimal:
        # aceita tanto o texto leve quanto formatado
        return parse_moeda_br(self._sv.get())

    def set_value(self, val):
        # set programático já em modo bonito
        val_fmt = formatar_moeda_br(val, com_prefixo=self._prefixo)
        self._set_text_preservando_cursor(val_fmt, force_end=True)


class DataEntry(ttk.Entry):
    """
    Entry de data DD/MM/AAAA com digitação estável, sem uso de StringVar.
    Controla KeyPress para inserir/remover dígitos e mapeia o cursor por índice lógico.
    • Digite apenas números; as barras aparecem sozinhas.
    • Backspace/Delete removem dígitos (as barras são virtuais).
    • Setas/Home/End funcionam como esperado.
    • F4 = hoje.
    • Valida no FocusOut.
    """
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._digits = ""     # somente dígitos (máx. 8)
        self._tem_foco = False

        # Eventos principais
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyPress>", self._on_keypress)
        self.bind("<F4>", self._hoje)
        self.bind("<<Paste>>", self._on_paste)  # suporta colar do sistema

        # Inicializa a renderização
        self._render(force_end=True)

    # ---------- Helpers de máscara/cursor ----------
    @staticmethod
    def _only_digits(s: str) -> str:
        import re as _re
        return _re.sub(r"\D", "", s or "")[:8]

    @staticmethod
    def _mask(d: str) -> str:
        d = (d or "")[:8]
        if len(d) > 4:
            return f"{d[:2]}/{d[2:4]}/{d[4:]}"
        elif len(d) > 2:
            return f"{d[:2]}/{d[2:]}"
        return d

    @staticmethod
    def _pos_to_dindex(masked: str, pos: int) -> int:
        """Quantos dígitos existem à esquerda de pos em 'masked'."""
        pos = max(0, min(pos, len(masked)))
        return sum(1 for ch in masked[:pos] if ch.isdigit())

    @staticmethod
    def _dindex_to_pos(masked: str, dindex: int) -> int:
        """Posição em 'masked' para manter 'dindex' dígitos à esquerda do cursor."""
        if dindex <= 0:
            return 0
        count = 0
        for i, ch in enumerate(masked):
            if ch.isdigit():
                count += 1
                if count == dindex:
                    return i + 1
        return len(masked)

    def _render(self, dindex: int = None, force_end: bool = False):
        masked = self._mask(self._digits)
        # Atualiza texto
        self.delete(0, "end")
        self.insert(0, masked)
        # Posiciona cursor
        try:
            if force_end:
                self.icursor("end")
            else:
                if dindex is None:
                    cur = self.index("insert")
                    dindex = self._pos_to_dindex(masked, cur)
                self.icursor(self._dindex_to_pos(masked, dindex))
        except Exception:
            pass

    # ---------- Eventos ----------
    def _on_focus_in(self, *_):
        self._tem_foco = True
        # sincronia caso tenha sido setado programaticamente
        self._digits = self._only_digits(self.get())
        self._render()

    def _on_focus_out(self, *_):
        self._tem_foco = False
        masked = self._mask(self._digits)
        # mantém o texto final
        self.delete(0, "end")
        self.insert(0, masked)
        # valida
        if masked and not self._valid(masked):
            messagebox.showwarning("Data", "Data inválida. Use DD/MM/AAAA.")
            # devolve foco e seleciona para facilitar correção
            self.after(0, lambda: (self.focus_set(), self.selection_range(0, "end")))

    def _on_keypress(self, event):
        # Navegação padrão
        if event.keysym in {"Left", "Right", "Home", "End"}:
            return

        # Ctrl+A/C/X: deixa padrão; Ctrl+V tratado via <<Paste>>
        if (event.state & 0x4) and event.keysym.upper() in {"A", "C", "X"}:
            return

        masked = self.get()
        pos = self.index("insert")
        dindex = self._pos_to_dindex(masked, pos)

        # Backspace/Delete removem DÍGITOS (não barras)
        if event.keysym == "BackSpace":
            if self._has_selection():
                self._delete_selection()
                return "break"
            if dindex > 0:
                self._digits = self._digits[:dindex-1] + self._digits[dindex:]
                self._render(dindex=dindex-1)
            return "break"

        if event.keysym == "Delete":
            if self._has_selection():
                self._delete_selection()
                return "break"
            if dindex < len(self._digits):
                self._digits = self._digits[:dindex] + self._digits[dindex+1:]
                self._render(dindex=dindex)
            return "break"

        # Digitação de dígitos
        if event.char and event.char.isdigit():
            if self._has_selection():
                # substitui seleção por um dígito
                sel_start = self.index("sel.first")
                sel_end = self.index("sel.last")
                dl = self._pos_to_dindex(masked, sel_start)
                dr = self._pos_to_dindex(masked, sel_end)
                new = self._digits[:dl] + event.char + self._digits[dr:]
                self._digits = new[:8]
                self._render(dindex=dl+1)
                return "break"
            if len(self._digits) >= 8:
                return "break"
            self._digits = self._digits[:dindex] + event.char + self._digits[dindex:]
            self._render(dindex=dindex+1)
            return "break"

        # Teclas irrelevantes ou '/' digitada manualmente: ignora
        return "break"

    def _on_paste(self, *_):
        try:
            clip = self.clipboard_get()
        except Exception:
            clip = ""
        if not clip:
            return "break"

        masked = self.get()
        if self._has_selection():
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            dl = self._pos_to_dindex(masked, sel_start)
            dr = self._pos_to_dindex(masked, sel_end)
            ins = self._only_digits(clip)
            restante = max(0, 8 - (len(self._digits) - (dr - dl)))
            ins = ins[:restante]
            self._digits = self._digits[:dl] + ins + self._digits[dr:]
            self._render(dindex=dl + len(ins))
        else:
            pos = self.index("insert")
            dindex = self._pos_to_dindex(masked, pos)
            ins = self._only_digits(clip)
            restante = max(0, 8 - len(self._digits))
            ins = ins[:restante]
            self._digits = self._digits[:dindex] + ins + self._digits[dindex:]
            self._render(dindex=dindex + len(ins))
        return "break"

    # ---------- Utilidades ----------
    def _has_selection(self) -> bool:
        try:
            self.index("sel.first"); self.index("sel.last")
            return True
        except Exception:
            return False

    def _delete_selection(self):
        masked = self.get()
        sel_start = self.index("sel.first")
        sel_end = self.index("sel.last")
        dl = self._pos_to_dindex(masked, sel_start)
        dr = self._pos_to_dindex(masked, sel_end)
        self._digits = self._digits[:dl] + self._digits[dr:]
        self._render(dindex=dl)

    @staticmethod
    def _valid(masked: str) -> bool:
        try:
            if not masked or len(masked) != 10:
                return False
            datetime.strptime(masked, "%d/%m/%Y")
            return True
        except Exception:
            return False

    # ---------- API ----------
    def value(self) -> str:
        """Retorna 'DD/MM/AAAA' (ou string vazia)."""
        return self._mask(self._digits)

    def set_value(self, s: str):
        """Aceita 'DDMMYYYY', 'DD/MM/YYYY' etc.; posiciona cursor ao final."""
        self._digits = self._only_digits(s)
        self._render(force_end=True)



# ===========================
#         TELA DE NOTAS
# ===========================
class TelaNotas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="white")
        banco.criar_tabelas()

        # ---------- Topo / Cabeçalho da Nota ----------
        topo = tk.Frame(self, bg="white")
        topo.pack(fill="x", padx=12, pady=10)

        # Fornecedor
        tk.Label(topo, text="Fornecedor:", bg="white").grid(row=0, column=0, sticky="w")
        self.cb_fornec = ttk.Combobox(topo, state="readonly", width=50)
        self.cb_fornec.grid(row=0, column=1, columnspan=3, padx=6, pady=2, sticky="w")
        self.cb_fornec.bind("<<ComboboxSelected>>", lambda e: (self._recarregar_vinculos(), self._recarregar_notas()))

        # Número + Data + Total
        tk.Label(topo, text="Número+Série*:", bg="white").grid(row=1, column=0, sticky="w")
        self.e_numero = ttk.Entry(topo, width=30)
        self.e_numero.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Data expedição*:", bg="white").grid(row=1, column=2, sticky="w")
        self.e_data = DataEntry(topo, width=12)
        self.e_data.grid(row=1, column=3, sticky="w", padx=6, pady=2)
        self.e_data.set_value(datetime.now().strftime("%d%m%Y"))  # hoje

        tk.Label(topo, text="Valor total*:", bg="white").grid(row=2, column=0, sticky="w")
        self.e_total = MoedaEntry(topo, width=18)
        self.e_total.grid(row=2, column=1, sticky="w", padx=6, pady=2)
        ttk.Button(topo, text="Recalcular pelo(s) item(ns)", command=self._recalcular_nota_total)\
            .grid(row=2, column=2, sticky="w")

        # SEI + Envio + Obs
        tk.Label(topo, text="Código SEI:", bg="white").grid(row=3, column=0, sticky="w")
        self.e_sei = ttk.Entry(topo, width=24)
        self.e_sei.grid(row=3, column=1, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Envio proc.:", bg="white").grid(row=3, column=2, sticky="w")
        self.e_envio = DataEntry(topo, width=12)
        self.e_envio.grid(row=3, column=3, sticky="w", padx=6, pady=2)

        tk.Label(topo, text="Observação:", bg="white").grid(row=4, column=0, sticky="w")
        self.e_obs = ttk.Entry(topo, width=60)
        self.e_obs.grid(row=4, column=1, columnspan=3, sticky="w", padx=6, pady=2)

        # Botões de cabeçalho
        btns_top = tk.Frame(topo, bg="white")
        btns_top.grid(row=0, column=4, rowspan=5, sticky="ne", padx=(10, 0))
        ttk.Button(btns_top, text="Nova Nota", command=self._nova_nota).pack(fill="x", pady=2)
        ttk.Button(btns_top, text="Salvar Nota", command=self._salvar_nota).pack(fill="x", pady=2)
        ttk.Button(btns_top, text="Editar nota selecionada", command=self._editar_nota_sel).pack(fill="x", pady=2)
        ttk.Button(btns_top, text="Excluir nota selecionada", command=self._excluir_nota_sel).pack(fill="x", pady=2)

        # ---------- Área de Itens (edição/pendentes) ----------
        area = ttk.LabelFrame(self, text="Itens da Nota (pendentes para salvar)")
        area.pack(fill="both", expand=True, padx=12, pady=10)

        form_it = tk.Frame(area)
        form_it.pack(fill="x", padx=8, pady=6)

        # Vínculos
        tk.Label(form_it, text="Vínculo ATA:").grid(row=0, column=0, sticky="w")
        self.cb_ata = ttk.Combobox(form_it, state="readonly", width=40)
        self.cb_ata.grid(row=0, column=1, padx=6, pady=2, sticky="w")

        tk.Label(form_it, text="Vínculo Empenho:").grid(row=0, column=2, sticky="w")
        self.cb_emp = ttk.Combobox(form_it, state="readonly", width=40)
        self.cb_emp.grid(row=0, column=3, padx=6, pady=2, sticky="w")

        # Campos do item
        tk.Label(form_it, text="Cód AGHU*:").grid(row=1, column=0, sticky="w")
        self.e_cod_item = ttk.Entry(form_it, width=20)
        self.e_cod_item.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(form_it, text="Data uso:").grid(row=1, column=2, sticky="w")
        self.e_data_uso = DataEntry(form_it, width=12)
        self.e_data_uso.grid(row=1, column=3, sticky="w", padx=6, pady=2)

        tk.Label(form_it, text="Vlr Unit*.:").grid(row=2, column=0, sticky="w")
        self.e_vu_item = MoedaEntry(form_it, width=18)
        self.e_vu_item.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        tk.Label(form_it, text="Qtde*:").grid(row=2, column=2, sticky="w")
        self.e_qt_item = ttk.Entry(form_it, width=10)
        self.e_qt_item.grid(row=2, column=3, sticky="w", padx=6, pady=2)

        tk.Label(form_it, text="Vlr Total:").grid(row=3, column=0, sticky="w")
        self.e_vt_item = ttk.Entry(form_it, width=18, state="readonly")
        self.e_vt_item.grid(row=3, column=1, sticky="w", padx=6, pady=2)

        tk.Label(form_it, text="Qtde consumida:").grid(row=3, column=2, sticky="w")
        self.e_qt_cons = ttk.Entry(form_it, width=10)
        self.e_qt_cons.grid(row=3, column=3, sticky="w", padx=6, pady=2)

        # Recalcula total do item sempre que VU/Qtde mudarem
        self.e_qt_item.bind("<KeyRelease>", lambda e: self._recalcular_total_item())
        self.e_vu_item.bind("<KeyRelease>", lambda e: self._recalcular_total_item())

        # Ações de item
        btns_it = tk.Frame(form_it, bg="white")
        btns_it.grid(row=1, column=4, rowspan=3, sticky="ne", padx=(10, 0))
        self.btn_add_item = ttk.Button(btns_it, text="Adicionar item", command=self._adicionar_item_na_tabela, state="disabled")
        self.btn_add_item.pack(fill="x", pady=2)
        ttk.Button(btns_it, text="Remover selecionado", command=self._remover_item_tabela).pack(fill="x", pady=2)

        # Tabela de itens pendentes (edição)
        cols = ("cod_aghu","data_uso","vl_unit","qtde","vl_total","qtde_consumida","ata_item_id","empenho_id","ata_leg","emp_leg")
        heads = ("Cód AGHU","Data uso","Vlr Unit","Qtde","Vlr Total","Qtde cons.","ID ATA","ID Emp","ATA","Empenho")
        widths = (100,100,100,70,110,100,60,60,180,180)
        self.tv_itens = ttk.Treeview(area, columns=cols, show="headings", height=8)
        for c, h, w in zip(cols, heads, widths):
            self.tv_itens.heading(c, text=h)
            self.tv_itens.column(c, width=w, anchor="w")
        self.tv_itens.pack(fill="both", expand=True, padx=8, pady=6)

        rod_it = tk.Frame(area, bg="white")
        rod_it.pack(fill="x", padx=8, pady=(0, 6))
        self.btn_salvar_itens = ttk.Button(rod_it, text="Salvar itens na nota", command=self._salvar_itens, state="disabled")
        self.btn_salvar_itens.pack(side="right")

        # ---------- Lista de Notas (para editar/excluir) ----------
        lf_list = ttk.LabelFrame(self, text="Notas — por fornecedor")
        lf_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        cols_n = ("id","numero","data_expedicao","vl_total","codigo_sei","observacao")
        heads_n = ("ID","Número","Data","Vlr Total","SEI","Obs")
        widths_n = (60,140,110,120,140,280)
        self.tv_notas = ttk.Treeview(lf_list, columns=cols_n, show="headings", height=8)
        for c, h, w in zip(cols_n, heads_n, widths_n):
            self.tv_notas.heading(c, text=h)
            self.tv_notas.column(c, width=w, anchor="w")
        self.tv_notas.pack(fill="both", expand=True, padx=8, pady=6)

        barra_list = tk.Frame(lf_list, bg="white")
        barra_list.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(barra_list, text="Recarregar", command=self._recarregar_notas).pack(side="left")
        ttk.Button(barra_list, text="Editar selec.", command=self._editar_nota_sel).pack(side="left", padx=6)
        ttk.Button(barra_list, text="Excluir selec.", command=self._excluir_nota_sel).pack(side="left", padx=6)

        # ---------- Estado ----------
        self.nota_id = None
        self.map_fornec = {}
        self.map_ata = {}
        self.map_emp = {}

        # ---------- Inicializações ----------
        self._carregar_fornecedores()
        self._recarregar_notas()

    # ====================================
    #  Carregamentos e helpers de estado
    # ====================================
    def _carregar_fornecedores(self):
        fs = banco.fornecedores_listar()
        self.map_fornec = {f["nome"]: f["id"] for f in fs}
        self.cb_fornec["values"] = list(self.map_fornec.keys())
        if fs and not self.cb_fornec.get():
            self.cb_fornec.current(0)
        self._recarregar_vinculos()

    def _fornecedor_id_atual(self):
        nome = self.cb_fornec.get()
        return self.map_fornec.get(nome) if nome else None

    def _recarregar_vinculos(self):
        fid = self._fornecedor_id_atual()
        if not fid:
            self.cb_ata["values"] = []; self.cb_emp["values"] = []
            return
        # ATA
        atas = banco.ata_itens_listar(fornecedor_id=fid)
        self.map_ata = {f'{a["pregao"]} | {a["cod_aghu"]} | {a["nome_item"]}': a["id"] for a in atas}
        self.cb_ata["values"] = list(self.map_ata.keys())
        # Empenho
        emps = banco.empenhos_listar(fornecedor_id=fid)
        self.map_emp = {f'{(e["numero_empenho"] or "-")} | {e["cod_aghu"]} | {e["nome_item"]}': e["id"] for e in emps}
        self.cb_emp["values"] = list(self.map_emp.keys())

    def _recarregar_notas(self):
        fid = self._fornecedor_id_atual()
        for i in self.tv_notas.get_children():
            self.tv_notas.delete(i)
        if not fid:
            return
        notas = banco.nota_listar(fornecedor_id=fid)
        for n in notas:
            self.tv_notas.insert("", "end", values=(
                n.get("id",""),
                n.get("numero",""),
                self._fmt_data_list(n.get("data_expedicao","")),
                formatar_moeda_br(n.get("vl_total", 0)),
                n.get("codigo_sei","") or "",
                n.get("observacao","") or "",
            ))

    def _fmt_data_list(self, s):
        # aceita 'YYYY-MM-DD' e exibe 'DD/MM/YYYY'
        try:
            if not s:
                return ""
            if "/" in s:  # já vem formatada
                return s
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return s or ""

    # ======================
    #  Cabeçalho da Nota
    # ======================
    def _nova_nota(self):
        self.nota_id = None
        # limpa cabeçalho
        self.e_numero.config(state="normal"); self.e_numero.delete(0, "end")
        self.e_data.config(state="normal"); self.e_data.set_value(datetime.now().strftime("%d%m%Y"))
        self.e_total.config(state="normal"); self.e_total.set_value(0)
        self.e_sei.delete(0, "end")
        self.e_envio.set_value("")
        self.e_obs.delete(0, "end")
        self.cb_fornec.config(state="readonly")
        # limpa itens pendentes
        for i in self.tv_itens.get_children():
            self.tv_itens.delete(i)
        self.btn_add_item.config(state="disabled")
        self.btn_salvar_itens.config(state="disabled")

    def _salvar_nota(self):
        fid = self._fornecedor_id_atual()
        if not fid:
            messagebox.showwarning("Validação","Selecione o fornecedor.")
            return

        numero = (self.e_numero.get() or "").strip()
        data_gui = self.e_data.value().strip()
        if not (numero and data_gui):
            messagebox.showwarning("Validação","Preencha número e data de expedição.")
            return

        # armazena data no padrão do banco (YYYY-MM-DD)
        try:
            dt = datetime.strptime(data_gui, "%d/%m/%Y").date()
            data_bd = dt.strftime("%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Validação","Data de expedição inválida.")
            return

        total_dec = self.e_total.value()
        d = {
            "fornecedor_id": fid,
            "numero": numero,
            "data_expedicao": data_bd,
            "vl_total": float(total_dec),
            "codigo_sei": (self.e_sei.get() or "").strip(),
            "data_envio_processo": (self.e_envio.value() or "").strip(),
            "observacao": (self.e_obs.get() or "").strip()
        }

        try:
            if self.nota_id:
                banco.nota_atualizar(self.nota_id, d)
                messagebox.showinfo("OK", f"Nota (ID {self.nota_id}) atualizada.")
            else:
                self.nota_id = banco.nota_inserir(d)
                messagebox.showinfo("OK", f"Nota criada (ID {self.nota_id}). Agora adicione os itens.")
                # habilita edição de itens
                self.btn_add_item.config(state="normal")
                self.btn_salvar_itens.config(state="normal")
                # congela cabeçalho essencial
                self.cb_fornec.config(state="disabled")
                self.e_numero.config(state="disabled")
                self.e_data.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar nota: {e}")
            return

        self._recarregar_notas()

    # ======================
    #  Itens da Nota
    # ======================
    def _recalcular_total_item(self):
        try:
            qt = Decimal(str((self.e_qt_item.get() or "0").replace(",", ".")))
        except Exception:
            qt = Decimal("0")
        vu = self.e_vu_item.value()
        total = (qt * vu).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.e_vt_item.configure(state="normal")
        self.e_vt_item.delete(0, "end")
        self.e_vt_item.insert(0, formatar_moeda_br(total))
        self.e_vt_item.configure(state="readonly")

    def _remover_item_tabela(self):
        sel = self.tv_itens.selection()
        if not sel:
            return
        for iid in sel:
            self.tv_itens.delete(iid)

    def _adicionar_item_na_tabela(self):
        if not self.nota_id:
            messagebox.showwarning("Atenção","Salve a nota antes de incluir itens.")
            return

        def _to_float(txt):
            try:
                return float(str(txt).replace(".", "").replace(",", "."))
            except Exception:
                return 0.0

        cod = (self.e_cod_item.get() or "").strip()
        if not cod:
            messagebox.showwarning("Validação","Informe o Cód AGHU do item.")
            return

        data_uso = self.e_data_uso.value().strip() or ""
        if data_uso and not validar_data_ddmmaa(data_uso):
            messagebox.showwarning("Validação","Data de uso inválida.")
            return

        vu = float(self.e_vu_item.value())
        try:
            qt = float((self.e_qt_item.get() or "0").replace(",", "."))
        except Exception:
            qt = 0.0
        total = float(_to_float(self.e_vt_item.get()))

        if not (vu and qt):
            messagebox.showwarning("Validação","Preencha Valor unitário e Quantidade.")
            return

        ata_leg = self.cb_ata.get() or ""
        emp_leg = self.cb_emp.get() or ""
        ata_id = self.map_ata.get(ata_leg)
        emp_id = self.map_emp.get(emp_leg)

        self.tv_itens.insert("", "end", values=(
            cod,
            data_uso,              # GUI (DD/MM/AAAA) para o usuário
            f"{vu:.2f}",
            f"{qt}",
            f"{total:.2f}",
            f"{(self.e_qt_cons.get() or '0')}",
            ata_id or "",
            emp_id or "",
            ata_leg,
            emp_leg
        ))

        # limpa campos do item (mantém vínculos)
        self.e_cod_item.delete(0, "end")
        self.e_data_uso.set_value("")
        self.e_vu_item.set_value(0)
        self.e_qt_item.delete(0, "end")
        self.e_vt_item.configure(state="normal"); self.e_vt_item.delete(0, "end"); self.e_vt_item.configure(state="readonly")
        self.e_qt_cons.delete(0, "end")

    def _salvar_itens(self):
        if not self.nota_id:
            return

        itens = []
        for iid in self.tv_itens.get_children():
            v = self.tv_itens.item(iid, "values")
            # v = (cod_aghu, data_uso_gui, vl_unit, qtde, vl_total, qtde_consumida, ata_item_id, empenho_id, ata_leg, emp_leg)

            # --- Conversão da data de uso (GUI -> ISO) ---
            data_uso_gui = (v[1] or "").strip()   # "DD/MM/AAAA" ou ""
            if data_uso_gui:
                try:
                    dt_uso = datetime.strptime(data_uso_gui, "%d/%m/%Y").date()
                    data_uso_bd = dt_uso.strftime("%Y-%m-%d")  # ISO
                except Exception:
                    data_uso_bd = None
            else:
                data_uso_bd = None

            itens.append({
                "cod_aghu": v[0],
                "data_uso": data_uso_bd,  # ISO no banco
                "vl_unit": float(str(v[2]).replace(".", "").replace(",", ".")),
                "qtde": float(str(v[3]).replace(".", "").replace(",", ".")),
                "vl_total": float(str(v[4]).replace(".", "").replace(",", ".")),
                "qtde_consumida": float(str(v[5]).replace(".", "").replace(",", ".")) if v[5] else 0.0,
                "ata_item_id": int(v[6]) if str(v[6]).isdigit() else None,
                "empenho_id": int(v[7]) if str(v[7]).isdigit() else None
            })

        if not itens:
            messagebox.showwarning("Itens", "Nenhum item para salvar.")
            return

        try:
            # Se estiver editando uma nota existente, substitui os itens por estes
            banco.nota_itens_excluir_por_nota(self.nota_id)
            banco.nota_itens_inserir(self.nota_id, itens)
            # Recalcula total no cabeçalho
            total = banco.nota_total_recalcular(self.nota_id)
            self.e_total.set_value(Decimal(str(total)))
            messagebox.showinfo("OK", "Itens salvos na nota e total recalculado.")
            # Limpa pendências
            for i in self.tv_itens.get_children():
                self.tv_itens.delete(i)
            self._recarregar_notas()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar itens: {e}")

    def _recalcular_nota_total(self):
        if not self.nota_id:
            messagebox.showwarning("Nota", "Salve a nota primeiro.")
            return
        try:
            total = banco.nota_total_recalcular(self.nota_id)
            self.e_total.set_value(Decimal(str(total)))
            messagebox.showinfo("OK", f"Total da nota atualizado para {formatar_moeda_br(total)}.")
            self._recarregar_notas()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao recalcular total: {e}")

    # ======================
    #  Editar / Excluir Nota
    # ======================
    def _nota_selecionada_id(self):
        sel = self.tv_notas.selection()
        if not sel:
            return None
        vals = self.tv_notas.item(sel[0], "values")
        try:
            return int(vals[0])
        except Exception:
            return None

    def _editar_nota_sel(self):
        nid = self._nota_selecionada_id()
        if not nid:
            messagebox.showwarning("Editar", "Selecione uma nota na lista.")
            return
        nota = banco.nota_obter(nid)
        if not nota:
            messagebox.showwarning("Editar", "Nota não encontrada.")
            return

        self.nota_id = nid
        # Cabeçalho
        self.cb_fornec.config(state="disabled")  # fornecedor não muda durante edição
        self.e_numero.config(state="normal"); self.e_numero.delete(0,"end"); self.e_numero.insert(0, nota.get("numero",""))
        # data no formato da GUI
        data_gui = self._fmt_data_list(nota.get("data_expedicao",""))
        self.e_data.config(state="normal"); self.e_data.set_value(data_gui)
        self.e_total.set_value(Decimal(str(nota.get("vl_total") or 0)))
        self.e_sei.delete(0, "end"); self.e_sei.insert(0, nota.get("codigo_sei") or "")
        self.e_envio.set_value(self._fmt_data_list(nota.get("data_envio_processo") or "") or "")
        self.e_obs.delete(0, "end"); self.e_obs.insert(0, nota.get("observacao") or "")
        # Ao editar, bloqueia número e data (mudanças fortes); pode liberar se quiser
        self.e_numero.config(state="disabled")
        self.e_data.config(state="disabled")

        # Itens atuais -> carregados na área pendente para edição
        for i in self.tv_itens.get_children():
            self.tv_itens.delete(i)
        itens = banco.nota_itens_listar(nid)
        for it in itens:
            self.tv_itens.insert("", "end", values=(
                it.get("cod_aghu",""),
                self._fmt_data_list(it.get("data_uso","")),
                f'{Decimal(str(it.get("vl_unit",0))).quantize(Decimal("0.01"))}',
                f'{Decimal(str(it.get("qtde",0))).quantize(Decimal("0.00"))}',
                f'{Decimal(str(it.get("vl_total",0))).quantize(Decimal("0.01"))}',
                f'{Decimal(str(it.get("qtde_consumida",0))).quantize(Decimal("0.00"))}',
                it.get("ata_item_id") or "",
                it.get("empenho_id") or "",
                it.get("pregao") or "",
                it.get("numero_empenho") or ""
            ))

        # habilita edição de itens
        self.btn_add_item.config(state="normal")
        self.btn_salvar_itens.config(state="normal")

    def _excluir_nota_sel(self):
        nid = self._nota_selecionada_id()
        if not nid:
            messagebox.showwarning("Excluir", "Selecione uma nota na lista.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir a nota selecionada e TODOS os itens?"):
            return
        try:
            banco.nota_excluir(nid)  # CASCADE remove itens
            if self.nota_id == nid:
                self._nova_nota()
            self._recarregar_notas()
            messagebox.showinfo("Excluir", "Nota e itens excluídos.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir nota: {e}")
