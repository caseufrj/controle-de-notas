# telas/tela_inicial.py
import os, sys, socket, traceback
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
import json
import base64
import os
from cryptography.fernet import Fernet

# Caminho do arquivo onde email e senha serão salvos
CONFIG_LOGIN_ARQ = os.path.join(os.path.expanduser("~"), "siconae_login.json")

# Caminho onde a chave será salva
CONFIG_KEY_ARQ = os.path.join(os.path.expanduser("~"), "siconae_key.key")


def _get_or_create_key():
    """
    Cria ou lê a chave usada para criptografar a senha.
    Essa chave é salva SOMENTE no PC do usuário.
    """
    if os.path.exists(CONFIG_KEY_ARQ):
        with open(CONFIG_KEY_ARQ, "rb") as f:
            return f.read()

    # gerar chave nova
    key = Fernet.generate_key()
    with open(CONFIG_KEY_ARQ, "wb") as f:
        f.write(key)
    return key


def salvar_login(email: str, senha: str):
    """
    Salva login localmente, senha CRIPTOGRAFADA com Fernet.
    """
    try:
        key = _get_or_create_key()
        f = Fernet(key)

        senha_enc = f.encrypt(senha.encode()).decode()

        dados = {
            "email": email,
            "senha": senha_enc
        }

        with open(CONFIG_LOGIN_ARQ, "w", encoding="utf-8") as f2:
            json.dump(dados, f2)

    except Exception:
        pass


def carregar_login_local():
    """Lê o email e senha criptografada e retorna descriptografado."""
    try:
        if not os.path.exists(CONFIG_LOGIN_ARQ):
            return {"email": "", "senha": ""}

        with open(CONFIG_LOGIN_ARQ, "r", encoding="utf-8") as arq:
            dados = json.load(arq)

        key = _get_or_create_key()
        f = Fernet(key)
        senha = f.decrypt(dados["senha"].encode()).decode()

        return {"email": dados.get("email",""), "senha": senha}

    except Exception:
        return {"email": "", "senha": ""}



def ler_login():
    """
    Lê o login salvo (se existir).
    Descriptografa a senha.
    """
    try:
        if not os.path.exists(CONFIG_LOGIN_ARQ):
            return {"email": "", "senha": ""}

        with open(CONFIG_LOGIN_ARQ, "r", encoding="utf-8") as f:
            dados = json.load(f)

        key = _get_or_create_key()
        f_key = Fernet(key)

        senha_dec = f_key.decrypt(dados["senha"].encode()).decode()

        return {"email": dados.get("email", ""), "senha": senha_dec}

    except Exception:
        return {"email": "", "senha": ""}

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

    # 🔥 remover scroll global antes de destruir widgets
    try:
        root.unbind_all("<MouseWheel>")
    except Exception:
        pass

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
        
LAYOUT_ALTURA = 900  # altura fixa do layout

