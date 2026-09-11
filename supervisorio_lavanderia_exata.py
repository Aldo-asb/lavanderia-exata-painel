# ============================================================================
# RESERVATÓRIO LAVANDERIA EXATA - SUPERVISÓRIO PYTHON / STREAMLIT
# Sensor hidrostático 4-20mA + LCD 4x20 (I2C) + 2 Bombas + Nível do Poço
# ============================================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, time as dtime
import time
import pytz
import urllib.parse
import pandas as pd

# --- 1. CONFIGURAÇÃO DO RESERVATÓRIO ---
CAPACIDADE_LITROS = 30000.0   # capacidade total do reservatorio
ALTURA_MAXIMA_M = 3.80        # faixa util do sensor de 5m (coluna real do reservatorio)
NIVEL_BAIXO_PCT = 15          # % abaixo do qual dispara alerta de nivel baixo (email)
NIVEL_CHEIO_PCT = 95          # % acima do qual dispara alerta de reservatorio cheio (email)

# Faixa de acionamento da BOMBA (valores padrao - podem ser sobrescritos pelo admin, ver Firebase)
BOMBA_LIGA_PCT = 70     # liga a bomba abaixo disso
BOMBA_DESLIGA_PCT = 95  # desliga a bomba acima disso

# --- 2. CONFIGURAÇÃO VISUAL (TEMA CLARO/ESCURO) ---
st.set_page_config(page_title="Lavanderia Exata - Supervisório", layout="wide", initial_sidebar_state="expanded")

tema_atual = st.session_state.get("tema", "Branco")

if tema_atual == "Branco":
    COR_BG = "#ffffff"
    COR_TEXTO = "#1e293b"
    COR_SIDEBAR_BG = "#f8fafc"
    COR_BORDA = "#e2e8f0"
    COR_CARD_BG = "#ffffff"
    COR_CARD_BG2 = "#f1f5f9"
    COR_MUTED = "#64748b"
    COR_MUTED2 = "#94a3b8"
    COR_ACCENT = "#2563eb"
    COR_ACCENT_RGB = "37,99,235"
    COR_TITULO = "#0f172a"
    COR_INPUT_BG = "#ffffff"
elif tema_atual == "Cinza Claro":
    COR_BG = "#e8ecf1"
    COR_TEXTO = "#1e293b"
    COR_SIDEBAR_BG = "#dde3ea"
    COR_BORDA = "#c7d0dc"
    COR_CARD_BG = "#f4f6f9"
    COR_CARD_BG2 = "#e2e8f0"
    COR_MUTED = "#64748b"
    COR_MUTED2 = "#94a3b8"
    COR_ACCENT = "#2563eb"
    COR_ACCENT_RGB = "37,99,235"
    COR_TITULO = "#0f172a"
    COR_INPUT_BG = "#ffffff"
else:  # Escuro
    COR_BG = "#0a0e1a"
    COR_TEXTO = "#e0e6f0"
    COR_SIDEBAR_BG = "#0d1220"
    COR_BORDA = "#1e2d4a"
    COR_CARD_BG = "#111827"
    COR_CARD_BG2 = "#0d1a2e"
    COR_MUTED = "#6b7fa3"
    COR_MUTED2 = "#94a3b8"
    COR_ACCENT = "#4a9eff"
    COR_ACCENT_RGB = "74,158,255"
    COR_TITULO = "#ffffff"
    COR_INPUT_BG = "#111827"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

* {{ box-sizing: border-box; }}

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background: {COR_BG};
    color: {COR_TEXTO};
}}

section[data-testid="stSidebar"] {{
    background: {COR_SIDEBAR_BG} !important;
    border-right: 1px solid {COR_BORDA};
}}
section[data-testid="stSidebar"] * {{ color: {COR_TEXTO} !important; }}
section[data-testid="stSidebar"] .stRadio label {{ 
    font-size: 14px !important; 
    padding: 6px 0 !important;
}}

.titulo-asb {{
    font-family: 'Rajdhani', sans-serif;
    color: {COR_TITULO};
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 4px;
    text-align: center;
    padding: 20px 0 4px 0;
    text-transform: uppercase;
}}
.subtitulo-asb {{
    color: {COR_ACCENT};
    font-size: 13px;
    text-align: center;
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-bottom: 32px;
}}
.divider-blue {{
    height: 2px;
    background: linear-gradient(90deg, transparent, {COR_ACCENT}, transparent);
    margin: 0 auto 32px auto;
    max-width: 400px;
}}

.asb-card {{
    background: {COR_CARD_BG};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 24px;
}}

.home-card {{
    background: linear-gradient(135deg, {COR_CARD_BG} 0%, {COR_CARD_BG2} 100%);
    border: 1px solid {COR_BORDA};
    border-radius: 14px;
    padding: 32px 24px;
    text-align: center;
    height: 100%;
    transition: border-color 0.3s ease;
}}
.home-card:hover {{ border-color: {COR_ACCENT}; }}
.home-icon {{ font-size: 36px; margin-bottom: 14px; }}
.home-card h3 {{ 
    font-family: 'Rajdhani', sans-serif;
    color: {COR_TITULO}; font-size: 20px; font-weight: 600; 
    letter-spacing: 1px; margin-bottom: 10px;
}}
.home-card p {{ color: {COR_MUTED}; font-size: 14px; line-height: 1.6; }}

