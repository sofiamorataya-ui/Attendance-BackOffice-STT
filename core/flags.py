"""
core/flags.py
Sistema de renderizado de banderas usando Twemoji.

Windows 10/11 desktop NO renderiza banderas emoji nativas (las muestra como letras
"GT"/"VE" en cuadrito). Para garantizar render consistente en todas las plataformas
(Windows, Mac, Linux, Android, iOS, TV) usamos Twemoji vía CDN.

Cada bandera se reemplaza por un <img> SVG de Twemoji.
"""

# CDN público de Twemoji 14 (latest stable)
TWEMOJI_BASE = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg"

# Mapeo país → unicode hex de Twemoji
FLAG_CODEPOINTS = {
    "GT": "1f1ec-1f1f9",   # 🇬🇹
    "VE": "1f1fb-1f1ea",   # 🇻🇪
    "US": "1f1fa-1f1f8",   # 🇺🇸
    "MX": "1f1f2-1f1fd",   # 🇲🇽
}


def flag_img(country_code: str, size: int = 16, css_extra: str = "") -> str:
    """
    Devuelve <img> de la bandera del país en SVG (Twemoji).

    Args:
        country_code: 'GT', 'VE', 'US', etc.
        size: tamaño en px
        css_extra: estilos adicionales (opcional)
    """
    cp = FLAG_CODEPOINTS.get(country_code.upper())
    if not cp:
        return ""
    return (
        f'<img src="{TWEMOJI_BASE}/{cp}.svg" '
        f'alt="{country_code}" '
        f'style="width:{size}px;height:{size}px;display:inline-block;'
        f'vertical-align:middle;{css_extra}" '
        f'loading="lazy" />'
    )


def flag_emoji_unicode(country_code: str) -> str:
    """
    Devuelve la bandera como caracter Unicode (fallback para st.selectbox etc.
    donde no se puede inyectar HTML).
    """
    flags = {
        "GT": "🇬🇹",
        "VE": "🇻🇪",
        "US": "🇺🇸",
        "MX": "🇲🇽",
    }
    return flags.get(country_code.upper(), "")
