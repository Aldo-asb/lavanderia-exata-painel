# ============================================================================
# RESERVATÓRIO LAVANDERIA EXATA - SUPERVISÓRIO PYTHON / STREAMLIT
# Sensor hidrostático 4-20mA + LCD 4x20 (I2C) + 2 Bombas + Nível do Poço
# ============================================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import time
import pytz
import urllib.parse
import pandas as pd

# --- 1. CONFIGURAÇÃO DO RESERVATÓRIO ---
CAPACIDADE_LITROS = 30000.0   # capacidade total do reservatorio
ALTURA_MAXIMA_M = 3.80        # faixa util do sensor de 5m (coluna real do reservatorio)
NIVEL_BAIXO_PCT = 15          # % abaixo do qual dispara alerta de nivel baixo (email)
NIVEL_CHEIO_PCT = 95          # % acima do qual dispara alerta de reservatorio cheio (email)

# Faixa de acionamento da BOMBA (precisa ser IDENTICA ao .ino)
BOMBA_LIGA_PCT = 70     # liga a bomba abaixo disso
BOMBA_DESLIGA_PCT = 95  # desliga a bomba acima disso

# --- 2. CONFIGURAÇÃO VISUAL (TEMA CLARO/ESCURO) ---
st.set_page_config(page_title="Lavanderia Exata - Supervisório", layout="wide", initial_sidebar_state="expanded")

tema_claro = st.session_state.get("tema_claro", False)

if tema_claro:
    COR_BG = "#f4f6fb"
    COR_TEXTO = "#1e293b"
    COR_SIDEBAR_BG = "#ffffff"
    COR_BORDA = "#dbe3f0"
    COR_CARD_BG = "#ffffff"
    COR_CARD_BG2 = "#eef2fb"
    COR_MUTED = "#64748b"
    COR_MUTED2 = "#94a3b8"
    COR_ACCENT = "#2563eb"
    COR_ACCENT_RGB = "37,99,235"
    COR_TITULO = "#0f172a"
    COR_INPUT_BG = "#ffffff"
