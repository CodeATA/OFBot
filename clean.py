#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import time

import qqbot
# import qqbot_m as qqbot
from qqbot_m.core.util.yaml_util import YamlUtil
from qqbot_m.model.ws_context import WsContext

config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yaml"))

POT_SCHEDULE_ID = config["schedule_ch"]["pot"]
STREAM_SCHEDULE_ID = config["schedule_ch"]["stream"]
GUILD_ID = config["guild"]["guild_id"]

if __name__ == "__main__":
    t_token = qqbot.Token(config["token"]["appid"], config["token"]["token"])

    schedule_api = qqbot.ScheduleAPI(t_token, False)
    all_schedule = schedule_api.get_schedules(POT_SCHEDULE_ID)

    if all_schedule == None:
        print("今日无日程 (但其他日期可能有)")
        exit()

    botself_api = qqbot.UserAPI(t_token, False)
    botself = botself_api.me()

    for sch in all_schedule:
        if sch.creator.user.id == botself.id:
            schedule_api.delete_schedule(POT_SCHEDULE_ID, sch.id)