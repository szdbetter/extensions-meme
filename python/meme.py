"""
Solana代币信息查询工具
作者: Your Name
版本: 1.0.0
描述: 该工具用于查询Solana链上代币信息，支持图片显示和基本信息展示
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLineEdit, QTextEdit, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QPixmap
import sys
import os
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json

# 设置Qt属性
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

class CoinDataFetcher:
    """代币数据获取类"""

    BASE_URL = "https://frontend-api-v3.pump.fun/coins/search"

    @staticmethod
    def fetch_coin_data(contract_address: str) -> Optional[Dict[str, Any]]:
        """
        获取代币数据

        Args:
            contract_address: 代币合约地址

        Returns:
            Optional[Dict]: 代币数据字典或None（如果获取失败）
        """
        params = {
            "offset": 0,
            "limit": 50,
            "sort": "market_cap",
            "includeNsfw": False,
            "order": "DESC",
            "searchTerm": contract_address,
            "type": "exact"
        }

        try:
            response = requests.get(CoinDataFetcher.BASE_URL, params=params)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            return data[0] if data and len(data) > 0 else None
        except requests.RequestException as e:
            print(f"API请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None

class ImageHandler:
    """图片处理类"""

    @staticmethod
    def download_and_display_image(image_url: str, label: QLabel) -> bool:
        """
        下载并显示图片

        Args:
            image_url: 图片URL
            label: 用于显示图片的QLabel控件

        Returns:
            bool: 是否成功显示图片
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()

            temp_file = "temp_image.png"
            with open(temp_file, "wb") as f:
                f.write(response.content)

            pixmap = QPixmap(temp_file)
            label.setPixmap(pixmap.scaled(
                label.width(),
                label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))

            os.remove(temp_file)
            return True

        except Exception as e:
            print(f"图片处理错误: {e}")
            return False

class TimeUtil:
    """时间工具类"""

    @staticmethod
    def get_time_diff(timestamp_ms: int) -> str:
        """
        计算时间差并返回友好的显示格式

        Args:
            timestamp_ms: 毫秒时间戳

        Returns:
            str: 格式化的时间差字符串
        """
        created_time = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
        now = datetime.now(timezone.utc)
        diff = now - created_time

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60

        if days > 0:
            return f"{days}天前"
        elif hours > 0:
            return f"{hours}小时前"
        else:
            return f"{minutes}分钟前"

