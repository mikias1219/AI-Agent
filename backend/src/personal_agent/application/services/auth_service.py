"""Single-owner local authentication, including existing environment-based passwords."""

import hashlib
import hmac

from personal_agent.application.security.passwords import hash_password, verify_password
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import WorkspaceAccount
from personal_agent.domain.ports import WorkspaceAccountRepository


class WorkspaceAuthService:
    def __init__(self, accounts: WorkspaceAccountRepository, configured_hash: str) -> None:
        self._accounts = accounts
        self._configured_hash = configured_hash

    def registered(self) -> bool:
        return bool(self._accounts.get() or self._configured_hash)

    def requires_email(self) -> bool:
        return self._accounts.get() is not None

    def profile(self) -> dict[str, str]:
        account = self._accounts.get()
        return (
            {"name": account.name, "email": account.email}
            if account
            else {"name": "Friend", "email": ""}
        )

    def register(self, name: str, email: str, password: str) -> None:
        if self.registered():
            raise StorageError("This local workspace already has an owner. Please log in.")
        if not name.strip() or len(password) < 8:
            raise ValueError("Enter your name and a password with at least 8 characters.")
        self._accounts.create(
            WorkspaceAccount(name.strip(), email.strip().lower(), hash_password(password))
        )

    def verify(self, password: str, email: str = "") -> bool:
        account = self._accounts.get()
        encoded = account.password_hash if account else self._configured_hash
        valid = verify_password(password, encoded)
        return valid and (not account or email.strip().lower() == account.email)

    def session_key(self, secret: str) -> str:
        account = self._accounts.get()
        encoded = account.password_hash if account else self._configured_hash
        return hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()

    def reset_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Use a password with at least 8 characters.")
        self._accounts.update_password(hash_password(password))
