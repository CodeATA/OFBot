#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from cgi import test
import os.path
import time
import re

import qqbot
# import qqbot_m as qqbot
from qqbot.core.util.yaml_util import YamlUtil
from qqbot.model.ws_context import WsContext

config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yaml"))

POT_SCHEDULE_ID = config["schedule_ch"]["pot"]
STREAM_SCHEDULE_ID = config["schedule_ch"]["stream"]
GUILD_ID = config["guild"]["guild_id"]

appoint_pat = re.compile(r"/预约直播 (?P<command>.*)")
cancel_pat = re.compile(r"/取消直播 (?P<sch_id>.*)")
split_pat = re.compile(r";|；")
time_pat = re.compile(r"(?P<mon>[0-9][0-9]?)-(?P<day>[0-9][0-9]?)\s+(?P<hour>[0-9][0-9]?)(:(?P<min>[0-9][0-9]?))?")

def process_command(command: str):
    res = {}
    res['stat'] = 0

    command_split = re.split(split_pat, command, maxsplit=3)
    res['title'] = command_split[0]
    start_time = command_split[1]
    end_time = command_split[2]
    description = ''
    if len(command_split) > 3:
            description = command_split[3]
    
    start_time = start_time.replace('：', ':')
    end_time = end_time.replace('：', ':')
    cur_time = time.localtime()
    m_start = re.match(time_pat, start_time)
    m_end = re.match(time_pat, end_time)
    if m_start:
        start_mon = int(m_start.group('mon'))
        start_day = int(m_start.group('day'))
        start_hour = int(m_start.group('hour'))
        if m_start.group('min') == None:
            start_min = int(0)
        else:
            start_min = int(m_start.group('min'))
    else:
        res['stat'] = 1 # 起始时间格式错误
        return res
    
    if m_end:
        end_mon = int(m_end.group('mon'))
        end_day = int(m_end.group('day'))
        end_hour = int(m_end.group('hour'))
        if m_end.group('min') == None:
            end_min = int(0)
        else:
            end_min = int(m_end.group('min'))
    else:
        res['stat'] = 2 # 结束时间格式错误
        return res

    if start_mon < cur_time.tm_mon:
        start_year = cur_time.tm_year + 1
    else:
        start_year = cur_time.tm_year
    if end_mon < cur_time.tm_mon:
        end_year = cur_time.tm_year + 1
    else:
        end_year = cur_time.tm_year
    start_time_struct = time.strptime(f"{start_year}-{start_mon}-{start_day} {start_hour}:{start_min}", '%Y-%m-%d %H:%M')
    end_time_struct = time.strptime(f"{end_year}-{end_mon}-{end_day} {end_hour}:{end_min}", '%Y-%m-%d %H:%M')
    start_timestamp = int(time.mktime(start_time_struct) * 1000)
    end_timestamp = int(time.mktime(end_time_struct) * 1000)

    if start_timestamp > end_timestamp:
        res['stat'] = 3 # 结束时间需要晚于起始时间
        return res
    
    res['description'] = description
    res['start_timestamp'] = str(start_timestamp)
    res['end_timestamp'] = str(end_timestamp)

    return res

