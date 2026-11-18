"""Tema visual de las aplicaciones, basado en el diseño de ``ecnt-frontend`` (React).

Reproduce en Streamlit: login centrado, barra lateral blanca con marca y menú, barra superior con
usuario, banner de bienvenida, tarjetas de indicadores con iconos (Lucide), avisos y tarjetas de alerta.
Admin usa azul corporativo (#1A365D) y EPS verde salud (#065F46), igual que el diseño original.
"""

from __future__ import annotations

import html
from contextlib import contextmanager

import plotly.graph_objects as go
import streamlit as st

# Paletas de cada ambiente (valores tomados de ecnt-frontend)
ENV = {
    "admin": {"primary": "#1A365D", "hover": "#11243E", "soft": "#EBF8FF", "brand": "ECNT",
              "tagline": "Vigilancia y predicción", "menu": "MENÚ PRINCIPAL", "avatar": "A"},
    "eps": {"primary": "#065F46", "hover": "#044E3A", "soft": "#ECFDF5", "brand": "EPS Salud",
            "tagline": "Portal de riesgo territorial", "menu": "MENÚ", "avatar": "E"},
}
COLORS = {  # cajas de icono
    "blue": ("#E0F2FE", "#0369A1"), "green": ("#DCFCE7", "#15803D"), "purple": ("#F3E8FF", "#7E22CE"),
    "orange": ("#FFEDD5", "#C2410C"), "red": ("#FEE2E2", "#B91C1C"), "teal": ("#CCFBF1", "#0F766E"),
}
RISK = {"muy alto": "#B91C1C", "alto": "#D55858", "medio": "#E0A72E", "bajo": "#5FAE7F", "muy bajo": "#269567"}
PRIORITY = {"alta": ("#D55858", "#FFF0F0"), "media": ("#E0A72E", "#FFF9EC"), "baja": ("#269567", "#E7F7EF")}

# Iconos Lucide (https://lucide.dev, licencia ISC) como trazos SVG de 24×24
_ICONS = {
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
                '<path d="M3 12a9 3 0 0 0 18 0"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "brain": '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>'
             '<path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>'
             '<path d="M12 5v13"/>',
    "trending": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>',
    "map": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2'
             'A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>'
              '<line x1="12" x2="12" y1="3" y2="15"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>'
              '<polyline points="2 12 12 17 22 12"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "arrow": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
            '<path d="M12 18v-6"/><path d="M9 15h6"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/>'
              '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
              '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
}


def icon(name: str, size: int = 20, color: str = "currentColor") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'{_ICONS.get(name, _ICONS["info"])}</svg>')


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


