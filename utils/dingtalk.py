import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from typing import Optional
from config import Config


class DingTalkBot:
    def __init__(self):
        self.enabled = Config.get("dingtalk.enabled", False)
        self.webhook = Config.get("dingtalk.webhook")
        self.secret = Config.get("dingtalk.secret")

    def _get_sign(self) -> tuple:
        """生成钉钉签名"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc,
                             digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send_message(self, msg: str,
                     error: Optional[Exception] = None) -> bool:
        """发送消息到钉钉群"""
        if not self.enabled:
            return False

        try:
            timestamp, sign = self._get_sign()
            webhook = f"{self.webhook}&timestamp={timestamp}&sign={sign}"

            headers = {'Content-Type': 'application/json'}

            # 使用 markdown 格式构建消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "ComfyUI错误告警",
                    "text": (
                        "### ComfyUI错误告警 🚨\n\n"
                        "> **时间：**<font color=#f77c25>" +
                        time.strftime('%Y-%m-%d %H:%M:%S') + "</font>\n\n"
                        "---\n"
                        "#### 📌 错误信息\n"
                        f"<font color=#ff0000>{msg}</font>\n\n"
                        "#### 🔍 错误详情\n"
                        f"```\n{str(error) if error else '无'}\n```\n"
                    )
                },
                "at": {
                    "isAtAll": True
                }
            }

            response = requests.post(webhook, json=data, headers=headers)
            return response.status_code == 200

        except Exception as e:
            print(f"钉钉消息发送失败: {e}")
            return False
