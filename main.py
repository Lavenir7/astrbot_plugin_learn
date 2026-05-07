from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import json

done_emoji = "✅"
todo_emoji = "✏️" # ◾

@register("astrbot_plugin_todo", "L'avenir", "TODO", "1.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.todo_json_path = Path(plugin_data_path) / "todo.json"

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""


    @filter.command("todotest")
    async def todotest(self, event: AstrMessageEvent):
        """todo插件测试"""
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(f"[todo] | {message_chain}")
        yield event.plain_result(f"{message_str}\n---\n{message_chain = }")

    def read_todo(self):
        if not self.todo_json_path.exists():
            return dict()
        with open(self.todo_json_path, "r") as f:
            return json.load(f)
    
    def write_todo(self, todo_list):
        if not self.todo_json_path.exists():
            self.todo_json_path.parent.mkdir(parents=True, exist_ok=True)
            self.todo_json_path.touch()
            with open(self.todo_json_path, "w") as f:
                json.dump(dict(), f)
        with open(self.todo_json_path, "w") as f:
            json.dump(todo_list, f)
    
    def print_todo_list(self, todo_list, user_name):
        index_width = len(str(len(todo_list)+1))
        todo_list_printer = f"{user_name} 待办列表："
        for i, todo in enumerate(todo_list):
            if todo["done"]:
                todo_list_printer += f"\n{done_emoji} [{i+1:>{index_width}}] ~~{todo['msg']}~~"
            else:
                todo_list_printer += f"\n{todo_emoji} [{i+1:>{index_width}}] {todo['msg']}"
        return todo_list_printer


    @filter.command_group("todo")
    def todo(self):
        """待办前置指令"""
        pass
    @todo.command("add")
    async def add(self, event: AstrMessageEvent, msg: str):
        """添加待办事项"""
        user_name = event.get_sender_name()
        todo_list = self.read_todo()
        if user_name not in todo_list:
            todo_list[user_name] = []
        msg_index = len(todo_list[user_name])
        todo_list[user_name].append({"msg": msg, "done": False})
        self.write_todo(todo_list)
        if len(msg) > 10:
            msg = msg[:10] + "..."
        yield event.plain_result(f"好的！已为 {user_name} 添加待办 [{msg_index+1}]: {msg}")

    @todo.command("rm")
    async def rm(self, event: AstrMessageEvent, index: int):
        """删除待办事项 n"""
        index -= 1
        user_name = event.get_sender_name()
        todo_list = self.read_todo()
        if user_name not in todo_list or len(todo_list[user_name]) == 0:
            yield event.plain_result(f"{user_name} 没有待办了呀~")
            return
        if index >= len(todo_list[user_name]) or index < 0:
            yield event.plain_result(f"没有待办 [{index+1}] 哦~")
            return
        todo_list[user_name].pop(index)
        self.write_todo(todo_list)
        yield event.plain_result(f"已删除 {user_name} 的第 {index+1} 项待办")
    
    @todo.command("done")
    async def done(self, event: AstrMessageEvent, index: int):
        """完成待办事项 n"""
        index -= 1
        user_name = event.get_sender_name()
        todo_list = self.read_todo()
        if user_name not in todo_list or len(todo_list[user_name]) == 0:
            yield event.plain_result(f"{user_name} 没有待办了呀~")
            return
        if index >= len(todo_list[user_name]) or index < 0:
            yield event.plain_result(f"没有待办 [{index+1}] 哦~")
            return
        todo_list[user_name][index]["done"] = True
        self.write_todo(todo_list)
        yield event.plain_result(f"已完成 {user_name} 的第 {index+1} 项待办")


    @todo.command("list")
    async def list(self, event: AstrMessageEvent, user_name: str = None):
        """查看待办事项列表"""
        if user_name is None:
            user_name = event.get_sender_name()
        todo_list = self.read_todo()
        if user_name not in todo_list or len(todo_list[user_name]) == 0:
            yield event.plain_result(f"{user_name} 没有待办了呀~")
            return
        todo_list = todo_list[user_name]
        todo_list_printer = self.print_todo_list(todo_list, user_name)
        yield event.plain_result(todo_list_printer)

    @todo.command("clear")
    async def clear(self, event: AstrMessageEvent, user_name: str = None):
        """清空待办事项"""
        if user_name is None:
            user_name = event.get_sender_name()
        todo_list = self.read_todo()
        if user_name not in todo_list or len(todo_list[user_name]) == 0:
            yield event.plain_result(f"{user_name} 没有待办了呀~")
            return
        todo_list[user_name] = []
        self.write_todo(todo_list)
        yield event.plain_result(f"已清空 {user_name} 的待办")



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
