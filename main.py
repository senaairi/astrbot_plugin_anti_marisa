import os
import shutil
import json
from astrbot.api import AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_path, get_astrbot_plugin_data_path
from astrbot.core import logger

@register("astrbot_plugin_anti_marisa", "lihz", "魔理沙偷走了重要的东西", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.prompt_text = ""
        self.config = config

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

        plugin_data_path = Path(get_astrbot_plugin_data_path()) / self.name
        os.makedirs(plugin_data_path, exist_ok=True)
        custom_prompt = plugin_data_path / "prompt.md"
        if os.path.exists(custom_prompt):
            with open(custom_prompt, 'r', encoding='utf-8') as file:
                self.prompt_text = file.read()
        else:
            prompt_path = Path(get_astrbot_plugin_path()) / self.name / "prompt.md"
            with open(prompt_path, 'r', encoding='utf-8') as file:
                self.prompt_text = file.read()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.on_waiting_llm_request(priority=20)
    async def on_waiting_llm_request(self, event: AstrMessageEvent):
        if self.config.get("enable") and self.config.get("providers_id"):
            llm_resp = await self.context.llm_generate(
                chat_provider_id=self.config.get("providers_id"),
                system_prompt=self.prompt_text,
                prompt=event.get_message_str(),
            )
            try:
                res = json.loads(llm_resp.result_chain.chain[-1].text)
                if res.get('status') == 'reject':
                    msg = self.config.get('reject_message')
                    if not msg:
                        msg = res.get('attack_type')
                        if msg:
                            msg = "你的消息被拒绝：" + msg
                    if not msg:
                        msg = "An prompt attack has been detected; your message has been discarded."
                    await event.send(event.plain_result(msg))
                    event.stop_event()
            except json.JSONDecodeError as e:
                logger.warning(f"解析LLM结果异常：{e}")
                return None
        return None