def montar_tela_inicial(root: tk.Tk):
    print("[DEBUG] tela_inicial: montar_tela_inicial()")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.configure(bg="#ffffff")

    estilizar(root)

    # =========================================================
    # CANVAS SCROLL PRINCIPAL
    # =========================================================
    scroll_canvas = tk.Canvas(root, highlightthickness=0, bd=0, bg="#ffffff")
    scroll_canvas.pack(fill="both", expand=True)

    root._tela_inicial_widgets = [scroll_canvas]

    # frame que conterá o layout fixo
    frame = tk.Frame(scroll_canvas, bg="#ffffff")
    frame_id = scroll_canvas.create_window(0, 0, anchor="nw", window=frame)

    # =========================================================
    # FORÇAR LARGURA DO FRAME PARA A MESMA DO CANVAS
    # =========================================================
    def ajustar_largura(evt=None):
        scroll_canvas.itemconfig(frame_id, width=scroll_canvas.winfo_width())

    scroll_canvas.bind("<Configure>", ajustar_largura)

    # =========================================================
    # SCROLL COM MOUSE (LOCAL, SEM ERRO EM OUTRAS TELAS)
    # =========================================================
    def on_mousewheel(evt):
        # só funciona se o canvas existir
        if not scroll_canvas.winfo_exists():
            return
        scroll_canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")

    # 🔥 focar automaticamente ao entrar com mouse
    scroll_canvas.bind("<Enter>", lambda e: scroll_canvas.focus_set())

    scroll_canvas.bind("<MouseWheel>", on_mousewheel)

    # =========================================================
    # LAYOUT INTERNO
    # =========================================================
    layout = tk.Canvas(frame, height=LAYOUT_ALTURA,
                       highlightthickness=0, bd=0, bg="#ffffff")
    layout.pack(fill="both", expand=True)

    # =========================================================
    # CARREGAR LOGO
    # =========================================================
    root._logo_img = None
    if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
        try:
            img = tk.PhotoImage(file=CAMINHO_LOGO)
            if img.width() > 250:
                img = img.subsample(img.width() // 250)
            root._logo_img = img
        except:
            pass

    # BOTÕES
    btn_login = ttk.Button(root, text="LOGIN", style="Primary.TButton",
                           command=lambda: abrir_modal_login(root))

    btn_reg = ttk.Button(root, text="REGISTRO / CADASTRO",
                         style="Outline.TButton",
                         command=lambda: abrir_modal_registro(root))

    win_login = layout.create_window(0, 0, anchor="center", window=btn_login)
    win_reg   = layout.create_window(0, 0, anchor="center", window=btn_reg)

    # =========================================================
    # RENDER MAIN (CENTRALIZADO)
    # =========================================================
    def render():
        layout.delete("grad")
        layout.delete("ui")

        w = layout.winfo_width()
        h = LAYOUT_ALTURA
        cx = w // 2

        # fundo
        if not NO_GRADIENT:
            desenhar_gradiente(layout, w, h, BG_TOP, BG_MID, BG_BOTTOM)
        else:
            layout.create_rectangle(0, 0, w, h, fill=BG_MID, outline="")

        # textos
        layout.create_text(cx, 70, text=TITULO,
                           font=("Segoe UI Semibold", 20),
                           fill="#113a5e", tags="ui")
        layout.create_text(cx, 108, text=APP_NAME,
                           font=("Segoe UI", 12),
                           fill="#1f4c77", tags="ui")

        # logo
        y_logo = 320
        if root._logo_img:
            layout.create_image(cx, y_logo, image=root._logo_img, tags="ui")

        # botões
        layout.coords(win_login, cx, y_logo + 240)
        layout.coords(win_reg, cx, y_logo + 300)

        # rodapé azul
        layout.create_rectangle(0, h - 48, w, h,
                                fill="#0b2f4a", width=0, tags="ui")

        # scroll region
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    layout.bind("<Configure>", lambda e: render())

    # salvar widgets
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

    # ---------- carregar email/senha salvos ----------
    cfg = carregar_login_local()
    email_salvo = cfg.get("email", "")
    senha_salva = cfg.get("senha", "")

    # ---------------- EMAIL ----------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")

    email_box = tk.Frame(frm, bg="white")
    email_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    
    ent_email = ttk.Entry(email_box, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    # preenche email salvo (sem @)
    if email_salvo:
        if email_salvo.endswith("@ebserh.gov.br"):
            ent_email.insert(0, email_salvo.replace("@ebserh.gov.br", ""))
        else:
            ent_email.insert(0, email_salvo)
    
    # indicador visual
    lbl_ok = tk.Label(email_box, text="⭕", bg="white", fg="red", font=("Segoe UI", 11))
    lbl_ok.pack(side="right", padx=5)
    
    def validar_email(e=None):
        txt = ent_email.get().strip()
        if len(txt) >= 3:
            lbl_ok.config(text="🟢", fg="green")
        else:
            lbl_ok.config(text="⭕", fg="red")
    
    ent_email.bind("<KeyRelease>", validar_email)

    # ---------------- SENHA + 👁 ----------------
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    pass_box = tk.Frame(frm)
    pass_box.grid(row=3, column=0, sticky="ew", pady=(0, 10))

    ent_senha = ttk.Entry(pass_box, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    # preencher senha salva
    if senha_salva:
        ent_senha.insert(0, senha_salva)

    ver_senha = tk.BooleanVar(value=False)

    def toggle_senha():
        ent_senha.config(show="" if ver_senha.get() else "•")

    ttk.Checkbutton(pass_box, text="👁", variable=ver_senha,
                    command=toggle_senha).pack(side="left", padx=6)

    # ---------------- SALVAR SENHA ----------------
    var_salvar = tk.BooleanVar(value=bool(email_salvo and senha_salva))
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

            # 👍 salvar SEM travar
            if var_salvar.get():
                salvar_login_local(email, senha)

            win.destroy()
            montar_sistema(root, auth)

        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login)\
        .grid(row=5, column=0, sticky="ew", pady=(0, 6))

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

    # animação leve
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

    # ------------------ NOME ------------------
    ttk.Label(frm, text="Nome completo", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40)
    ent_nome.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    # ------------------ E-MAIL (DIGITAR COMPLETO) ------------------
    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")

    email_box = tk.Frame(frm, bg="white")
    email_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))

    ent_email = ttk.Entry(email_box, width=40)
    ent_email.pack(side="left", fill="x", expand=True)

    lbl_ok = tk.Label(email_box, text="⭕", bg="white", fg="red", font=("Segoe UI", 11))
    lbl_ok.pack(side="right", padx=6)

    def validar_email(evt=None):
        email = ent_email.get().strip().lower()

        # exige email COMPLETO
        if "@" in email and email.endswith(".gov.br"):
            lbl_ok.config(text="🟢", fg="green")
        else:
            lbl_ok.config(text="⭕", fg="red")

    ent_email.bind("<KeyRelease>", validar_email)

    # ------------------ SENHA + REGRAS DINÂMICAS ------------------
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w")

    pass_box = tk.Frame(frm)
    pass_box.grid(row=5, column=0, sticky="ew")

    ent_senha = ttk.Entry(pass_box, width=34, show="•")
    ent_senha.pack(side="left", fill="x", expand=True)

    ver_senha = tk.BooleanVar(value=False)
    
    def toggle_senha():
        ent_senha.config(show="" if ver_senha.get() else "•")

    ttk.Checkbutton(pass_box, text="👁", variable=ver_senha,
                    command=toggle_senha).pack(side="left", padx=6)

    # ----------- Regras estilo GOV.BR (cada linha muda individualmente) -----------
    regras_frame = tk.Frame(frm)
    regras_frame.grid(row=6, column=0, sticky="w", pady=(2, 12))

    lbl_regra1 = tk.Label(regras_frame, text="✖ mínimo 8 caracteres", fg="#d9534f", font=("Segoe UI", 8))
    lbl_regra2 = tk.Label(regras_frame, text="✖ letra minúscula",      fg="#d9534f", font=("Segoe UI", 8))
    lbl_regra3 = tk.Label(regras_frame, text="✖ letra maiúscula",      fg="#d9534f", font=("Segoe UI", 8))
    lbl_regra4 = tk.Label(regras_frame, text="✖ número",               fg="#d9534f", font=("Segoe UI", 8))
    lbl_regra5 = tk.Label(regras_frame, text="✖ símbolo (ex: @, !, %)", fg="#d9534f", font=("Segoe UI", 8))

    lbl_regra1.pack(anchor="w")
    lbl_regra2.pack(anchor="w")
    lbl_regra3.pack(anchor="w")
    lbl_regra4.pack(anchor="w")
    lbl_regra5.pack(anchor="w")

    def validar_regras(evt=None):
        s = ent_senha.get()

        # Regra 1: tamanho
        if len(s) >= 8:
            lbl_regra1.config(text="✔ mínimo 8 caracteres", fg="green")
        else:
            lbl_regra1.config(text="✖ mínimo 8 caracteres", fg="#d9534f")

        # Regra 2: minúscula
        if any(c.islower() for c in s):
            lbl_regra2.config(text="✔ letra minúscula", fg="green")
        else:
            lbl_regra2.config(text="✖ letra minúscula", fg="#d9534f")

        # Regra 3: maiúscula
        if any(c.isupper() for c in s):
            lbl_regra3.config(text="✔ letra maiúscula", fg="green")
        else:
            lbl_regra3.config(text="✖ letra maiúscula", fg="#d9534f")

        # Regra 4: número
        if any(c.isdigit() for c in s):
            lbl_regra4.config(text="✔ número", fg="green")
        else:
            lbl_regra4.config(text="✖ número", fg="#d9534f")

        # Regra 5: símbolo
        if any(c in "@#$!%*?&" for c in s):
            lbl_regra5.config(text="✔ símbolo (ex: @, !, %)", fg="green")
        else:
            lbl_regra5.config(text="✖ símbolo (ex: @, !, %)", fg="#d9534f")

    ent_senha.bind("<KeyRelease>", validar_regras)

    # ---- Regras estilo GOV.BR ----
    regras = tk.Label(
        frm,
        text=(
            "Sua senha deve conter:\n"
            "• 8 ou mais caracteres\n"
            "• letra minúscula\n"
            "• letra maiúscula\n"
            "• número\n"
            "• símbolo (ex: @, #, !, %)"
        ),
        fg="#444",
        font=("Segoe UI", 8),
        justify="left"
    )
    regras.grid(row=6, column=0, sticky="w", pady=(2, 12))

    # validação dinâmica GOV.BR
    def validar_senha(evt=None):
        s = ent_senha.get()

        ok = True
        if len(s) < 8: ok = False
        if not any(c.islower()  for c in s): ok = False
        if not any(c.isupper()  for c in s): ok = False
        if not any(c.isdigit()  for c in s): ok = False
        if not any(c in "@#$!%*?&" for c in s): ok = False

        if ok:
            regras.config(fg="green")
        else:
            regras.config(fg="#d9534f")  # vermelho suave

    ent_senha.bind("<KeyRelease>", validar_senha)

    # ------------------ CONFIRMAR SENHA ------------------
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

    # ------------------ REGISTRAR ------------------
    def do_registrar(event=None):
        nome = ent_nome.get().strip()
        email = ent_email.get().strip()
        s1 = ent_senha.get().strip()
        s2 = ent_conf.get().strip()

        if not nome:
            messagebox.showerror("Erro", "Informe seu nome.")
            return

        if "@" not in email:
            messagebox.showerror("Erro", "Digite o e‑mail completo.")
            return

        if s1 != s2:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        # checar regras
        if (len(s1) < 8 or
            not any(c.islower() for c in s1) or
            not any(c.isupper() for c in s1) or
            not any(c.isdigit() for c in s1) or
            not any(c in "@#$!%*?&" for c in s1)):
            messagebox.showerror("Erro", "A senha não atende aos requisitos.")
            return

        try:
            from auth import usuario_registrar
            usuario_registrar(email, s1, nome)
            messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    ttk.Button(frm, text="Registrar", style="Primary.TButton",
               command=do_registrar)\
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
