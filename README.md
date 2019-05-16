# Description

Use GitHub API v3 to get all public repositories under a given organization and send notice to slack channel.

# Dependencies

- python3
- GitHub access token (user - settings - developer settings - personal access tokens)

```
pip install -r requirements.txt
```

# UT

```
python -m unittest
```
# Run

Get slack hook URL from slack config, get git token from 1password, or generate a new one in your account then store it in 1password for team sharing.
```
export GIT_TOKEN=xxx
export SLACK_HOOK=https://hooks.slack.com/services/xx/yy/zz
python repo_privacy_check.py
```
