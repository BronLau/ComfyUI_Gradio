import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from config import Config


class DingTalkBot:
    def __init__(self):
        self.webhook = Config.get("dingtalk.webhook")
        self.secret = Config.get("dingtalk.secret")

    def send_message(self, content: str, error: Exception = None):
        """发送普通消息或错误消息"""
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
                            f"```\n{str(error) if error else '无'}\n```\n"
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
                        "title": "4090 ComfyUI 使用统计",
                        "text": content
                    }
                }

            url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"
            response = requests.post(url, headers=headers, json=message)
            response.raise_for_status()
        except Exception as e:
            print(f"钉钉消息发送失败: {e}")

    def _calculate_sign(self, timestamp: str) -> str:
        """计算签名"""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return urllib.parse.quote_plus(
            base64.b64encode(hmac_code).decode('utf-8')
        )
