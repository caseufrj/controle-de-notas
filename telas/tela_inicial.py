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
def desmontar_tela_inicial(root: tk.Tk):
    # cancela render pendente (debounce)
    if hasattr(root, "_render_after") and root._render_after:
        try:
            root.after_cancel(root._render_after)
        except Exception:
            pass
        root._render_after = None

    # destrói widgets gerenciados por nós
    if hasattr(root, "_tela_inicial_widgets"):
        for w in root._tela_inicial_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        root._tela_inicial_widgets = []

    # limpa ids de janela do Canvas (se houver)
    for attr in ("_login_win", "_reg_win"):
        if hasattr(root, attr):
            setattr(root, attr, None)

    # remove o bind do <Configure> (evita chamadas tardias ao render)
    try:
        if getattr(root, "_cfg_bind_id", None) is not None:
            root.unbind("<Configure>", root._cfg_bind_id)
            root._cfg_bind_id = None
        else:
            root.unbind("<Configure>")
    except Exception:
        pass

def montar_tela_inicial(root: tk.Tk):
    print("[DEBUG] tela_inicial: montar_tela_inicial()")
    root.protocol("WM_DELETE_WINDOW", root.destroy)

    # FIX para o erro: "unknown color name ''"
    root.configure(bg="#ffffff")   # <<< ESTA LINHA RESOLVE TUDO

    # inicializa banco
    try:
        try:
            from banco import criar_tabelas as _criar_tabelas
        except ImportError:
            from bd import criar_tabelas as _criar_tabelas
        _criar_tabelas()
    except Exception:
        pass

    # inicializa auth
    try:
        from auth import auth_init
        auth_init()
    except Exception:
        pass

    estilizar(root)

    # ================================
    # 1) CANVAS FIXO DO FUNDO (GRADIENTE)
    # ================================
    canvas_bg = tk.Canvas(root, highlightthickness=0, bd=0)
    canvas_bg.pack(fill="both", expand=True)

    root._tela_inicial_widgets = [canvas_bg]
    root._render_after = None

    # carregar logo
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

    # ================================
    # 2) FRAME ROLÁVEL SOBRE O FUNDO
    # ================================
    scroll_canvas = tk.Canvas(
        root,
        highlightthickness=0,
        bd=0,
        relief="flat",
        background="",  # usa fundo transparente herdado
    )
    scroll_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

    scroll_frame = tk.Frame(scroll_canvas, bg="", padx=0, pady=0)
    win_id = scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="n")

    # rolagem do mouse
    def on_mousewheel(evt):
        scroll_canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")

    scroll_canvas.bind_all("<MouseWheel>", on_mousewheel)

    # atualizar scrollregion
    def on_configure(evt):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        scroll_canvas.itemconfig(win_id, width=scroll_canvas.winfo_width())

    scroll_frame.bind("<Configure>", on_configure)

    # ================================
    # 3) BOTÕES (ÁREA ROLÁVEL)
    # ================================
    def on_click_login():
        abrir_modal_login(root)

    def on_click_registro():
        abrir_modal_registro(root)

    # espaço para alinhar abaixo da logo
    tk.Frame(scroll_frame, height=460, bg="").pack()

    ttk.Button(scroll_frame, text="LOGIN", style="Primary.TButton",
               command=on_click_login).pack(pady=(10, 8))

    ttk.Button(scroll_frame, text="REGISTRO / CADASTRO", style="Outline.TButton",
               command=on_click_registro).pack(pady=(4, 40))

    root._tela_inicial_widgets.extend([scroll_canvas, scroll_frame])

    # ================================
    # 4) FUNDO FIXO (LOGO, TÍTULO, GRADIENTE)
    # ================================
    def render_bg():
        if not canvas_bg.winfo_exists():
            return

        try:
            canvas_bg.delete("grad")
            canvas_bg.delete("ui")
        except:
            pass

        w = canvas_bg.winfo_width()
        h = canvas_bg.winfo_height()
        if w <= 0 or h <= 0:
            return

        # gradiente
        if not NO_GRADIENT:
            desenhar_gradiente(canvas_bg, w, h, BG_TOP, BG_MID, BG_BOTTOM)
        else:
            canvas_bg.create_rectangle(0, 0, w, h, fill=BG_MID, outline="", tags="grad")

        cx = w // 2

        # texto fixo
        canvas_bg.create_text(cx, 70, text=TITULO,
                              font=("Segoe UI Semibold", 20),
                              fill="#113a5e", tags="ui")
        canvas_bg.create_text(cx, 108, text=APP_NAME,
                              font=("Segoe UI", 12),
                              fill="#1f4c77", tags="ui")

        # logo fixa
        y_logo = 320
        if root._logo_img:
            canvas_bg.create_image(cx, y_logo, image=root._logo_img, tags="ui")
        else:
            canvas_bg.create_oval(cx - 34, y_logo - 34,
                                  cx + 34, y_logo + 34,
                                  outline="#0d3758", width=3, tags="ui")

        # barra inferior
        canvas_bg.create_rectangle(0, h - 48, w, h,
                                   fill="#0b2f4a", width=0, tags="ui")

    # debounce
    def debounce(evt=None):
        if root._render_after:
            try: root.after_cancel(root._render_after)
            except: pass
        root._render_after = root.after(60, render_bg)

    canvas_bg.bind("<Configure>", debounce)
    root.after(100, render_bg)


