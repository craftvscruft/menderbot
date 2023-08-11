from os.path import exists, join

import yaml

from menderbot.git_client import git_show_top_level


def get_config_path():
    git_path = git_show_top_level()
    if not git_path:
        return None
    return join(git_path, ".menderbot-config.yaml")


DEFAULT_CONFIG_YAML = """
# Menderbot may send source code in this repo to the enabled APIs.
# If this includes propietary information, make sure you are authorized to do so.
# Set consent to yes if this is OK.
consent: no
apis:
    openai:
        enabled: yes
        api_key_env_var: OPENAI_API_KEY
        # organization_env_var: OPENAI_ORGANIZATION
        # api_base: https://api.openai.com/v1
"""


def has_llm_consent():
    return has_config() and load_config()["consent"]


def has_config():
    config_path = get_config_path()
    return config_path and exists(get_config_path())


def create_default_config():
    config_path = get_config_path()
    if exists(config_path):
        # Should not have been called when file exists
        return
    if not config_path:
        print("Cannot resolve config path. Not in git repo?")
        return
    with open(config_path, "w", encoding="utf-8") as conf_file:
        print("Writing default config ")
        conf_file.write(DEFAULT_CONFIG_YAML)


def load_config() -> dict:
    loader = yaml.SafeLoader
    config_path = get_config_path()
    if not config_path:
        print("Cannot resolve config path. Not in git repo?")
        # Maybe should raise?
        return yaml.load("", Loader=loader)
    if not has_config():
        create_default_config()
    with open(config_path, "rb") as conf_file:
        return yaml.load(conf_file, Loader=loader)