async def _schedule_handler(context: WsContext, message: qqbot.Message):
    # msg_api = qqbot.AsyncMessageAPI(t_token, False)
    dmsg_api = qqbot.AsyncDmsAPI(t_token, False)
    schedule_api = qqbot.AsyncScheduleAPI(t_token, False)
    channel_api = qqbot.AsyncChannelAPI(t_token, False)

    qqbot.logger.info("event_type %s" % context.event_type + ",receive message %s" % message.content)

    if message.content.startswith("/预约直播"):
        # command_str = re.match(appoint_pat, message.content).group('command')
        processed_sch = process_command(re.match(appoint_pat, message.content).group('command'))

        if processed_sch['stat'] == 1:
            message_to_send = qqbot.MessageSendRequest(
                content="起始时间格式错误！",
                msg_id=message.id
                )
            await dmsg_api.post_direct_message(message.guild_id, message_to_send)
            return
        elif processed_sch['stat'] == 2:
            message_to_send = qqbot.MessageSendRequest(
                content="结束时间格式错误！",
                msg_id=message.id
                )
            await dmsg_api.post_direct_message(message.guild_id, message_to_send)
            return
        elif processed_sch['stat'] == 3:
            message_to_send = qqbot.MessageSendRequest(
                content="结束时间需晚于起始时间！",
                msg_id=message.id
                )
            await dmsg_api.post_direct_message(message.guild_id, message_to_send)
            return

        to_create = qqbot.ScheduleToCreate(
            name = processed_sch['title'],
            description = processed_sch['description'],
            start_timestamp = processed_sch['start_timestamp'],
            end_timestamp = processed_sch['end_timestamp'],
            remind_type="0",
        )
        schedule = await schedule_api.create_schedule(
            POT_SCHEDULE_ID,
            to_create
        )
        '''
        这里需要更新一次日程，把刚刚创建的日程ID附在日程描述的最后。
        这是因为现阶段QQ频道API十分蛋疼，只有日程创建者能更新或删除日程。
        而机器人创建的日程无论传不传creator参数进去，创建者永远是机器人。
        这可能也是为了避免创建者变动后机器人无法修改，但也导致了无法使用创建者来找到要修改的日程。
        另一个蛋疼的地方是获取日程列表的API只能获取当天的日程，所以只能把日程ID附在描述里，否则找不到正确的日程。
        '''
        to_patch = qqbot.ScheduleToPatch(
            name = processed_sch['title'],
            description = processed_sch['description'] + f"\n\n{schedule.id}",
            start_timestamp = processed_sch['start_timestamp'],
            end_timestamp = processed_sch['end_timestamp'],
            remind_type="0",
        )
        patched_schedule = await schedule_api.update_schedule(
            POT_SCHEDULE_ID,
            schedule.id,
            to_patch
        )
        ret_message = qqbot.MessageSendRequest(
            content=f'日程创建成功，ID：{patched_schedule.id}',
            msg_id=message.id
        )
        await dmsg_api.post_direct_message(message.guild_id, ret_message)

    elif message.content.startswith("/取消直播"):
        sch_id = re.match(cancel_pat, message.content).group('sch_id')
        to_cancel = await schedule_api.get_schedule(POT_SCHEDULE_ID, sch_id)
        if to_cancel == None:
            message_to_send = qqbot.MessageSendRequest(
                content='日程 ID 错误，日程不存在！',
                msg_id=message.id
                )
            await dmsg_api.post_direct_message(message.guild_id, message_to_send)
            return
        await schedule_api.delete_schedule(POT_SCHEDULE_ID, sch_id)

    elif message.content.startswith("/频道列表"):
        channels = await channel_api.get_channels(GUILD_ID)
        msg_content = ''
        for ch in channels:
            if ch.name != '':
                msg_content += f"{ch.name}, {ch.id}\n"
        message_to_send = qqbot.MessageSendRequest(
            content=msg_content,
            msg_id=message.id
        )
        await dmsg_api.post_direct_message(message.guild_id, message_to_send)
    
    elif message.content.startswith("/绑定点歌"):
        return

    else:
        message_to_send = qqbot.MessageSendRequest(
            content='指令列表：\n/预约直播 标题;开始时间(mm-dd HH:MM);结束时间(mm-dd HH:MM);描述(可选)\n/取消直播 日程ID\n/更新直播 日程ID;\n/频道列表\n/绑定点歌 频道ID（未实装，仅监听频道消息）',
            msg_id=message.id
            )
        await dmsg_api.post_direct_message(message.guild_id, message_to_send)
        return


if __name__ == "__main__":
    t_token = qqbot.Token(config["token"]["appid"], config["token"]["token"])
    qqbot_handler = qqbot.Handler(qqbot.HandlerType.DIRECT_MESSAGE_EVENT_HANDLER, _schedule_handler)
    qqbot.async_listen_events(t_token, False, qqbot_handler)
