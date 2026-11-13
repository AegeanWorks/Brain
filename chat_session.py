"""A conversation you can hold in a terminal, without losing your place.

The session owns the message list, the context cap and the transcript
formatting. It knows nothing about HTTP, so it is testable on its own and
the CLI stays a thin shell around it.

Human-facing choices worth naming:

* ``/reset`` clears history, ``/model`` shows what is being talked to, and
  the cap drops *oldest* turns while always keeping the system prompt, so
  a long conversation degrades instead of failing.
* Every reply is one short block with a footer (model, seconds), because a
  wall of untimed text is hard to trust or to compare.
"""

DEFAULT_SYSTEM = (
    "You are the assistant in a local Brain session. Be direct and "
    "concrete. If you are unsure, say so plainly."
)

#: Keep this many non-system messages; older turns are dropped first.
DEFAULT_MAX_TURNS = 24

COMMANDS = {
    "/help": "show commands",
    "/reset": "forget the conversation",
    "/model": "show the model and endpoint",
    "/quit": "leave",
}


class ChatSession:
    """Hold a bounded conversation and render it for a person."""

    def __init__(self, client, system=DEFAULT_SYSTEM, max_turns=DEFAULT_MAX_TURNS):
        if max_turns < 2:
            raise ValueError(
                "Why: max_turns must be at least 2 to keep a question and a "
                "reply. Fix: pass max_turns=24.")
        self.client = client
        self.system = str(system)
        self.max_turns = int(max_turns)
        self.messages = [{"role": "system", "content": self.system}]
        self.turns = 0

    # -- state -----------------------------------------------------------

    def reset(self):
        """Drop every turn but the system prompt; return how many were cut."""
        removed = len(self.messages) - 1
        self.messages = [{"role": "system", "content": self.system}]
        self.turns = 0
        return removed

    def _trim(self):
        """Keep the system prompt plus the newest ``max_turns`` messages."""
        body = self.messages[1:]
        overflow = len(body) - self.max_turns
        if overflow > 0:
            self.messages = [self.messages[0]] + body[overflow:]

    # -- turn ------------------------------------------------------------

    def ask(self, text, temperature=0.2, max_tokens=512):
        """Send one user turn and append the reply; return the result dict."""
        cleaned = str(text).strip()
        if not cleaned:
            raise ValueError(
                "Why: the message is empty. Fix: type a question or use /help.")
        self.messages.append({"role": "user", "content": cleaned})
        result = self.client.chat(self.messages, temperature=temperature,
                                  max_tokens=max_tokens)
        self.messages.append({"role": "assistant", "content": result["text"]})
        self.turns += 1
        self._trim()
        return result

    # -- rendering -------------------------------------------------------

    @staticmethod
    def footer(result):
        """One line naming the model and how long the reply took."""
        model = result.get("model") or "unknown model"
        seconds = result.get("seconds") or 0.0
        return "[%s, %.1fs]" % (model, seconds)

    @staticmethod
    def banner(client, source=None):
        """Greeting that states what is being talked to and how to leave."""
        model, base = client.identify()
        where = "%s at %s" % (model or "server default model", base)
        if source:
            where += " (%s)" % source
        return ("Brain chat — %s\n"
                "Type your message. /help for commands, /quit to leave."
                % where)

    @staticmethod
    def help_text():
        """Return the command list as aligned lines."""
        width = max(len(name) for name in COMMANDS)
        return "\n".join("%-*s  %s" % (width, name, text)
                         for name, text in COMMANDS.items())
