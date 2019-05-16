import repo_privacy_check
import unittest
from unittest import mock
from unittest.mock import patch
from io import StringIO
import json


class MockResponse:
    def __init__(self, headers, text, status_code):
        self.headers = headers
        self.text = json.dumps(text)
        self.status_code = status_code

    def json(self):
        return self.json_data


def mocked_requests_get(*args, **kwargs):
    return MockResponse(
        {},
        [
            {"html_url": "http://github.com/test1", "private": True},
            {"html_url": "http://github.com/test2", "private": False}
        ],
        200
    )


def mocked_requests_get_err(*args, **kwargs):
    return MockResponse({}, [], 400)


def mocked_requests_post_err(*args, **kwargs):
    return MockResponse({}, [], 400)


class TestStringMethods(unittest.TestCase):
    def test_no_git_token(self):
        with patch.dict('os.environ', {"GIT_TOKEN": ""}):
            with self.assertRaises(SystemExit) as cm:
                with patch('sys.stderr', new=StringIO()) as stderr:
                    repo_privacy_check._get_env("GIT_TOKEN")
                    self.assertEqual(stderr.getvalue().strip(), "GIT_TOKEN ENV var not set")
            self.assertEqual(cm.exception.code, 1)

    def test_no_slack_hook_url(self):
        with patch.dict('os.environ', {"SLACK_HOOK": ""}):
            with self.assertRaises(SystemExit) as cm:
                with patch('sys.stderr', new=StringIO()) as stderr:
                    repo_privacy_check._get_env("SLACK_HOOK")
                    self.assertEqual(stderr.getvalue().strip(), "SLACK_HOOK ENV var not set")
            self.assertEqual(cm.exception.code, 1)

    def test_build_get_all_repos_request(self):
        with patch.dict('os.environ', {"GIT_TOKEN": "123"}):
            url, header = repo_privacy_check._build_get_all_repos_request()
            self.assertEqual(url, "https://api.github.com/orgs/ki-labs/repos")
            self.assertEqual(header, {"Authorization": "Bearer 123"})

    def test_get_last_page_no_link_in_header(self):
        r = MockResponse({}, {}, 200)
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.stderr', new=StringIO()) as stderr:
                repo_privacy_check._get_last_page(r)
                self.assertEqual(stderr.getvalue().strip(),
                                 "Calling GitHub API Error, Link does not exist in response header!")
        self.assertEqual(cm.exception.code, 1)

    def test_get_last_page_no_page_in_link(self):
        r = MockResponse({"Link": "abc"}, {}, 200)
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.stderr', new=StringIO()) as stderr:
                repo_privacy_check._get_last_page(r)
                self.assertEqual(stderr.getvalue().strip(),
                                 "Calling GitHub API Error, no page found in response header!")
        self.assertEqual(cm.exception.code, 1)

    def test_parse_public_repos(self):
        r = MockResponse(
            {},
            [
                {"html_url": "http://github.com/test1", "private": True},
                {"html_url": "http://github.com/test2", "private": False}
            ],
            200
        )
        res = repo_privacy_check._parse_public_repos(r)
        self.assertEqual(res, ["http://github.com/test2"])

    def test_parse_public_repos_all_private(self):
        r = MockResponse(
            {},
            [
                {"html_url": "http://github.com/test1", "private": True},
                {"html_url": "http://github.com/test2", "private": True}
            ],
            200
        )
        res = repo_privacy_check._parse_public_repos(r)
        self.assertEqual(res, [])

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_process_remaining_pages(self, mock_get):
        with patch.dict('os.environ', {"GIT_TOKEN": "123"}):
            public_repos = repo_privacy_check._process_remaining_pages(2)
            self.assertEqual(public_repos, ["http://github.com/test2"])

    def test_process_remaining_pages_only_1_page(self):
        public_repos = repo_privacy_check._process_remaining_pages(1)
        self.assertEqual(public_repos, [])

    def test_build_slack_payload(self):
        res = repo_privacy_check._build_slack_payload(["http://github.com/test2"])
        expected = {
            "text": "The following repositories are public:\n" + "http://github.com/test2" +
                    "\nPlease make sure they should be public!\n"
        }
        self.assertEqual(res, expected)

    def test_build_slack_payload_no_pub_repo(self):
        res = repo_privacy_check._build_slack_payload([])
        expected = {
            "text": "The following repositories are public:\n" + "\nPlease make sure they should be public!\n"
        }
        self.assertEqual(res, expected)

    @mock.patch('requests.post', side_effect=mocked_requests_post_err)
    def test_slack_notify_post_error(self, mock_post):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.stderr', new=StringIO()) as stderr:
                repo_privacy_check._slack_notify([])
                self.assertEqual(stderr.getvalue().strip(), "Posting to slack error!")
        self.assertEqual(cm.exception.code, 1)

    @mock.patch('requests.get', side_effect=mocked_requests_get_err)
    def test_run(self, mock_get):
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.stderr', new=StringIO()) as stderr:
                repo_privacy_check.run()
                self.assertEqual(stderr.getvalue().strip(), "Calling GitHub API Error!")
        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