.barra-wrap {{ height: 6px; border-radius: 6px; overflow: hidden; margin-top: 12px; background: {COR_BORDA}; }}
.barra-on {{ height: 100%; background: linear-gradient(90deg, #22c55e, #86efac, #22c55e); background-size: 200%; animation: slide 1.5s linear infinite; }}
.barra-off {{ height: 100%; background: #ef4444; }}
.barra-inativa {{ height: 100%; background: {COR_BORDA}; }}
@keyframes slide {{ 0%{{background-position:200% 0}} 100%{{background-position:0 0}} }}

.gauge-card {{
    background: {COR_CARD_BG};
    border: 1px solid {COR_BORDA};
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
    position: relative;
}}
.gauge-label {{
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: {COR_ACCENT};
    font-weight: 600;
    margin-bottom: 16px;
}}
.gauge-value {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 72px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 6px;
}}
.gauge-unit {{
    font-size: 20px;
    color: {COR_MUTED};
    margin-bottom: 20px;
}}
.gauge-bar-bg {{ height: 8px; background: {COR_BORDA}; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }}
.gauge-bar-fill {{ height: 100%; border-radius: 8px; transition: width 0.8s ease; }}
.gauge-nivel-fill {{ background: linear-gradient(90deg, #ef4444, #fbbf24, #22c55e); }}
.gauge-volume-fill {{ background: linear-gradient(90deg, #06b6d4, #3b82f6); }}
.gauge-meta {{ font-size: 12px; color: {COR_MUTED2}; }}
.dado-antigo {{ 
    background: rgba(239,68,68,0.1); 
    border: 1px solid rgba(239,68,68,0.3); 
    border-radius: 6px; 
    padding: 6px 12px; 
    font-size: 11px; 
    color: #ef4444; 
    margin-top: 8px;
    letter-spacing: 1px;
}}
.dado-fresco {{
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.3);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    color: #22c55e;
    margin-top: 8px;
    letter-spacing: 1px;
}}

.diag-status-ok {{
    background: rgba(34,197,94,0.08);
    border: 1px solid #22c55e;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    color: #22c55e;
    font-family: 'Rajdhani', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 24px;
}}
.diag-status-off {{
    background: rgba(239,68,68,0.08);
    border: 1px solid #ef4444;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    color: #ef4444;
    font-family: 'Rajdhani', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 24px;
}}
.diag-status-alert {{
    background: rgba(245,158,11,0.08);
    border: 1px solid #f59e0b;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    color: #f59e0b;
    font-family: 'Rajdhani', sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 24px;
}}
.diag-info-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    background: {COR_CARD_BG};
    border: 1px solid {COR_BORDA};
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    font-size: 14px;
    color: {COR_MUTED2};
}}
.diag-info-label {{ font-weight: 600; color: {COR_TEXTO}; min-width: 200px; }}

/* Botao poco seco */
.poco-seco-alert {{
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.5);
    border-radius: 12px;
    padding: 14px 20px;
    text-align: center;
    color: #ef4444;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 16px;
}}
.poco-ok-alert {{
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.4);
    border-radius: 12px;
    padding: 14px 20px;
    text-align: center;
    color: #22c55e;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 16px;
}}

div[data-testid="stButton"] > button {{
    width: 100%;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    letter-spacing: 2px !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 14px 20px !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stButton"] > button:not([kind]) {{
    background: linear-gradient(135deg, {COR_ACCENT}, {COR_ACCENT}) !important;
    color: white !important;
}}

.section-header {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 3px;
    color: {COR_TITULO};
    text-transform: uppercase;
    padding-bottom: 8px;
    border-bottom: 1px solid {COR_BORDA};
    margin-bottom: 24px;
}}

.chat-container {{ 
    background: {COR_SIDEBAR_BG}; 
    border: 1px solid {COR_BORDA};
    border-radius: 12px; 
    max-height: 420px; 
    overflow-y: auto; 
    padding: 16px;
}}
.msg-balao {{ 
    background: {COR_CARD_BG}; 
    border-left: 3px solid {COR_ACCENT}; 
    border-radius: 8px; 
    padding: 10px 14px; 
    margin-bottom: 8px; 
    font-size: 13px; 
    color: {COR_TEXTO};
}}
.msg-balao b {{ color: {COR_ACCENT}; }}
.msg-balao small {{ color: {COR_MUTED}; }}

.card-contato {{
    background: {COR_CARD_BG};
    border: 1px solid {COR_BORDA};
    border-left: 4px solid #22c55e;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    color: {COR_TEXTO};
    font-size: 14px;
}}

.auto-info {{
    background: rgba({COR_ACCENT_RGB},0.07);
    border: 1px solid rgba({COR_ACCENT_RGB},0.25);
    border-radius: 12px;
    padding: 20px;
    color: {COR_TEXTO};
    font-size: 15px;
    margin-bottom: 16px;
}}

.stTextInput input, .stNumberInput input {{
    background: {COR_INPUT_BG} !important;
    border: 1px solid {COR_BORDA} !important;
    border-radius: 8px !important;
    color: {COR_TEXTO} !important;
}}
.stRadio label {{ color: {COR_TEXTO} !important; }}
</style>
""", unsafe_allow_html=True)


# --- 3. FUNÇÕES CORE ---
def obter_hora_brasilia():
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

def enviar_email(assunto, mensagem):
    if not st.session_state.get("email_ativo", True): return
    try:
        remetente = st.secrets.get("email_user", "")
        senha = st.secrets.get("email_password", "")
        msg = MIMEText(mensagem)
        msg['Subject'], msg['From'], msg['To'] = assunto, remetente, remetente
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha)
            server.send_message(msg)
    except: pass

@st.cache_resource
def conectar_firebase():
    if not firebase_admin._apps:
        try:
            cred_dict = {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key": st.secrets["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["client_email"],
                "token_uri": st.secrets["token_uri"]
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': 'https://lavanderia-exata-default-rtdb.firebaseio.com/'})
            return True
        except Exception as e:
            st.error(f"ERRO AO CONECTAR NO FIREBASE: {e}")
            return False
    return True

def registrar_evento(acao):
    usuario = st.session_state.get("user_nome", "desconhecido")
    agora_f = obter_hora_brasilia().strftime('%d/%m/%Y %H:%M:%S')
    try:
        db.reference("historico_acoes").push({"data": agora_f, "usuario": usuario, "acao": acao})
        enviar_email(f"Lavanderia Exata: {acao}", f"Evento: {acao}\nUsuário: {usuario}\nData: {agora_f}")
    except: pass

def checar_dado_fresco(ultimo_pulso_ms, tolerancia_segundos=60):
    if not ultimo_pulso_ms:
        return False
    try:
        ultimo_pulso_ms = float(ultimo_pulso_ms)
    except (TypeError, ValueError):
        return False
    agora_ms = time.time() * 1000
    return (agora_ms - ultimo_pulso_ms) < (tolerancia_segundos * 1000)


# --- 4. ESTADOS ---
defaults = {
    "logado": False, "is_admin": False, "email_ativo": True,
    "modo_operacao": "MANUAL", "ciclo_ativo": False, "tema": "Branco"
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 5. LOGIN ---
if not st.session_state["logado"]:
    conectar_firebase()
    st.markdown("<div class='titulo-asb'>Lavanderia Exata</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitulo-asb'>Supervisório de Reservatório · IoT 2026</div>", unsafe_allow_html=True)
    st.markdown("<div class='divider-blue'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.container():
            st.markdown("<div class='asb-card'>", unsafe_allow_html=True)
            u = st.text_input("Usuário", placeholder="seu login")
            p = st.text_input("Senha", type="password", placeholder="••••••••")
            if st.button("ACESSAR SISTEMA"):
                if u == "admin" and p == "exata2026":
                    st.session_state.update({"logado": True, "user_nome": "Admin Master", "is_admin": True})
                    st.rerun()
                else:
                    try:
                        usrs = db.reference("usuarios_autorizados").get()
                        if usrs:
                            for k_u, v_u in usrs.items():
                                if v_u['login'] == u and v_u['senha'] == p:
                                    st.session_state.update({"logado": True, "user_nome": v_u['nome'], "is_admin": False})
                                    st.rerun()
                    except: pass
                    st.error("Credenciais inválidas.")
            st.markdown("</div>", unsafe_allow_html=True)

# --- 6. PAINEL PRINCIPAL ---
else:
    conectar_firebase()

    # SIDEBAR
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center; padding: 16px 0 8px 0;'>
            <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                        color:{COR_ACCENT}; letter-spacing:2px;'>LAVANDERIA EXATA</div>
            <div style='font-size:11px; color:{COR_MUTED}; letter-spacing:1px;'>SUPERVISÓRIO DE RESERVATÓRIO</div>
            <div style='margin-top:10px; font-size:13px; color:{COR_MUTED2};'>
                👤 {st.session_state.get("user_nome","")}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        opts = ["🏠 Home", "🚰 Controle das Bombas", "💧 Nível do Reservatório", "📊 Relatórios", "🛠️ Diagnóstico"]
        if st.session_state["is_admin"]: opts.append("👥 Gestão de Usuários")
        menu = st.radio("Navegação", opts, label_visibility="collapsed")

        st.divider()
        st.session_state["tema"] = st.radio(
            "🌓 Tema", ["Branco", "Cinza Claro", "Escuro"],
            index=["Branco", "Cinza Claro", "Escuro"].index(st.session_state["tema"]),
            horizontal=True
        )
        st.session_state["email_ativo"] = st.toggle("📧 Notificações por Email", value=st.session_state["email_ativo"])

        num_wa = st.text_input("WhatsApp Suporte (com DDD)", placeholder="5511999999999")
        if num_wa:
            txt = urllib.parse.quote(f"Olá, sou {st.session_state['user_nome']}. Reportando ocorrência no reservatório da Lavanderia Exata.")
            st.markdown(f'<a href="https://wa.me/{num_wa}?text={txt}" target="_blank" style="color:{COR_ACCENT}; font-size:13px;">💬 Abrir Suporte WhatsApp</a>', unsafe_allow_html=True)

        st.divider()
        if st.button("⏻ Encerrar Sessão"):
            st.session_state["logado"] = False
            st.rerun()

    # ─── HOME ───────────────────────────────────────────────────────────────
    if menu == "🏠 Home":
        st.markdown("<div class='titulo-asb'>Lavanderia Exata</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtitulo-asb'>Monitoramento em Tempo Real do Reservatório · 30.000 L</div>", unsafe_allow_html=True)
        st.markdown("<div class='divider-blue'></div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3, gap="medium")
        cards = [
            ("💧", "Nível em Tempo Real", "Monitoramento contínuo do nível do reservatório via sensor hidrostático 4-20mA (faixa 3,80m), com atualização a cada poucos segundos."),
            ("🚰", "Controle das Bombas", "Acionamento remoto de duas bombas de recalque (B1 Principal e B2 Reserva), manual ou automático por nível, com proteção de poço seco e registro de auditoria."),
            ("🔔", "Alertas Automáticos", "Notificações por e-mail quando o reservatório atinge nível crítico ou quando o poço está seco, evitando falta de água ou transbordamento."),
        ]
        for col, (icon, title, desc) in zip([c1, c2, c3], cards):
            with col:
                st.markdown(f"""
                <div class='home-card'>
                    <div class='home-icon'>{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>""", unsafe_allow_html=True)

    # ─── CONTROLE DAS BOMBAS ────────────────────────────────────────────────
    elif menu == "🚰 Controle das Bombas":
        st.markdown("<div class='section-header'>Controle das Bombas de Recalque</div>", unsafe_allow_html=True)

        # Botão de Atualização de Tela
        col_ref1, col_ref2 = st.columns([3, 1])
        with col_ref2:
            if st.button("🔄 ATUALIZAR STATUS DAS BOMBAS", use_container_width=True):
                st.rerun()

        modo = st.radio("Modo de Operação Geral", ["MANUAL", "AUTOMÁTICO"], horizontal=True)
        st.session_state["modo_operacao"] = modo
        st.markdown("<br>", unsafe_allow_html=True)

        # Le os status reais e comandos do Firebase
        try:
            status_real_b1 = db.reference("reservatorio/bomba1_status").get() or "OFF"
            status_real_b2 = db.reference("reservatorio/bomba2_status").get() or "OFF"
            cmd_b1 = db.reference("controle/bomba1_comando").get() or "OFF"
            cmd_b2 = db.reference("controle/bomba2_comando").get() or "OFF"
            nivel_poco = db.reference("reservatorio/nivel_poco").get() or "OK"
            ultimo_pulso_ctrl = db.reference("reservatorio/ultimo_pulso").get()
        except:
            status_real_b1, status_real_b2 = "DESCONHECIDO", "DESCONHECIDO"
            cmd_b1, cmd_b2 = "OFF", "OFF"
            nivel_poco = "DESCONHECIDO"
            ultimo_pulso_ctrl = None

        online = checar_dado_fresco(ultimo_pulso_ctrl, tolerancia_segundos=45)

        # Status REAL de operação (contato auxiliar) - só é confiável se houver comunicação.
        # Separado do comando (o que foi enviado), para não confundir "está operando" com "luz do botão".
        b1_operando = online and (status_real_b1 == "ON")
        b2_operando = online and (status_real_b2 == "ON")

        # Comando enviado (usado só para acender/apagar o botão pressionado, não representa operação real)
        comando_b1_ligar = (cmd_b1 == "ON")
        comando_b2_ligar = (cmd_b2 == "ON")

        # Estado do automático por software
        try:
            auto_software_ativo = db.reference("controle/auto_software_ativo").get() or False
        except:
            auto_software_ativo = False

        # Aviso geral de comunicação (item 01/02): sem comunicação, não exibimos status
        # de poço nem de bombas para não confundir o operador com dado desatualizado.
        if not online:
            st.markdown("""
            <div style='background:rgba(100,116,139,0.1); border:1px solid rgba(100,116,139,0.4);
                border-radius:10px; padding:14px 20px; margin-bottom:20px; text-align:center;
                color:#94a3b8; font-size:14px; font-weight:600; letter-spacing:1px;'>
                📡 SEM COMUNICAÇÃO COM O DISPOSITIVO — status do poço e das bombas indisponíveis no momento.
            </div>
            """, unsafe_allow_html=True)
        else:
            # Alerta de poço seco (só exibido com comunicação ativa)
            if nivel_poco == "BAIXO":
                st.markdown("""
                <div class='poco-seco-alert'>
                    ⚠️ NÍVEL DO POÇO BAIXO — As bombas estão PROTEGIDAS e não ligarão no automático.
                    Verifique o abastecimento do poço antes de forçar o acionamento manual.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='poco-ok-alert'>
                    ✅ Nível do poço OK — Abastecimento normal.
                </div>
                """, unsafe_allow_html=True)

        # ABAS DE NAVEGAÇÃO / SUBMENU PARA AS BOMBAS
        tab_b1, tab_b2, tab_auto = st.tabs(["💧 BOMBA 1 (Principal)", "🔄 BOMBA 2 (Reserva)", "🤖 MODO AUTOMÁTICO"])

        # --- ABA BOMBA 1 ---
        with tab_b1:
            st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin:12px 0 8px 0;'>💧 BOMBA 1 — EQUIPAMENTO PRINCIPAL</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:{COR_MUTED}; font-size:13px; margin-bottom:16px;'>Bomba primária conectada ao Poço 1. Esta é a bomba responsável pelo abastecimento diário.</div>", unsafe_allow_html=True)

            # Card de STATUS REAL DE OPERAÇÃO (item 01/02/04) — reflete o contato auxiliar, não o botão.
            # Só é exibido com comunicação ativa; sem comunicação mostra estado neutro (não confunde o operador).
            if not online:
                st.markdown(f"""
                <div style='text-align:center; margin-bottom:20px; padding:16px; border-radius:12px; border:2px solid #64748b; background:rgba(100,116,139,0.1);'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; letter-spacing:2px; color:#94a3b8;'>
                        📡 SEM COMUNICAÇÃO — STATUS INDISPONÍVEL
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                cor_b1 = "#22c55e" if b1_operando else "#ef4444"
                label_b1 = "● BOMBA 1 EM OPERAÇÃO" if b1_operando else "○ BOMBA 1 PARADA"
                bg_card_b1 = "rgba(34,197,94,0.18)" if b1_operando else "rgba(239,68,68,0.12)"

                st.markdown(f"""
                <div style='text-align:center; margin-bottom:20px; padding:16px; border-radius:12px; border:2px solid {cor_b1}; background:{bg_card_b1};'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; letter-spacing:2px; color:{cor_b1};'>
                        {label_b1}
                    </span><br>
                    <small style='color:{COR_MUTED2}; font-size:12px;'>Status real (contato auxiliar), independente do botão abaixo</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"<div style='color:{COR_MUTED}; font-size:12px; text-align:center; margin-bottom:10px;'>Último comando enviado: <b style='color:{COR_ACCENT};'>{'LIGAR' if comando_b1_ligar else 'DESLIGAR'}</b></div>", unsafe_allow_html=True)

            if modo == "MANUAL":
                col1_b1, col2_b1 = st.columns(2, gap="large")
                with col1_b1:
                    ativo_ligar = comando_b1_ligar
                    st.markdown(f"""
                    <div style='background:{"rgba(34,197,94,0.25)" if ativo_ligar else "rgba(34,197,94,0.05)"};
                        border:{"2px solid #22c55e" if ativo_ligar else "1px solid #22c55e40"};
                        border-radius:14px; padding:24px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                        <div style='font-size:36px; margin-bottom:8px;'>💧</div>
                        <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                            letter-spacing:2px; color:{"#22c55e" if ativo_ligar else COR_MUTED};'>LIGAR BOMBA 1</div>
                        <div class='barra-wrap' style='margin-top:14px;'>
                            <div class='{"barra-on" if ativo_ligar else "barra-inativa"}'></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("▶ LIGAR BOMBA 1", key="btn_ligar_b1", use_container_width=True):
                        # Envia 'ON' para energizar relé Active LOW no ESP32 (firmware v2.4+)
                        db.reference("controle/bomba1_comando").set("ON")
                        registrar_evento("LIGOU A BOMBA 1 (manual)")
                        st.rerun()

                with col2_b1:
                    ativo_desligar = not comando_b1_ligar
                    st.markdown(f"""
                    <div style='background:{"rgba(239,68,68,0.25)" if ativo_desligar else "rgba(239,68,68,0.05)"};
                        border:{"2px solid #ef4444" if ativo_desligar else "1px solid #ef444440"};
                        border-radius:14px; padding:24px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                        <div style='font-size:36px; margin-bottom:8px;'>⭕</div>
                        <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                            letter-spacing:2px; color:{"#ef4444" if ativo_desligar else COR_MUTED};'>DESLIGAR BOMBA 1</div>
                        <div class='barra-wrap' style='margin-top:14px;'>
                            <div class='{"barra-off" if ativo_desligar else "barra-inativa"}'></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("⏹ DESLIGAR BOMBA 1", key="btn_desligar_b1", use_container_width=True):
                        # Envia 'OFF' para desenergizar relé Active LOW no ESP32 (firmware v2.4+)
                        db.reference("controle/bomba1_comando").set("OFF")
                        registrar_evento("DESLIGOU A BOMBA 1 (manual)")
                        st.rerun()
            else:
                st.markdown("<div class='auto-info'>ℹ️ Modo Automático Selecionado. O controle manual direto está desabilitado na aba principal. Para alterar regras, utilize a aba MODO AUTOMÁTICO.</div>", unsafe_allow_html=True)

        # --- ABA BOMBA 2 ---
        with tab_b2:
            st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin:12px 0 8px 0;'>🔄 BOMBA 2 — EQUIPAMENTO DE RESERVA (STANDBY)</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:{COR_MUTED}; font-size:13px; margin-bottom:16px;'>Bomba reserva configurada para backup do sistema. Aguardando a perfuração do segundo poço para uso simultâneo.</div>", unsafe_allow_html=True)

            # Card de STATUS REAL DE OPERAÇÃO — reflete o contato auxiliar, não o botão.
            if not online:
                st.markdown(f"""
                <div style='text-align:center; margin-bottom:20px; padding:16px; border-radius:12px; border:2px solid #64748b; background:rgba(100,116,139,0.1);'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; letter-spacing:2px; color:#94a3b8;'>
                        📡 SEM COMUNICAÇÃO — STATUS INDISPONÍVEL
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                cor_b2 = "#22c55e" if b2_operando else "#ef4444"
                label_b2 = "● BOMBA 2 EM OPERAÇÃO" if b2_operando else "○ BOMBA 2 PARADA"
                bg_card_b2 = "rgba(34,197,94,0.18)" if b2_operando else "rgba(239,68,68,0.12)"

                st.markdown(f"""
                <div style='text-align:center; margin-bottom:20px; padding:16px; border-radius:12px; border:2px solid {cor_b2}; background:{bg_card_b2};'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; letter-spacing:2px; color:{cor_b2};'>
                        {label_b2}
                    </span><br>
                    <small style='color:{COR_MUTED2}; font-size:12px;'>Status real (contato auxiliar), independente do botão abaixo</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"<div style='color:{COR_MUTED}; font-size:12px; text-align:center; margin-bottom:10px;'>Último comando enviado: <b style='color:{COR_ACCENT};'>{'LIGAR' if comando_b2_ligar else 'DESLIGAR'}</b></div>", unsafe_allow_html=True)

            if modo == "MANUAL":
                col1_b2, col2_b2 = st.columns(2, gap="large")
                with col1_b2:
                    ativo_ligar_b2 = comando_b2_ligar
                    st.markdown(f"""
                    <div style='background:{"rgba(34,197,94,0.25)" if ativo_ligar_b2 else "rgba(34,197,94,0.05)"};
                        border:{"2px solid #22c55e" if ativo_ligar_b2 else "1px solid #22c55e40"};
                        border-radius:14px; padding:24px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                        <div style='font-size:36px; margin-bottom:8px;'>💧</div>
                        <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                            letter-spacing:2px; color:{"#22c55e" if ativo_ligar_b2 else COR_MUTED};'>LIGAR BOMBA 2</div>
                        <div class='barra-wrap' style='margin-top:14px;'>
                            <div class='{"barra-on" if ativo_ligar_b2 else "barra-inativa"}'></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("▶ LIGAR BOMBA 2", key="btn_ligar_b2", use_container_width=True):
                        # Envia 'ON' para energizar relé Active LOW no ESP32 (firmware v2.4+)
                        db.reference("controle/bomba2_comando").set("ON")
                        registrar_evento("LIGOU A BOMBA 2 (manual)")
                        st.rerun()

                with col2_b2:
                    ativo_desligar_b2 = not comando_b2_ligar
                    st.markdown(f"""
                    <div style='background:{"rgba(239,68,68,0.25)" if ativo_desligar_b2 else "rgba(239,68,68,0.05)"};
                        border:{"2px solid #ef4444" if ativo_desligar_b2 else "1px solid #ef444440"};
                        border-radius:14px; padding:24px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                        <div style='font-size:36px; margin-bottom:8px;'>⭕</div>
                        <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                            letter-spacing:2px; color:{"#ef4444" if ativo_desligar_b2 else COR_MUTED};'>DESLIGAR BOMBA 2</div>
                        <div class='barra-wrap' style='margin-top:14px;'>
                            <div class='{"barra-off" if ativo_desligar_b2 else "barra-inativa"}'></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("⏹ DESLIGAR BOMBA 2", key="btn_desligar_b2", use_container_width=True):
                        # Envia 'OFF' para desenergizar relé Active LOW no ESP32 (firmware v2.4+)
                        db.reference("controle/bomba2_comando").set("OFF")
                        registrar_evento("DESLIGOU A BOMBA 2 (manual)")
                        st.rerun()
            else:
                st.markdown("<div class='auto-info'>ℹ️ Modo Automático Selecionado. O controle manual direto está desabilitado na aba principal. Para alterar regras, utilize a aba MODO AUTOMÁTICO.</div>", unsafe_allow_html=True)

        # --- ABA MODO AUTOMÁTICO ---
        with tab_auto:
            st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin:12px 0 8px 0;'>🤖 CONFIGURAÇÃO DO MODO AUTOMÁTICO</div>", unsafe_allow_html=True)

            st.markdown("""
            <div class='auto-info'>🌊 <b>AUTOMÁTICO POR HARDWARE (BÓIA / SENSOR)</b> — No conceito de operação atual com 1 poço ativo, a Bomba 1 atua como principal. O backup por software monitora o nível e aciona o enchimento automaticamente quando necessário.</div>
            """, unsafe_allow_html=True)

            novo_auto = st.toggle(
                "🤖 Ativar automático por SOFTWARE (backup da bóia)",
                value=bool(auto_software_ativo),
                key="toggle_auto_software"
            )
            if novo_auto != auto_software_ativo:
                db.reference("controle/auto_software_ativo").set(novo_auto)
                registrar_evento("ATIVOU o automático por software" if novo_auto else "DESATIVOU o automático por software")
                st.rerun()

            # Le os limiares atuais do Firebase (valor salvo pelo admin) com fallback nos padroes
            try:
                bomba_liga_pct_atual = float(db.reference("controle/bomba_liga_pct").get() or BOMBA_LIGA_PCT)
                bomba_desliga_pct_atual = float(db.reference("controle/bomba_desliga_pct").get() or BOMBA_DESLIGA_PCT)
            except:
                bomba_liga_pct_atual = float(BOMBA_LIGA_PCT)
                bomba_desliga_pct_atual = float(BOMBA_DESLIGA_PCT)

            if novo_auto:
                st.markdown(f"""
                <div class='diag-info-row'>
                    <span>📉</span><span class='diag-info-label'>Liga a bomba abaixo de:</span><span><b>{bomba_liga_pct_atual:.0f}%</b> do reservatório</span>
                </div>
                <div class='diag-info-row'>
                    <span>📈</span><span class='diag-info-label'>Desliga a bomba acima de:</span><span><b>{bomba_desliga_pct_atual:.0f}%</b> do reservatório</span>
                </div>
                <div class='diag-info-row'>
                    <span>🛡️</span><span class='diag-info-label'>Proteção de poço seco:</span><span>ATIVA (não liga se poço BAIXO)</span>
                </div>
                <div class='diag-info-row'>
                    <span>🚰</span><span class='diag-info-label'>Bomba de Operação:</span><span>Bomba 1 (Principal) | Bomba 2 (Reserva)</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{COR_MUTED}; text-align:center; padding:12px;'>Automático por software desligado — controle via comando manual ou bóia do painel.</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- Ajuste dos limiares: SOMENTE ADMIN (item 05) ---
            if st.session_state["is_admin"]:
                st.markdown(f"""
                <div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:700; letter-spacing:2px;
                    color:{COR_TITULO}; margin-bottom:10px;'>⚙️ AJUSTAR PARÂMETROS (SOMENTE ADMINISTRADOR)</div>
                """, unsafe_allow_html=True)
                col_p1, col_p2 = st.columns(2, gap="medium")
                with col_p1:
                    novo_liga = st.number_input(
                        "Liga a bomba abaixo de (%)", min_value=0, max_value=100,
                        value=int(bomba_liga_pct_atual), step=1, key="input_liga_pct"
                    )
                with col_p2:
                    novo_desliga = st.number_input(
                        "Desliga a bomba acima de (%)", min_value=0, max_value=100,
                        value=int(bomba_desliga_pct_atual), step=1, key="input_desliga_pct"
                    )
                if st.button("💾 SALVAR PARÂMETROS", use_container_width=True, key="btn_salvar_pct"):
                    if novo_liga >= novo_desliga:
                        st.error("O valor de 'Liga abaixo de' precisa ser menor que 'Desliga acima de'.")
                    else:
                        db.reference("controle/bomba_liga_pct").set(float(novo_liga))
                        db.reference("controle/bomba_desliga_pct").set(float(novo_desliga))
                        registrar_evento(f"Alterou parâmetros do automático: liga={novo_liga}% / desliga={novo_desliga}%")
                        st.success("Parâmetros atualizados. O ESP32 vai aplicar o novo limiar no próximo ciclo (poucos segundos).")
                        st.rerun()
            else:
                st.markdown(f"""
                <div style='background:rgba(100,116,139,0.08); border:1px solid rgba(100,116,139,0.3);
                    border-radius:10px; padding:14px 18px; text-align:center; color:{COR_MUTED}; font-size:13px;'>
                    🔒 Ajuste dos parâmetros de liga/desliga automático disponível apenas para o Administrador Master.
                </div>
                """, unsafe_allow_html=True)

    # ─── NÍVEL DO RESERVATÓRIO ──────────────────────────────────────────────
    elif menu == "💧 Nível do Reservatório":
        st.markdown("<div class='section-header'>Nível do Reservatório · 30.000 L</div>", unsafe_allow_html=True)

        altura_m, volume_l, percentual, falha_sensor, ultimo_pulso, nivel_poco = None, None, None, False, None, "OK"

        try:
            res = db.reference("reservatorio").get()

            if isinstance(res, dict) and res and not any(k in res for k in ["nivel_metros", "percentual", "volume_litros"]):
                chaves = list(res.keys())
                res = res[chaves[-1]] if isinstance(res[chaves[-1]], dict) else res

            if not res:
                res = db.reference("sensor").get() or {}

            if isinstance(res, dict):
                altura_m = res.get("nivel_metros") or res.get("nivel") or res.get("altura")
                volume_l = res.get("volume_litros") or res.get("volume")
                percentual = res.get("percentual") or res.get("pct") or res.get("nivel_pct")
                falha_sensor = res.get("falha_sensor", False)
                ultimo_pulso = res.get("ultimo_pulso") or res.get("timestamp")
                nivel_poco = res.get("nivel_poco", "OK")

                if altura_m is not None:
                    altura_m = float(altura_m)
                    if percentual is None:
                        percentual = (altura_m / ALTURA_MAXIMA_M) * 100.0
                    if volume_l is None:
                        volume_l = (percentual / 100.0) * CAPACIDADE_LITROS

        except Exception as e:
            st.error(f"Erro na leitura dos dados: {e}")

        dado_disponivel = (percentual is not None or altura_m is not None)
        dado_fresco = checar_dado_fresco(ultimo_pulso, tolerancia_segundos=60)

        altura_exibir = float(altura_m) if altura_m is not None else None
        volume_exibir = float(volume_l) if volume_l is not None else None
        pct_exibir = float(percentual) if percentual is not None else None

        pct_barra_nivel = min(max(pct_exibir or 0, 0), 100) if pct_exibir is not None else 0
        pct_barra_volume = min(max(((volume_exibir or 0) / CAPACIDADE_LITROS) * 100, 0), 100) if volume_exibir is not None else 0

        # Alerta de poço seco na aba de medição também
        if nivel_poco == "BAIXO":
            st.markdown("""
            <div style='background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.4);
                border-radius:10px; padding:14px 20px; margin-bottom:20px; text-align:center;
                color:#f59e0b; font-size:14px; font-weight:600; letter-spacing:1px;'>
                ⚠️ NÍVEL DO POÇO BAIXO — Abastecimento do poço comprometido. As bombas estão protegidas.
            </div>
            """, unsafe_allow_html=True)

        if dado_disponivel and not dado_fresco:
            st.markdown("""
            <div style='background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.4);
                border-radius:10px; padding:14px 20px; margin-bottom:20px; text-align:center;
                color:#ef4444; font-size:14px; font-weight:600; letter-spacing:1px;'>
                ⚠️ ATENÇÃO: Dispositivo sem comunicação recente — dados podem estar desatualizados.
            </div>
            """, unsafe_allow_html=True)

        if falha_sensor:
            st.markdown("""
            <div style='background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.4);
                border-radius:10px; padding:14px 20px; margin-bottom:20px; text-align:center;
                color:#ef4444; font-size:14px; font-weight:600; letter-spacing:1px;'>
                ⚠️ FALHA NO SENSOR — cabo rompido ou perda de sinal. Verifique a fiação do sensor hidrostático.
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2, gap="large")

        with col1:
            valor_pct = f"{pct_exibir:.0f}" if pct_exibir is not None else "—"
            st.markdown(f"""
            <div class='gauge-card'>
                <div class='gauge-label'>Nível do Reservatório</div>
                <div class='gauge-value' style='color:{COR_ACCENT};'>{valor_pct}</div>
                <div class='gauge-unit'>%</div>
                <div class='gauge-bar-bg'>
                    <div class='gauge-bar-fill gauge-nivel-fill' style='width:{pct_barra_nivel}%;'></div>
                </div>
                <div class='gauge-meta'>Coluna d'água: {f"{altura_exibir:.2f} m" if altura_exibir is not None else "—"} de {ALTURA_MAXIMA_M:.2f} m</div>
                <div class='{"dado-fresco" if dado_fresco else "dado-antigo"}'>
                    {"✔ Dado em tempo real" if dado_fresco else "✘ Sem leitura recente"}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            valor_vol = f"{volume_exibir:,.0f}".replace(",", ".") if volume_exibir is not None else "—"
            st.markdown(f"""
            <div class='gauge-card'>
                <div class='gauge-label'>Volume Armazenado</div>
                <div class='gauge-value' style='color:#06b6d4;'>{valor_vol}</div>
                <div class='gauge-unit'>litros</div>
                <div class='gauge-bar-bg'>
                    <div class='gauge-bar-fill gauge-volume-fill' style='width:{pct_barra_volume}%;'></div>
                </div>
                <div class='gauge-meta'>Capacidade total: {CAPACIDADE_LITROS:,.0f} L</div>
                <div class='{"dado-fresco" if dado_fresco else "dado-antigo"}'>
                    {"✔ Dado em tempo real" if dado_fresco else "✘ Sem leitura recente"}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if ultimo_pulso:
            try:
                segundos_atras = int((time.time() * 1000 - float(ultimo_pulso)) / 1000)
                if segundos_atras < 60:
                    tempo_str = f"há {segundos_atras}s"
                elif segundos_atras < 3600:
                    tempo_str = f"há {segundos_atras//60}min"
                else:
                    tempo_str = f"há {segundos_atras//3600}h"
                st.markdown(f"<div style='text-align:center; color:{COR_MUTED}; font-size:12px; letter-spacing:1px;'>Último sinal do dispositivo: <b style='color:{COR_MUTED2};'>{tempo_str}</b></div>", unsafe_allow_html=True)
            except:
                st.markdown(f"<div style='text-align:center; color:{COR_MUTED}; font-size:12px;'>Não foi possível calcular o tempo do último sinal.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center; color:#ef4444; font-size:12px;'>Nenhum sinal recebido do dispositivo.</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn = st.columns([1, 2, 1])
        with col_btn[1]:
            if st.button("🔄 ATUALIZAR AGORA", use_container_width=True):
                if altura_m is not None:
                    try:
                        db.reference("historico_sensores").push({
                            "altura_m": altura_m, "volume_l": volume_l, "percentual": percentual,
                            "data": obter_hora_brasilia().strftime('%H:%M:%S')
                        })
                    except: pass
                st.rerun()

    # ─── RELATÓRIOS ─────────────────────────────────────────────────────────
    elif menu == "📊 Relatórios":
        st.markdown("<div class='section-header'>Relatórios</div>", unsafe_allow_html=True)

        def _ts_para_datahora(ts):
            try:
                return datetime.fromtimestamp(float(ts) / 1000, pytz.timezone('America/Sao_Paulo'))
            except (TypeError, ValueError):
                return None

        def carregar_pontos_nivel(data_alvo, cache_pontos):
            linhas = []
            for v in cache_pontos.values():
                dt = _ts_para_datahora(v.get("data"))
                if dt is not None and dt.date() == data_alvo:
                    linhas.append({
                        "horario": dt,
                        "percentual": v.get("percentual"),
                        "volume_litros": v.get("volume_litros"),
                        "bomba1_status": v.get("bomba1_status", "—"),
                        "bomba2_status": v.get("bomba2_status", "—"),
                        "nivel_poco": v.get("nivel_poco", "—"),
                    })
            linhas.sort(key=lambda x: x["horario"])
            return linhas

        def calcular_consumo_litros(linhas):
            consumo = 0.0
            for i in range(1, len(linhas)):
                v_ant = linhas[i - 1]["volume_litros"]
                v_atu = linhas[i]["volume_litros"]
                if v_ant is not None and v_atu is not None and v_ant > v_atu:
                    consumo += (v_ant - v_atu)
            return consumo

        def carregar_eventos_bomba(data_alvo, cache_eventos, bomba_filtro=None):
            eventos = []
            for v in cache_eventos.values():
                dt = _ts_para_datahora(v.get("data"))
                if dt is not None and dt.date() == data_alvo:
                    bomba = v.get("bomba", "B1")  # fallback para compatibilidade antiga
                    if bomba_filtro is None or bomba == bomba_filtro:
                        eventos.append({"horario": dt, "evento": v.get("evento"), "bomba": bomba})
            eventos.sort(key=lambda x: x["horario"])
            return eventos

        def calcular_acionamentos(eventos, data_alvo):
            num_ligou = sum(1 for e in eventos if e["evento"] == "LIGOU")
            tempo_ligada_seg = 0.0
            inicio_on = None
            for e in eventos:
                if e["evento"] == "LIGOU":
                    inicio_on = e["horario"]
                elif e["evento"] == "DESLIGOU" and inicio_on is not None:
                    tempo_ligada_seg += (e["horario"] - inicio_on).total_seconds()
                    inicio_on = None
            if inicio_on is not None:
                agora_local = datetime.now(pytz.timezone('America/Sao_Paulo'))
                if data_alvo == agora_local.date():
                    fim_ref = agora_local
                else:
                    fim_ref = pytz.timezone('America/Sao_Paulo').localize(
                        datetime.combine(data_alvo, datetime.max.time())
                    )
                tempo_ligada_seg += (fim_ref - inicio_on).total_seconds()
            return num_ligou, tempo_ligada_seg / 3600.0

        # ── BALANÇO DE MASSA: vazão real calibrada + consumo estimado ──────
        # Em vez de fixar um horário (ex: madrugada), o sistema procura sozinho,
        # todo dia, a MAIOR janela contínua em que a bomba ficou ligada e o nível
        # só subiu (sem nenhuma queda) — isso é 100% água entrando, sem consumo
        # simultâneo, não importa em que horário do dia isso aconteça. Assim o
        # sistema se adapta automaticamente ao horário real de enchimento (ex:
        # 18h-22h) e continua funcionando mesmo se esse horário mudar no futuro.
        TOLERANCIA_RUIDO_LITROS = 50  # pequena folga p/ ruido do sensor nao quebrar a janela
        FRACAO_MINIMA_BOMBA_LIGADA = 0.95  # bomba precisa estar ligada quase o intervalo todo
        HORAS_MINIMAS_CALIBRACAO = 1.0     # janela minima p/ confiar na medicao

        def segundos_ligada_intervalo(cache_eventos, bomba, inicio_dt, fim_dt):
            """Tempo (segundos) que a bomba ficou ligada dentro de [inicio_dt, fim_dt),
            considerando corretamente o estado que ela já vinha antes da janela."""
            eventos_todos = []
            for v in cache_eventos.values():
                if v.get("bomba", "B1") != bomba:
                    continue
                dt = _ts_para_datahora(v.get("data"))
                if dt is not None:
                    eventos_todos.append((dt, v.get("evento")))
            eventos_todos.sort(key=lambda x: x[0])

            estado_ligado = False
            for dt, ev in eventos_todos:
                if dt <= inicio_dt:
                    estado_ligado = (ev == "LIGOU")
                else:
                    break

            segundos = 0.0
            cursor = inicio_dt
            for dt, ev in eventos_todos:
                if dt <= inicio_dt:
                    continue
                if dt >= fim_dt:
                    break
                if estado_ligado:
                    segundos += (dt - cursor).total_seconds()
                cursor = dt
                estado_ligado = (ev == "LIGOU")
            if estado_ligado:
                segundos += (fim_dt - cursor).total_seconds()
            return segundos

        def calcular_vazao_calibrada_lph(data_alvo, cache_pontos, cache_eventos):
            """Mede a vazao real do poco (L/h) achando automaticamente a maior janela
            do dia em que a bomba ficou ligada e o nivel so subiu (enchimento puro,
            sem consumo simultaneo). Retorna None se nao houver janela confiavel,
            ou um dicionario com detalhes da janela encontrada."""
            pontos_dia = carregar_pontos_nivel(data_alvo, cache_pontos)
            if len(pontos_dia) < 2:
                return None

            melhor_dv, melhor_horas = 0.0, 0.0
            melhor_inicio, melhor_fim = None, None
            run_dv, run_horas = 0.0, 0.0
            run_inicio = None

            for i in range(1, len(pontos_dia)):
                p_ant, p_atu = pontos_dia[i - 1], pontos_dia[i]
                v_ant, v_atu = p_ant["volume_litros"], p_atu["volume_litros"]
                dt_ant, dt_atu = p_ant["horario"], p_atu["horario"]
                dur_seg = (dt_atu - dt_ant).total_seconds()

                seg_qualifica = False
                dv = None
                if v_ant is not None and v_atu is not None and dur_seg > 0:
                    dv = v_atu - v_ant
                    seg_on = segundos_ligada_intervalo(cache_eventos, "B1", dt_ant, dt_atu)
                    frac_on = seg_on / dur_seg
                    if dv >= -TOLERANCIA_RUIDO_LITROS and frac_on >= FRACAO_MINIMA_BOMBA_LIGADA:
                        seg_qualifica = True

                if seg_qualifica:
                    if run_horas == 0.0:
                        run_inicio = dt_ant
                    run_dv += max(dv, 0.0)
                    run_horas += dur_seg / 3600.0
                    if run_horas > melhor_horas:
                        melhor_dv, melhor_horas = run_dv, run_horas
                        melhor_inicio, melhor_fim = run_inicio, dt_atu
                else:
                    run_dv, run_horas, run_inicio = 0.0, 0.0, None

            if melhor_horas < HORAS_MINIMAS_CALIBRACAO or melhor_dv <= 0:
                return None

            return {
                "vazao_lph": melhor_dv / melhor_horas,
                "horas": melhor_horas,
                "litros": melhor_dv,
                "inicio": melhor_inicio.strftime("%H:%M") if melhor_inicio else "",
                "fim": melhor_fim.strftime("%H:%M") if melhor_fim else "",
            }

        def calcular_perfil_consumo_intervalo(linhas_dia, cache_eventos, vazao_lph):
            """Decompoe o consumo em cada intervalo de 30min do dia, mesmo quando a
            bomba esta enchendo ao mesmo tempo, usando a vazao ja calibrada:
            consumo_intervalo = (horas_ligada_no_intervalo x vazao) - variacao_real_medida.
            Retorna uma lista de {horario, consumo_litros} para plotar o perfil do dia."""
            perfil = []
            for i in range(1, len(linhas_dia)):
                p_ant, p_atu = linhas_dia[i - 1], linhas_dia[i]
                v_ant, v_atu = p_ant["volume_litros"], p_atu["volume_litros"]
                if v_ant is None or v_atu is None:
                    continue
                dv_medido = v_atu - v_ant
                seg_on = segundos_ligada_intervalo(cache_eventos, "B1", p_ant["horario"], p_atu["horario"])
                agua_entrada = (seg_on / 3600.0) * vazao_lph
                consumo_intervalo = agua_entrada - dv_medido
                perfil.append({
                    "horario": p_atu["horario"],
                    "consumo_litros": max(consumo_intervalo, 0.0)
                })
            return perfil

        try:
            cache_pontos_nivel = db.reference("historico_sensores").get() or {}
        except Exception:
            cache_pontos_nivel = {}
        try:
            cache_eventos_bomba = db.reference("historico_bomba").get() or {}
        except Exception:
            cache_eventos_bomba = {}

        # ── CONSUMO DE ÁGUA ──────────────────────────────────────────────
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin-bottom:16px;'>💧 CONSUMO DE ÁGUA</div>", unsafe_allow_html=True)

        data_selecionada = st.date_input("Selecione o dia", value=obter_hora_brasilia().date())

        linhas_dia = carregar_pontos_nivel(data_selecionada, cache_pontos_nivel)

        if not linhas_dia:
            st.markdown(f"""
            <div style='color:{COR_MUTED}; padding:20px; text-align:center; border:1px dashed {COR_BORDA}; border-radius:10px;'>
                Nenhum registro automático de nível para este dia ainda.
                O ESP32 grava um ponto a cada 30 minutos — aguarde o primeiro ciclo.
            </div>
            """, unsafe_allow_html=True)
        else:
            consumo_litros = calcular_consumo_litros(linhas_dia)
            eventos_b1 = carregar_eventos_bomba(data_selecionada, cache_eventos_bomba, "B1")
            eventos_b2 = carregar_eventos_bomba(data_selecionada, cache_eventos_bomba, "B2")
            num_ac_b1, horas_b1 = calcular_acionamentos(eventos_b1, data_selecionada)
            num_ac_b2, horas_b2 = calcular_acionamentos(eventos_b2, data_selecionada)
            total_horas = horas_b1 + horas_b2

            # Vazão Oficial (medida manualmente, teste de balde) - buscada aqui em cima
            # para já podermos mostrar "tempo ligado × vazão" ao lado do consumo simples.
            try:
                vazao_oficial = float(db.reference("controle/vazao_poco_lph").get() or 6500.0)
            except:
                vazao_oficial = 6500.0
            agua_bombeada_simples = total_horas * vazao_oficial

            m1, m2, m3, m4, m5 = st.columns(5, gap="medium")
            with m1:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Consumo (método simples)</div>
                    <div class='gauge-value' style='color:#06b6d4; font-size:48px;'>{consumo_litros:,.0f}</div>
                    <div class='gauge-unit'>litros no dia</div>
                </div>
                """.replace(",", "."), unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Água Bombeada (tempo × vazão)</div>
                    <div class='gauge-value' style='color:#f59e0b; font-size:40px;'>{agua_bombeada_simples:,.0f}</div>
                    <div class='gauge-unit'>litros — {total_horas:.1f}h × {vazao_oficial:,.0f} L/h</div>
                </div>
                """.replace(",", "."), unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Acionamentos B1</div>
                    <div class='gauge-value' style='color:{COR_ACCENT}; font-size:48px;'>{num_ac_b1}</div>
                    <div class='gauge-unit'>vezes ligou no dia</div>
                </div>
                """, unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Acionamentos B2</div>
                    <div class='gauge-value' style='color:#a855f7; font-size:48px;'>{num_ac_b2}</div>
                    <div class='gauge-unit'>vezes ligou no dia</div>
                </div>
                """, unsafe_allow_html=True)
            with m5:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Tempo Ligadas</div>
                    <div class='gauge-value' style='color:#22c55e; font-size:48px;'>{total_horas:.1f}</div>
                    <div class='gauge-unit'>horas no dia (B1+B2)</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Consumo por balanço de massa (mais preciso) ──────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:700; letter-spacing:2px;
                color:{COR_TITULO}; margin-bottom:10px;'>⚖️ CONSUMO POR BALANÇO (mais preciso — considera bomba e consumo simultâneos)</div>
            """, unsafe_allow_html=True)

            resultado_calibracao = calcular_vazao_calibrada_lph(data_selecionada, cache_pontos_nivel, cache_eventos_bomba)
            vazao_auto_detectada = resultado_calibracao["vazao_lph"] if resultado_calibracao else None

            # Grava a auto-detecção num node próprio (nao afetado pelos botoes de apagar
            # historico), so para consulta/comparacao - NAO alimenta mais o calculo principal.
            if resultado_calibracao:
                try:
                    db.reference(f"calibracao_vazao_diaria/{data_selecionada.isoformat()}").set({
                        "data": data_selecionada.isoformat(),
                        "vazao_lph": round(resultado_calibracao["vazao_lph"], 1),
                        "horas_janela": round(resultado_calibracao["horas"], 2),
                        "litros_janela": round(resultado_calibracao["litros"], 1),
                        "janela_inicio": resultado_calibracao["inicio"],
                        "janela_fim": resultado_calibracao["fim"],
                    })
                except:
                    pass

            # Vazão OFICIAL já foi buscada mais acima (usada também no card "Água Bombeada"
            # ao lado do consumo simples). Reaproveitamos aqui para o cálculo do balanço.
            vazao_usada = vazao_oficial

            volume_inicio_dia = linhas_dia[0]["volume_litros"]
            volume_fim_dia = linhas_dia[-1]["volume_litros"]

            if volume_inicio_dia is not None and volume_fim_dia is not None:
                agua_bombeada = total_horas * vazao_usada
                consumo_balanco = agua_bombeada + volume_inicio_dia - volume_fim_dia

                cb1, cb2, cb3 = st.columns(3, gap="medium")
                with cb1:
                    st.markdown(f"""
                    <div class='gauge-card'>
                        <div class='gauge-label'>Vazão Oficial Usada</div>
                        <div class='gauge-value' style='color:#f59e0b; font-size:40px;'>{vazao_usada:,.0f}</div>
                        <div class='gauge-unit'>L/h — configurada manualmente (teste de balde)</div>
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)
                with cb2:
                    st.markdown(f"""
                    <div class='gauge-card'>
                        <div class='gauge-label'>Água Bombeada no Dia</div>
                        <div class='gauge-value' style='color:#3b82f6; font-size:40px;'>{agua_bombeada:,.0f}</div>
                        <div class='gauge-unit'>litros (tempo ligada × vazão)</div>
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)
                with cb3:
                    st.markdown(f"""
                    <div class='gauge-card'>
                        <div class='gauge-label'>Consumo Real (balanço)</div>
                        <div class='gauge-value' style='color:#22c55e; font-size:40px;'>{consumo_balanco:,.0f}</div>
                        <div class='gauge-unit'>litros no dia</div>
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)

                st.markdown(f"""
                <div style='color:{COR_MUTED}; font-size:12px; text-align:center; margin-top:8px;'>
                    Fórmula: (horas ligada × vazão oficial) + nível início do dia − nível fim do dia.
                    A vazão oficial é o valor que você mediu e configurou manualmente (teste de balde) — não muda sozinha.
                </div>
                """, unsafe_allow_html=True)

                # Comparação (informativa) com a auto-detecção pelo sistema, para você
                # acompanhar se o poço está perdendo vazão com o tempo. NÃO entra no cálculo.
                if vazao_auto_detectada is not None:
                    diferenca_pct = ((vazao_auto_detectada - vazao_oficial) / vazao_oficial) * 100 if vazao_oficial else 0
                    st.markdown(f"""
                    <div style='background:rgba(100,116,139,0.08); border:1px solid rgba(100,116,139,0.25);
                        border-radius:10px; padding:12px 18px; margin-top:12px; text-align:center; font-size:13px; color:{COR_MUTED};'>
                        🔍 <b>Comparação (só informativo, não entra na conta):</b> o sistema detectou sozinho uma janela de
                        enchimento hoje ({resultado_calibracao['inicio']}–{resultado_calibracao['fim']}) com vazão de
                        <b style='color:{COR_TITULO};'>{vazao_auto_detectada:,.0f} L/h</b>
                        ({'+' if diferenca_pct >= 0 else ''}{diferenca_pct:.0f}% em relação à oficial).
                        Se essa diferença crescer com o tempo, pode indicar que o poço está perdendo vazão.
                    </div>
                    """.replace(",", "."), unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background:rgba(100,116,139,0.08); border:1px solid rgba(100,116,139,0.25);
                        border-radius:10px; padding:12px 18px; margin-top:12px; text-align:center; font-size:13px; color:{COR_MUTED};'>
                        🔍 O sistema não conseguiu detectar sozinho uma janela de enchimento confiável hoje para comparar
                        (normal enquanto o feedback físico das bombas não estiver conectado). Isso não afeta o cálculo acima,
                        que usa só a vazão oficial configurada manualmente.
                    </div>
                    """, unsafe_allow_html=True)

                # ── Perfil de consumo ao longo do dia (mesmo em horário comercial) ──
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:700; letter-spacing:2px;
                    color:{COR_TITULO}; margin-bottom:6px;'>📊 PERFIL DE CONSUMO AO LONGO DO DIA (estimado)</div>
                <div style='color:{COR_MUTED}; font-size:12px; margin-bottom:12px;'>
                    Usa a vazão oficial para separar consumo de enchimento em cada intervalo de 30min,
                    revelando os horários de pico de demanda da lavanderia, mesmo durante o expediente.
                </div>
                """, unsafe_allow_html=True)

                perfil_consumo = calcular_perfil_consumo_intervalo(linhas_dia, cache_eventos_bomba, vazao_usada)
                if perfil_consumo:
                    df_perfil = pd.DataFrame(perfil_consumo).set_index("horario")
                    st.bar_chart(df_perfil["consumo_litros"])
                    pico = df_perfil["consumo_litros"].idxmax()
                    st.markdown(f"<div style='color:{COR_MUTED}; font-size:12px; text-align:center;'>Horário de maior consumo no dia: <b style='color:{COR_TITULO};'>{pico.strftime('%H:%M')}</b> (~{df_perfil['consumo_litros'].max():,.0f} L no intervalo)</div>".replace(",", "."), unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color:{COR_MUTED}; text-align:center;'>Sem dados suficientes para montar o perfil deste dia.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{COR_MUTED}; text-align:center; padding:12px;'>Dados insuficientes para o balanço neste dia.</div>", unsafe_allow_html=True)

            # ── Histórico de calibrações de vazão (para consulta/envio) ──
            with st.expander("📜 Ver histórico de vazões medidas (por dia)"):
                try:
                    cache_calibracao = db.reference("calibracao_vazao_diaria").get() or {}
                except:
                    cache_calibracao = {}

                if cache_calibracao:
                    linhas_calib = sorted(cache_calibracao.values(), key=lambda x: x.get("data", ""), reverse=True)
                    df_calib = pd.DataFrame(linhas_calib)
                    st.dataframe(df_calib, use_container_width=True, hide_index=True)
                    csv_calib = df_calib.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Exportar histórico de vazões (CSV)",
                        data=csv_calib,
                        file_name=f"vazoes_medidas_{obter_hora_brasilia().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_calibracao_vazao"
                    )
                else:
                    st.markdown(f"<div style='color:{COR_MUTED}; text-align:center; padding:12px;'>Ainda não há medições de vazão registradas.</div>", unsafe_allow_html=True)

            if st.session_state["is_admin"]:
                with st.expander("⚙️ Vazão Oficial do Poço (medida com teste de balde)"):
                    st.markdown(f"""
                    <div style='color:{COR_MUTED}; font-size:13px; margin-bottom:14px;'>
                        Meça com um balde de volume conhecido: cronometre quantos segundos o poço leva para enchê-lo.
                        Esse valor vira a <b>Vazão Oficial</b>, usada em todos os cálculos de consumo — não depende
                        do feedback do contator, então continua confiável mesmo antes da fiação real estar conectada.
                    </div>
                    """, unsafe_allow_html=True)

                    col_bd1, col_bd2 = st.columns(2, gap="medium")
                    with col_bd1:
                        litros_balde = st.number_input(
                            "Volume do balde (litros)", min_value=1, max_value=1000,
                            value=20, step=1, key="input_litros_balde"
                        )
                    with col_bd2:
                        segundos_balde = st.number_input(
                            "Tempo para encher o balde (segundos)", min_value=1, max_value=3600,
                            value=10, step=1, key="input_segundos_balde"
                        )
                    vazao_calculada_balde = (litros_balde / segundos_balde) * 3600
                    st.markdown(f"""
                    <div style='text-align:center; font-family:Rajdhani,sans-serif; font-size:22px; font-weight:700;
                        color:{COR_ACCENT}; margin:10px 0;'>Vazão calculada: {vazao_calculada_balde:,.0f} L/h</div>
                    """.replace(",", "."), unsafe_allow_html=True)
                    if st.button("💾 Salvar como Vazão Oficial", use_container_width=True, key="btn_salvar_vazao_balde"):
                        db.reference("controle/vazao_poco_lph").set(float(vazao_calculada_balde))
                        registrar_evento(f"Atualizou a Vazão Oficial do poço para {vazao_calculada_balde:.0f} L/h (teste de balde)")
                        st.success("Vazão Oficial atualizada.")
                        st.rerun()

                    st.markdown("<hr style='opacity:0.15; margin:18px 0;'>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color:{COR_MUTED}; font-size:13px; margin-bottom:8px;'>Ou, se já souber o valor, digite direto:</div>", unsafe_allow_html=True)
                    novo_valor_direto = st.number_input(
                        "Vazão Oficial (L/h)", min_value=0, max_value=50000,
                        value=int(vazao_oficial), step=100, key="input_vazao_direta"
                    )
                    if st.button("💾 Salvar valor direto", use_container_width=True, key="btn_salvar_vazao_direta"):
                        db.reference("controle/vazao_poco_lph").set(float(novo_valor_direto))
                        registrar_evento(f"Atualizou a Vazão Oficial do poço para {novo_valor_direto} L/h (valor direto)")
                        st.success("Vazão Oficial atualizada.")
                        st.rerun()


            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:{COR_MUTED2}; font-size:13px; margin-bottom:8px;'>Nível do reservatório (%) ao longo do dia — subidas = bomba enchendo, descidas = consumo</div>", unsafe_allow_html=True)

            df_dia = pd.DataFrame(linhas_dia).set_index("horario")
            st.line_chart(df_dia["percentual"])

            csv_bytes = pd.DataFrame(linhas_dia).to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Exportar CSV do dia",
                data=csv_bytes,
                file_name=f"consumo_lavanderia_exata_{data_selecionada.isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ── COMPARATIVO 7 DIAS ──────────────────────────────────────────
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin-bottom:16px;'>📅 COMPARATIVO — ÚLTIMOS 7 DIAS</div>", unsafe_allow_html=True)

        hoje = obter_hora_brasilia().date()
        dias_semana = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
        consumo_por_dia = {}
        for d in dias_semana:
            linhas_d = carregar_pontos_nivel(d, cache_pontos_nivel)
            consumo_por_dia[d] = calcular_consumo_litros(linhas_d)

        if any(consumo_por_dia.values()):
            df_semana = pd.DataFrame({
                "dia": [d.strftime("%d/%m") for d in dias_semana],
                "litros consumidos": [consumo_por_dia[d] for d in dias_semana],
            }).set_index("dia")
            st.bar_chart(df_semana)
            media_semana = sum(consumo_por_dia.values()) / len(consumo_por_dia)
            st.markdown(f"<div style='text-align:center; color:{COR_MUTED}; font-size:13px;'>Média diária na semana: <b style='color:{COR_TITULO};'>{media_semana:,.0f} L</b></div>".replace(",", "."), unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color:{COR_MUTED}; padding:20px; text-align:center;'>Ainda não há histórico suficiente para o comparativo semanal.</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ── HISTÓRICO DE AÇÕES ─────────────────────────────────────────
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; color:{COR_TITULO}; letter-spacing:2px; margin-bottom:16px;'>📝 HISTÓRICO DE AÇÕES</div>", unsafe_allow_html=True)

        if st.session_state["is_admin"]:
            with st.expander("⚠️ Zona de risco: apagar históricos (somente admin)"):
                st.markdown(f"""
                <div style='color:#ef4444; font-size:13px; margin-bottom:12px;'>
                    Atenção: cada botão abaixo apaga <b>permanentemente</b> só a categoria indicada.
                    Isso NÃO afeta usuários cadastrados nem o status atual do sistema.
                    Baixe o backup em JSON antes de apagar, caso queira guardar os dados.
                </div>
                """, unsafe_allow_html=True)

                categorias_historico = {
                    "historico_sensores": "📈 Histórico de Nível (leituras do reservatório)",
                    "historico_bomba": "🔌 Histórico de Acionamento das Bombas",
                    "historico_acoes": "📝 Histórico de Ações dos Usuários",
                }

                for chave_no_firebase, titulo_categoria in categorias_historico.items():
                    st.markdown(f"**{titulo_categoria}**")
                    col_bkp, col_chk, col_del = st.columns([1, 1.4, 1])
                    with col_bkp:
                        try:
                            dados_categoria = db.reference(chave_no_firebase).get() or {}
                        except:
                            dados_categoria = {}
                        import json as _json
                        st.download_button(
                            "⬇️ Backup (.json)",
                            data=_json.dumps(dados_categoria, ensure_ascii=False, indent=2).encode("utf-8"),
                            file_name=f"{chave_no_firebase}_{obter_hora_brasilia().strftime('%Y%m%d_%H%M')}.json",
                            mime="application/json",
                            use_container_width=True,
                            key=f"backup_{chave_no_firebase}"
                        )
                    with col_chk:
                        confirma = st.checkbox(
                            "Já fiz backup, apagar mesmo assim",
                            key=f"confirma_{chave_no_firebase}"
                        )
                    with col_del:
                        if st.button("🗑️ Apagar", use_container_width=True, key=f"apagar_{chave_no_firebase}", disabled=not confirma):
                            try:
                                db.reference(chave_no_firebase).delete()
                                registrar_evento(f"Apagou o histórico: {titulo_categoria}")
                                st.success(f"{titulo_categoria} apagado.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao apagar: {e}")
                    st.markdown("<hr style='opacity:0.15;'>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        try:
            logs = db.reference("historico_acoes").get()
        except:
            logs = None

        if logs:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            for k in reversed(list(logs.keys())):
                v = logs[k]
                st.markdown(f"""
                <div class='msg-balao'>
                    <b>{v.get("usuario","?")}</b>: {v.get("acao","?")} 
                    <br><small>🕐 {v.get("data","")}</small>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; color:{COR_MUTED}; padding:40px;'>Nenhum registro encontrado.</div>", unsafe_allow_html=True)

    # ─── DIAGNÓSTICO ────────────────────────────────────────────────────────
    elif menu == "🛠️ Diagnóstico":
        st.markdown("<div class='section-header'>Diagnóstico do Sistema</div>", unsafe_allow_html=True)

        try:
            res_diag = db.reference("reservatorio").get() or {}
            if isinstance(res_diag, dict) and res_diag and not any(k in res_diag for k in ["nivel_metros", "percentual", "ultimo_pulso"]):
                chaves = list(res_diag.keys())
                res_diag = res_diag[chaves[-1]] if isinstance(res_diag[chaves[-1]], dict) else res_diag

            ultimo_p = res_diag.get("ultimo_pulso") if isinstance(res_diag, dict) else None
            status_b1 = res_diag.get("bomba1_status", "—") if isinstance(res_diag, dict) else "—"
            status_b2 = res_diag.get("bomba2_status", "—") if isinstance(res_diag, dict) else "—"
            cmd_b1 = res_diag.get("bomba1_comando", "—") if isinstance(res_diag, dict) else "—"
            cmd_b2 = res_diag.get("bomba2_comando", "—") if isinstance(res_diag, dict) else "—"
            nivel_poco = res_diag.get("nivel_poco", "—") if isinstance(res_diag, dict) else "—"
        except Exception as e:
            st.error(f"Erro na leitura de diagnóstico: {e}")
            ultimo_p = None
            status_b1 = status_b2 = "Erro"
            cmd_b1 = cmd_b2 = "Erro"
            nivel_poco = "Erro"

        online = checar_dado_fresco(ultimo_p, tolerancia_segundos=45)

        if online:
            st.markdown("<div class='diag-status-ok'>✅ SISTEMA ONLINE — Comunicação Ativa</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='diag-status-off'>⚠️ SISTEMA OFFLINE — Sem Comunicação</div>", unsafe_allow_html=True)

        if nivel_poco == "BAIXO":
            st.markdown("<div class='diag-status-alert'>⚠️ NÍVEL DO POÇO BAIXO — Proteção Ativa</div>", unsafe_allow_html=True)

        agora_ms = time.time() * 1000
        if ultimo_p:
            try:
                seg_atras = int((agora_ms - float(ultimo_p)) / 1000)
                ultimo_sinal_str = f"{seg_atras}s atrás" if seg_atras < 60 else f"{seg_atras//60}min atrás"
            except:
                ultimo_sinal_str = "Valor de timestamp inválido"
        else:
            ultimo_sinal_str = "Nunca recebido"

        st.markdown(f"""
        <div class='diag-info-row'>
            <span>📡</span>
            <span class='diag-info-label'>Último Heartbeat:</span>
            <span>{ultimo_sinal_str}</span>
        </div>
        <div class='diag-info-row'>
            <span>🔌</span>
            <span class='diag-info-label'>Bomba 1 (real / comando):</span>
            <span>{status_b1} / {'LIGAR' if cmd_b1=='ON' else 'DESLIGAR'}</span>
        </div>
        <div class='diag-info-row'>
            <span>🔌</span>
            <span class='diag-info-label'>Bomba 2 (real / comando):</span>
            <span>{status_b2} / {'LIGAR' if cmd_b2=='ON' else 'DESLIGAR'}</span>
        </div>
        <div class='diag-info-row'>
            <span>💧</span>
            <span class='diag-info-label'>Nível do Poço:</span>
            <span>{nivel_poco}</span>
        </div>
        <div class='diag-info-row'>
            <span>🕐</span>
            <span class='diag-info-label'>Hora do Servidor:</span>
            <span>{obter_hora_brasilia().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:600; color:{COR_MUTED2}; letter-spacing:2px; margin-bottom:14px;'>AÇÕES DE MANUTENÇÃO</div>", unsafe_allow_html=True)

        d1, d2 = st.columns(2, gap="medium")
        with d1:
            if st.button("🔁 REINICIAR / RECONECTAR", use_container_width=True):
                try: db.reference("controle/restart").set(True)
                except: pass
                registrar_evento("Solicitou reinício/reconexão do dispositivo")
                st.success("Comando enviado. O dispositivo deve reiniciar e reconectar em instantes.")

        with d2:
            if st.session_state["is_admin"]:
                st.markdown("<div style='font-size:11px; color:#ef4444; margin-bottom:6px; text-align:center; letter-spacing:1px;'>⚠️ SÓ ADMIN MASTER</div>", unsafe_allow_html=True)
                if st.button("📡 RECONFIGURAR WI-FI", use_container_width=True):
                    try: db.reference("controle/wifi_reset").set(True)
                    except: pass
                    registrar_evento("Solicitou reconfiguração de WiFi (reset)")
                    st.success("Comando enviado. O dispositivo vai apagar o WiFi salvo e abrir o portal de configuração (rede ASB_WIFI).")
            else:
                st.markdown(f"""
                <div style='background:rgba(100,116,139,0.08); border:1px solid rgba(100,116,139,0.3);
                    border-radius:10px; padding:16px; text-align:center; color:{COR_MUTED}; font-size:13px; height:100%;'>
                    🔒 Reconfiguração de WiFi disponível apenas para o Administrador Master.
                    Fale com a ASB Automação Industrial se precisar trocar de rede.
                </div>
                """, unsafe_allow_html=True)

    # ─── GESTÃO DE USUÁRIOS ─────────────────────────────────────────────────
    elif menu == "👥 Gestão de Usuários" and st.session_state["is_admin"]:
        st.markdown("<div class='section-header'>Gerenciamento de Operadores</div>", unsafe_allow_html=True)

        with st.form("cad_u"):
            cf1, cf2, cf3 = st.columns(3, gap="medium")
            with cf1: n = st.text_input("Nome Completo")
            with cf2: l = st.text_input("Login")
            with cf3: s = st.text_input("Senha", type="password")
            if st.form_submit_button("CADASTRAR OPERADOR", use_container_width=True):
                if n and l and s:
                    try:
                        db.reference("usuarios_autorizados").push({
                            "nome": n, "login": l, "senha": s,
                            "data": obter_hora_brasilia().strftime('%d/%m/%Y')
                        })
                        st.success(f"Operador '{n}' cadastrado com sucesso.")
                    except: st.error("Erro ao cadastrar.")
                else:
                    st.warning("Preencha todos os campos.")
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:600; color:{COR_MUTED2}; letter-spacing:2px; margin-bottom:14px;'>OPERADORES CADASTRADOS</div>", unsafe_allow_html=True)

        try:
            usrs = db.reference("usuarios_autorizados").get()
        except:
            usrs = None

        if usrs:
            for k_u, v_u in usrs.items():
                col_info, col_del = st.columns([6, 1])
                with col_info:
                    st.markdown(f"""
                    <div class='card-contato'>
                        🟢 <b style='color:{COR_TITULO};'>{v_u['nome']}</b><br>
                        <span>Usuário:</span> {v_u['login']} &nbsp;|&nbsp;
                        <span>Senha:</span> {v_u['senha']}<br>
                        <small>Cadastrado em: {v_u.get('data','—')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑️", key=f"del_{k_u}", use_container_width=True, help=f"Apagar {v_u['nome']}"):
                        try:
                            db.reference(f"usuarios_autorizados/{k_u}").delete()
                            registrar_evento(f"APAGOU o operador '{v_u['nome']}'")
                            st.success(f"Operador '{v_u['nome']}' removido.")
                        except:
                            st.error("Erro ao remover operador.")
                        st.rerun()
        else:
            st.markdown(f"<div style='color:{COR_MUTED}; padding:20px;'>Nenhum operador cadastrado.</div>", unsafe_allow_html=True)

# LAVANDERIA EXATA - v2.3 (supervisório alinhado com solicitações de melhorias da ASB AUTOMAÇÃO)
#   - CORRIGIDO: convenção de comando das bombas alinhada ao firmware v2.4+ do ESP32
#     ("ON" = liga a bomba / energiza o relé, "OFF" = desliga a bomba / desenergiza o relé)
#   - Adequação dos botões Ligar/Desligar para relés Active LOW do ESP32
#   - Destaque visual forte e dinâmico dos botões conforme estado acionado/desligado
#   - Botão de atualização manual no controle de bombas
#   - Abas separadas por equipamento (Bomba 1 Principal, Bomba 2 Reserva e Automático)
#   - Conceito visual de Bomba 1 Principal e Bomba 2 Reserva/Standby