# ---------------------------------------------------------------------------------------------
# Hoja de estilos global
# ---------------------------------------------------------------------------------------------
def apply_theme(env: str) -> None:
    p = ENV[env]
    _html(f"""<style>
    html, body, [class*="css"], .stApp {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        Helvetica, Arial, sans-serif; color: #1E293B; }}
    .stApp, [data-testid="stAppViewContainer"] {{ background: #F1F5F9; }}
    [data-testid="stHeader"] {{ background: transparent; height: 2.5rem; }}
    /* Se ocultan SOLO el botón Deploy y el menú de Streamlit. La barra de herramientas (stToolbar) debe
       seguir visible: contiene el botón para volver a abrir la barra lateral cuando se colapsa. */
    [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stDecoration"], #MainMenu {{
        display: none !important; }}
    [data-testid="stExpandSidebarButton"] {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px;
        color: {p['primary']}; }}
    [data-testid="stSidebarHeader"] {{ height: 1.2rem; min-height: 1.2rem; padding: 0.4rem; }}
    [data-testid="stMainBlockContainer"], .block-container {{ max-width: 1300px; padding: 1.2rem 2rem 3rem; }}
    h1, h2, h3, h4 {{ color: {p['primary']}; letter-spacing: -0.2px; }}
    h1 {{ font-size: 1.45rem !important; }} h2 {{ font-size: 1.15rem !important; }} h3 {{ font-size: 1rem !important; }}

    /* Barra lateral blanca, como ecnt-frontend */
    [data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #CBD5E1; min-width: 250px !important;
        max-width: 260px !important; }}
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0.6rem 0.9rem 1rem; }}
    [data-testid="stSidebarNav"] {{ display: none; }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a, [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
        border-radius: 4px; padding: 0.42rem 0.5rem; color: #475569 !important; text-decoration: none; }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{ background: #F1F5F9; }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] p, [data-testid="stSidebar"] [data-testid="stPageLink"] span {{
        font-size: 13px; color: #475569; }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.15rem; }}
    .ecnt-nav-active a, .ecnt-nav-active [data-testid="stPageLink-NavLink"] {{ background: #E2E8F0 !important; }}
    .ecnt-nav-active p, .ecnt-nav-active span {{ color: {p['primary']} !important; font-weight: 600 !important; }}
    .ecnt-brand {{ display: flex; align-items: center; gap: 12px; padding: 0 4px 16px;
        border-bottom: 1px solid #CBD5E1; margin-bottom: 4px; }}
    .ecnt-brand-icon {{ width: 40px; height: 40px; background: {p['soft']}; color: {p['primary']}; display: flex;
        align-items: center; justify-content: center; border-radius: 4px; }}
    .ecnt-brand .name {{ font-size: 18px; font-weight: 700; color: {p['primary']}; line-height: 1.2; }}
    .ecnt-brand span {{ display: block; color: #64748B; font-size: 11px; }}
    .ecnt-section {{ margin: 16px 0 14px; color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 1px;
        padding-left: 6px; }}
    .ecnt-profile {{ display: flex; align-items: center; gap: 10px; padding: 12px 4px 22px;
        border-top: 1px solid #CBD5E1; margin-top: 18px; }}
    .ecnt-avatar {{ width: 32px; height: 32px; border-radius: 4px; display: flex; align-items: center;
        justify-content: center; background: #E2E8F0; color: {p['primary']}; font-weight: 700; font-size: 12px; }}
    .ecnt-profile strong {{ display: block; font-size: 12px; color: #0F172A; }}
    .ecnt-profile span {{ display: block; font-size: 11px; color: #64748B; }}
    .ecnt-profile .mail {{ font-size: 10px; color: #94A3B8; word-break: break-all; }}

    /* Barra superior */
    .ecnt-topbar {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; min-height: 56px;
        display: flex; align-items: center; justify-content: space-between; padding: 0 18px; margin-bottom: 18px; }}
    .ecnt-topbar .crumb {{ color: #64748B; font-size: 12px; }}
    .ecnt-topbar .crumb b {{ color: {p['primary']}; }}
    .ecnt-topbar .right {{ display: flex; align-items: center; gap: 18px; }}
    .ecnt-bell {{ position: relative; color: #64748B; display: flex; }}
    .ecnt-bell .dot {{ position: absolute; top: -4px; right: -8px; background: #D55858; color: #fff; font-size: 9px;
        border-radius: 8px; padding: 1px 5px; font-weight: 700; }}
    .ecnt-user {{ display: flex; align-items: center; gap: 10px; }}
    .ecnt-user strong {{ display: block; font-size: 12px; color: #0F172A; }}
    .ecnt-user span {{ display: block; font-size: 11px; color: #64748B; }}

    /* Encabezados de página */
    .ecnt-header {{ display: flex; justify-content: space-between; align-items: flex-end; margin: 4px 0 16px; }}
    .ecnt-header .title {{ font-size: 21px; font-weight: 700; color: {p['primary']}; line-height: 1.25; }}
    .ecnt-header p {{ margin: 4px 0 0; color: #64748B; font-size: 13px; }}
    .ecnt-pill {{ display: inline-flex; align-items: center; gap: 6px; background: #FFFFFF; border: 1px solid #CBD5E1;
        border-radius: 4px; padding: 6px 10px; font-size: 12px; color: #475569; }}

    /* Banner de bienvenida */
    .ecnt-welcome {{ background: {p['primary']}; border-radius: 4px; padding: 24px; display: flex;
        justify-content: space-between; align-items: center; color: #FFFFFF; margin-bottom: 18px; }}
    .ecnt-welcome .label {{ font-size: 10px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
        opacity: .8; }}
    .ecnt-welcome .title {{ font-size: 21px; font-weight: 700; margin: 8px 0; color: #FFFFFF; }}
    .ecnt-welcome p {{ color: #CBD5E1; font-size: 13px; max-width: 620px; margin: 0; }}
    .ecnt-welcome .big {{ width: 70px; height: 70px; display: flex; align-items: center; justify-content: center;
        background: rgba(255,255,255,.1); border-radius: 4px; }}

    /* Tarjetas de indicadores */
    .ecnt-stats {{ display: grid; grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr)); gap: 15px;
        margin-bottom: 8px; }}
    .ecnt-stat {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 16px; display: flex;
        gap: 12px; align-items: flex-start; }}
    .ecnt-ico {{ width: 38px; height: 38px; border-radius: 4px; display: flex; align-items: center;
        justify-content: center; flex-shrink: 0; }}
    .ecnt-stat span {{ display: block; color: #64748B; font-size: 11px; }}
    .ecnt-stat .val {{ font-size: 22px; font-weight: 700; color: #0F172A; margin: 4px 0 2px; line-height: 1.2; }}
    .ecnt-stat small {{ color: #94A3B8; font-size: 10px; }}
    @media (max-width: 1000px) {{ .ecnt-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

    /* Tarjetas de acción */
    .ecnt-action {{ display: flex; gap: 12px; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px;
        padding: 16px; min-height: 92px; }}
    .ecnt-action .title {{ font-size: 13px; font-weight: 700; margin: 0 0 4px; color: #0F172A; }}
    .ecnt-action p {{ font-size: 12px; color: #64748B; margin: 0; }}

    /* Avisos */
    .ecnt-notice {{ display: flex; gap: 12px; border-radius: 4px; padding: 14px; margin: 16px 0; font-size: 12px;
        line-height: 1.5; }}
    .ecnt-notice.warning {{ background: #FEF3C7; color: #92400E; }}
    .ecnt-notice.info {{ background: #E0F2FE; color: #075985; }}
    .ecnt-notice.success {{ background: #ECFDF5; color: #065F46; }}
    .ecnt-notice.danger {{ background: #FEE2E2; color: #991B1B; }}
    .ecnt-notice svg {{ flex-shrink: 0; margin-top: 1px; }}

    /* Sección */
    .ecnt-section-heading .title {{ font-size: 15px; font-weight: 700; margin: 18px 0 0; color: {p['primary']}; }}
    .ecnt-section-heading p {{ font-size: 12px; color: #64748B; margin: 3px 0 10px; }}

    /* Tablas HTML (directorio y alertas) */
    .ecnt-table {{ width: 100%; border-collapse: collapse; background: #FFFFFF; font-size: 12.5px; }}
    .ecnt-table th {{ text-align: left; background: #F8FAFC; color: #64748B; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .4px; padding: 10px 12px; border-bottom: 1px solid #CBD5E1; }}
    .ecnt-table td {{ padding: 10px 12px; border-bottom: 1px solid #E2E8F0; color: #1E293B; vertical-align: middle; }}
    .ecnt-table tr:hover td {{ background: #F8FAFC; }}
    .ecnt-tablewrap {{ border: 1px solid #CBD5E1; border-radius: 4px; overflow: auto; max-height: 520px; }}
    .ecnt-badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .ecnt-bar {{ display: flex; align-items: center; gap: 8px; }}
    .ecnt-bar .track {{ width: 90px; height: 6px; background: #E2E8F0; border-radius: 3px; overflow: hidden; }}
    .ecnt-bar .fill {{ height: 100%; }}
    .ecnt-muted {{ color: #64748B; font-size: 11px; }}

    /* Tarjetas de alerta */
    .ecnt-alert {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-left-width: 4px; border-radius: 4px;
        padding: 14px 16px; margin-bottom: 10px; }}
    .ecnt-alert .head {{ display: flex; justify-content: space-between; align-items: center; }}
    .ecnt-alert .type {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 4px;
        font-size: 11px; font-weight: 600; }}
    .ecnt-alert .title {{ font-size: 14px; font-weight: 700; margin: 8px 0 2px; color: #0F172A; }}
    .ecnt-alert p {{ font-size: 12px; color: #475569; margin: 0; }}
    .ecnt-alert .foot {{ display: flex; gap: 10px; margin-top: 10px; font-size: 11px; color: #64748B; }}

    /* Widgets de Streamlit */
    [data-testid="stMetric"] {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 12px 14px; }}
    [data-testid="stMetricLabel"] p {{ color: #64748B; font-size: 11px; }}
    [data-testid="stMetricValue"] {{ color: #0F172A; font-size: 1.35rem; }}
    [data-testid="stVerticalBlockBorderWrapper"], div[class*="st-key-card"] {{ background: #FFFFFF; border-radius: 4px; }}
    .stButton button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] button {{ background: {p['primary']}; border-color: {p['primary']};
        color: #FFFFFF; border-radius: 6px; font-weight: 600; }}
    .stButton button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover,
    [data-testid="stFormSubmitButton"] button:hover {{ background: {p['hover']}; border-color: {p['hover']}; }}
    .stButton button, [data-testid="stDownloadButton"] button {{ border-radius: 6px; font-size: 13px; }}
    [data-testid="stForm"] {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; }}
    [data-testid="stDataFrame"] {{ border: 1px solid #CBD5E1; border-radius: 4px; }}
    [data-baseweb="tab-list"] {{ gap: 4px; }}
    [data-baseweb="tab"] {{ font-size: 13px; }}
    [data-testid="stExpander"] details {{ background: #FFFFFF; border-radius: 4px; }}

    /* Login */
    .st-key-login_card {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,.05); padding: 32px 30px 18px; margin-top: 6vh; }}
    .st-key-login_card [data-testid="stForm"] {{ border: none; padding: 0; }}
    .ecnt-login-head {{ text-align: center; }}
    .ecnt-login-head .logo {{ background: {p['soft']}; color: {p['primary']}; width: 60px; height: 60px; display: flex;
        align-items: center; justify-content: center; border-radius: 12px; margin: 0 auto 14px; }}
    .ecnt-login-head h1 {{ color: #0F172A !important; font-size: 28px !important; margin: 0; padding: 0; }}
    .ecnt-login-head .subtitle {{ color: #64748B; font-size: 12px; line-height: 1.5; margin: 10px 0 18px; }}
    .ecnt-login-head .welcome {{ display: flex; align-items: center; justify-content: center; gap: 8px;
        color: {p['primary']}; font-weight: 600; font-size: 18px; }}
    .ecnt-login-head .desc {{ color: #64748B; font-size: 12px; margin: 6px 0 4px; }}
    .ecnt-login-foot {{ text-align: center; }}
    .ecnt-login-foot .security {{ display: flex; justify-content: center; align-items: center; gap: 6px;
        color: #059669; font-size: 11px; margin-top: 14px; }}
    .ecnt-login-foot footer {{ color: #94A3B8; font-size: 10px; margin-top: 12px; border-top: 1px solid #F1F5F9;
        padding-top: 12px; }}
    </style>""")


