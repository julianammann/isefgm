import asyncio
import socket
import time
from collections.abc import Iterator

import aiosmtplib
import httpx
import pytest
from testcontainers.core.container import DockerContainer

from giftmanager.core.config import Settings
from giftmanager.core.mail import (
    Mail,
    MailError,
    MailFailure,
    SmtpMailer,
    classify,
    is_reserved_address,
)
from tests.mail import RecordingMailer

pytestmark = pytest.mark.requirement("F-13", "Q-02")


_MAIL = Mail(to="konto@isefgm.localhost", subject="s", body="b")


def _clear_smtp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # mise loads .env into the environment; keep it out of tests that build Settings.
    for name in ("HOST", "PORT", "SECURITY", "USERNAME", "PASSWORD", "FROM", "TIMEOUT_SECONDS"):
        monkeypatch.delenv(f"SMTP_{name}", raising=False)


@pytest.fixture(scope="module")
def mailpit() -> Iterator[tuple[str, int, int]]:
    container = DockerContainer("docker.io/axllent/mailpit:v1.31.6").with_exposed_ports(1025, 8025)
    with container:
        host = container.get_container_host_ip()
        smtp_port = int(container.get_exposed_port(1025))
        http_port = int(container.get_exposed_port(8025))
        deadline = time.monotonic() + 30
        while True:
            try:
                httpx.get(
                    f"http://{host}:{http_port}/api/v1/messages", timeout=1
                ).raise_for_status()
                break
            except httpx.HTTPError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        yield host, smtp_port, http_port


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (aiosmtplib.SMTPConnectError("refused"), MailFailure.TRANSIENT),
        (aiosmtplib.SMTPConnectTimeoutError("timeout"), MailFailure.TRANSIENT),
        (aiosmtplib.SMTPAuthenticationError(535, "bad key"), MailFailure.TRANSIENT),
        (aiosmtplib.SMTPSenderRefused(451, "later", "a@b.c"), MailFailure.TRANSIENT),
        # A refused sender is a config problem for every mail, nothing was delivered: retry.
        (aiosmtplib.SMTPSenderRefused(550, "no", "a@b.c"), MailFailure.TRANSIENT),
        (
            aiosmtplib.SMTPRecipientsRefused(
                [aiosmtplib.SMTPRecipientRefused(450, "later", "x@y.z")]
            ),
            MailFailure.TRANSIENT,
        ),
        (
            aiosmtplib.SMTPRecipientsRefused(
                [aiosmtplib.SMTPRecipientRefused(550, "unknown", "x@y.z")]
            ),
            MailFailure.PERMANENT,
        ),
        (aiosmtplib.SMTPDataError(451, "later"), MailFailure.TRANSIENT),
        (aiosmtplib.SMTPDataError(554, "rejected"), MailFailure.PERMANENT),
        (aiosmtplib.SMTPDataError(-1, "malformed"), MailFailure.UNCLEAR),
        (aiosmtplib.SMTPServerDisconnected("gone"), MailFailure.UNCLEAR),
        (aiosmtplib.SMTPReadTimeoutError("slow"), MailFailure.UNCLEAR),
        (RuntimeError("boom"), MailFailure.UNCLEAR),
    ],
)
def test_classify(exc: Exception, expected: MailFailure) -> None:
    assert classify(exc) is expected


@pytest.mark.parametrize(
    ("address", "reserved"),
    [
        ("test1@example.org", True),
        ("A@Example.ORG", True),
        ("x@mail.example.org", True),
        ("x@example.com", True),
        ("x@example.net", True),
        ("x@foo.test", True),
        ("x@foo.invalid", True),
        ("x@foo.example", True),
        ("x@example.org.de", False),
        ("x@notexample.org", False),
        ("konto@isefgm.localhost", False),
    ],
)
def test_is_reserved_address(address: str, reserved: bool) -> None:
    assert is_reserved_address(address) is reserved