# -----------------------------------------------------------------------------
# Modais
# -----------------------------------------------------------------------------
def abrir_modal_login(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Login - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)

    # animação leve (fade-in)
    try:
        win.attributes("-alpha", 0.0)
        for i in range(1, 11):
            win.attributes("-alpha", i/10)
            win.update()
            win.after(10)
    except:
        pass

    frm = ttk.Frame(win, padding=20)
    frm.grid(row=0, column=0)

    # ----------------------- E-MAIL -----------------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")

    email_frame = tk.Frame(frm)
    email_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    ent_email = ttk.Entry(email_frame, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    # domínio fantasma (placeholder inteligente)
    lbl_dom = tk.Label(email_frame, text="@ebserh.gov.br",
                        fg="#777", bg="white", font=("Segoe UI", 10))
    lbl_dom.place(x=0, y=0)

    valid_icon = tk.Label(email_frame, text="⭕", fg="red", bg="white")
    valid_icon.pack(side="right", padx=4)

    def atualizar_dom(e=None):
        txt = ent_email.get().strip()
        lbl_dom.place_configure(x=max(0, len(txt)*7))  # desloca o domínio
        # validação visual
        if txt and "@" not in txt:
            valid_icon.config(text="🟢")
        elif txt.endswith("@ebserh.gov.br"):
            valid_icon.config(text="🟢")
        else:
            valid_icon.config(text="⭕")

    ent_email.bind("<KeyRelease>", atualizar_dom)

    # ----------------------- SENHA -----------------------
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    senha_frame = tk.Frame(frm)
    senha_frame.grid(row=3, column=0, sticky="ew")

    ent_senha = ttk.Entry(senha_frame, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    var_ver_senha = tk.BooleanVar(value=False)

    def toggle_senha():
        ent_senha.config(show="" if var_ver_senha.get() else "•")

    ttk.Checkbutton(senha_frame, text="👁", width=3,
                    variable=var_ver_senha, command=toggle_senha)\
        .pack(side="left", padx=4)

    # força da senha
    barra = tk.Canvas(frm, height=6, width=280, bg="#ddd")
    barra.grid(row=4, column=0, pady=(6, 15))

    def avaliar_forca(e=None):
        s = ent_senha.get()
        barra.delete("all")

        if len(s) < 1:
            return
        
        força = 0
        if len(s) >= 8: força += 1
        if any(c.isdigit() for c in s): força += 1
        if any(c.isupper() for c in s): força += 1
        if any(c in "@#$!&*" for c in s): força += 1

        cor = "#ff3b30"   # fraca
        if força == 2: cor = "#ffcc00"
        if força >= 3: cor = "#4cd964"

        barra.create_rectangle(0, 0, força * 70, 6, fill=cor, width=0)

    ent_senha.bind("<KeyRelease>", avaliar_forca)

    # ----------------------- SALVAR SENHA -----------------------
    var_salvar = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm, text="Salvar senha", variable=var_salvar)\
        .grid(row=5, column=0, sticky="w", pady=(0, 12))

    # ----------------------- BOTÃO LOGIN -----------------------
    def do_login(event=None):
        email_raw = ent_email.get().strip()
        email_final = email_raw + "@ebserh.gov.br" if "@" not in email_raw else email_raw
        senha = ent_senha.get().strip()

        try:
            from auth import usuario_login
            ua = f"SICONAE-Desktop/{os.name}"
            ip = socket.gethostbyname(socket.gethostname())
            auth = usuario_login(email_final, senha, ua, ip)

            if var_salvar.get():
                import utils
                utils.salvar_config({"login_email": email_final, "login_senha": senha})

            win.destroy()
            montar_sistema(root, auth)

        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login)\
        .grid(row=6, column=0, sticky="ew", pady=(0, 6))

    # ----------------------- ESQUECI SENHA -----------------------
    def esqueci():
        messagebox.showinfo(
            "Recuperar senha",
            "Para recuperar sua senha:\n"
            "- Acesse: https://webmail.ebserh.gov.br\n"
            "- Clique em 'Esqueci minha senha'\n"
            "- Ou abra um chamado na TI."
        )

    ttk.Button(frm, text="Esqueci minha senha", style="Outline.TButton",
               command=esqueci)\
        .grid(row=7, column=0, sticky="ew")

    # apertar Enter
    win.bind("<Return>", do_login)
    ent_email.focus_set()
    _center_window(win)


