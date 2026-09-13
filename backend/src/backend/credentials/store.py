from pydantic import SecretStr

from backend.credentials.vault import WindowsVault
from backend.llm.client import ModelError


class CredentialStore:
    def __init__(self):
        self._key: SecretStr | None = None
        self._storage = "none"
        self._warning: str | None = None
        self._vault: WindowsVault | None = None

        try:
            self._vault = WindowsVault()
            key = self._vault.load()
        except Exception:
            self._vault = None
            self._warning = "无法访问系统凭据库，之前保存的凭据状态无法确认"
        else:
            if key:
                self._key = SecretStr(key)
                self._storage = "system"

    def set_key(self, key: str, *, remember: bool = False) -> None:
        key = key.strip()
        if not key:
            raise ValueError("API Key 不能为空")

        if self._vault is not None:
            self._delete_saved()

        self._key = SecretStr(key)
        self._storage = "session"
        self._warning = None

        if self._vault is None:
            self._warning = "凭据库不可用，当前 Key 仅本次使用；旧凭据可能仍保留"
            return

        if remember:
            self._storage = "unknown"
            self._warning = "系统凭据保存状态无法确认"
            try:
                self._vault.save(key)
            except Exception:
                self._delete_saved()
                self._storage = "session"
                self._warning = "安全保存失败，已退回仅本次使用"
            else:
                self._storage = "system"
                self._warning = None

    def require_key(self) -> str:
        if self._key is None:
            raise ModelError("MODEL_KEY_REQUIRED", "请先设置 DeepSeek API Key")
        return self._key.get_secret_value()

    def clear(self) -> None:
        self._delete_saved()
        self.release()

    def release(self) -> None:
        self._key = None
        self._storage = "none"
        self._warning = None

    def _delete_saved(self) -> None:
        try:
            if self._vault is None:
                self._vault = WindowsVault()
            self._vault.delete()
        except Exception:
            raise RuntimeError("无法清除系统凭据，请稍后重试") from None

    def status(self) -> dict:
        result = {
            "configured": self._key is not None,
            "storage": self._storage,
        }
        if self._warning:
            result["warning"] = self._warning
        return result