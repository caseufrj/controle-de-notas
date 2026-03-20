# telas/tela_inicial.py
import os, socket, traceback
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

APP_NAME = "SICONAE"
TITULO = "Sistema de Controle de Atas e Empenhos"
CAMINHO_LOGO = None  # opcional: caminho para logo .png

PRIMARY = "#0d3758"
PRIMARY_HOVER = "#12476f"
PRIMARY_TEXT = "#ffffff"
OUTLINE_TEXT = "#0d3758"
BG_TOP = "#cfe9ff"
BG_MID = "#e8f4ff"
BG_BOTTOM = "#f6fbff"

# Se quiser forçar sem gradiente (debug/performance), defina no Windows:
# setx SICONAE_NO_GRADIENT 1
NO_GRADIENT = os.environ.get("SICONAE_NO_GRADIENT") == "1"

# ---------- utils visual ----------
def _hex_to_rgb(hx: str):
    return tuple(int(hx[i:i+2], 16) for i in (1,3,5))

def desenhar_gradiente(canvas: tk.Canvas, w: int, h: int, top: str, mid: str, bottom: str, steps: int = 120) -> None:
    """
    Gradiente vertical leve (no máximo 'steps' retângulos).
    Evita desenhar 1 linha por pixel para não estourar GDI/recursos do Tk.
    """
    canvas.delete("grad")  # apaga só o que for gradiente
    if w <= 0 or h <= 0 or steps <= 0:
        return

    t = _hex_to_rgb(top); m = _hex_to_rgb(mid); b = _hex_to_rgb(bottom)

    # Primeira metade: top -> mid | Segunda: mid -> bottom
    half = max(1, steps // 2)
    # Altura de cada faixa
    band_h = max(1, h // steps)

    def interp(c1, c2, r):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * r) for i in range(3))

    y = 0
    # top -> mid
    for i in range(half):
        r = i / max(1, half - 1)
        rgb = interp(t, m, r)
        color = "#%02x%02x%02x" % rgb
        canvas.create_rectangle(0, y, w, min(h, y + band_h), outline="", fill=color, tags=("grad",))
        y += band_h

    # mid -> bottom
    remain = steps - half
    for j in range(remain):
        r = j / max(1, remain - 1)
        rgb = interp(m, b, r)
        color = "#%02x%02x%02x" % rgb
        canvas.create_rectangle(0, y, w, min(h, y + band_h), outline="", fill=color, tags=("grad",))
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

# ---------- montagem/desmontagem tela inicial ----------
def desmontar_tela_inicial(root: tk.Tk):
    # apaga tudo que foi criado pela tela inicial
    if hasattr(root, "_tela_inicial_widgets"):
        for w in root._tela_inicial_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        root._tela_inicial_widgets = []
    # cancela render pendente (debounce)
    if hasattr(root, "_render_after") and root._render_after:
        try:
            root.after_cancel(root._render_after)
        except Exception:
            pass
        root._render_after = None

def montar_tela_inicial(root: tk.Tk):
    print("[DEBUG] tela_inicial: montar_tela_inicial()")

    # prepara banco (imports tardios e tolerantes)
    try:
        try:
            from banco import criar_tabelas as _criar_tabelas
            print("[DEBUG] tela_inicial: import banco.criar_tabelas OK")
        except ImportError:
            from bd import criar_tabelas as _criar_tabelas
            print("[DEBUG] tela_inicial: import bd.criar_tabelas OK (fallback)")
        try:
            _criar_tabelas()
            print("[DEBUG] tela_inicial: criar_tabelas() OK")
        except Exception as e:
            print("[DEBUG] tela_inicial: criar_tabelas() FALHOU:", e)
    except Exception as e:
        print("[DEBUG] tela_inicial: import criar_tabelas FALHOU:", e)
        log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "="*80 + "\n")
            f.write("Falha ao importar/rodar criar_tabelas do banco:\n")
            f.write(traceback.format_exc())

    # inicializa auth
    try:
        from auth import auth_init
        auth_init()
        print("[DEBUG] tela_inicial: auth_init() OK")
    except Exception as e:
        print("[DEBUG] tela_inicial: auth_init() FALHOU:", e)
        log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "="*80 + "\n")
            f.write("Falha no auth_init():\n")
            f.write(traceback.format_exc())

    estilizar(root)

    canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)

    # guardar referências para destruir depois
    root._tela_inicial_widgets = [canvas]
    root._render_after = None  # para debounce

    def render():
        try:
            canvas.delete("all")
            w, h = root.winfo_width(), root.winfo_height()
            if not NO_GRADIENT:
                # gradiente leve e sem tempestade de desenho
                desenhar_gradiente(canvas, w, h, BG_TOP, BG_MID, BG_BOTTOM, steps=120)
            else:
                # fundo sólido (fallback)
                canvas.create_rectangle(0, 0, w, h, fill=BG_MID, outline="")

            cx = w // 2
            canvas.create_text(cx, 70, text=TITULO, font=("Segoe UI Semibold", 20), fill="#113a5e")
            canvas.create_text(cx, 108, text=APP_NAME, font=("Segoe UI", 12), fill="#1f4c77")

            y_logo = 150
            if CAMINHO_LOGO and os.path.exists(CAMINHO_LOGO):
                try:
                    img = tk.PhotoImage(file=CAMINHO_LOGO)
                    # manter referência para não perder a imagem
                    canvas.image = img
                    canvas.create_image(cx, y_logo, image=img)
                except Exception:
                    canvas.create_oval(cx - 34, y_logo - 34, cx + 34, y_logo + 34, outline="#0d3758", width=3)
            else:
                canvas.create_oval(cx - 34, y_logo - 34, cx + 34, y_logo + 34, outline="#0d3758", width=3)

            # LOGIN
            btn_login = ttk.Button(root, text="LOGIN", style="Primary.TButton",
                                   command=lambda: abrir_modal_login(root))
            canvas.create_window(cx, y_logo + 96, window=btn_login, anchor="center")
            root._tela_inicial_widgets.append(btn_login)

            # REGISTRO
            btn_reg = ttk.Button(root, text="REGISTRO / CADASTRO", style="Outline.TButton",
                                 command=lambda: abrir_modal_registro(root))
            canvas.create_window(cx, y_logo + 150, window=btn_reg, anchor="center")
            root._tela_inicial_widgets.append(btn_reg)

            canvas.create_rectangle(0, h - 48, w, h, fill="#0b2f4a", width=0)
        finally:
            # limpa a flag do debounce
            root._render_after = None

    def schedule_render(_evt=None):
        # Debounce: renderiza no máx. a cada 60ms, cancelando chamadas anteriores
        if root._render_after:
            try:
                root.after_cancel(root._render_after)
            except Exception:
                pass
        root._render_after = root.after(60, render)

    root.bind("<Configure>", schedule_render)
    # Render inicial
    schedule_render()

