"""
core/flags.py
Sistema de banderas que funciona en TODOS los entornos.

IMPORTANTE:
- Windows 10/11 desktop NO renderiza banderas emoji nativas (las muestra como "GT"/"VE")
- Android/iOS SÍ las renderizan
- Twemoji JS funciona en la página principal pero puede fallar en iframes

ESTRATEGIA:
- Para HTML inline (cards, tablas): usar `flag_img_inline()` que devuelve <img> SVG directo
- Para selectbox y otros widgets de Streamlit que no permiten HTML: usar `flag_emoji_unicode()`
"""

TWEMOJI_BASE = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg"

FLAG_CODEPOINTS = {
    "GT": "1f1ec-1f1f9",   # 🇬🇹
    "VE": "1f1fb-1f1ea",   # 🇻🇪
    "US": "1f1fa-1f1f8",   # 🇺🇸
    "MX": "1f1f2-1f1fd",   # 🇲🇽
}


def flag_img_inline(country_code: str, size: int = 14) -> str:
    """
    Devuelve <img> SVG de la bandera (sin depender de JS de Twemoji).
    Usar en HTML inline donde queremos que funcione SIEMPRE.

    Args:
        country_code: 'GT', 'VE', 'US', etc.
        size: tamaño en px (default 14 = mini al lado del nombre)
    """
    cp = FLAG_CODEPOINTS.get(str(country_code).upper())
    if not cp:
        return ""
    return (
        f'<img src="{TWEMOJI_BASE}/{cp}.svg" '
        f'alt="{country_code}" '
        f'style="width:{size}px;height:{size}px;display:inline-block;'
        f'vertical-align:middle;margin-right:6px;" '
        f'loading="lazy" />'
    )


def flag_emoji_unicode(country_code: str) -> str:
    """
    Devuelve el caracter Unicode de la bandera.
    Usar SOLO en widgets de Streamlit donde no se puede inyectar HTML
    (selectbox, radio, etc.). El JS global de Twemoji se encarga de convertirlas.
    """
    flags = {
        "GT": "🇬🇹",
        "VE": "🇻🇪",
        "US": "🇺🇸",
        "MX": "🇲🇽",
    }
    return flags.get(str(country_code).upper(), "")
