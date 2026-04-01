# telas/tela_inicial.py
import os, sys, socket, traceback
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"

PRIMARY = "#0d3758"
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"

# Para forçar fundo sólido (sem gradiente) em debug/perf:
#   setx SICONAE_NO_GRADIENT 1
NO_GRADIENT = os.environ.get("SICONAE_NO_GRADIENT") == "1"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _center_window(win: tk.Toplevel):
    """Centraliza a janela 'win' no centro do monitor principal."""
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = max(20, (sh // 2) - (h // 2))
    win.geometry(f"+{x}+{y}")


# -----------------------------------------------------------------------------
# Caminho de recursos (funciona no .py e no .exe do PyInstaller)
# -----------------------------------------------------------------------------
def _resource_path(rel_path: str) -> str:
    """
    Resolve caminho de recurso tanto em execução normal quanto empacotado (PyInstaller).
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        # arquivo atual está em .../telas/tela_inicial.py → subir 1 nível
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, rel_path)


CAMINHO_LOGO = _resource_path(os.path.join("assets", "logo.png"))


# -----------------------------------------------------------------------------
# Visual helpers
# -----------------------------------------------------------------------------
def _hex_to_rgb(hx: str):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def desenhar_gradiente(canvas: tk.Canvas, w: int, h: int,
                       top: str, mid: str, bottom: str, steps: int = 80) -> None:
    """
    Gradiente vertical leve (até 'steps' faixas), com tag 'grad'.
    Não desenha 1 linha por pixel para não estourar GDI/Tk.
    """
    if w <= 0 or h <= 0 or steps <= 0:
        return

    t = _hex_to_rgb(top)
    m = _hex_to_rgb(mid)
    b = _hex_to_rgb(bottom)

    half = max(1, steps // 2)
    band_h = max(1, h // steps)

    def interp(c1, c2, r):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * r) for i in range(3))

    y = 0
    # top -> mid
    for i in range(half):
        r = i / max(1, half - 1)
        rgb = interp(t, m, r)
        color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        canvas.create_rectangle(0, y, w, min(h, y + band_h),
                                outline="", fill=color, tags=("grad",))
        y += band_h

    # mid -> bottom
    remain = steps - half
    for j in range(remain):
        r = j / max(1, remain - 1)
        rgb = interp(m, b, r)
        color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        canvas.create_rectangle(0, y, w, min(h, y + band_h),
                                outline="", fill=color, tags=("grad",))
        y += band_h


def estilizar(root: tk.Tk):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure("Primary.TButton", font=("Segoe UI Semibold", 20),
                 background=PRIMARY, foreground=PRIMARY_TEXT,
                 padding=(32, 12), borderwidth=0, relief="flat")
    st.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])
    st.configure("Outline.TButton", font=("Segoe UI Semibold", 12),
                 background="white", foreground=OUTLINE_TEXT,
                 padding=(22, 8), borderwidth=2, relief="solid")
    st.map("Outline.TButton", background=[("active", "#f2f7ff")])


# -----------------------------------------------------------------------------
# Montagem/Desmontagem da Tela Inicial
# -----------------------------------------------------------------------------
LAYOUT_ALTURA = 900  # 🔥 altura fixa da sua tela base

def montar_tela_inicial(root: tk.Tk):
    print("[DEBUG] tela_inicial: montar_tela_inicial()")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.configure(bg="#ffffff")

    estilizar(root)

    # =========================================================
    # CANVAS SCROLL PRINCIPAL
    # =========================================================
    canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)

    root._tela_inicial_widgets = [canvas]

    # Frame com ALTURA FIXA (ESSA É A CHAVE)
    frame = tk.Frame(canvas, height=LAYOUT_ALTURA, bg="")
    window_id = canvas.create_window((0, 0), window=frame, anchor="nw")

    # =========================================================
    # SCROLL INVISÍVEL
    # =========================================================
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    def update_scroll(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(window_id, width=canvas.winfo_width())

    frame.bind("<Configure>", update_scroll)

    # =========================================================
    # CANVAS INTERNO (SEU LAYOUT)
    # =========================================================
    layout = tk.Canvas(frame, height=LAYOUT_ALTURA, highlightthickness=0, bd=0)
    layout.pack(fill="both", expand=True)

    # =========================================================
    # LOGO
    # =========================================================
    root._logo_img = None
    if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
        try:
            img = tk.PhotoImage(file=CAMINHO_LOGO)
            if img.width() > 250:
                fator = img.width() // 250
                img = img.subsample(fator, fator)
            root._logo_img = img
        except:
            pass

    # =========================================================
    # BOTÕES
    # =========================================================
    btn_login = ttk.Button(root, text="LOGIN", style="Primary.TButton",
                           command=lambda: abrir_modal_login(root))

    btn_reg = ttk.Button(root, text="REGISTRO / CADASTRO",
                         style="Outline.TButton",
                         command=lambda: abrir_modal_registro(root))

    login_win = layout.create_window(0, 0, window=btn_login, anchor="center")
    reg_win   = layout.create_window(0, 0, window=btn_reg,   anchor="center")

    # =========================================================
    # RENDER (AGORA FIXO)
    # =========================================================
    def render():
        layout.delete("grad")
        layout.delete("ui")

        w = layout.winfo_width()
        h = LAYOUT_ALTURA  # 🔥 FIXO (ESSENCIAL)

        cx = w // 2

        # posições FIXAS (como você queria)
        y_titulo = 70
        y_sub    = 108
        y_logo   = 320

        # fundo
        if not NO_GRADIENT:
            desenhar_gradiente(layout, w, h, BG_TOP, BG_MID, BG_BOTTOM)
        else:
            layout.create_rectangle(0, 0, w, h, fill=BG_MID, outline="")

        # textos
        layout.create_text(cx, y_titulo, text=TITULO,
                           font=("Segoe UI Semibold", 20),
                           fill="#113a5e", tags="ui")

        layout.create_text(cx, y_sub, text=APP_NAME,
                           font=("Segoe UI", 12),
                           fill="#1f4c77", tags="ui")

        # logo
        if root._logo_img:
            layout.create_image(cx, y_logo, image=root._logo_img, tags="ui")
        else:
            layout.create_oval(cx-34, y_logo-34,
                               cx+34, y_logo+34,
                               outline="#0d3758", width=3, tags="ui")

        # botões (posição FIXA)
        layout.coords(login_win, cx, y_logo + 240)
        layout.coords(reg_win, cx, y_logo + 300)

        # rodapé FIXO no layout
        layout.create_rectangle(0, h - 48, w, h,
                                fill="#0b2f4a", width=0, tags="ui")

    layout.bind("<Configure>", lambda e: render())

    root._tela_inicial_widgets.extend([frame, layout])
"""
    def schedule_render(evt=None):
        if root._render_after:
            try:
                root.after_cancel(root._render_after)
            except:
                pass
        root._render_after = root.after(40, render)

    schedule_render()
    root._cfg_bind_id = canvas.bind("<Configure>", schedule_render)
    """
# -----------------------------------------------------------------------------
# Modais
# -----------------------------------------------------------------------------
def abrir_modal_login(root: tk.Tk):
    # --- Modal ---
    win = tk.Toplevel(root)
    win.title("Login - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)

    # --- Animação leve ---
    try:
        win.attributes("-alpha", 0.0)
        for i in range(1, 11):
            win.attributes("-alpha", i/10)
            win.update()
            win.after(12)
    except:
        pass

    frm = ttk.Frame(win, padding=20)
    frm.grid(row=0, column=0)

    # ---------------- EMAIL ----------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")

    email_box = tk.Frame(frm, bg="white")
    email_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))

    ent_email = ttk.Entry(email_box, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    # domínio fantasma
    lbl_dom = tk.Label(email_box, text="@ebserh.gov.br",
                       fg="#888", bg="white", font=("Segoe UI", 10))
    lbl_dom.place(x=0, y=0)

    # indicador visual 🟢 / ⭕
    lbl_ok = tk.Label(email_box, text="⭕", bg="white", fg="red", font=("Segoe UI", 11))
    lbl_ok.pack(side="right", padx=5)

    def atualizar_dom(e=None):
        txt = ent_email.get().strip()
        lbl_dom.place_configure(x=max(0, len(txt) * 7))
        if txt and "@" not in txt:
            lbl_ok.config(text="🟢", fg="green")
        elif txt.endswith("@ebserh.gov.br"):
            lbl_ok.config(text="🟢", fg="green")
        else:
            lbl_ok.config(text="⭕", fg="red")

    ent_email.bind("<KeyRelease>", atualizar_dom)

    # ---------------- SENHA + 👁 ----------------
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    pass_box = tk.Frame(frm)
    pass_box.grid(row=3, column=0, sticky="ew", pady=(0, 10))

    ent_senha = ttk.Entry(pass_box, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    ver_senha = tk.BooleanVar(value=False)

    def toggle_senha():
        ent_senha.config(show="" if ver_senha.get() else "•")

    ttk.Checkbutton(pass_box, text="👁", variable=ver_senha,
                    command=toggle_senha).pack(side="left", padx=6)

    # ---------------- SALVAR SENHA ----------------
    var_salvar = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm, text="Salvar senha", variable=var_salvar)\
        .grid(row=4, column=0, sticky="w", pady=(0, 10))

    # ---------------- BOTÃO LOGIN ----------------
    def do_login(event=None):
        raw = ent_email.get().strip()
        email = raw + "@ebserh.gov.br" if "@" not in raw else raw
        senha = ent_senha.get().strip()

        try:
            from auth import usuario_login
            ua = f"SICONAE-Desktop/{os.name}"
            ip = socket.gethostbyname(socket.gethostname())
            auth = usuario_login(email, senha, ua, ip)

            if var_salvar.get():
                try:
                    import utils
                    utils.salvar_config({"login_email": email, "login_senha": senha})
                except:
                    pass

            win.destroy()
            montar_sistema(root, auth)

        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login)\
        .grid(row=5, column=0, sticky="ew", pady=(0, 6))

    # ---------------- ESQUECI SENHA ----------------
    def esqueci():
        messagebox.showinfo(
            "Recuperar senha",
            "Para recuperar sua senha:\n"
            "- Acesse: https://webmail.ebserh.gov.br\n"
            "- Clique em 'Esqueci minha senha'\n"
            "- Ou abra um chamado na TI."
        )

    ttk.Button(frm, text="Esqueci minha senha", style="Outline.TButton",
               command=esqueci).grid(row=6, column=0, sticky="ew")

    ent_email.focus_set()
    win.bind("<Return>", do_login)
    _center_window(win)


def abrir_modal_registro(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Registro / Cadastro - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)

    # animação
    try:
        win.attributes("-alpha", 0.0)
        for i in range(1, 11):
            win.attributes("-alpha", i/10)
            win.update()
            win.after(12)
    except:
        pass

    frm = ttk.Frame(win, padding=20)
    frm.grid(row=0, column=0)

    # ---------------- NOME ----------------
    ttk.Label(frm, text="Nome completo", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40)
    ent_nome.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    # ---------------- EMAIL + placeholder ----------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    email_box = tk.Frame(frm, bg="white")
    email_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    ent_email = ttk.Entry(email_box, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    lbl_dom = tk.Label(email_box, text="@ebserh.gov.br",
                       fg="#888", bg="white", font=("Segoe UI", 10))
    lbl_dom.place(x=0, y=0)

    lbl_ok = tk.Label(email_box, text="⭕", bg="white", fg="red")
    lbl_ok.pack(side="right", padx=5)

    def atualizar_dom(e=None):
        txt = ent_email.get().strip()
        lbl_dom.place_configure(x=max(0, len(txt)*7))
        if txt and "@" not in txt:
            lbl_ok.config(text="🟢")
        elif txt.endswith("@ebserh.gov.br"):
            lbl_ok.config(text="🟢")
        else:
            lbl_ok.config(text="⭕")

    ent_email.bind("<KeyRelease>", atualizar_dom)

    # ---------------- SENHA + 👁 + força ----------------
    ttk.Label(frm, text="Senha (mín. 8 caracteres)", font=("Segoe UI", 10))\
       .grid(row=4, column=0, sticky="w")

    pass_box = tk.Frame(frm)
    pass_box.grid(row=5, column=0, sticky="ew")

    ent_senha = ttk.Entry(pass_box, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    ver_senha = tk.BooleanVar(value=False)
    def toggle():
        ent_senha.config(show="" if ver_senha.get() else "•")
    ttk.Checkbutton(pass_box, text="👁", variable=ver_senha,
                    command=toggle).pack(side="left", padx=6)

    # barra de força
    força = tk.Canvas(frm, width=280, height=6, bg="#eee")
    força.grid(row=6, column=0, pady=(5, 12))

    def medir_forca(e=None):
        s = ent_senha.get()
        força.delete("all")

        lvl = 0
        if len(s) >= 8: lvl += 1
        if any(c.isdigit() for c in s): lvl += 1
        if any(c.isupper() for c in s): lvl += 1
        if any(c in "@#$!&*" for c in s): lvl += 1

        cor = "#ff3b30"
        if lvl == 2: cor = "#ffcc00"
        if lvl >= 3: cor = "#4cd964"

        força.create_rectangle(0, 0, lvl * 70, 6, fill=cor, width=0)

    ent_senha.bind("<KeyRelease>", medir_forca)

    # ---------------- CONFIRMAR SENHA ----------------
    ttk.Label(frm, text="Confirmar senha", font=("Segoe UI", 10)).grid(row=7, column=0, sticky="w")

    conf_box = tk.Frame(frm)
    conf_box.grid(row=8, column=0, sticky="ew")

    ent_conf = ttk.Entry(conf_box, width=34, show="•")
    ent_conf.pack(side="left", fill="x", expand=True)

    ver_conf = tk.BooleanVar(value=False)
    def toggle_conf():
        ent_conf.config(show="" if ver_conf.get() else "•")
    ttk.Checkbutton(conf_box, text="👁", variable=ver_conf,
                    command=toggle_conf).pack(side="left", padx=6)

    # ---------------- BOTÃO REGISTRAR ----------------
    def do_registrar(event=None):
        nome = ent_nome.get().strip()
        raw = ent_email.get().strip()
        email = raw + "@ebserh.gov.br" if "@" not in raw else raw
        s1 = ent_senha.get().strip()
        s2 = ent_conf.get().strip()

        if not nome:
            messagebox.showerror("Erro", "Informe seu nome.")
            return

        if s1 != s2:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        if len(s1) < 8:
            messagebox.showerror("Erro", "A senha deve ter pelo menos 8 caracteres.")
            return

        try:
            from auth import usuario_registrar
            usuario_registrar(email, s1, nome)
            messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    ttk.Button(frm, text="Registrar", style="Primary.TButton",
               command=do_registrar).grid(row=9, column=0, sticky="ew")

    win.bind("<Return>", do_registrar)
    ent_nome.focus_set()
    _center_window(win)


# -----------------------------------------------------------------------------
# Montar sistema no root (troca de cena)
# -----------------------------------------------------------------------------
def montar_sistema(root: tk.Tk, auth: Dict[str, Any]):
    """
    Desmonta a tela inicial e monta o sistema na mesma janela.
    Se algo der errado, reconstrói a tela inicial e mostra o erro.
    """
    print("[DEBUG] tela_inicial: montar_sistema() chamado")

    # Desmonta a cena da tela inicial
    desmontar_tela_inicial(root)

    # Se já houver um sistema montado, desmonta
    atual = getattr(root, "_sistema", None)
    if atual:
        try:
            atual.desmontar()
        except Exception:
            pass
        root._sistema = None

    def on_sair(_root: tk.Tk):
        try:
            if hasattr(_root, "_sistema") and _root._sistema:
                _root._sistema = None
        except Exception:
            pass
        montar_tela_inicial(_root)

    try:
        from telas.sistema import SistemaApp
        print("[DEBUG] tela_inicial: import telas.sistema.SistemaApp OK")
        root._sistema = SistemaApp(root, auth, on_sair=on_sair)
        print("[DEBUG] tela_inicial: SistemaApp montado OK")
    except Exception as e:
        print("[DEBUG] tela_inicial: SistemaApp FALHOU:", e)
        log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write("Falha ao montar o SistemaApp:\n")
            f.write(traceback.format_exc())
        messagebox.showerror("Erro ao abrir o sistema", f"{e}\n\nLog: {log_path}")
        montar_tela_inicial(root)