# ---------- modais ----------
def abrir_modal_login(root: tk.Tk):
    win = tk.Toplevel(root); win.title("Login - SICONAE")
    win.transient(root); win.grab_set(); win.resizable(False, False)
    frm = ttk.Frame(win, padding=16); frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="E-mail EBSERH", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_email = ttk.Entry(frm, width=40); ent_email.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(frm, text="Senha", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
    ent_senha = ttk.Entry(frm, width=40, show="•"); ent_senha.grid(row=3, column=0, sticky="ew", pady=(0, 12))

    def do_login():
        try:
            # import tardio do auth
            from auth import usuario_login

            ua = f"SICONAE-Desktop/{os.name}"
            ip = socket.gethostbyname(socket.gethostname())
            auth = usuario_login(ent_email.get().strip(), ent_senha.get(), ua, ip)

            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            montar_sistema(root, auth)
        except Exception as e:
            messagebox.showerror("Erro no login", str(e))

    ttk.Button(frm, text="Entrar", style="Primary.TButton", command=do_login).grid(row=4, column=0, sticky="ew")
    ent_email.focus_set()

def abrir_modal_registro(root: tk.Tk):
    win = tk.Toplevel(root); win.title("Registro / Cadastro - SICONAE")
    win.transient(root); win.grab_set(); win.resizable(False, False)
    frm = ttk.Frame(win, padding=16); frm.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frm, text="Nome", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
    ent_nome = ttk.Entry(frm, width=40); ent_nome.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(frm, text="E-mail EBSERH (@ebserh.gov.br)", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w")
    ent_email = ttk.Entry(frm, width=40); ent_email.grid(row=3, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(frm, text="Senha (mín. 10 caracteres)", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w")
    ent_senha = ttk.Entry(frm, width=40, show="•"); ent_senha.grid(row=5, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(frm, text="Confirmar Senha", font=("Segoe UI", 10)).grid(row=6, column=0, sticky="w")
    ent_conf = ttk.Entry(frm, width=40, show="•"); ent_conf.grid(row=7, column=0, sticky="ew", pady=(0, 12))

    def do_registrar():
        try:
            from auth import usuario_registrar
            s1, s2 = ent_senha.get(), ent_conf.get()
            if s1 != s2:
                messagebox.showerror("Erro", "As senhas não coincidem.")
                return
            usuario_registrar(ent_email.get().strip(), s1, ent_nome.get().strip() or None)
            messagebox.showinfo("Sucesso", "Usuário criado. Faça login.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Erro no registro", str(e))

    ttk.Button(frm, text="Registrar", style="Primary.TButton", command=do_registrar).grid(row=8, column=0, sticky="ew")
    ent_nome.focus_set()

# ---------- montar sistema no root ----------
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

    # Monta o sistema com fallback de erro
    def on_sair(_root: tk.Tk):
        try:
            if hasattr(_root, "_sistema") and _root._sistema:
                _root._sistema = None
        except Exception:
            pass
        montar_tela_inicial(_root)

    try:
        # import tardio para evitar erro no import global se houver dependências
        from telas.sistema import SistemaApp
        print("[DEBUG] tela_inicial: import telas.sistema.SistemaApp OK")
        root._sistema = SistemaApp(root, auth, on_sair=on_sair)
        print("[DEBUG] tela_inicial: SistemaApp montado OK")
    except Exception as e:
        print("[DEBUG] tela_inicial: SistemaApp FALHOU:", e)
        log_path = os.path.join(os.path.expanduser("~"), "controle_notas_erro.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "="*80 + "\n")
            f.write("Falha ao montar o SistemaApp:\n")
            f.write(traceback.format_exc())

        messagebox.showerror(
            "Erro ao abrir o sistema",
            f"{e}\n\nUm log foi salvo em:\n{log_path}"
        )
        # Reconstrói a tela inicial para o usuário tentar novamente
        montar_tela_inicial(root)
