import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from pet.harvest import HarvestClient, insecure_permissions, keyring_token, load_credentials


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def fake_opener(answers, seen):
    def opener(request, timeout):
        seen.append(request)
        path = request.full_url.split("/v2/")[1].split("?")[0]
        return FakeResponse(answers[path])

    return opener


def no_keyring(command, **_):
    raise FileNotFoundError("secret-tool")


def keyring_with(token):
    def run(command, **_):
        return SimpleNamespace(returncode=0, stdout=token + "\n", stderr="")

    return run


class CredentialsTest(unittest.TestCase):
    def write(self, folder, text):
        path = Path(folder) / "harvest.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_account_and_token(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, '{"account_id": 12345, "token": " abc "}')
            self.assertEqual(load_credentials(path, no_keyring), ("12345", "abc"))

    def test_missing_incomplete_or_corrupt_gives_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_credentials(Path(folder) / "none.json", no_keyring))
            for bad in ("{oops", "[1]", '{"account_id": "1"}', '{"token": "x"}', '{"account_id": "", "token": ""}'):
                self.assertIsNone(load_credentials(self.write(folder, bad), no_keyring), bad)

    def test_token_comes_from_the_keyring_when_the_file_has_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, '{"account_id": "7"}')
            self.assertEqual(load_credentials(path, keyring_with("secret")), ("7", "secret"))

    def test_token_in_the_file_wins_over_the_keyring(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, '{"account_id": "7", "token": "file"}')
            self.assertEqual(load_credentials(path, keyring_with("secret")), ("7", "file"))

    def test_keyring_failures_give_empty_token(self):
        self.assertEqual(keyring_token(no_keyring), "")
        self.assertEqual(keyring_token(lambda c, **_: SimpleNamespace(returncode=1, stdout="x", stderr="")), "")

        def times_out(command, **_):
            raise subprocess.TimeoutExpired(command, 1)

        self.assertEqual(keyring_token(times_out), "")


class PermissionsTest(unittest.TestCase):
    def test_warns_when_others_can_read_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "harvest.json"
            path.write_text("{}", encoding="utf-8")
            os.chmod(path, 0o644)
            self.assertIn("chmod 600", insecure_permissions(path))
            os.chmod(path, 0o600)
            self.assertIsNone(insecure_permissions(path))

    def test_missing_file_gives_no_warning(self):
        self.assertIsNone(insecure_permissions("/nonexistent/harvest.json"))


class ClientTest(unittest.TestCase):
    def test_running_timer_asks_for_own_running_entries(self):
        seen = []
        answers = {"users/me": {"id": 7}, "time_entries": {"time_entries": [{"id": 1, "hours": 2.5}]}}
        client = HarvestClient("123", "tok", fake_opener(answers, seen))
        self.assertEqual(client.running_timer(), {"id": 1, "hours": 2.5})
        query = seen[-1].full_url
        self.assertIn("user_id=7", query)
        self.assertIn("is_running=true", query)
        self.assertEqual(seen[-1].get_header("Authorization"), "Bearer tok")
        self.assertEqual(seen[-1].get_header("Harvest-account-id"), "123")

    def test_no_running_entry(self):
        answers = {"users/me": {"id": 7}, "time_entries": {"time_entries": []}}
        self.assertIsNone(HarvestClient("1", "t", fake_opener(answers, [])).running_timer())

    def test_user_id_is_asked_once(self):
        seen = []
        answers = {"users/me": {"id": 7}, "time_entries": {"time_entries": []}}
        client = HarvestClient("1", "t", fake_opener(answers, seen))
        client.running_timer()
        client.running_timer()
        self.assertEqual(sum("users/me" in r.full_url for r in seen), 1)

    def test_time_url_uses_company_domain(self):
        client = HarvestClient("1", "t", fake_opener({"company": {"full_domain": "example.harvestapp.com"}}, []))
        self.assertEqual(client.time_url(), "https://example.harvestapp.com/time")

    def test_time_url_rejects_other_domains(self):
        client = HarvestClient("1", "t", fake_opener({"company": {"full_domain": "evil.example/x.harvestapp.com"}}, []))
        self.assertIsNone(client.time_url())

    def test_time_url_failure_gives_none_and_is_retried(self):
        def broken(request, timeout):
            raise OSError("offline")

        client = HarvestClient("1", "t", broken)
        self.assertIsNone(client.time_url())
        self.assertIsNone(client.domain)


if __name__ == "__main__":
    unittest.main()
