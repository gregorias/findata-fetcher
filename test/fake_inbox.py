"""A fake implementation of gmail.InboxProtocol for testing purposes."""
import email
import enum
from dataclasses import dataclass


@enum.unique
class ENTRY_STATE(enum.Enum):
    INBOX = 'inbox'
    ARCHIVE = 'archived'


@dataclass
class InboxEntry:
    msg: email.message.Message
    state: ENTRY_STATE


class FakeInbox:

    @staticmethod
    def connect(creds):
        return FakeInbox()

    def __init__(self):
        self.entries = []

    def add_message_to_inbox(self, msg: email.message.Message):
        self.entries.append(InboxEntry(msg=msg, state=ENTRY_STATE.INBOX))

    def archive(self, num: bytes):
        """Archives a message.
        """
        assert (isinstance(num, bytes))
        idx = int(num) - 1
        assert idx < len(self.entries) and idx >= 0, f'Invalid idx ({idx})'
        self.entries[int(num) - 1].state = ENTRY_STATE.ARCHIVE

    def fetch(self, num: bytes):
        assert (isinstance(num, bytes))
        idx = int(num) - 1
        assert idx < len(self.entries) and idx >= 0, f'Invalid idx ({idx})'
        return self.entries[int(num) - 1].msg

    def search_inbox(self, subject: str) -> list[bytes]:
        nums = []
        for i, e in enumerate(self.entries):
            if (e.state == ENTRY_STATE.INBOX and subject in e.msg['Subject']):
                nums.append(str(i + 1).encode('utf-8'))
        return nums
