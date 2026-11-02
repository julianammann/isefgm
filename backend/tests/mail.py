import asyncio
from dataclasses import dataclass, field

from giftmanager.core.mail import Mail, MailError, MailFailure


@dataclass
class RecordingMailer:
    """In-memory Mailer for tests: records mails or fails on demand."""

    sent: list[Mail] = field(default_factory=list[Mail])
    fail_with: MailFailure | None = None
    delay: float = 0.0
    fail_for: dict[str, MailFailure] = field(default_factory=dict[str, MailFailure])

    async def send(self, mail: Mail) -> None:
        await asyncio.sleep(self.delay)
        if mail.to in self.fail_for:
            raise MailError(self.fail_for[mail.to], "simulated")
        if self.fail_with is not None:
            raise MailError(self.fail_with, "simulated")
        self.sent.append(mail)