async def test_smtp_mailer_delivers_to_mailpit(
    mailpit: tuple[str, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    host, smtp_port, http_port = mailpit
    _clear_smtp_env(monkeypatch)
    settings = Settings(_env_file=None, smtp_host=host, smtp_port=smtp_port)  # pyright: ignore[reportCallIssue]
    await SmtpMailer(settings).send(
        Mail(
            to="konto@isefgm.localhost", subject="Geburtstage im März", body="Hallo Jörg,\n\nÄpfel"
        )
    )
    async with httpx.AsyncClient(base_url=f"http://{host}:{http_port}") as http:
        messages = (await http.get("/api/v1/messages")).json()
        assert messages["total"] == 1
        msg = messages["messages"][0]
        assert msg["Subject"] == "Geburtstage im März"
        assert msg["To"][0]["Address"] == "konto@isefgm.localhost"
        assert msg["From"] == {"Name": "Geschenke-Manager", "Address": "noreply@isefgm.localhost"}
        text = (await http.get(f"/api/v1/message/{msg['ID']}")).json()["Text"]
    assert "Hallo Jörg" in text and "Äpfel" in text


async def test_smtp_mailer_unreachable_server_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_smtp_env(monkeypatch)
    settings = Settings(_env_file=None, smtp_host="127.0.0.1", smtp_port=1, smtp_timeout_seconds=2)  # pyright: ignore[reportCallIssue]
    with pytest.raises(MailError) as err:
        await SmtpMailer(settings).send(_MAIL)
    assert err.value.failure is MailFailure.TRANSIENT


@pytest.mark.parametrize(
    "mail",
    [
        Mail(to="konto@isefgm.localhost", subject="a\nb", body="b"),
        Mail(to="a@b.c\nBcc: x@y.z", subject="s", body="b"),
    ],
    ids=["subject", "recipient"],
)
async def test_header_injection_is_permanent(mail: Mail) -> None:
    with pytest.raises(MailError) as err:
        await SmtpMailer(Settings(_env_file=None)).send(mail)  # pyright: ignore[reportCallIssue]
    assert err.value.failure is MailFailure.PERMANENT


@pytest.mark.parametrize("answers", [False, True], ids=["closes-on-greeting", "silent"])
async def test_connect_phase_failure_is_transient(
    answers: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_smtp_env(monkeypatch)

    async def handle(_: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if answers:
            await asyncio.sleep(10)  # accepts but never sends a greeting
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    settings = Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_timeout_seconds=1,
    )
    try:
        with pytest.raises(MailError) as err:
            await SmtpMailer(settings).send(_MAIL)
    finally:
        server.close()
    assert err.value.failure is MailFailure.TRANSIENT


@pytest.mark.parametrize(
    ("silent", "credentials"),
    [(False, False), (True, False), (False, True)],
    ids=["closes-after-greeting", "silent-after-greeting", "closes-after-greeting-with-login"],
)
async def test_failure_after_greeting_is_transient(
    silent: bool, credentials: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # EHLO must run in the connect phase even without STARTTLS/login: nothing was delivered yet.
    _clear_smtp_env(monkeypatch)

    async def handle(_: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(b"220 test ESMTP\r\n")
        await writer.drain()
        if silent:
            await asyncio.sleep(10)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    auth = {"smtp_username": "user", "smtp_password": "pw"} if credentials else {}
    settings = Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_timeout_seconds=1,
        **auth,
    )
    try:
        with pytest.raises(MailError) as err:
            await SmtpMailer(settings).send(_MAIL)
    finally:
        server.close()
    assert err.value.failure is MailFailure.TRANSIENT


async def test_ehlo_uses_sender_domain_without_dns_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_smtp_env(monkeypatch)

    def no_lookup() -> str:
        raise AssertionError("socket.getfqdn must not be called")

    monkeypatch.setattr(socket, "getfqdn", no_lookup)
    commands: list[str] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(b"220 test ESMTP\r\n")
        in_data = False
        while line := await reader.readline():
            text = line.decode().rstrip("\r\n")
            if in_data:
                if text == ".":
                    in_data = False
                    writer.write(b"250 queued\r\n")
            else:
                commands.append(text)
                verb = text.split(" ")[0].upper()
                in_data = verb == "DATA"
                writer.write(
                    b"354 go\r\n"
                    if in_data
                    else b"221 bye\r\n"
                    if verb == "QUIT"
                    else b"250 ok\r\n"
                )
            await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    settings = Settings(_env_file=None, smtp_host="127.0.0.1", smtp_port=port)  # pyright: ignore[reportCallIssue]
    try:
        await SmtpMailer(settings).send(_MAIL)
    finally:
        server.close()
    assert commands[0] == "EHLO isefgm.localhost"


async def test_invalid_client_config_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_smtp_env(monkeypatch)
    settings = Settings(_env_file=None, smtp_host="mail.invalid\r")  # pyright: ignore[reportCallIssue]
    with pytest.raises(MailError) as err:
        await SmtpMailer(settings).send(_MAIL)
    assert err.value.failure is MailFailure.TRANSIENT


async def test_recording_mailer_fails_on_demand_then_records() -> None:
    mailer = RecordingMailer(fail_with=MailFailure.PERMANENT)
    mail = Mail(to="konto@isefgm.localhost", subject="s", body="b")
    with pytest.raises(MailError) as err:
        await mailer.send(mail)
    assert err.value.failure is MailFailure.PERMANENT
    assert mailer.sent == []
    mailer.fail_with = None
    await mailer.send(mail)
    assert mailer.sent == [mail]
