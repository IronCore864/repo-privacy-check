import os
import sys
import re
import json

import requests

GIT_TOKEN = "GIT_TOKEN"
SLACK_HOOK = "SLACK_HOOK"


def _get_env(env_var):
    var = os.getenv(env_var)
    if not var:
        print("{} ENV var not set".format(env_var), file=sys.stderr)
        exit(1)
    return var


def _build_get_all_repos_request(page=None):
    org = "ki-labs"
    endpoint = "/orgs/{}/repos".format(org)
    if page:
        endpoint += "?page={}".format(page)
    url = 'https://api.github.com{}'.format(endpoint)
    headers = {"Authorization": "Bearer {}".format(_get_env(GIT_TOKEN))}
    return url, headers


# when requesting without page, the pagination info is in response headers "Links"
def _get_last_page(r):
    try:
        links = r.headers["Link"]
    except KeyError:
        print("Calling GitHub API Error, Link does not exist in response header!", file=sys.stderr)
        exit(1)

    m = re.search(r"page=([0-9]*)>; rel=\"last\"", links)
    if m:
        last_page = m.group(1)
    else:
        print("Calling GitHub API Error, no page found in response header!", file=sys.stderr)
        exit(1)
    return int(last_page)


def _parse_public_repos(r):
    public_repos = []
    json_data = json.loads(r.text)
    for repo in json_data:
        if not repo["private"]:
            public_repos.append(repo["html_url"])
    return public_repos


def _process_remaining_pages(last_page):
    public_repos = []
    for page in range(2, last_page + 1):
        url, headers = _build_get_all_repos_request(page)
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            public_repos += _parse_public_repos(r)
        else:
            print("Calling GitHub API Error!", file=sys.stderr)
            exit(1)
    return public_repos


def _build_slack_payload(public_repos):
    return {
        "text": "The following repositories are public:\n" + "\n".join(
            public_repos) + "\nPlease make sure they should be public!\n"
    }


def _slack_notify(public_repos):
    r = requests.post(
        _get_env(SLACK_HOOK),
        data=json.dumps(_build_slack_payload(public_repos)),
        headers={'Content-Type': 'application/json'}
    )
    if r.status_code != 200:
        print("Posting to slack error!", file=sys.stderr)
        exit(1)


def run():
    public_repos = []
    url, headers = _build_get_all_repos_request()
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        public_repos += _parse_public_repos(r)
        last_page = _get_last_page(r)
        public_repos += _process_remaining_pages(last_page)
    else:
        print("Calling GitHub API Error!", file=sys.stderr)
        exit(1)
    _slack_notify(public_repos)


if __name__ == "__main__":
    run()
