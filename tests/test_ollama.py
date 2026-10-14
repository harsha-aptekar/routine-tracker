"""Tests for the Ollama client and the prompt builder, using a fake local server."""
import json
import threading
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

from routine_tracker.lifelog import Achievement, ClaudeRequest
from routine_tracker.ollama_client import Ollama, OllamaError
from routine_tracker.recommend import _bullets_only, build_prompt
from routine_tracker.stats import BlockStat, Period, Report, Skip
from routine_tracker.study import StudyReport

MODELS = {"models": [{"name": "tiny:1b", "size": 1}, {"name": "mid:3b", "size": 2}]}


class FakeOllama(BaseHTTPRequestHandler):
    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(MODELS)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self._send({"response": f"  echo {payload['model']}: {payload['prompt'][:5]}  "})

    def log_message(self, *args):
        pass


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.host = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_uses_largest_installed_model(self):
        self.assertEqual(Ollama(host=self.host).generate("hello"), "echo mid:3b: hello")

    def test_configured_model_wins(self):
        self.assertEqual(Ollama("big:7b", self.host).generate("hello"), "echo big:7b: hello")

    def test_unreachable_server_gives_friendly_error(self):
        with self.assertRaises(OllamaError) as caught:
            Ollama(host="http://127.0.0.1:1").generate("x")
        self.assertIn("Is it running", str(caught.exception))


class PromptTest(unittest.TestCase):
    def test_prompt_contains_the_facts(self):
        day = date(2026, 10, 12)
        study = StudyReport({"Python": 120}, {"Python": 360}, [Achievement(day, "study_1", "Python", "decorators")], [ClaudeRequest(day, "explain asyncio")], ["Algebra"])
        routine = Report(70, 80, 0, 0, {}, [BlockStat("Study 06:30", 40, 2, 0, 3)], {}, [Skip(day, "Study 06:30", "overslept")], {}, None)
        prompt = build_prompt(Period.week(day), study, routine)
        for expected in ("Python: 2.0h this period, 6.0h last period", "not studied at all this period: Algebra", "Weak block: Study 06:30 done only 40%", "overslept", "decorators", "I asked Claude: explain asyncio", "TASK:"):
            self.assertIn(expected, prompt)

    def test_preamble_is_stripped(self):
        self.assertEqual(_bullets_only("Here are tips:\n\n* Do A\n- Do B\nbye"), "* Do A\n- Do B")
        self.assertEqual(_bullets_only("no bullets here"), "no bullets here")
