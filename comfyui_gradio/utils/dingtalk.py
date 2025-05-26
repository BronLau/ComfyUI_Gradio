import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import logging
from comfyui_gradio.config import Config


class DingTalkBot:
    def __init__(self):
        self.enabled = Config.get("dingtalk.enabled", False)
        self.webhook = Config.get("dingtalk.webhook", "")
        self.secret = Config.get("dingtalk.secret", "")
        self.logger = logging.getLogger("dingtalk")

    def send_message(self, content: str, error: Exception = None):
        """发送普通消息或错误消息"""
        # 如果钉钉推送未启用，直接返回
        if not self.enabled:
            self.logger.info("钉钉推送未启用，跳过消息发送")
            return

        # 检查webhook和secret是否配置
        if not self.webhook or not self.secret:
            self.logger.error("钉钉推送配置不完整，请检查webhook和secret配置")
            return

        try:
            timestamp = str(round(time.time() * 1000))
            sign = self._calculate_sign(timestamp)

            headers = {'Content-Type': 'application/json'}

            # 根据是否有error参数决定消息类型
            if error:
                # 错误消息使用红色标记
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": "ComfyUI 错误告警",
                        "text": (
                            "### ComfyUI 错误告警 🚨\n\n"
                            "> **时间：**<font color=#f77c25>" +
                            time.strftime('%Y-%m-%d %H:%M:%S') + "</font>\n\n"
                            "---\n"
                            "#### 📌 错误详情\n"
                            f"```\n{content}\n```\n"
                        )
                    },
                    "at": {
                        "isAtAll": True
                    }
                }
            else:
                # 统计报告使用普通格式
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": "ComfyUI 使用统计",
                        "text": content
                    }
                }

            url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"
            response = requests.post(
                url, headers=headers, json=message, timeout=10)  # 添加超时时间
            response.raise_for_status()
            self.logger.info("钉钉消息发送成功")
        except requests.exceptions.Timeout:
            self.logger.error("钉钉消息发送超时")
        except requests.exceptions.ConnectionError:
            self.logger.error("钉钉消息发送连接失败，请检查网络连接")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"钉钉消息发送HTTP错误: {e}")
        except Exception as e:
            self.logger.error(f"钉钉消息发送失败: {e}")

    def _calculate_sign(self, timestamp: str) -> str:
        """计算签名"""
        try:
            # 按照钉钉开放平台文档要求的格式生成待签名字符串
            string_to_sign = f"{timestamp}\n{self.secret}"

            # 使用HMAC-SHA256算法计算签名
            hmac_code = hmac.new(
                self.secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()

            # Base64编码并URL转义
            return urllib.parse.quote_plus(
                base64.b64encode(hmac_code).decode('utf-8')
            )
        except Exception as e:
            self.logger.error(f"计算钉钉签名失败: {e}")
            return ""