# ---------------------------------------------------------------------------------------------
# Estructura: barra lateral, barra superior, encabezados
# ---------------------------------------------------------------------------------------------
def sidebar(env: str, sections: dict, current, user: dict, on_logout) -> None:
    """Barra lateral al estilo ecnt-frontend: marca, título de sección, menú y perfil."""
    p = ENV[env]
    with st.sidebar:
        _html(f'<div class="ecnt-brand"><div class="ecnt-brand-icon">{icon("activity", 24)}</div>'
              f'<div><div class="name">{p["brand"]}</div><span>{p["tagline"]}</span></div></div>')
        for section, pages in sections.items():
            _html(f'<div class="ecnt-section">{esc(section.upper())}</div>')
            for page in pages:
                with st.container(key=f"nav_{page.url_path.replace('-', '_')}"):
                    st.page_link(page, label=page.title, icon=page.icon)
        active_key = f"nav_{current.url_path.replace('-', '_')}"
        _html(f"<style>.st-key-{active_key} a, .st-key-{active_key} [data-testid='stPageLink-NavLink']"
              f"{{background:#E2E8F0 !important;}} .st-key-{active_key} p, .st-key-{active_key} span"
              f"{{color:{p['primary']} !important;font-weight:600 !important;}}</style>")
        rol = {"admin": "Administrador", "investigador": "Investigador", "eps": "Usuario EPS"}.get(user["rol"],
                                                                                                  user["rol"])
        initial = esc((user.get("nombre") or "U")[:1].upper())
        _html(f'<div class="ecnt-profile"><div class="ecnt-avatar">{initial}</div><div>'
              f'<strong>{esc(user["nombre"])}</strong><span>{esc(rol)}</span><span class="mail">{esc(user["email"])}'
              f'</span></div></div>')
        if st.button("⎋  Cerrar sesión", width="stretch", key="logout"):
            on_logout()


