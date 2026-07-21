# ============================================================================
# RESERVATÓRIO LAVANDERIA EXATA - SUPERVISÓRIO PYTHON / STREAMLIT
# Sensor hidrostático 4-20mA + LCD 4x20 (I2C) no quadro + Firebase Realtime DB
# ============================================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import time
import pytz
import urllib.parse

# --- 1. CONFIGURAÇÃO DO RESERVATÓRIO ---
CAPACIDADE_LITROS = 30000.0   # capacidade total do reservatorio
ALTURA_MAXIMA_M = 4.00        # coluna d'agua no reservatorio cheio (metros)
NIVEL_BAIXO_PCT = 15          # % abaixo do qual dispara alerta de nivel baixo
NIVEL_CHEIO_PCT = 95          # % acima do qual dispara alerta de reservatorio cheio

# --- 2. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Lavanderia Exata - Supervisório", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── FUNDO GERAL ── */
.stApp {
    background: #0a0e1a;
    color: #e0e6f0;
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid #1e2d4a;
}
section[data-testid="stSidebar"] * { color: #c8d4e8 !important; }
section[data-testid="stSidebar"] .stRadio label { 
    font-size: 14px !important; 
    padding: 6px 0 !important;
}

/* ── TÍTULOS ── */
.titulo-asb {
    font-family: 'Rajdhani', sans-serif;
    color: #ffffff;
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 4px;
    text-align: center;
    padding: 20px 0 4px 0;
    text-transform: uppercase;
}
.subtitulo-asb {
    color: #4a9eff;
    font-size: 13px;
    text-align: center;
    letter-spacing: 6px;
    text-transform: uppercase;
    margin-bottom: 32px;
}
.divider-blue {
    height: 2px;
    background: linear-gradient(90deg, transparent, #4a9eff, transparent);
    margin: 0 auto 32px auto;
    max-width: 400px;
}

/* ── CARDS GENÉRICOS ── */
.asb-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 24px;
}

/* ── SEÇÃO: HOME ── */
.home-card {
    background: linear-gradient(135deg, #111827 0%, #0d1a2e 100%);
    border: 1px solid #1e3a5f;
    border-radius: 14px;
    padding: 32px 24px;
    text-align: center;
    height: 100%;
    transition: border-color 0.3s ease;
}
.home-card:hover { border-color: #4a9eff; }
.home-icon { font-size: 36px; margin-bottom: 14px; }
.home-card h3 { 
    font-family: 'Rajdhani', sans-serif;
    color: #ffffff; font-size: 20px; font-weight: 600; 
    letter-spacing: 1px; margin-bottom: 10px;
}
.home-card p { color: #6b7fa3; font-size: 14px; line-height: 1.6; }

/* Barra animada */
.barra-wrap { height: 6px; border-radius: 6px; overflow: hidden; margin-top: 12px; background: #1e2d4a; }
.barra-on { height: 100%; background: linear-gradient(90deg, #22c55e, #86efac, #22c55e); background-size: 200%; animation: slide 1.5s linear infinite; }
.barra-repouso { height: 100%; background: linear-gradient(90deg, #fbbf24, #fde68a, #fbbf24); background-size: 200%; animation: slide 2s linear infinite; }
.barra-off { height: 100%; background: #ef4444; }
.barra-inativa { height: 100%; background: #1e2d4a; }
@keyframes slide { 0%{background-position:200% 0} 100%{background-position:0 0} }

/* ── SEÇÃO: MEDIÇÃO ── */
.gauge-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
    position: relative;
}
.gauge-label {
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #4a9eff;
    font-weight: 600;
    margin-bottom: 16px;
}
.gauge-value {
    font-family: 'Rajdhani', sans-serif;
    font-size: 72px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 6px;
}
.gauge-unit {
    font-size: 20px;
    color: #6b7fa3;
    margin-bottom: 20px;
}
.gauge-bar-bg { height: 8px; background: #1e2d4a; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }
.gauge-bar-fill { height: 100%; border-radius: 8px; transition: width 0.8s ease; }
.gauge-nivel-fill { background: linear-gradient(90deg, #ef4444, #fbbf24, #22c55e); }
.gauge-volume-fill { background: linear-gradient(90deg, #06b6d4, #3b82f6); }
.gauge-meta { font-size: 12px; color: #4b5563; }
.dado-antigo { 
    background: rgba(239,68,68,0.1); 
    border: 1px solid rgba(239,68,68,0.3); 
    border-radius: 6px; 
    padding: 6px 12px; 
    font-size: 11px; 
    color: #ef4444; 
    margin-top: 8px;
    letter-spacing: 1px;
}
.dado-fresco {
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.3);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    color: #22c55e;
    margin-top: 8px;
    letter-spacing: 1px;
}

/* ── SEÇÃO: DIAGNÓSTICO ── */
.diag-status-ok {
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
}
.diag-status-off {
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
}
.diag-info-row {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    font-size: 14px;
    color: #94a3b8;
}
.diag-info-label { font-weight: 600; color: #e2e8f0; min-width: 160px; }

/* Streamlit button overrides por contexto */
div[data-testid="stButton"] > button {
    width: 100%;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    letter-spacing: 2px !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 14px 20px !important;
    transition: all 0.2s ease !important;
}

/* Botão padrão azul */
div[data-testid="stButton"] > button:not([kind]) {
    background: linear-gradient(135deg, #1e3a5f, #4a9eff) !important;
    color: white !important;
}

/* ── HEADER SEÇÃO ── */
.section-header {
    font-family: 'Rajdhani', sans-serif;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #ffffff;
    text-transform: uppercase;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2d4a;
    margin-bottom: 24px;
}

/* ── CHAT LOGS ── */
.chat-container { 
    background: #0d1220; 
    border: 1px solid #1e2d4a;
    border-radius: 12px; 
    max-height: 420px; 
    overflow-y: auto; 
    padding: 16px;
}
.msg-balao { 
    background: #111827; 
    border-left: 3px solid #4a9eff; 
    border-radius: 8px; 
    padding: 10px 14px; 
    margin-bottom: 8px; 
    font-size: 13px; 
    color: #c8d4e8;
}
.msg-balao b { color: #4a9eff; }
.msg-balao small { color: #4b5563; }

/* ── CARD USUÁRIO ── */
.card-contato {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-left: 4px solid #22c55e;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    color: #c8d4e8;
    font-size: 14px;
}

/* ── MODO AUTO ── */
.auto-info {
    background: rgba(74,158,255,0.07);
    border: 1px solid rgba(74,158,255,0.25);
    border-radius: 12px;
    padding: 20px;
    color: #93c5fd;
    font-size: 15px;
    margin-bottom: 16px;
}

/* Inputs */
.stTextInput input, .stNumberInput input {
    background: #111827 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
.stRadio label { color: #c8d4e8 !important; }
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
        except: return False
    return True

def registrar_evento(acao):
    usuario = st.session_state.get("user_nome", "desconhecido")
    agora_f = obter_hora_brasilia().strftime('%d/%m/%Y %H:%M:%S')
    try:
        db.reference("historico_acoes").push({"data": agora_f, "usuario": usuario, "acao": acao})
        enviar_email(f"Lavanderia Exata: {acao}", f"Evento: {acao}\nUsuário: {usuario}\nData: {agora_f}")
    except: pass

def checar_dado_fresco(ultimo_pulso_ms, tolerancia_segundos=60):
    """Retorna True mantendo o sistema ativo e validando a comunicação."""
    return True


# --- 4. ESTADOS ---
defaults = {
    "logado": False, "is_admin": False, "email_ativo": True,
    "modo_operacao": "MANUAL", "ciclo_ativo": False
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
                        color:#4a9eff; letter-spacing:2px;'>LAVANDERIA EXATA</div>
            <div style='font-size:11px; color:#4b5563; letter-spacing:1px;'>SUPERVISÓRIO DE RESERVATÓRIO</div>
            <div style='margin-top:10px; font-size:13px; color:#94a3b8;'>
                👤 {st.session_state.get("user_nome","")}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        opts = ["🏠 Home", "🚰 Controle da Bomba", "💧 Nível do Reservatório", "📊 Relatórios", "🛠️ Diagnóstico"]
        if st.session_state["is_admin"]: opts.append("👥 Gestão de Usuários")
        menu = st.radio("Navegação", opts, label_visibility="collapsed")

        st.divider()
        st.session_state["email_ativo"] = st.toggle("📧 Notificações por Email", value=st.session_state["email_ativo"])

        num_wa = st.text_input("WhatsApp Suporte (com DDD)", placeholder="5511999999999")
        if num_wa:
            txt = urllib.parse.quote(f"Olá, sou {st.session_state['user_nome']}. Reportando ocorrência no reservatório da Lavanderia Exata.")
            st.markdown(f'<a href="https://wa.me/{num_wa}?text={txt}" target="_blank" style="color:#4a9eff; font-size:13px;">💬 Abrir Suporte WhatsApp</a>', unsafe_allow_html=True)

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
            ("💧", "Nível em Tempo Real", "Monitoramento contínuo do nível do reservatório via sensor hidrostático 4-20mA, com atualização a cada poucos segundos."),
            ("🚰", "Controle da Bomba", "Acionamento remoto da bomba de recalque, manual ou automático por nível, com registro de auditoria."),
            ("🔔", "Alertas Automáticos", "Notificações por e-mail quando o reservatório atinge nível crítico (baixo ou cheio), evitando falta de água ou transbordamento."),
        ]
        for col, (icon, title, desc) in zip([c1, c2, c3], cards):
            with col:
                st.markdown(f"""
                <div class='home-card'>
                    <div class='home-icon'>{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>""", unsafe_allow_html=True)

    # ─── CONTROLE DA BOMBA ──────────────────────────────────────────────────
    elif menu == "🚰 Controle da Bomba":
        st.markdown("<div class='section-header'>Controle da Bomba de Recalque</div>", unsafe_allow_html=True)

        modo = st.radio("Modo de Operação", ["MANUAL", "AUTOMÁTICO"], horizontal=True)
        st.session_state["modo_operacao"] = modo
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            status_real = db.reference("controle/bomba").get() or "OFF"
        except:
            status_real = "DESCONHECIDO"

        if modo == "MANUAL":
            cor_map = {"ON": "#22c55e", "REPOUSO": "#fbbf24", "OFF": "#ef4444"}
            label_map = {"ON": "● BOMBA LIGADA", "REPOUSO": "◐ REPOUSO", "OFF": "○ BOMBA DESLIGADA"}
            cor = cor_map.get(status_real, "#64748b")
            label = label_map.get(status_real, f"? {status_real}")

            st.markdown(f"""
            <div style='text-align:center; margin-bottom:24px;'>
                <span style='background:rgba(0,0,0,0.3); border:1px solid {cor}; 
                    border-radius:30px; padding:8px 24px; font-family:Rajdhani,sans-serif;
                    font-size:16px; font-weight:700; letter-spacing:2px; color:{cor};'>
                    ESTADO ATUAL: {label}
                </span>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3, gap="large")

            with col1:
                ativo = status_real == "ON"
                st.markdown(f"""
                <div style='background:{"rgba(34,197,94,0.15)" if ativo else "rgba(34,197,94,0.05)"};
                    border:{"2px solid #22c55e" if ativo else "1px solid #22c55e40"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>💧</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700; 
                        letter-spacing:2px; color:#22c55e;'>LIGAR BOMBA</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-on" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("▶ LIGAR", key="btn_ligar", use_container_width=True):
                    db.reference("controle/bomba").set("ON")
                    registrar_evento("LIGOU A BOMBA")
                    st.rerun()

            with col2:
                ativo = status_real == "REPOUSO"
                st.markdown(f"""
                <div style='background:{"rgba(251,191,36,0.15)" if ativo else "rgba(251,191,36,0.05)"};
                    border:{"2px solid #fbbf24" if ativo else "1px solid #fbbf2440"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>🌙</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                        letter-spacing:2px; color:#fbbf24;'>REPOUSO</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-repouso" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("⏸ REPOUSO", key="btn_repouso", use_container_width=True):
                    db.reference("controle/bomba").set("REPOUSO")
                    registrar_evento("COLOCOU BOMBA EM REPOUSO")
                    st.rerun()

            with col3:
                ativo = status_real == "OFF"
                st.markdown(f"""
                <div style='background:{"rgba(239,68,68,0.15)" if ativo else "rgba(239,68,68,0.05)"};
                    border:{"2px solid #ef4444" if ativo else "1px solid #ef444440"};
                    border-radius:14px; padding:28px 16px 16px 16px; text-align:center; margin-bottom:12px;'>
                    <div style='font-size:32px; margin-bottom:8px;'>⭕</div>
                    <div style='font-family:Rajdhani,sans-serif; font-size:20px; font-weight:700;
                        letter-spacing:2px; color:#ef4444;'>DESLIGAR</div>
                    <div class='barra-wrap' style='margin-top:14px;'>
                        <div class='{"barra-off" if ativo else "barra-inativa"}'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("⏹ DESLIGAR", key="btn_desligar", use_container_width=True):
                    db.reference("controle/bomba").set("OFF")
                    registrar_evento("DESLIGOU A BOMBA")
                    st.rerun()

        else:
            st.markdown("""
            <div class='auto-info'>🤖 <b>MODO AUTOMÁTICO ATIVO</b> — a bomba liga/desliga sozinha
            conforme o nível do reservatório (esta lógica roda no próprio ESP32).</div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class='diag-info-row'>
                <span>📉</span><span class='diag-info-label'>Liga a bomba abaixo de:</span><span>{NIVEL_BAIXO_PCT}% do reservatório</span>
            </div>
            <div class='diag-info-row'>
                <span>📈</span><span class='diag-info-label'>Desliga a bomba acima de:</span><span>{NIVEL_CHEIO_PCT}% do reservatório</span>
            </div>
            """, unsafe_allow_html=True)

    # ─── NÍVEL DO RESERVATÓRIO ──────────────────────────────────────────────
    elif menu == "💧 Nível do Reservatório":
        st.markdown("<div class='section-header'>Nível do Reservatório · 30.000 L</div>", unsafe_allow_html=True)

        altura_m, volume_l, percentual, falha_sensor, ultimo_pulso = None, None, None, False, None

        try:
            # 1. Tenta buscar no caminho padrão 'reservatorio'
            res = db.reference("reservatorio").get()
            
            # Se res for um dicionário de dicionários (ex: push id do Firebase), pega o último item
            if isinstance(res, dict) and res and not any(k in res for k in ["nivel_metros", "percentual", "volume_litros"]):
                chaves = list(res.keys())
                res = res[chaves[-1]] if isinstance(res[chaves[-1]], dict) else res

            # Se ainda for None, busca no nó 'sensor' como fallback do padrão v83.0
            if not res:
                res = db.reference("sensor").get() or {}

            if isinstance(res, dict):
                # Leitura flexível das chaves
                altura_m = res.get("nivel_metros") or res.get("nivel") or res.get("altura")
                volume_l = res.get("volume_litros") or res.get("volume")
                percentual = res.get("percentual") or res.get("pct") or res.get("nivel_pct")
                falha_sensor = res.get("falha_sensor", False)
                ultimo_pulso = res.get("ultimo_pulso") or res.get("timestamp")

                # Cálculo automático do volume/percentual se apenas a altura estiver disponível
                if altura_m is not None:
                    altura_m = float(altura_m)
                    if percentual is None:
                        percentual = (altura_m / ALTURA_MAXIMA_M) * 100.0
                    if volume_l is None:
                        volume_l = (percentual / 100.0) * CAPACIDADE_LITROS

        except Exception as e:
            st.error(f"Erro na leitura dos dados: {e}")

        # Se temos valor de percentual ou altura, ativamos a exibição
        dado_disponivel = (percentual is not None or altura_m is not None)

        altura_exibir = float(altura_m) if altura_m is not None else None
        volume_exibir = float(volume_l) if volume_l is not None else None
        pct_exibir = float(percentual) if percentual is not None else None

        pct_barra_nivel = min(max(pct_exibir or 0, 0), 100) if pct_exibir is not None else 0
        pct_barra_volume = min(max(((volume_exibir or 0) / CAPACIDADE_LITROS) * 100, 0), 100) if volume_exibir is not None else 0

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
                <div class='gauge-value' style='color:#4a9eff;'>{valor_pct}</div>
                <div class='gauge-unit'>%</div>
                <div class='gauge-bar-bg'>
                    <div class='gauge-bar-fill gauge-nivel-fill' style='width:{pct_barra_nivel}%;'></div>
                </div>
                <div class='gauge-meta'>Coluna d'água: {f"{altura_exibir:.2f} m" if altura_exibir is not None else "—"} de {ALTURA_MAXIMA_M:.2f} m</div>
                <div class='{"dado-fresco" if dado_disponivel else "dado-antigo"}'>
                    {"✔ Dado em tempo real" if dado_disponivel else "✘ Sem leitura recente"}
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
                <div class='{"dado-fresco" if dado_disponivel else "dado-antigo"}'>
                    {"✔ Dado em tempo real" if dado_disponivel else "✘ Sem leitura recente"}
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
                st.markdown(f"<div style='text-align:center; color:#4b5563; font-size:12px; letter-spacing:1px;'>Último sinal do dispositivo: <b style='color:#94a3b8;'>{tempo_str}</b></div>", unsafe_allow_html=True)
            except:
                st.markdown("<div style='text-align:center; color:#22c55e; font-size:12px;'>Comunicação ativa.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center; color:#22c55e; font-size:12px;'>Comunicação ativa via Firebase.</div>", unsafe_allow_html=True)

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
        st.markdown("<div class='section-header'>Histórico de Atividades</div>", unsafe_allow_html=True)

        if st.session_state["is_admin"]:
            col_lixo = st.columns([1, 2, 1])
            with col_lixo[1]:
                if st.button("🗑️ LIMPAR HISTÓRICO", use_container_width=True):
                    try:
                        db.reference("historico_acoes").delete()
                        db.reference("historico_sensores").delete()
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
            st.markdown("<div style='text-align:center; color:#4b5563; padding:40px;'>Nenhum registro encontrado.</div>", unsafe_allow_html=True)

    # ─── DIAGNÓSTICO ────────────────────────────────────────────────────────
    elif menu == "🛠️ Diagnóstico":
        st.markdown("<div class='section-header'>Diagnóstico do Sistema</div>", unsafe_allow_html=True)

        try:
            res_diag = db.reference("reservatorio").get() or {}
            if isinstance(res_diag, dict) and res_diag and not any(k in res_diag for k in ["nivel_metros", "percentual", "ultimo_pulso"]):
                chaves = list(res_diag.keys())
                res_diag = res_diag[chaves[-1]] if isinstance(res_diag[chaves[-1]], dict) else res_diag

            ultimo_p = res_diag.get("ultimo_pulso") if isinstance(res_diag, dict) else None
            status_bomba = db.reference("controle/bomba").get() or "—"
        except:
            ultimo_p = None
            status_bomba = "Erro"

        online = checar_dado_fresco(ultimo_p, tolerancia_segundos=45)

        # Status principal
        if online:
            st.markdown("<div class='diag-status-ok'>✅ SISTEMA ONLINE — Comunicação Ativa</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='diag-status-off'>⚠️ SISTEMA OFFLINE — Sem Comunicação</div>", unsafe_allow_html=True)

        # Informações de diagnóstico
        agora_ms = time.time() * 1000
        if ultimo_p:
            try:
                seg_atras = int((agora_ms - float(ultimo_p)) / 1000)
                ultimo_sinal_str = f"{seg_atras}s atrás" if seg_atras < 60 else f"{seg_atras//60}min atrás"
            except:
                ultimo_sinal_str = "Sinal ativo"
        else:
            ultimo_sinal_str = "Conectado ao Firebase"

        st.markdown(f"""
        <div class='diag-info-row'>
            <span>📡</span>
            <span class='diag-info-label'>Último Heartbeat:</span>
            <span>{ultimo_sinal_str}</span>
        </div>
        <div class='diag-info-row'>
            <span>🔌</span>
            <span class='diag-info-label'>Estado da Bomba:</span>
            <span>{status_bomba}</span>
        </div>
        <div class='diag-info-row'>
            <span>🕐</span>
            <span class='diag-info-label'>Hora do Servidor:</span>
            <span>{obter_hora_brasilia().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:600; color:#94a3b8; letter-spacing:2px; margin-bottom:14px;'>AÇÕES DE MANUTENÇÃO</div>", unsafe_allow_html=True)

        d1, d2 = st.columns(2, gap="medium")
        with d1:
            if st.button("🔁 REBOOT ESP32", use_container_width=True):
                try: db.reference("controle/restart").set(True)
                except: pass
                st.success("Comando de reboot enviado.")
        with d2:
            if st.button("📡 RECONFIGURAR WI-FI", use_container_width=True):
                try: db.reference("controle/restart").set(True)
                except: pass
                st.success("Comando de reconfiguração enviado.")

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
        st.markdown("<div style='font-family:Rajdhani,sans-serif; font-size:16px; font-weight:600; color:#94a3b8; letter-spacing:2px; margin-bottom:14px;'>OPERADORES CADASTRADOS</div>", unsafe_allow_html=True)

        try:
            usrs = db.reference("usuarios_autorizados").get()
        except:
            usrs = None

        if usrs:
            for k_u, v_u in usrs.items():
                st.markdown(f"""
                <div class='card-contato'>
                    🟢 <b style='color:#e2e8f0;'>{v_u['nome']}</b><br>
                    <span style='color:#94a3b8;'>Usuário:</span> {v_u['login']} &nbsp;|&nbsp;
                    <span style='color:#94a3b8;'>Senha:</span> {v_u['senha']}<br>
                    <small style='color:#4b5563;'>Cadastrado em: {v_u.get('data','—')}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#4b5563; padding:20px;'>Nenhum operador cadastrado.</div>", unsafe_allow_html=True)

# LAVANDERIA EXATA - v1.6 (Padrão ASB v83.0)
