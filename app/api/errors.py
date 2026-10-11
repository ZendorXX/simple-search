from elastic_transport import TransportError
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

SERVICE_UNAVAILABLE_ERRORS = (TransportError, SQLAlchemyError)


def service_unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=503, detail=detail)