def topbar(env: str, user: dict, page_title: str, notifications: int | None = None) -> None:
    initial = esc((user.get("nombre") or "U")[:1].upper())
    bell = ""
    if notifications is not None:
        dot = f'<span class="dot">{notifications}</span>' if notifications else ""
        bell = f'<div class="ecnt-bell" title="Alertas abiertas">{icon("bell", 20)}{dot}</div>'
    area = "Ambiente Administrador / Investigador" if env == "admin" else "Portal EPS"
    _html(f'<div class="ecnt-topbar"><div class="crumb">{area} › <b>{esc(page_title)}</b></div>'
          f'<div class="right">{bell}<div class="ecnt-user"><div class="ecnt-avatar">{initial}</div>'
          f'<div><strong>{esc(user["nombre"])}</strong><span>{esc(page_title)}</span></div></div></div></div>')


def page_header(title: str, subtitle: str = "", right: str = "") -> None:
    r = f'<div class="ecnt-pill">{right}</div>' if right else ""
    _html(f'<div class="ecnt-header"><div><div class="title">{esc(title)}</div><p>{esc(subtitle)}</p></div>{r}</div>')


def section(title: str, subtitle: str = "") -> None:
    _html(f'<div class="ecnt-section-heading"><div class="title">{esc(title)}</div><p>{esc(subtitle)}</p></div>')


