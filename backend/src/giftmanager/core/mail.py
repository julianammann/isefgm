"""Outgoing e-mail: the `Mailer` interface, its SMTP implementation and failure classes.

Callers decide retry vs. no-retry only from `MailFailure`:
- TRANSIENT: the server certainly did not accept the mail, so a retry is safe.
- PERMANENT: the server rejected the mail for good, so a retry is pointless.
- UNCLEAR: the mail may or may not have been delivered, so a retry could duplicate it.
"""

import enum
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from typing import Protocol

import aiosmtplib

from giftmanager.core.config import Settings, get_settings

_RESERVED_DOMAINS = ("example.org", "example.com", "example.net")
_RESERVED_TLDS = ("test", "invalid", "example")


@dataclass(frozen=True)
class Mail:
    """A plain-text mail to one recipient."""

    to: str
    subject: str
    body: str


class MailFailure(enum.StrEnum):
    """Why a send failed; decides retry vs. no-retry."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNCLEAR = "unclear"


class MailError(Exception):
    """The only exception a `Mailer` raises."""

    def __init__(self, failure: MailFailure, detail: str) -> None:
        super().__init__(f"{failure.value}: {detail}")
        self.failure = failure
        self.detail = detail


class Mailer(Protocol):
    """Sends mail; implementations raise only `MailError`."""

    async def send(self, mail: Mail) -> None:
        """Send `mail`; raises only `MailError`."""
        ...


def _by_code(code: int) -> MailFailure:
    if 400 <= code < 500:
        return MailFailure.TRANSIENT
    if 500 <= code < 600:
        return MailFailure.PERMANENT
    # e.g. aiosmtplib's -1 for a malformed reply, which can arrive after the final dot.
    return MailFailure.UNCLEAR


def classify(exc: Exception) -> MailFailure:
    """Map an exception from the SMTP exchange to a `MailFailure`."""
    # Order matters: subclasses first (SMTPConnectTimeoutError is also an SMTPTimeoutError,
    # SMTPAuthenticationError is also an SMTPResponseException).
    if isinstance(
        exc,
        aiosmtplib.SMTPConnectError | aiosmtplib.SMTPAuthenticationError | aiosmtplib.SMTPHeloError,
    ):
        return MailFailure.TRANSIENT
    if isinstance(exc, aiosmtplib.SMTPRecipientsRefused):
        if all(400 <= r.code < 500 for r in exc.recipients):
            return MailFailure.TRANSIENT
        return MailFailure.PERMANENT
    if isinstance(exc, aiosmtplib.SMTPResponseException):
        return _by_code(exc.code)
    return MailFailure.UNCLEAR


def is_reserved_address(address: str) -> bool:
    """True for RFC 2606 / 6761 reserved domains, which must never receive real mail."""
    domain = address.rpartition("@")[2].lower()
    if domain.rpartition(".")[2] in _RESERVED_TLDS:
        return True
    return any(domain == d or domain.endswith(f".{d}") for d in _RESERVED_DOMAINS)


def _sender_domain(settings: Settings) -> str:
    return parseaddr(settings.smtp_from)[1].rpartition("@")[2]


class SmtpMailer:
    """`Mailer` that delivers over SMTP using the `smtp_*` settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, mail: Mail) -> None:
        """Send `mail`; any failure is raised as a classified `MailError`."""
        s = self._settings
        try:
            message = EmailMessage()
            message["From"] = s.smtp_from
            message["To"] = mail.to
            message["Subject"] = mail.subject
            message["Date"] = formatdate(localtime=False)
            message["Message-ID"] = make_msgid(domain=_sender_domain(s))
            message.set_content(mail.body)
        except Exception as exc:  # e.g. CR/LF in a header; nothing was sent
            raise MailError(MailFailure.PERMANENT, str(exc)) from exc
        try:
            client = aiosmtplib.SMTP(
                hostname=s.smtp_host,
                port=s.smtp_port,
                use_tls=s.smtp_security == "tls",
                # An explicit False: otherwise aiosmtplib opportunistically tries STARTTLS.
                start_tls=s.smtp_security == "starttls",
                username=s.smtp_username,
                password=s.smtp_password.get_secret_value() if s.smtp_password else None,
                timeout=s.smtp_timeout_seconds,
                # Explicit: otherwise aiosmtplib calls socket.getfqdn(), a DNS lookup on every send.
                local_hostname=_sender_domain(s),
            )
        except Exception as exc:  # e.g. a host with CR/LF; a fixed config retries fine
            raise MailError(MailFailure.TRANSIENT, str(exc)) from exc
        try:
            # Greeting, EHLO, STARTTLS and login: no mail transaction has started yet.
            try:
                await client.connect()
                # connect() runs EHLO itself only with STARTTLS/login; otherwise send_message would.
                if client.is_ehlo_or_helo_needed:
                    await client.ehlo()
            except Exception as exc:
                raise MailError(MailFailure.TRANSIENT, str(exc)) from exc
            try:
                await client.send_message(message)
            except Exception as exc:
                raise MailError(classify(exc), str(exc)) from exc
        finally:
            # A failed close must not turn a sent mail into a failure.
            try:
                await client.quit()
            except Exception:  # noqa: BLE001
                client.close()


def get_mailer() -> Mailer:
    """Return the configured mailer."""
    return SmtpMailer(get_settings())
