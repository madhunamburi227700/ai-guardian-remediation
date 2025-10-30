import json


class EventStreamer:
    def __init__(self):
        self.events: list[str] = []

    def prepare_message(self, message_type: str, text: str | None = None) -> dict:
        """Builds the base message structure."""
        match message_type:
            case "error":
                data = {"type": message_type, "error": text}
            case "diff":
                data = {"type": message_type, "content": text}
            case "done":
                data = {"type": "done"}
            case _:
                data = {"type": message_type, "data": text}

        return data

    def format_message(self, data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    def emit(
        self, message_type: str = None, text: str = None, raw_data: dict | None = None
    ) -> str:
        """Creates, formats, stores, and returns a message for streaming."""
        if raw_data is not None:
            data = raw_data
        else:
            data = self.prepare_message(message_type, text)

        message = self.format_message(data)
        self.events.append(message)
        return message

    def all(self) -> list[str]:
        """Return all emitted (formatted) messages."""
        return self.events
