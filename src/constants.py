# Playwright ``FormData`` 支持的标量类型集合，bytes 不在其中。
PLAYWRIGHT_FORM_SCALAR_TYPES: tuple[type, ...] = (str, int, float, bool)