class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        """初始化主窗口"""
        super(MainWindow, self).__init__()
        self.init_ui()

    def init_ui(self):
        """初始化UI组件"""
        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(current_dir, "Main.ui")

        if not os.path.exists(ui_file):
            self.show_error_and_exit(f"错误: UI文件不存在: {ui_file}")

        # 加载UI
        loader = QUiLoader()
        try:
            self.ui = loader.load(ui_file)
            if self.ui is None:
                self.show_error_and_exit("错误: 无法加载UI文件")
        except Exception as e:
            self.show_error_and_exit(f"加载UI文件时出错: {str(e)}")

        # 获取并验证控件
        self.init_controls()

        # 连接信号和槽
        self.btnQuery.clicked.connect(self.query_coin_info)

        # 显示主窗口
        self.ui.show()

    def init_controls(self):
        """初始化并验证控件"""
        self.btnQuery = self.ui.findChild(QPushButton, 'btnQuery')
        self.leCA = self.ui.findChild(QLineEdit, 'leCA')
        self.txtCoinInfo = self.ui.findChild(QTextEdit, 'txtCoinInfo')
        self.labelCoinPic = self.ui.findChild(QLabel, 'labelCoinPic')

        if not all([self.btnQuery, self.leCA, self.txtCoinInfo, self.labelCoinPic]):
            self.show_error_and_exit("错误: 无法找到所有必需的UI控件")

        # 设置默认CA地址
        default_ca = "9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump"
        self.leCA.setText(default_ca)

        # 自动触发查询
        self.query_coin_info()

    def format_coin_info(self, coin_data: Dict[str, Any]) -> str:
        """
        格式化代币信息，使用HTML格式美化显示

        Args:
            coin_data: 代币数据字典

        Returns:
            str: HTML格式的代币信息
        """
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', '')
        created_time = TimeUtil.get_time_diff(coin_data.get('created_timestamp', 0))
        description = coin_data.get('description', '暂无描述')
        image_uri = coin_data.get('image_uri', '')
        twitter = coin_data.get('twitter', '')
        website = coin_data.get('website', '')
        contract = coin_data.get('mint', '')

        # 使用HTML格式化信息
        html = f"""
        <html>
        <head>
        <style type="text/css">
            .container {{
                font-family: Arial, sans-serif;
                padding: 10px;
            }}
            .header {{
                display: flex;
                align-items: flex-start;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .coin-image {{
                width: 80px;
                height: 80px;
                object-fit: contain;
            }}
            .title {{
                font-size: 16px;
                margin-bottom: 5px;
            }}
            .info {{
                flex: 1;
            }}
            .description {{
                margin-top: 10px;
                line-height: 1.4;
            }}
            .buttons {{
                margin-top: 15px;
            }}
            .button {{
                display: inline-block;
                padding: 5px 10px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 3px;
                margin-right: 10px;
                font-size: 12px;
            }}
        </style>
        </head>
        <body>
        <div class='container'>
            <div class='header'>
                <img src='{image_uri}' class='coin-image' onerror="this.src='default.png'"/>
                <div class='info'>
                    <div class='title'>代币名称：{name} ({symbol})，{created_time}</div>
                    <div class='description'>
                        代币介绍：<br/>
                        {description}
                    </div>
                </div>
            </div>
            <div class='buttons'>
                <a href='https://gmgn.ai/sol/token/{contract}' class='button' target='_blank'>GMGN</a>
                <a href='https://www.pump.news/en/{contract}-solana' class='button' target='_blank'>PUMPNEWS</a>
                <a href='https://twitter.com/search?q={contract}' class='button' target='_blank'>搜推特</a>
                <a href='{twitter}' class='button' target='_blank'>官推</a>
                <a href='{website}' class='button' target='_blank'>官网</a>
            </div>
        </div>
        </body>
        </html>
        """
        return html

    def query_coin_info(self):
        """查询代币信息"""
        contract_address = self.leCA.text().strip()
        if not contract_address:
            error_html = """
            <html>
            <head>
            <style type="text/css">
                .error-message {
                    color: #e74c3c;
                    font-family: Arial, sans-serif;
                    padding: 10px;
                    font-size: 14px;
                }
            </style>
            </head>
            <body>
                <div class='error-message'>
                    请输入代币合约地址
                </div>
            </body>
            </html>
            """
            self.txtCoinInfo.setHtml(error_html)
            return
            
        # 获取代币数据
        coin_data = CoinDataFetcher.fetch_coin_data(contract_address)
        
        if coin_data:
            # 显示代币信息
            self.txtCoinInfo.setHtml(self.format_coin_info(coin_data))
            self.txtCoinInfo.setOpenExternalLinks(True)  # 允许打开外部链接
        else:
            error_html = """
            <html>
            <head>
            <style type="text/css">
                .error-message {
                    color: #e74c3c;
                    font-family: Arial, sans-serif;
                    padding: 10px;
                    font-size: 14px;
                }
            </style>
            </head>
            <body>
                <div class='error-message'>
                    未找到代币信息或发生错误
                </div>
            </body>
            </html>
            """
            self.txtCoinInfo.setHtml(error_html)

    @staticmethod
    def show_error_and_exit(message: str):
        """显示错误信息并退出程序"""
        print(message)
        sys.exit(1)

def main():
    """程序入口函数"""
    try:
        # 创建应用
        app = QApplication(sys.argv)
        window = MainWindow()
        sys.exit(app.exec())
    except Exception as e:
        print(f"程序启动时出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
