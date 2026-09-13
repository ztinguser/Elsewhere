from keyring.backends.Windows import WinVaultKeyring
from keyring.errors import PasswordDeleteError


class WindowsVault:
    """读写 Windows 凭据管理器"""
    def __init__(self, service: str = "Elsewhere.DeepSeek"):
        self._backend = WinVaultKeyring()
        self._backend.persist = "local machine"
        self._service = service

    def load(self) -> str | None:
        return self._backend.get_password(self._service, "api-key")

    def save(self, key: str) -> None:
        self._backend.set_password(self._service, "api-key", key)

    def delete(self) -> None:
        try:
            self._backend.delete_password(self._service, "api-key")
        except PasswordDeleteError:
            pass