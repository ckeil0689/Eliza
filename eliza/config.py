# -*- coding: utf-8 -*-
"""
.. module:: useful_1
   :platform: Unix, Windows
   :synopsis: A useful module indeed.

.. moduleauthor:: Andrew Carter <andrew@invalid.com>


"""
import json
import logging
import sys

import hvac
import os
import re
import requests
import yaml

logger = logging.getLogger('eliza')


class ConfigLoader():
    """Loads yaml config files and info.json.
    """

    def __init__(self, use_vault=True, vault_addr="", vault_token="", verify=True):
        self.__use_vault = use_vault

        self.__environ_pattern = re.compile(r'^<%= ENV\[\'(.*)\'\] %\>(.*)$')
        self.__vault_pattern = re.compile(r'^<%= VAULT\[\'(.*)\'\] %\>(.*)$')
        self.__vault_addr = vault_addr or os.environ.get('VAULT_ADDR', "")
        self.__vault_token = vault_token or os.environ.get('VAULT_TOKEN', "")
        if not self.__vault_addr: logger.error("vault_addr not set")
        if not self.__vault_token: logger.error("vault_token not set")
        self.__client = self.__get_vault_client(verify)

    @staticmethod
    def load_application_info(path):
        """Will load info.json at given path.

        The info.json is used to store build/version information.

        :param path: directory where to find your config files. Example: resources/
        :return: info.json as dictionary.
        """
        with open(path + 'info.json', 'r') as infoFile:
            info = json.loads(infoFile.read())
        return info

    def load_config(self, path, environment):
        """Will load default.yaml and <environment>.yaml at given path.
        The environment config will override the default values.

        :param path: directory where to find your config files. Example: resources/
        :param environment: name of your file <environment>.yaml
        :return: your config as dictionary.
        """
        yaml.add_implicit_resolver("!environ", self.__environ_pattern)
        yaml.add_constructor('!environ', self.get_from_environment)
        yaml.add_implicit_resolver("!vault", self.__vault_pattern)
        yaml.add_constructor('!vault', self.get_from_vault)

        try:
            with open(path + 'default.yaml', 'r') as configFile:
                config = yaml.load(configFile.read())
            with open(path + environment + '.yaml', 'r') as configFile:
                env_config = yaml.load(configFile.read())
            if env_config:
                config.update(env_config)
            return config
        except hvac.exceptions.Forbidden:
            logger.error("Could not read vault secrets (Authentication forbidden). Exiting.")
            sys.exit(1)
        except yaml.YAMLError:
            logger.error("Configuration files malformed. Exiting.")
            sys.exit(1)

    def __get_vault_client(self, verify):
        try:
            client = hvac.Client(url=self.__vault_addr,
                                 token=self.__vault_token,
                                 verify=verify)
        except requests.exceptions.ConnectionError:
            logger.error("Could not reach vault ({0}). Exiting.".format(self.__vault_addr))
            sys.exit(1)
        return client

    def __get_from_environment(self, loader, node):
        value = loader.construct_scalar(node)
        env_var, remaining_path = self.__environ_pattern.match(value).groups()
        return os.environ.get(env_var, '') + remaining_path

    def __get_from_vault(self, loader, node):
        value = loader.construct_scalar(node)
        vault_path, remaining_path = self.__vault_pattern.match(value).groups()
        if self.__use_vault:
            return self.__client.read(vault_path)['data']['value'] + remaining_path
        return '' + remaining_path