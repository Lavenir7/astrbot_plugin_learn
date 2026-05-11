from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import json
from datetime import datetime

'''
todo.json:
{
    "user1": {
        "attrs": {
            "perm": "000",
            # perm: [查看待办, 操作待办, 修改属性]
            # - 000/0: 仅私人可见可操作；
            # - 100/4: 公开可查看待办；
            # - 110/6: 公开可查看、操作待办；
            # - 001/1: 公开可修改属性
            # - 111/7: 公开可查看、操作待办，可修改属性
            "create_date": "2026-05-09 19:18:32",
            "todo_number": [0, 0, 0], # [待办总数, 待办未完成数, 待办已完成数]
        },
        "todo": [
            {"msg": "...", "done": False},
        ]
    },
    "user2": {
        ...
    }
}
'''

done_emoji = "✅"
todo_emoji = "◾" # ✏️

@register("astrbot_plugin_todo", "L'avenir", "TODO", "2.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.todo_json_path = Path(plugin_data_path) / "todo.json"

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""


    @filter.command("todotest")
    async def todotest(self, event: AstrMessageEvent):
        """插件学习测试（来自todo插件）"""
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(f"[todo] | {message_chain}")
        todo_test = self.read_todo()
        yield event.plain_result(f"{todo_test}")

    def init_user_todo(self) -> dict:
        init_utd = {
            "attrs": {
                "perm": self.config["mod"],
                "create_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "todo_number": [0, 0, 0],
            },
            "todo": [],
        }
        return init_utd
    
    def todo_info(self, msg) -> dict:
        todo_inf = {
            "msg": msg,
            "done": False,
        }
        return todo_inf

    def read_todo(self) -> dict:
        if not self.todo_json_path.exists():
            return dict()
        with open(self.todo_json_path, "r") as f:
            return json.load(f)
    
    def write_todo(self, todo_list: dict) -> None:
        if not self.todo_json_path.exists():
            self.todo_json_path.parent.mkdir(parents=True, exist_ok=True)
            self.todo_json_path.touch()
            with open(self.todo_json_path, "w") as f:
                json.dump(dict(), f)
        with open(self.todo_json_path, "w") as f:
            json.dump(todo_list, f)
    
    def print_todo(self, todo_list: dict, user_name: str, simple: int = 0) -> str:
        """
        simple: 简洁等级
        - 0: 全部待办、待办统计；
        - 1: 无待办统计；
        - 2: 无待办统计和已完成待办；
        """
        todo_number = todo_list["attrs"]["todo_number"]
        index_width = len(str(todo_number[0]+1))
        todo = todo_list["todo"]
        todo_printer = f"{user_name}待办列表："
        for i, todoi in enumerate(todo):
            if todoi["done"]:
                if simple < 2:
                    todo_printer += f"\n{done_emoji} [{i+1:>{index_width}}] ~~{todoi['msg']}~~"
            else:
                todo_printer += f"\n{todo_emoji} [{i+1:>{index_width}}] {todoi['msg']}"
        if simple < 1 and todo_number[2] != 0:
            todo_printer += "\n----------"
            todo_printer += f"\n真棒，已经完成{todo_number[2]}项待办啦！"
            todo_printer += f"\n还有{todo_number[1]}项待办未完成，加油哦！"
        return todo_printer

    def update_todo_number(self, todo_list: dict, user_name: str):
        todo_number_new = [0, 0, 0]
        for todoi in todo_list[user_name]["todo"]:
            todo_number_new[0] += 1
            if todoi["done"]:
                todo_number_new[2] += 1
            else:
                todo_number_new[1] += 1
        todo_list[user_name]["attrs"]["todo_number"] = todo_number_new

    def get_mod(self, mod: str) -> str | None:
        if len(mod) == 1 and int(mod) >= 0 and int(mod) <= 7:
            mod = f"{bin(int(mod))[2:]:0>3}"
        elif len(mod) == 3 and all([mi in "01" for mi in mod]):
            mod = mod
        else:
            return None
        return mod


    @filter.command_group("todo")
    def todo(self):
        """待办前置指令"""
        pass
    @todo.command("add")
    async def add(self, event: AstrMessageEvent, msg: str, user_name: str = None):
        """添加待办事项"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        todo_list = self.read_todo()
        if user_name not in todo_list:
            todo_list[user_name] = self.init_user_todo()
            yield event.plain_result(f"你好呀，{user_name}~ 欢迎使用待办功能")
        if int(todo_list[user_name]["attrs"]["perm"][1]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有操作{user_name}待办的权限哦~")
            return
        msg_index = len(todo_list[user_name]["todo"])
        todo_list[user_name]["todo"].append(self.todo_info(msg))
        self.update_todo_number(todo_list, user_name)
        self.write_todo(todo_list)
        if len(msg) > 10:
            msg = msg[:10] + "..."
        yield event.plain_result(f"好的，已为{user_name}添加待办 [{msg_index+1}]: {msg}")

    @todo.command("rm")
    async def rm(self, event: AstrMessageEvent, index: int, user_name: str = None):
        """删除待办事项 n"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        index -= 1
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name} 没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][1]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有操作{user_name}待办的权限哦~")
            return
        if len(todo_list[user_name]["todo"]) == 0:
            yield event.plain_result(f"{user_name} 已经没有待办啦~")
            return
        if index >= len(todo_list[user_name]["todo"]) or index < 0:
            yield event.plain_result(f"没有待办 [{index+1}] 哦~")
            return
        todo_list[user_name]["todo"].pop(index)
        self.update_todo_number(todo_list, user_name)
        self.write_todo(todo_list)
        yield event.plain_result(f"好的，把{user_name}的第{index+1}项待办删掉啦！")
    
    @todo.command("done")
    async def done(self, event: AstrMessageEvent, index: int, user_name: str = None):
        """完成待办事项 n"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        index -= 1
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name}没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][1]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有操作{user_name}待办的权限哦~")
            return
        if len(todo_list[user_name]["todo"]) == 0:
            yield event.plain_result(f"{user_name}已经没有待办啦~")
            return
        if index >= len(todo_list[user_name]["todo"]) or index < 0:
            yield event.plain_result(f"没有待办 [{index+1}] 哦~")
            return
        todo_list[user_name]["todo"][index]["done"] = True
        self.update_todo_number(todo_list, user_name)
        self.write_todo(todo_list)
        yield event.plain_result(f"哇！{user_name}，你真的太棒啦！")
        yield event.plain_result(f"好的，我这就拿小本本记下来。{user_name}... 把第{index+1}项... 待办完成了！")

    @todo.command("show")
    async def show(self, event: AstrMessageEvent, user_name: str = None):
        """查看待办列表"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name}没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][1]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有查看{user_name}待办的权限哦~")
            return
        if len(todo_list[user_name]["todo"]) == 0:
            yield event.plain_result(f"{user_name}已经没有待办啦~")
            return
        todo_printer = self.print_todo(todo_list, user_name)
        yield event.plain_result(todo_printer)

    @todo.command("clear")
    async def clear(self, event: AstrMessageEvent, user_name: str = None):
        """清空待办列表"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name}没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][1]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有操作{user_name}待办的权限哦~")
            return
        if len(todo_list[user_name]["todo"]) == 0:
            yield event.plain_result(f"{user_name}已经没有待办啦~")
            return
        todo_list[user_name]["todo"] = []
        self.update_todo_number(todo_list, user_name)
        self.write_todo(todo_list)
        yield event.plain_result(f"好的，把{user_name}的待办清空啦！")

    @todo.command("chmod")
    async def chmod(self, event: AstrMessageEvent, mod: str, user_name: str = None):
        """更改待办的权限范围"""        
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name}没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][2]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有修改{user_name}待办属性的权限哦~")
            return
        mod = self.get_mod(mod)
        if mod == None:            
            yield event.plain_result('''⚠️权限格式错误！
            格式为 （查看待办, 操作待办, 修改属性），如：
            - 000/0: 仅私人可见可操作；
            - 100/4: 公开可查看待办；
            - 110/6: 公开可查看、操作待办；
            - 001/1: 公开可修改属性
            - 111/7: 公开可查看、操作待办，可修改属性''')
            return
        todo_list[user_name]["attrs"]["perm"] = mod
        self.write_todo(todo_list)
        mod_explain = (("查看待办", "操作待办", "修改属性"), ("私人", "公开"))
        yield event.plain_result(f"好的，把{user_name}待办的权限更改为【{' | '.join(f'{mod_explain[0][i]}: {mod_explain[1][int(modi)]}' for i, modi in enumerate(mod))}】啦")

    @todo.command("how")
    async def how(self, event: AstrMessageEvent, user_name: str = None):
        """让 AI 给待办做一个规划"""
        requester_name = event.get_sender_name()
        if user_name is None:
            user_name = requester_name
        todo_list = self.read_todo()
        if user_name not in todo_list:
            yield event.plain_result(f"{user_name}没有待办呀~")
            return
        if int(todo_list[user_name]["attrs"]["perm"][0]) and requester_name != user_name:
            yield event.plain_result(f"不好意思，{requester_name}。你没有查看{user_name}待办的权限哦~")
            return
        if len(todo_list[user_name]["todo"]) == 0:
            yield event.plain_result(f"{user_name}已经没有待办啦~")
            return
        umo = event.unified_msg_origin
        provider_id = await self.context.get_current_chat_provider_id(umo=umo)
        todo_printer = self.print_todo(todo_list, user_name, 2)
        prompt = f"""{self.config['how_prompt_pre']}
        ---
        > [!note]
        > 已经完成的待办已隐藏

        {todo_printer}"""
        llm_resp = await self.context.llm_generate(
            chat_provider_id=provider_id,
            prompt=prompt,
        )
        yield event.plain_result(llm_resp.completion_text)


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