def welcome(label: str, title: str, text: str, icon_name: str = "activity") -> None:
    _html(f'<div class="ecnt-welcome"><div><span class="label">{esc(label)}</span><div class="title">{esc(title)}</div>'
          f'<p>{esc(text)}</p></div><div class="big">{icon(icon_name, 45, "#FFFFFF")}</div></div>')


def stat_cards(items: list[tuple]) -> None:
    """items: (icono, color, etiqueta, valor, nota)."""
    cards = []
    for ic, color, label, value, small in items:
        bg, fg = COLORS[color]
        cards.append(f'<div class="ecnt-stat"><div class="ecnt-ico" style="background:{bg};color:{fg}">'
                     f'{icon(ic, 22)}</div><div><span>{esc(label)}</span><div class="val">{esc(value)}</div>'
                     f'<small>{esc(small)}</small></div></div>')
    _html(f'<div class="ecnt-stats" style="--n:{len(items)}">{"".join(cards)}</div>')


def action_card(ic: str, color: str, title: str, text: str) -> None:
    bg, fg = COLORS[color]
    _html(f'<div class="ecnt-action"><div class="ecnt-ico" style="background:{bg};color:{fg}">{icon(ic, 23)}</div>'
          f'<div><div class="title">{esc(title)}</div><p>{esc(text)}</p></div></div>')


