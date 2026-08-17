from app.scrapers.registrars.base import RegistrarAdapter
from app.scrapers.registrars.bigshare_adapter import BigshareAdapter
from app.scrapers.registrars.kfintech_adapter import KfintechAdapter
from app.scrapers.registrars.linkintime_adapter import LinkIntimeAdapter
from app.scrapers.registrars.manual_fallback_adapter import ManualFallbackAdapter

_ADAPTERS: dict[str, RegistrarAdapter] = {
    "linkintime": LinkIntimeAdapter(),
    "bigshare": BigshareAdapter(),
    "kfintech": KfintechAdapter(),
    "cameo": ManualFallbackAdapter("cameo", "https://ipo.cameoindia.com/"),
    "skyline": ManualFallbackAdapter("skyline", "https://www.skylinerta.com/ipo.php"),
    "purva": ManualFallbackAdapter("purva", "https://www.purvashare.com/ipo_allotment_status.php"),
}


def get_adapter(registrar_name: str) -> RegistrarAdapter | None:
    return _ADAPTERS.get(registrar_name)