def abrir_modal_registro(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Registro / Cadastro - SICONAE")
    win.transient(root)
    win.grab_set()
    win.resizable(False, False)

    # animação leve (fade-in)
    try:
        win.attributes("-alpha", 0.0)
        for i in range(1, 11):
            win.attributes("-alpha", i/10)
            win.update()
            win.after(10)
    except:
        pass

    frm = ttk.Frame(win, padding=20)
    frm.grid(row=0, column=0, sticky="nsew")

    # ----------------------- NOME -----------------------
    ttk.Label(frm, text="Nome completo", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40)
    ent_nome.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    # ----------------------- E-MAIL -----------------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    email_frame = tk.Frame(frm, bg="white")
    email_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    ent_email = ttk.Entry(email_frame, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    lbl_dom = tk.Label(email_frame, text="@ebserh.gov.br",
                       fg="#777", bg="white", font=("Segoe UI", 10))
    lbl_dom.place(x=0, y=0)

    valid_icon = tk.Label(email_frame, text="⭕", fg="red", bg="white")
    valid_icon.pack(side="right", padx=4)

    def atualizar_dom_email(e=None):
        txt = ent_email.get().strip()
        lbl_dom.place_configure(x=max(0, len(txt) * 7))
        if txt and "@" not in txt:
            valid_icon.config(text="🟢")
        elif txt.endswith("@ebserh.gov.br"):
            valid_icon.config(text="🟢")
        else:
            valid_icon.config(text="⭕")

    ent_email.bind("<KeyRelease>", atualizar_dom_email)

    # ----------------------- SENHA -----------------------
    ttk.Label(frm, text="Senha (mín. 8 caracteres)", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w")

    senha_frame = tk.Frame(frm)
    senha_frame.grid(row=5, column=0, sticky="ew", pady=(0, 4))

    ent_senha = ttk.Entry(senha_frame, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    var_ver_senha = tk.BooleanVar(value=False)
    def toggle_senha():
        ent_senha.config(show="" if var_ver_senha.get() else "•")

    ttk.Checkbutton(senha_frame, text="👁", width=3,
                    variable=var_ver_senha, command=toggle_senha).pack(side="left", padx=4)

    # barra de força da senha
    barra = tk.Canvas(frm, height=6, width=280, bg="#ddd")
    barra.grid(row=6, column=0, pady=(4, 10))

    def avaliar_forca(e=None):
        s = ent_senha.get()
        barra.delete("all")

        if not s:
            return
        força = 0
        if len(s) >= 8: força += 1
        if any(c.isdigit() for c in s): força += 1
        if any(c.isupper() for c in s): força += 1
        if any(c in "@#$!&*" for c in s): força += 1

        cor = "#ff3b30" # fraca
        if força == 2: cor = "#ffcc00"
        if força >= 3: cor = "#4cd964"

        barra.create_rectangle(0, 0, força * 70, 6, fill=cor, width=0)

    ent_senha.bind("<KeyRelease>", avaliar_forca)

    # ----------------------- CONFIRMAR SENHA -----------------------
    ttk.Label(frm, text="Confirmar senha", font=("Segoe UI", 10)).grid(row=7, column=0, sticky="w")

    conf_frame = tk.Frame(frm)
    conf_frame.grid(row=8, column=0, sticky="ew", pady=(0, 12))

    ent_conf = ttk.Entry(conf_frame, width=34, show="•")
    ent_conf.pack(side="left", fill="x", expand=True)

    var_ver_conf = tk.BooleanVar(value=False)
    def toggle_conf():
        ent_conf.config(show="" if var_ver_conf.get() else "•")

    ttk.Checkbutton(conf_frame, text="👁", width=3,
                    variable=var_ver_conf, command=toggle_conf).pack(side="left", padx=4)

    # ----------------------- REGISTRAR -----------------------
    def do_registrar(event=None):
        nome = ent_nome.get().strip()
        email_raw = ent_email.get().strip()
        senha = ent_senha.get().strip()
        conf = ent_conf.get().strip()

        if not nome:
            messagebox.showerror("Erro", "Informe seu nome completo.")
            return

        email_final = email_raw + "@ebserh.gov.br" if "@" not in email_raw else email_raw

        if senha != conf:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        if len(senha) < 8:
            messagebox.showerror("Erro", "A senha deve ter pelo menos 8 caracteres.")
            return

        try:
            from auth import usuario_registrar
            usuario_registrar(email_final, senha, nome)
            messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro no registro", str(e))

    ttk.Button(frm, text="Registrar", style="Primary.TButton", command=do_registrar)\
        .grid(row=9, column=0, sticky="ew")

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