def notice(text_html: str, kind: str = "warning", ic: str = "shield") -> None:
    _html(f'<div class="ecnt-notice {kind}">{icon(ic, 20)}<div>{text_html}</div></div>')


@contextmanager
def card(title: str | None = None, subtitle: str = ""):
    with st.container(border=True):
        if title:
            _html(f'<div class="ecnt-section-heading" style="margin-top:-6px"><div class="title">{esc(title)}</div>'
                  f'<p>{esc(subtitle)}</p></div>')
        yield


def badge(text: str, color: str) -> str:
    return f'<span class="ecnt-badge" style="background:{color}1A;color:{color}">{esc(text)}</span>'


def bar(value: float, vmax: float, color: str, label: str) -> str:
    w = 0 if not vmax else max(0, min(100, 100 * value / vmax))
    return (f'<div class="ecnt-bar"><div class="track"><div class="fill" style="width:{w:.0f}%;background:{color}">'
            f'</div></div><span>{esc(label)}</span></div>')


def html_table(headers: list[str], rows: list[list[str]]) -> None:
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    _html(f'<div class="ecnt-tablewrap"><table class="ecnt-table"><thead><tr>{th}</tr></thead>'
          f'<tbody>{body}</tbody></table></div>')


def alert_card(a: dict) -> None:
    color, bg = PRIORITY.get(a["prioridad"], ("#64748B", "#F1F5F9"))
    ic = {"alta": "alert", "media": "clock", "baja": "check"}.get(a["prioridad"], "info")
    _html(f'<div class="ecnt-alert" style="border-left-color:{color}"><div class="head">'
          f'<span class="type" style="color:{color};background:{bg}">{icon(ic, 15)} {esc(a.get("regla"))}</span>'
          f'<span class="ecnt-muted">#{a["id"]} · {esc(str(a.get("creado", ""))[:10])}</span></div>'
          f'<div class="title">{esc(a["municipio"])} <span class="ecnt-muted">({esc(a["departamento"])})</span></div>'
          f'<p>{esc(a["detalle"])}</p><div class="foot">{badge("Prioridad " + a["prioridad"], color)}'
          f'<span>Estado: <b>{esc(a["estado"])}</b></span><span>Responsable: <b>{esc(a.get("responsable") or "—")}'
          f'</b></span></div></div>')


# ---------------------------------------------------------------------------------------------
# Gráficos (estilo Recharts del frontend)
# ---------------------------------------------------------------------------------------------
def style_fig(fig: go.Figure, height: int | None = None, legend_bottom: bool = True) -> go.Figure:
    fig.update_layout(template="plotly_white", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      font=dict(family="Segoe UI, Roboto, Arial", size=11, color="#64748B"),
                      title_font=dict(size=14, color="#0F172A"), margin=dict(l=10, r=10, t=40, b=10),
                      hoverlabel=dict(font_size=12))
    fig.update_xaxes(gridcolor="#E1EAF0", linecolor="#CBD5E1", zerolinecolor="#E1EAF0")
    fig.update_yaxes(gridcolor="#E1EAF0", linecolor="#CBD5E1", zerolinecolor="#E1EAF0")
    if legend_bottom:
        fig.update_layout(legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center", title_text=""),
                          margin=dict(l=10, r=10, t=40, b=30))
    if height:
        fig.update_layout(height=height)
    return fig
