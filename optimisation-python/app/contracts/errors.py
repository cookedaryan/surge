"""Stable contract error raised by request resolvers and mapped by the endpoint."""

from app.contracts.codes import ContractErrorCode


class ContractError(Exception):
    def __init__(
        self,
        code: ContractErrorCode,
        message: str,
        *,
        http_status: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status

    def detail(self) -> dict[str, str]:
        return {"code": self.code.value, "message": self.message}