else:
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
    "modo_operacao": "MANUAL", "ciclo_ativo": False, "tema_claro": False
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
        st.session_state["tema_claro"] = st.toggle("🌓 Tema Claro", value=st.session_state["tema_claro"])
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
            ("🚰", "Controle das Bombas", "Acionamento remoto de duas bombas de recalque (B1 e B2), manual ou automático por nível, com proteção de poço seco e registro de auditoria."),
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

        modo = st.radio("Modo de Operação", ["MANUAL", "AUTOMÁTICO"], horizontal=True)
        st.session_state["modo_operacao"] = modo
        st.markdown("<br>", unsafe_allow_html=True)

        # Le os status reais e comandos do Firebase
        try:
            status_real_b1 = db.reference("reservatorio/bomba1_status").get() or "OFF"
            status_real_b2 = db.reference("reservatorio/bomba2_status").get() or "OFF"
            cmd_b1 = db.reference("reservatorio/bomba1_comando").get() or "OFF"
            cmd_b2 = db.reference("reservatorio/bomba2_comando").get() or "OFF"
            nivel_poco = db.reference("reservatorio/nivel_poco").get() or "OK"
        except:
            status_real_b1, status_real_b2 = "DESCONHECIDO", "DESCONHECIDO"
            cmd_b1, cmd_b2 = "DESCONHECIDO", "DESCONHECIDO"
            nivel_poco = "DESCONHECIDO"

        # Estado do automático por software
        try:
            auto_software_ativo = db.reference("controle/auto_software_ativo").get() or False
        except:
            auto_software_ativo = False

        # Alerta de poço seco
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

        if modo == "MANUAL":
            # Cards de status das bombas
            col_status1, col_status2 = st.columns(2, gap="medium")

            with col_status1:
                cor_b1 = "#22c55e" if status_real_b1 == "ON" else "#ef4444"
                label_b1 = "● BOMBA 1 LIGADA" if status_real_b1 == "ON" else "○ BOMBA 1 DESLIGADA"
                st.markdown(f"""
                <div style='text-align:center; margin-bottom:16px; padding:12px; border-radius:10px; border:1px solid {cor_b1}; background:rgba({"34,197,94" if status_real_b1=="ON" else "239,68,68"},0.08);'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:700; letter-spacing:2px; color:{cor_b1};'>
                        {label_b1}
                    </span><br>
                    <small style='color:{COR_MUTED};'>Comando ESP: {cmd_b1}</small>
                </div>
                """, unsafe_allow_html=True)

            with col_status2:
                cor_b2 = "#22c55e" if status_real_b2 == "ON" else "#ef4444"
                label_b2 = "● BOMBA 2 LIGADA" if status_real_b2 == "ON" else "○ BOMBA 2 DESLIGADA"
                st.markdown(f"""
                <div style='text-align:center; margin-bottom:16px; padding:12px; border-radius:10px; border:1px solid {cor_b2}; background:rgba({"34,197,94" if status_real_b2=="ON" else "239,68,68"},0.08);'>
                    <span style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:700; letter-spacing:2px; color:{cor_b2};'>
                        {label_b2}
                    </span><br>
                    <small style='color:{COR_MUTED};'>Comando ESP: {cmd_b2}</small>
                </div>
                """, unsafe_allow_html=True)

            if auto_software_ativo:
                st.markdown("""
                <div class='auto-info'>⚠️ O automático por software está <b>ATIVO</b> (aba
                Automático). O ESP32 decide sozinho com base no nível e pode sobrescrever o
                comando manual abaixo. Desative o automático por software se quiser controle
                100% manual.</div>
                """, unsafe_allow_html=True)

            # Controles B1
            st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:18px; font-weight:600; color:{COR_TITULO}; letter-spacing:2px; margin:16px 0 12px 0;'>🔧 BOMBA 1</div>", unsafe_allow_html=True)
            col1_b1, col2_b1 = st.columns(2, gap="large")
            with col1_b1:
                ativo = status_real_b1 == "ON"
                st.markdown(f"""
                <div style='background:{"rgba(34,197,94,0.15)" if ativo else "rgba(34,197,94,0.05)"};
                    border:{"2px solid #22c55e" if ativo else "1px solid #22c55e40"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>💧</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                        letter-spacing:2px; color:#22c55e;'>LIGAR B1</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-on" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("▶ LIGAR B1", key="btn_ligar_b1", use_container_width=True):
                    db.reference("controle/bomba1_comando").set("ON")
                    registrar_evento("LIGOU A BOMBA 1 (manual)")
                    st.rerun()

            with col2_b1:
                ativo = status_real_b1 == "OFF"
                st.markdown(f"""
                <div style='background:{"rgba(239,68,68,0.15)" if ativo else "rgba(239,68,68,0.05)"};
                    border:{"2px solid #ef4444" if ativo else "1px solid #ef444440"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>⭕</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                        letter-spacing:2px; color:#ef4444;'>DESLIGAR B1</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-off" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("⏹ DESLIGAR B1", key="btn_desligar_b1", use_container_width=True):
                    db.reference("controle/bomba1_comando").set("OFF")
                    registrar_evento("DESLIGOU A BOMBA 1 (manual)")
                    st.rerun()

            # Controles B2
            st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:18px; font-weight:600; color:{COR_TITULO}; letter-spacing:2px; margin:24px 0 12px 0;'>🔧 BOMBA 2</div>", unsafe_allow_html=True)
            col1_b2, col2_b2 = st.columns(2, gap="large")
            with col1_b2:
                ativo = status_real_b2 == "ON"
                st.markdown(f"""
                <div style='background:{"rgba(34,197,94,0.15)" if ativo else "rgba(34,197,94,0.05)"};
                    border:{"2px solid #22c55e" if ativo else "1px solid #22c55e40"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>💧</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                        letter-spacing:2px; color:#22c55e;'>LIGAR B2</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-on" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("▶ LIGAR B2", key="btn_ligar_b2", use_container_width=True):
                    db.reference("controle/bomba2_comando").set("ON")
                    registrar_evento("LIGOU A BOMBA 2 (manual)")
                    st.rerun()

            with col2_b2:
                ativo = status_real_b2 == "OFF"
                st.markdown(f"""
                <div style='background:{"rgba(239,68,68,0.15)" if ativo else "rgba(239,68,68,0.05)"};
                    border:{"2px solid #ef4444" if ativo else "1px solid #ef444440"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>⭕</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                        letter-spacing:2px; color:#ef4444;'>DESLIGAR B2</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-off" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("⏹ DESLIGAR B2", key="btn_desligar_b2", use_container_width=True):
                    db.reference("controle/bomba2_comando").set("OFF")
                    registrar_evento("DESLIGOU A BOMBA 2 (manual)")
                    st.rerun()

        else:
            st.markdown("""
            <div class='auto-info'>🌊 <b>AUTOMÁTICO POR HARDWARE (BÓIA)</b> — hoje quem liga e
            desliga as bombas sozinha é a bóia elétrica instalada no quadro das bombas. O controle
            abaixo é um <b>backup por software</b>, para os casos em que a bóia apresentar algum
            problema. Se o poço estiver seco, o software NÃO liga as bombas, mesmo no automático.</div>
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

            if novo_auto:
                st.markdown(f"""
                <div class='diag-info-row'>
                    <span>📉</span><span class='diag-info-label'>Liga as bombas abaixo de:</span><span>{BOMBA_LIGA_PCT}% do reservatório</span>
                </div>
                <div class='diag-info-row'>
                    <span>📈</span><span class='diag-info-label'>Desliga as bombas acima de:</span><span>{BOMBA_DESLIGA_PCT}% do reservatório</span>
                </div>
                <div class='diag-info-row'>
                    <span>🛡️</span><span class='diag-info-label'>Proteção de poço seco:</span><span>ATIVA (não liga se poço BAIXO)</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{COR_MUTED}; text-align:center; padding:12px;'>Automático por software desligado — a bóia elétrica está no comando.</div>", unsafe_allow_html=True)

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

            m1, m2, m3, m4 = st.columns(4, gap="medium")
            with m1:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Consumo Estimado</div>
                    <div class='gauge-value' style='color:#06b6d4; font-size:48px;'>{consumo_litros:,.0f}</div>
                    <div class='gauge-unit'>litros no dia</div>
                </div>
                """.replace(",", "."), unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Acionamentos B1</div>
                    <div class='gauge-value' style='color:{COR_ACCENT}; font-size:48px;'>{num_ac_b1}</div>
                    <div class='gauge-unit'>vezes ligou no dia</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Acionamentos B2</div>
                    <div class='gauge-value' style='color:#a855f7; font-size:48px;'>{num_ac_b2}</div>
                    <div class='gauge-unit'>vezes ligou no dia</div>
                </div>
                """, unsafe_allow_html=True)
            with m4:
                total_horas = horas_b1 + horas_b2
                st.markdown(f"""
                <div class='gauge-card'>
                    <div class='gauge-label'>Tempo Ligadas</div>
                    <div class='gauge-value' style='color:#22c55e; font-size:48px;'>{total_horas:.1f}</div>
                    <div class='gauge-unit'>horas no dia (B1+B2)</div>
                </div>
                """, unsafe_allow_html=True)

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
            col_lixo = st.columns([1, 2, 1])
            with col_lixo[1]:
                if st.button("🗑️ LIMPAR HISTÓRICO", use_container_width=True):
                    try:
                        db.reference("historico_acoes").delete()
                        db.reference("historico_sensores").delete()
                        db.reference("historico_bomba").delete()
                    except: pass
                    st.rerun()
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
            <span>{status_b1} / {cmd_b1}</span>
        </div>
        <div class='diag-info-row'>
            <span>🔌</span>
            <span class='diag-info-label'>Bomba 2 (real / comando):</span>
            <span>{status_b2} / {cmd_b2}</span>
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

# LAVANDERIA EXATA - v2.0 (supervisório alinhado com firmware v2.0)
#   - Sensor de 5m (faixa util 3,80m)
#   - Duas bombas com controle individual (B1 e B2)
#   - Feedback real dos contatores auxiliares
#   - Nível do poço com proteção de seco
#   - Relatórios separados por bomba
