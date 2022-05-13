#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import time

import qqbot
from qqbot.core.util.yaml_util import YamlUtil
from qqbot.model.ws_context import WsContext

test_config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yaml"))

if __name__ == "__main__":
    t_token = qqbot.Token(test_config["token"]["appid"], test_config["token"]["token"])
    user_api = qqbot.UserAPI(t_token, False)
    channel_api = qqbot.ChannelAPI(t_token, False)

    guilds = user_api.me_guilds()
    for guild in guilds:
        print( f'{guild.name}, {guild.id}' )
        channels = channel_api.get_channels(guild.id)
        for channel in channels:
            print( f"  {channel.name}, {channel.id}" )
