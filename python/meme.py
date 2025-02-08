"""
Solana代币信息查询工具
作者: Your Name
版本: 1.0.0
描述: 该工具用于查询Solana链上代币信息，支持图片显示和基本信息展示
"""

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLineEdit,
                             QTextEdit, QLabel, QTableView, QStyledItemDelegate, QStyle, QHeaderView,
                             QListView, QStyleOptionViewItem, QTabWidget)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import (Qt, QCoreApplication, QAbstractTableModel, QModelIndex, QThread, Signal,
                         QDateTime, QSize, QUrl, QAbstractListModel, QEvent, QRect)
from PySide6.QtGui import (QPixmap, QColor, QBrush, QFont, QPalette,
                          QStandardItemModel, QStandardItem, QTextDocument,
                          QAbstractTextDocumentLayout, QDesktopServices)
from qt_material import apply_stylesheet
import sys
import os
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import base64
import locale
import urllib.parse

# 设置Qt属性
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# 设置数字格式化
locale.setlocale(locale.LC_ALL, '')

class TableStyleDelegate(QStyledItemDelegate):
    """表格样式代理类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.header_font = QFont()
        self.header_font.setPointSize(12)  # 设置表头字体大小

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # 设置表头样式
        if isinstance(index.model(), QAbstractTableModel):
            if index.parent().isValid() == False and index.model().headerData(index.row(), Qt.Vertical, Qt.DisplayRole) is not None:
                option.font = self.header_font
                return

        # 设置买卖操作的背景色
        model = index.model()
        if hasattr(model, '_data') and index.row() < len(model._data):
            op = model._data[index.row()].get('op', '')
            if op == 'buy':
                option.backgroundBrush = QBrush(QColor('#e6ffe6'))  # 浅绿色
            elif op == 'sell':
                option.backgroundBrush = QBrush(QColor('#ffe6e6'))  # 浅红色

class ApiWorker(QThread):
    """API异步工作线程"""
    finished = Signal(object)  # 完成信号
    error = Signal(str)      # 错误信号

    def __init__(self, api_call, *args, **kwargs):
        super().__init__()
        self.api_call = api_call
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.api_call(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DevHistoryTableModel(QAbstractTableModel):
    """开发者历史发币表格模型"""

    def __init__(self, data: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = ["发币", "成功", "市值", "时间"]
        self._sort_column = 0  # 默认排序列
        self._sort_order = Qt.AscendingOrder  # 默认升序

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            row_data = self._data[index.row()]
            col = index.column()

            if col == 0:
                return row_data.get('symbol', '')
            elif col == 1:
                return "是" if row_data.get('complete', False) else "否"
            elif col == 2:
                market_cap = row_data.get('usd_market_cap', 0)
                return self.format_market_cap(market_cap)
            elif col == 3:
                timestamp = row_data.get('created_timestamp', 0)
                return TimeUtil.get_time_diff(timestamp)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder):
        """实现排序"""
        self.layoutAboutToBeChanged.emit()

        if column == 0:  # 发币
            self._data.sort(key=lambda x: x.get('symbol', ''), reverse=(order == Qt.DescendingOrder))
        elif column == 1:  # 成功
            self._data.sort(key=lambda x: x.get('complete', False), reverse=(order == Qt.DescendingOrder))
        elif column == 2:  # 市值
            self._data.sort(key=lambda x: x.get('usd_market_cap', 0), reverse=(order == Qt.DescendingOrder))
        elif column == 3:  # 时间
            self._data.sort(key=lambda x: x.get('created_timestamp', 0), reverse=(order == Qt.DescendingOrder))

        self._sort_column = column
        self._sort_order = order
        self.layoutChanged.emit()

    @staticmethod
    def format_market_cap(value: float) -> str:
        """格式化市值显示"""
        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        return f"{value:.1f}"

class DevTradeTableModel(QAbstractTableModel):
    """开发者交易记录表格模型"""

    def __init__(self, data: List[Dict[str, Any]], creator: str, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = ["操作", "From", "To", "价格", "金额", "数量", "时间"]
        self.creator = creator
        self._sort_column = 0
        self._sort_order = Qt.AscendingOrder

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            row_data = self._data[index.row()]
            col = index.column()

            if col == 0:
                op_map = {
                    "buy": "买入",
                    "sell": "卖出",
                    "trans_in": "转入",
                    "trans_out": "转出"
                }
                return op_map.get(row_data.get('op', ''), '')
            elif col == 1:
                address = row_data.get('from', '')
                return "Dev" if address == self.creator else self.format_address(address)
            elif col == 2:
                address = row_data.get('to', '')
                return "Dev" if address == self.creator else self.format_address(address)
            elif col == 3:
                price = row_data.get('price', 0)
                return f"${price:.6f}" if price else ''
            elif col == 4:
                volume = row_data.get('volume', 0)
                return locale.format_string("%d", int(volume), grouping=True) if volume else ''
            elif col == 5:
                amount = row_data.get('amount', 0)
                return locale.format_string("%d", int(amount), grouping=True) if amount else ''
            elif col == 6:
                timestamp = row_data.get('time', 0)
                return TimeUtil.get_time_diff(timestamp * 1000)  # 转换为毫秒

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder):
        """实现排序"""
        self.layoutAboutToBeChanged.emit()

        if column == 0:  # 操作
            self._data.sort(key=lambda x: x.get('op', ''), reverse=(order == Qt.DescendingOrder))
        elif column == 1:  # From
            self._data.sort(key=lambda x: x.get('from', ''), reverse=(order == Qt.DescendingOrder))
        elif column == 2:  # To
            self._data.sort(key=lambda x: x.get('to', ''), reverse=(order == Qt.DescendingOrder))
        elif column == 3:  # 价格
            self._data.sort(key=lambda x: x.get('price', 0), reverse=(order == Qt.DescendingOrder))
        elif column == 4:  # 金额
            self._data.sort(key=lambda x: x.get('volume', 0), reverse=(order == Qt.DescendingOrder))
        elif column == 5:  # 数量
            self._data.sort(key=lambda x: x.get('amount', 0), reverse=(order == Qt.DescendingOrder))
        elif column == 6:  # 时间
            self._data.sort(key=lambda x: x.get('time', 0), reverse=(order == Qt.DescendingOrder))

        self._sort_column = column
        self._sort_order = order
        self.layoutChanged.emit()

    @staticmethod
    def format_address(address: str) -> str:
        """格式化地址显示"""
        if len(address) <= 6:
            return address
        return f"{address[:3]}...{address[-3:]}"

class DevDataFetcher:
    """开发者数据获取类"""

    @staticmethod
    def fetch_dev_history(creator: str) -> Optional[List[Dict[str, Any]]]:
        """获取开发者历史发币记录"""
        url = f"https://frontend-api-v3.pump.fun/coins/user-created-coins/{creator}"
        params = {
            "offset": 0,
            "limit": 10,
            "includeNsfw": False
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取开发者历史记录失败: {e}")
            return None

    @staticmethod
    def fetch_dev_trades(contract: str) -> Optional[Dict[str, Any]]:
        """获取开发者交易记录"""
        url = f"https://debot.ai/api/dashboard/token/dev/info"
        params = {
            "chain": "solana",
            "token": contract
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get('data', {})
        except Exception as e:
            print(f"获取开发者交易记录失败: {e}")
            return None

    @staticmethod
    def format_dev_info(creator: str, original_text: str = "") -> str:
        """格式化开发者信息"""
        dev_info = f"""<span style='color: #000; font-weight: bold;'>DEV信息：</span>
                  <a href='https://gmgn.ai/sol/address/{creator}' style='color: #3498db; text-decoration: none;'>{creator}</a>
                  <span style='cursor: pointer; font-size: 0.5em;' 
                  onclick='window.copyDevAddress("{creator}")'>📋</span>"""
        return f"""
        <html>
        <head>
        <style>
            a:hover {{ text-decoration: underline; }}
        </style>
        <script>
            function copyDevAddress(address) {{
                navigator.clipboard.writeText(address);
                window.logCopied(address);
            }}
        </script>
        </head>
        <body>
            {dev_info}
        </body>
        </html>
        """

    @staticmethod
    def format_dev_history(history_data: List[Dict[str, Any]]) -> str:
        """格式化开发者历史信息"""
        if not history_data:
            return "未找到开发者历史信息"

        total_coins = len(history_data)
        success_coins = sum(1 for coin in history_data if coin.get('complete', False))
        max_market_cap = max((coin.get('usd_market_cap', 0) for coin in history_data), default=0)

        total_display = f"{total_coins}+" if total_coins >= 10 else str(total_coins)
        success_display = f"{success_coins}+" if success_coins >= 10 else str(success_coins)
        market_cap_display = DevHistoryTableModel.format_market_cap(max_market_cap)

        return f"发币：{total_display}次，成功：{success_display}次，最高市值：{market_cap_display}"

    @staticmethod
    def format_dev_trade_status(trade_data: Dict[str, Any]) -> str:
        """格式化开发者交易状态"""
        status = []

        if trade_data.get('position_clear'):
            status.append("<span style='color: #e74c3c;'>清仓</span>")
        if trade_data.get('position_increase'):
            status.append("加仓")
        if trade_data.get('position_decrease'):
            status.append("减仓")
        if trade_data.get('trans_out_amount', 0) > 0:
            status.append("转出")

        return "，".join(status) if status else "无操作"

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
    def get_image_base64(image_url: str) -> str:
        """
        获取图片的base64编码

        Args:
            image_url: 图片URL

        Returns:
            str: base64编码的图片数据
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/png;base64,{image_data}"
        except Exception as e:
            print(f"图片处理错误: {e}")
            return ""

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

class SmartMoneyTableModel(QAbstractTableModel):
    """聪明钱交易表格模型"""

    def __init__(self, data: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = ["聪明钱", "操作", "价格", "金额(SOL)"]
        print(f"SmartMoneyTableModel initialized with {len(data)} rows")  # 调试信息

    def rowCount(self, parent=QModelIndex()) -> int:
        count = len(self._data)
        print(f"rowCount called, returning {count}")  # 调试信息
        return count

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            try:
                row_data = self._data[index.row()]
                col = index.column()

                if col == 0:  # 聪明钱
                    address = row_data.get('address', '')
                    labels = row_data.get('labels', [])
                    return ', '.join(labels) if labels else address[:6] + '...'
                elif col == 1:  # 操作
                    return "买入" if row_data.get('is_buy', False) else "卖出"
                elif col == 2:  # 价格
                    return f"${row_data.get('price_usd', 0):.4f}"
                elif col == 3:  # 金额
                    return f"{int(row_data.get('volume_native', 0))}"
            except Exception as e:
                print(f"Error in data method: {e}")  # 调试信息
                return str(e)

        elif role == Qt.BackgroundRole:
            row_data = self._data[index.row()]
            if row_data.get('is_buy', False):
                return QBrush(QColor('#e6ffe6'))  # 浅绿色
            else:
                return QBrush(QColor('#ffe6e6'))  # 浅红色

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

class SocialTableModel(QAbstractTableModel):
    """社交媒体表格模型"""

    def __init__(self, tweets=None, parent=None):
        super().__init__(parent)
        self._tweets = tweets or []
        self._headers = ["用户名", "蓝标", "浏览", "点赞", "转发", "内容"]
        self._sort_column = 0
        self._sort_order = Qt.AscendingOrder

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tweets)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            tweet = self._tweets[index.row()]
            col = index.column()
            user = tweet.get("user", {})

            if col == 0:  # 用户名
                return f"{user.get('name', '')} (@{user.get('screen_name', '')})"
            elif col == 1:  # 蓝标
                return "✓" if user.get("is_blue_verified") else ""
            elif col == 2:  # 浏览
                return f"{tweet.get('views', 0):,}"
            elif col == 3:  # 点赞
                return f"{tweet.get('favorite_count', 0):,}"
            elif col == 4:  # 转发
                return f"{tweet.get('retweet_count', 0):,}"
            elif col == 5:  # 内容
                return tweet.get("text", "")

        elif role == Qt.TextAlignmentRole:
            if index.column() in [2, 3, 4]:  # 数字列右对齐
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.ForegroundRole:
            if index.column() == 1:  # 蓝标列使用Twitter蓝色
                return QColor("#1DA1F2")

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder):
        """实现排序"""
        self.layoutAboutToBeChanged.emit()

        if column == 0:  # 用户名
            self._tweets.sort(key=lambda x: x.get("user", {}).get("name", ""), reverse=(order == Qt.DescendingOrder))
        elif column == 1:  # 蓝标
            self._tweets.sort(key=lambda x: x.get("user", {}).get("is_blue_verified", False), reverse=(order == Qt.DescendingOrder))
        elif column == 2:  # 浏览
            self._tweets.sort(key=lambda x: x.get("views", 0), reverse=(order == Qt.DescendingOrder))
        elif column == 3:  # 点赞
            self._tweets.sort(key=lambda x: x.get("favorite_count", 0), reverse=(order == Qt.DescendingOrder))
        elif column == 4:  # 转发
            self._tweets.sort(key=lambda x: x.get("retweet_count", 0), reverse=(order == Qt.DescendingOrder))
        elif column == 5:  # 内容
            self._tweets.sort(key=lambda x: x.get("text", ""), reverse=(order == Qt.DescendingOrder))

        self._sort_column = column
        self._sort_order = order
        self.layoutChanged.emit()

class HTMLDelegate(QStyledItemDelegate):
    """HTML格式的列表项代理"""
    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = options.widget.style() if options.widget else QApplication.style()

        doc = QTextDocument()
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        return QSize(doc.idealWidth(), doc.size().height())

class HeadlessBrowser:
    """无头浏览器工具类，用于处理需要浏览器环境的API请求"""

    @staticmethod
    async def login_chain_fm(page):
        """登录Chain.fm"""
        try:
            # 访问登录页面
            await page.goto('https://chain.fm/login')

            # 等待登录按钮出现
            await page.waitForSelector('button[data-provider="google"]')

            # 点击Google登录按钮
            await page.click('button[data-provider="google"]')

            # 等待登录完成，这里需要等待URL变化
            await page.waitForNavigation()

            # 检查是否登录成功
            current_url = page.url
            if 'chain.fm' in current_url and 'login' not in current_url:
                print("登录成功")
                return True
            else:
                print("登录失败")
                return False

        except Exception as e:
            print(f"登录过程出错: {str(e)}")
            return False

    @staticmethod
    async def fetch_with_puppeteer(url: str) -> Optional[Dict]:
        """
        使用Puppeteer无头浏览器获取API数据

        Args:
            url: API地址

        Returns:
            Optional[Dict]: API返回的数据或None（如果获取失败）
        """
        try:
            import asyncio
            from pyppeteer import launch

            # 启动浏览器，这里设置为非无头模式以便调试
            browser = await launch(
                headless=False,  # 设置为False以便查看浏览器操作
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            # 创建新页面
            page = await browser.newPage()

            # 设置页面视口
            await page.setViewport({'width': 1920, 'height': 1080})

            # 设置用户代理
            await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36')

            # 先进行登录
            login_success = await HeadlessBrowser.login_chain_fm(page)
            if not login_success:
                await browser.close()
                return None

            # 访问API URL
            response = await page.goto(url)

            # 等待页面加载完成
            await page.waitForSelector('body')

            # 获取响应内容
            content = await response.json()

            # 关闭浏览器
            await browser.close()

            return content

        except Exception as e:
            print(f"Puppeteer请求失败: {str(e)}")
            return None

    @staticmethod
    def fetch_api_data(url: str) -> Optional[Dict]:
        """
        同步方式调用Puppeteer获取API数据

        Args:
            url: API地址

        Returns:
            Optional[Dict]: API返回的数据或None（如果获取失败）
        """
        try:
            import asyncio
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            loop = asyncio.get_event_loop()
            return loop.run_until_complete(HeadlessBrowser.fetch_with_puppeteer(url))

        except Exception as e:
            print(f"获取API数据失败: {str(e)}")
            return None

class NodeService:
    """Node.js服务交互类"""

    BASE_URL = "http://localhost:3000"

    @staticmethod
    def fetch_chain_fm_data(contract_address: str) -> Optional[Dict]:
        """
        从本地Node.js服务获取Chain.fm数据

        Args:
            contract_address: 代币合约地址

        Returns:
            Optional[Dict]: API返回的数据或None（如果获取失败）
        """
        try:
            url = "https://chain.fm/api/trpc/parsedTransaction.list"

            # 构建batch请求格式
            batch_input = {
                "0": {
                    "json": {
                        "page": 1,
                        "pageSize": 30,
                        "dateRange": None,
                        "token": contract_address,
                        "address": [],
                        "useFollowing": True,
                        "includeChannels": [],
                        "lastUpdateTime": None,
                        "events": []
                    },
                    "meta": {
                        "values": {
                            "dateRange": ["undefined"],
                            "lastUpdateTime": ["undefined"]
                        }
                    }
                }
            }

            # 构建完整的URL
            full_url = f"{url}?batch=1&input={json.dumps(batch_input)}"

            response = requests.post(NodeService.BASE_URL, json={
                "url": full_url,
                "dataType": "chain_fm_transactions"
            })

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return result.get('response', {}).get('data', [])
            else:
                print(f"获取数据失败: {result.get('error')}")
                return None

        except Exception as e:
            print(f"从Node.js服务获取数据失败: {str(e)}")
            return None

class NoDataTableModel(QAbstractTableModel):
    """无数据时的表格模型"""

    def __init__(self, message="暂无数据", parent=None):
        super().__init__(parent)
        self._message = message
        self._headers = ["提示"]

    def rowCount(self, parent=QModelIndex()) -> int:
        return 1

    def columnCount(self, parent=QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self._message
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        """初始化主窗口"""
        super(MainWindow, self).__init__()
        self.clipboard = QApplication.clipboard()  # 初始化剪贴板
        self.current_tweet_category = "top"  # 默认推文类型
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
        self.btnQueryTradeInfo.clicked.connect(self.query_gmgn_info)

        # 显示主窗口
        self.ui.show()

    def init_controls(self):
        """初始化并验证控件"""
        # 定义所有需要的控件及其名称
        controls = {
            'btnQuery': (QPushButton, '查询按钮'),
            'btnQueryTradeInfo': (QPushButton, 'GMGN数据查询按钮'),
            'leCA': (QLineEdit, '合约地址输入框'),
            'labelDevInfo': (QLabel, '开发者信息标签'),
            'labelDevHistory': (QLabel, '开发者历史标签'),
            'labelDevTrade': (QLabel, '开发者交易标签'),
            'tableDevHistory': (QTableView, '开发者历史表格'),
            'tableDevTrade': (QTableView, '开发者交易表格'),
            'tableSmartMoney': (QTableView, '聪明钱交易表格'),
            'tableSocial': (QTableView, '社交媒体表格'),
            'labelSmartMoneyInfo': (QLabel, '聪明钱统计信息'),
            'listViewLog': (QListView, '日志列表'),
            'labelCoinPic': (QLabel, '代币图片'),
            'labelCoinSymbol': (QLabel, '代币名称'),
            'labelCoinDescription': (QLabel, '代币描述'),
            'labelFilterTweets': (QLabel, '推文数标签'),
            'labelFollowers': (QLabel, '关注者标签'),
            'labelLikes': (QLabel, '点赞标签'),
            'labelViews': (QLabel, '浏览标签'),
            'labelOfficalTweets': (QLabel, '官方推文标签'),
            'labelSmartBuy': (QLabel, '智能买入标签'),
            'tabSocialOptions': (QTabWidget, '推文类型选项卡'),
            'labelHolderInfo': (QLabel, 'Holder信息'),
            'labelWalletTag': (QLabel, '钱包分类'),
            'labelTop10': (QLabel, 'Top10'),
        }

        # 检查每个控件
        missing_controls = []
        for control_name, (control_type, display_name) in controls.items():
            control = self.ui.findChild(control_type, control_name)
            if control is None:
                missing_controls.append(f"{display_name}({control_name})")
            setattr(self, control_name, control)

        if missing_controls:
            self.show_error_and_exit(f"错误: 以下UI控件未找到:\n" + "\n".join(missing_controls))

        # 初始化日志列表模型
        self.log_model = QStandardItemModel()
        self.listViewLog.setModel(self.log_model)

        # 设置列表视图可以选择和复制
        self.listViewLog.setSelectionMode(QListView.ExtendedSelection)  # 允许多选
        self.listViewLog.setTextElideMode(Qt.ElideNone)  # 不省略文本

        # 设置列表视图样式
        self.listViewLog.setStyleSheet("""
            QListView {
                border: 1px solid #dcdcdc;
                background-color: white;
                font-size: 12px;
            }
            QListView::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListView::item:selected {
                background-color: #e3f2fd;
                color: #000000;
            }
            QListView::item:nth-child(odd) {
                background-color: #f8f9fa;
            }
            QListView::item:nth-child(even) {
                background-color: white;
            }
        """)

        # 移除之前的按钮样式，使用Material主题样式
        self.btnQuery.setProperty('class', 'primary')  # 使用Material主题的主要按钮样式
        self.btnQueryTradeInfo.setProperty('class', 'primary')  # 使用Material主题的主要按钮样式

        # 设置表格样式，与Material主题配合
        table_delegate = TableStyleDelegate()
        for table in [self.tableDevHistory, self.tableDevTrade, self.tableSocial]:
            table.setItemDelegate(table_delegate)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            # 启用表格排序
            table.setSortingEnabled(True)
            # 设置表格样式
            table.setStyleSheet("""
                QTableView {
                    border: 1px solid #dcdcdc;
                    background-color: white;
                    gridline-color: #f0f0f0;
                }
                QTableView::item {
                    padding: 5px;
                }
                QTableView::item:hover {
                    background-color: #f8f9fa;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    padding: 5px;
                    border: none;
                    border-right: 1px solid #dcdcdc;
                    border-bottom: 1px solid #dcdcdc;
                }
                QHeaderView::section:hover {
                    background-color: #e3f2fd;
                }
            """)

        # 设置列表视图样式，与Material主题配合
        self.listViewLog.setProperty('class', 'dense')  # 使用Material主题的紧凑列表样式

        # 设置默认CA地址
        default_ca = "9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump"
        self.leCA.setText(default_ca)

        # 连接推文类型切换事件
        self.tabSocialOptions.currentChanged.connect(self.on_tweet_tab_changed)

    def copy_dev_address(self, address: str):
        """复制开发者地址到剪贴板"""
        self.clipboard.setText(address)
        self.add_log("复制成功", f"已复制Dev地址：{address}")

    @staticmethod
    def format_dev_info(creator: str) -> str:
        """格式化开发者信息"""
        return f"""
        <html>
        <head>
        <style>
            a:hover {{ text-decoration: underline; }}
            .copy-icon {{
                cursor: pointer;
                font-size: 0.5em;
                color: #666;
            }}
            .dev-label {{
                color: #000;
                font-weight: bold;
            }}
            .dev-address {{
                color: #3498db;
                text-decoration: none;
            }}
        </style>
        </head>
        <body>
            <span class='dev-label'>DEV信息：</span>
            <a href='https://gmgn.ai/sol/address/{creator}' class='dev-address'>{creator}</a>
            <span class='copy-icon' onclick='copyAddress'> 📋</span>
        </body>
        </html>
        """

    def format_coin_info(self, coin_data: Dict[str, Any]) -> str:
        """格式化代币信息，使用Material Design风格"""
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', '')
        created_time = TimeUtil.get_time_diff(coin_data.get('created_timestamp', 0))
        description = coin_data.get('description', '暂无描述')
        image_uri = coin_data.get('image_uri', '')
        twitter = coin_data.get('twitter', '')
        website = coin_data.get('website', '')
        contract = coin_data.get('mint', '')

        # 获取base64编码的图片
        image_data = ImageHandler.get_image_base64(image_uri) if image_uri else ''

        # 更新HTML样式以匹配Material Design
        html = f"""
        <html>
        <head>
        <style type="text/css">
            .container {{
                font-family: Roboto, Arial, sans-serif;
                padding: 16px;
                max-width: 800px;
                background-color: var(--background);
                color: var(--text);
            }}
            .header {{
                display: flex;
                align-items: flex-start;
                gap: 16px;
                margin-bottom: 16px;
            }}
            .coin-image {{
                width: 48px;
                height: 48px;
                object-fit: cover;
                border-radius: 8px;
                flex-shrink: 0;
            }}
            .info {{
                flex: 1;
                min-width: 0;
            }}
            .title {{
                font-size: 18px;
                font-weight: 500;
                margin-bottom: 8px;
                color: var(--primary);
            }}
            .description {{
                font-size: 14px;
                line-height: 1.5;
                color: var(--text-secondary);
            }}
            .buttons {{
                margin-top: 16px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }}
            .button {{
                display: inline-block;
                padding: 8px 16px;
                background-color: var(--primary);
                color: var(--on-primary);
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            .button:hover {{
                background-color: var(--primary-dark);
            }}
        </style>
        </head>
        <body>
        <div class='container'>
            <div class='header'>
                <img src='{image_data}' class='coin-image' onerror="this.style.display='none'"/>
                <div class='info'>
                    <div class='title'>{name} ({symbol})</div>
                    <div class='description'>
                        创建时间：{created_time}<br/>
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

    def update_dev_info(self, coin_data: Dict[str, Any]):
        """更新开发者信息"""
        creator = coin_data.get('creator')
        if not creator:
            return

        # 获取开发者历史记录
        history_data = DevDataFetcher.fetch_dev_history(creator)
        if history_data:
            # 更新开发者信息标签
            self.labelDevInfo.setText(self.format_dev_info(creator))
            self.labelDevInfo.setOpenExternalLinks(True)  # 允许打开外部链接

            # 设置点击事件
            self.labelDevInfo.mousePressEvent = lambda e: self.handle_dev_info_click(e, creator)

            self.labelDevHistory.setText(DevDataFetcher.format_dev_history(history_data))

            # 按市值排序
            sorted_history = sorted(history_data,
                                  key=lambda x: (x.get('usd_market_cap', 0), x.get('created_timestamp', 0)),
                                  reverse=True)

            # 更新历史表格
            history_model = DevHistoryTableModel(sorted_history)
            self.tableDevHistory.setModel(history_model)
            self.tableDevHistory.resizeColumnsToContents()

        # 获取开发者交易记录
        trade_data = DevDataFetcher.fetch_dev_trades(coin_data.get('mint', ''))
        if trade_data and 'transactions' in trade_data:
            # 更新交易表格
            trade_model = DevTradeTableModel(trade_data['transactions'], creator)
            self.tableDevTrade.setModel(trade_model)
            self.tableDevTrade.resizeColumnsToContents()

    def add_log(self, operation: str, status: str = "", link: str = ""):
        """添加日志到列表视图
        Args:
            operation: 正在执行的操作
            status: 状态信息（成功/失败及相关数据）
            link: 可选的链接
        """
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")

        # 构建HTML格式的日志文本
        log_html = f"""
        <div style='margin: 2px 0;'>
            <span style='color: #666;'>[{current_time}]</span> 
            <span style='color: #000000;'>▶ {operation}</span>
        """

        if link:
            log_html += f""" <a href='{link}' style='color: #2196F3; text-decoration: none;'>[链接]</a>"""

        if status:
            if "成功" in status:
                status_color = "#4CAF50"  # 绿色
            elif "失败" in status or "错误" in status:
                status_color = "#F44336"  # 红色
                status = f"<b>{status}</b>"  # 加粗错误信息
            else:
                status_color = "#000000"  # 黑色
            log_html += f""" <span style='color: {status_color};'>→ {status}</span>"""

        log_html += "</div>"

        item = QStandardItem()
        item.setData(log_html, Qt.DisplayRole)

        # 设置交替背景色
        row = self.log_model.rowCount()
        if row % 2 == 0:
            item.setBackground(QBrush(QColor("#f8f9fa")))
        else:
            item.setBackground(QBrush(QColor("#ffffff")))

        self.log_model.insertRow(0, item)  # 在顶部插入
        self.listViewLog.setItemDelegate(HTMLDelegate(self.listViewLog))  # 使用HTML代理
        self.listViewLog.scrollToTop()

    def clear_previous_results(self):
        """清空上次查询的结果"""
        # 清空表格
        self.tableDevTrade.setModel(None)
        self.tableDevHistory.setModel(None)

        # 清空标签
        self.labelDevInfo.clear()
        self.labelDevHistory.clear()
        self.labelDevTrade.clear()
        self.labelFilterTweets.clear()
        self.labelFollowers.clear()
        self.labelLikes.clear()
        self.labelViews.clear()
        self.labelOfficalTweets.clear()
        self.labelSmartBuy.clear()
        self.labelCoinDescription.clear()
        self.labelCoinSymbol.clear()
        self.labelCoinPic.clear()
        self.labelSmartMoneyInfo.clear()

    def query_coin_info(self):
        """查询代币信息"""
        contract_address = self.leCA.text().strip()
        if not contract_address:
            self.show_error_message("请输入代币合约地址")
            return

        # 清空上次查询结果
        self.clear_previous_results()

        # 禁用查询按钮
        self.btnQuery.setEnabled(False)
        self.btnQuery.setText("查询中...")

        # 添加日志
        self.add_log("开始查询代币信息", f"合约地址: {contract_address}", f"https://gmgn.ai/sol/token/{contract_address}")

        # 1. 创建异步工作线程获取代币数据
        self.coin_worker = ApiWorker(CoinDataFetcher.fetch_coin_data, contract_address)
        self.coin_worker.finished.connect(lambda data: self.on_coin_data_received(data, contract_address))
        self.coin_worker.error.connect(self.on_api_error)
        self.coin_worker.start()

    def on_coin_data_received(self, coin_data, contract_address):
        """处理代币数据"""
        if coin_data:
            # 添加日志
            self.add_log("获取代币信息",
                        f"成功 - {coin_data.get('name', '')} ({coin_data.get('symbol', '')})",
                        f"https://gmgn.ai/sol/token/{coin_data.get('mint', '')}")

            # 更新代币相关标签
            self.update_coin_labels(coin_data)

            # 2. 获取开发者交易记录
            creator = coin_data.get('creator')
            if creator:
                self.add_log("请求开发者交易记录", "正在获取...", f"https://gmgn.ai/sol/address/{creator}")
                self.trade_worker = ApiWorker(DevDataFetcher.fetch_dev_trades, coin_data.get('mint', ''))
                self.trade_worker.finished.connect(lambda data: self.on_trade_data_received(data, creator, contract_address))
                self.trade_worker.error.connect(self.on_api_error)
                self.trade_worker.start()
        else:
            self.add_log("获取代币信息", "失败 - 未找到代币信息或发生错误")
            self.btnQuery.setEnabled(True)
            self.btnQuery.setText("查询")

    def on_trade_data_received(self, trade_data, creator, contract_address):
        """处理交易数据"""
        if trade_data:
            self.labelDevTrade.setText(f"交易信息（{DevDataFetcher.format_dev_trade_status(trade_data)}）")

            if 'transactions' in trade_data:
                self.add_log("获取开发者交易记录", f"成功 - {len(trade_data['transactions'])}条交易")
                trade_model = DevTradeTableModel(trade_data['transactions'], creator)
                self.tableDevTrade.setModel(trade_model)

                # 3. 获取开发者历史记录
                self.add_log("请求开发者历史记录", "正在获取...", f"https://gmgn.ai/sol/address/{creator}")
                self.history_worker = ApiWorker(DevDataFetcher.fetch_dev_history, creator)
                self.history_worker.finished.connect(lambda data: self.on_history_data_received(data, creator, contract_address))
                self.history_worker.error.connect(self.on_api_error)
                self.history_worker.start()

    def on_history_data_received(self, history_data, creator, contract_address):
        """处理历史数据"""
        if history_data:
            self.add_log("获取开发者历史记录", f"成功 - {len(history_data)}条记录")

            # 更新开发者信息标签
            self.labelDevInfo.setText(self.format_dev_info(creator))
            self.labelDevInfo.setOpenExternalLinks(True)

            # 设置点击事件
            self.labelDevInfo.mousePressEvent = lambda e: self.handle_dev_info_click(e, creator)

            self.labelDevHistory.setText(DevDataFetcher.format_dev_history(history_data))

            # 按市值排序
            sorted_history = sorted(history_data,
                                  key=lambda x: (x.get('usd_market_cap', 0), x.get('created_timestamp', 0)),
                                  reverse=True)

            history_model = DevHistoryTableModel(sorted_history)
            self.tableDevHistory.setModel(history_model)

            # 4. 获取聪明钱数据
            self.add_log("请求聪明钱信息", "正在获取...", "https://chain.fm")
            try:
                data = NodeService.fetch_chain_fm_data(contract_address)
                if data and len(data) > 0:
                    result = data[0].get('result', {})
                    transactions = result.get('data', {}).get('json', {}).get('data', {}).get('parsedTransactions', [])
                    address_labels = result['data']['json']['data']['data'][0]['renderContext']['addressLabelsMap']
                    self.update_smart_money_info(transactions, address_labels)

                    # 5. 获取社交媒体信息
                    self.get_social_media_info(contract_address)
                else:
                    self.add_log("获取聪明钱数据", "失败 - 返回数据为空")
                    # 即使聪明钱数据为空，也继续获取社交媒体信息
                    self.get_social_media_info(contract_address)
            except Exception as e:
                self.add_log("获取聪明钱数据", f"错误 - {str(e)}")
                # 发生错误时也继续获取社交媒体信息
                self.get_social_media_info(contract_address)

    def get_social_media_info(self, contract_address):
        """获取社交媒体信息"""
        # 获取社交统计信息
        url = f"https://www.pump.news/api/trpc/analyze.getBatchTokenDataByTokenAddress,watchlist.batchTokenWatchState?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22tokenAddresses%22%3A%5B%22{contract_address}%22%5D%7D%7D%2C%221%22%3A%7B%22json%22%3A%7B%22tokenAddresses%22%3A%5B%22{contract_address}%22%5D%7D%7D%7D"

        self.social_worker = ApiWorker(requests.get, url)
        self.social_worker.finished.connect(lambda response: self.update_social_info(response.json()))
        self.social_worker.error.connect(self.on_api_error)
        self.social_worker.start()

        # 获取推文列表
        self.get_tweets_by_category(contract_address, self.current_tweet_category)

    def get_tweets_by_category(self, contract_address: str, category: str):
        """根据类型获取推文数据"""
        # 清除现有数据
        self.tableSocial.setModel(None)

        # 添加日志
        self.add_log(f"获取推文", f"正在获取{category}类型推文...")

        tweets_url = f"https://www.pump.news/api/trpc/utils.getCannyList,service.getServiceCallCount,tweets.getTweetsByTokenAddress?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%2C%22meta%22%3A%7B%22values%22%3A%5B%22undefined%22%5D%7D%7D%2C%221%22%3A%7B%22json%22%3A%7B%22service%22%3A%22optimize%22%7D%7D%2C%222%22%3A%7B%22json%22%3A%7B%22tokenAddress%22%3A%22{contract_address}%22%2C%22type%22%3A%22filter%22%2C%22category%22%3A%22{category}%22%7D%7D%7D"

        self.tweets_worker = ApiWorker(requests.get, tweets_url)
        self.tweets_worker.finished.connect(lambda response: self.update_tweets(response.json()))
        self.tweets_worker.error.connect(self.on_api_error)
        self.tweets_worker.start()

    def update_social_info(self, data):
        """更新社交信息"""
        try:
            # 更新统计数据
            stats = data[0]["result"]["data"]["json"]["data"]["data"][0]["stats"]
            self.labelFilterTweets.setText(f"推文数：{stats['filter_tweets']}")
            self.labelFollowers.setText(f"触达人数：{stats['followers']:,}人")
            self.labelLikes.setText(f"点赞：{stats['likes']:,}")
            self.labelViews.setText(f"浏览：{stats['views']:,}")
            self.labelOfficalTweets.setText(f"官方推文：{stats['official_tweets']}")
            self.labelSmartBuy.setText(f"智能买入：{data[0]['result']['data']['json']['data']['data'][0]['smartbuy']}")

            # 更新描述
            summary = data[0]["result"]["data"]["json"]["data"]["data"][0]["analysis"]["lang-zh-CN"]["summary"]
            self.labelCoinDescription.setText(summary)

        except Exception as e:
            self.add_log("更新社交统计信息", f"错误 - {str(e)}")

    def update_tweets(self, tweets_data):
        """更新推文信息"""
        try:
            if not tweets_data or not isinstance(tweets_data, list) or len(tweets_data) < 3:
                error_msg = "获取推文数据失败：数据格式无效"
                self.add_log("更新推文列表", f"错误 - {error_msg}")
                self.tableSocial.setModel(NoDataTableModel(error_msg))
                return

            tweets = tweets_data[2]["result"]["data"]["json"]["data"]["data"]["tweets"]
            if not tweets:
                error_msg = f"未找到{self.current_tweet_category}类型的推文"
                self.add_log("更新推文列表", f"提示 - {error_msg}")
                self.tableSocial.setModel(NoDataTableModel(error_msg))
                return

            self.add_log("推文列表", f"成功获取 {len(tweets)} 条{self.current_tweet_category}类型推文")

            # 更新社交媒体表格
            model = SocialTableModel(tweets)
            self.tableSocial.setModel(model)

            # 设置列宽
            header = self.tableSocial.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 用户名列
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # 蓝标列
            header.setDefaultSectionSize(40)  # 蓝标列宽度
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 浏览列
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 点赞列
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 转发列
            header.setSectionResizeMode(5, QHeaderView.Stretch)  # 内容列

            # 设置表格样式
            self.tableSocial.setStyleSheet("""
                QTableView {
                    border: 1px solid #dcdcdc;
                    background-color: white;
                    gridline-color: #f0f0f0;
                }
                QTableView::item {
                    padding: 5px;
                }
                QTableView::item:hover {
                    background-color: #f8f9fa;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    padding: 5px;
                    border: none;
                    border-right: 1px solid #dcdcdc;
                    border-bottom: 1px solid #dcdcdc;
                }
            """)

            # 添加点击事件处理
            self.tableSocial.clicked.connect(self.on_social_table_clicked)

        except Exception as e:
            error_msg = f"更新推文失败：{str(e)}"
            self.add_log("更新推文列表", f"错误 - {error_msg}")
            self.tableSocial.setModel(NoDataTableModel(error_msg))

    def on_social_table_clicked(self, index):
        """处理社交媒体表格点击事件"""
        if index.column() == 5:  # 内容列
            tweet = self.tableSocial.model()._tweets[index.row()]
            tweet_id = tweet.get("tweet_id")
            user_screen_name = tweet.get("user", {}).get("screen_name")
            if tweet_id and user_screen_name:
                url = f"https://twitter.com/{user_screen_name}/status/{tweet_id}"
                QDesktopServices.openUrl(QUrl(url))

    def update_coin_labels(self, coin_data: Dict[str, Any]):
        """更新代币相关标签"""
        # 设置代币名称
        symbol_text = f"{coin_data.get('name', 'Unknown')} ({coin_data.get('symbol', '')})"
        self.labelCoinSymbol.setText(symbol_text)
        self.labelCoinSymbol.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 5px;
            }
        """)

        # 设置代币描述
        description = coin_data.get('description', '暂无描述')
        self.labelCoinDescription.setText(description)
        self.labelCoinDescription.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                padding: 5px;
                line-height: 1.4;
            }
        """)
        self.labelCoinDescription.setWordWrap(True)  # 允许文字换行

        # 设置代币图片
        image_uri = coin_data.get('image_uri', '')
        if image_uri:
            ImageHandler.download_and_display_image(image_uri, self.labelCoinPic)
            self.labelCoinPic.setMinimumSize(64, 64)
            self.labelCoinPic.setMaximumSize(64, 64)
            self.labelCoinPic.setScaledContents(True)
            self.labelCoinPic.setStyleSheet("""
                QLabel {
                    border: 1px solid #dcdcdc;
                    border-radius: 4px;
                    padding: 2px;
                }
            """)

    def handle_dev_info_click(self, event, creator: str):
        """处理开发者信息标签的点击事件"""
        # 获取点击位置的HTML
        pos = event.pos()
        html = self.labelDevInfo.text()

        # 如果点击了复制图标
        if "📋" in html[self.labelDevInfo.hitTest(pos)]:
            self.copy_dev_address(creator)

    def update_smart_money_info(self, transactions_data: List[Dict[str, Any]],
                             address_labels_map: Dict[str, List[Dict[str, str]]]):
        """更新聪明钱信息"""
        processed_data = []
        buy_count = 0
        sell_count = 0
        buy_volume = 0
        sell_volume = 0

        self.add_log(f"开始处理{len(transactions_data)}条交易数据")

        # 保存原始数据到文件
        try:
            with open('smart_money_raw_data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'transactions': transactions_data,
                    'address_labels': address_labels_map
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log("保存原始数据", f"错误 - 无法保存到文件: {str(e)}")

        for tx in transactions_data:
            for event in tx.get('events', []):
                address = event.get('address', '')
                labels = address_labels_map.get(address, [])

                if not labels:  # 如果没有标签，跳过
                    continue

                # 只取第一个标签
                first_label = labels[0].get('label', '')

                data = event.get('data', {})
                order = data.get('order', {})
                input_token = data.get('input', {}).get('token', '')
                output_token = data.get('output', {}).get('token', '')
                contract = self.leCA.text().strip()

                is_buy = output_token == contract
                volume_native = order.get('volume_native', 0)

                if is_buy:
                    buy_count += 1
                    buy_volume += volume_native
                else:
                    sell_count += 1
                    sell_volume += volume_native

                processed_data.append({
                    'address': address,
                    'labels': [first_label],  # 只保存第一个标签
                    'is_buy': is_buy,
                    'price_usd': order.get('price_usd', 0),
                    'volume_native': volume_native
                })

        # 保存处理后的数据到文件
        try:
            with open('smart_money_processed_data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_data': processed_data,
                    'summary': {
                        'buy_count': buy_count,
                        'sell_count': sell_count,
                        'buy_volume': buy_volume,
                        'sell_volume': sell_volume
                    }
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log("保存处理后数据", f"错误 - 无法保存到文件: {str(e)}")

        self.add_log(f"处理完成: 买入{buy_count}笔, 卖出{sell_count}笔")

        # 更新表格
        if processed_data:
            model = SmartMoneyTableModel(processed_data)
            self.tableSmartMoney.setModel(model)
            self.tableSmartMoney.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            # 设置表格代理以处理背景色
            self.tableSmartMoney.setItemDelegate(TableStyleDelegate())

            # 打印一些调试信息
            self.add_log("表格数据", f"成功 - 添加了{len(processed_data)}行数据")
        else:
            self.add_log("表格数据", "警告 - 没有可显示的数据")

        # 更新统计信息
        net_volume = buy_volume - sell_volume
        info_html = f"""
        <html>
        <body>
            <span>聪明钱：</span>
            <span style='color: #4CAF50;'>买{buy_count}人 {int(buy_volume)}SOL</span>，
            <span style='color: #F44336;'>卖{sell_count}人 {int(sell_volume)}SOL</span>，
            <span style='color: {"#4CAF50" if net_volume >= 0 else "#F44336"}'>
                净{("买入" if net_volume >= 0 else "卖出")} {abs(int(net_volume))}SOL
            </span>
        </body>
        </html>
        """
        self.labelSmartMoneyInfo.setText(info_html)
        self.add_log("聪明钱信息更新完成")

    def on_api_error(self, error_msg):
        """处理API错误"""
        self.add_log("API请求错误", f"错误 - {error_msg}")
        self.btnQuery.setEnabled(True)
        self.btnQuery.setText("查询")

    def show_error_message(self, message: str):
        """显示错误信息"""
        self.add_log("错误", message, "")

    @staticmethod
    def show_error_and_exit(message: str):
        """显示错误信息并退出程序"""
        print(message)
        sys.exit(1)

    def on_tweet_tab_changed(self, index):
        """处理推文类型选项卡切换事件"""
        # 获取当前选中的tab名称
        current_tab = self.tabSocialOptions.tabText(index).lower()

        # 根据tab名称确定category
        if "官方" in current_tab:
            new_category = "official"
        else:
            new_category = "top"

        # 如果类型没有改变，不需要重新获取数据
        if new_category == self.current_tweet_category:
            return

        # 更新当前类型
        self.current_tweet_category = new_category

        # 获取当前合约地址
        contract_address = self.leCA.text().strip()
        if not contract_address:
            return

        # 添加日志
        category_name = "官方" if new_category == "official" else "热门"
        self.add_log(f"切换推文类型", f"切换到{category_name}推文")

        # 重新获取推文数据
        self.get_tweets_by_category(contract_address, new_category)

    def query_gmgn_info(self):
        """查询GMGN数据"""
        contract_address = self.leCA.text().strip()
        if not contract_address:
            self.show_error_message("请输入代币合约地址")
            return

        # 禁用查询按钮
        self.btnQueryTradeInfo.setEnabled(False)
        self.btnQueryTradeInfo.setText("查询中...")

        # 添加日志
        self.add_log("开始查询GMGN数据", f"合约地址: {contract_address}")

        # 构建API URLs和参数
        base_params = {
            "device_id": "520cc162-92cd-4ee6-9add-25e40e359805",
            "client_id": "gmgn_web_2025.0128.214338",
            "from_app": "gmgn",
            "app_ver": "2025.0128.214338",
            "tz_name": "Asia/Shanghai",
            "tz_offset": "28800",
            "app_lang": "en"
        }

        urls = {
            "holder": f"https://gmgn.ai/api/v1/token_stat/sol/{contract_address}",
            "wallet_tags": f"https://gmgn.ai/api/v1/token_wallet_tags_stat/sol/{contract_address}",
            "top_holders": f"https://gmgn.ai/api/v1/mutil_window_token_security_launchpad/sol/{contract_address}"
        }

        try:
            self.add_log("通过本地Node.js服务获取数据")
            results = {}
            for name, url in urls.items():
                response = requests.post("http://localhost:3000", json={
                    "url": f"{url}?{urllib.parse.urlencode(base_params)}",
                    "dataType": "gmgn_data"
                })

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        results[name] = data.get('response')
                        self.add_log(f"获取{name}数据", "成功")
                    else:
                        self.add_log(f"获取{name}数据", f"失败 - {data.get('error')}")
                else:
                    self.add_log(f"获取{name}数据", f"失败 - 状态码: {response.status_code}")

            if results:
                self.display_gmgn_results(results)

                # 获取Chain.fm数据
                # chain_fm_response = requests.post("http://localhost:3000", json={
                #     "url": "https://chain.fm/api/trpc/parsedTransaction.list",
                #     "dataType": "chain_fm_transactions",
                #     "token": contract_address
                # })
                #
                # if chain_fm_response.status_code == 200:
                #     chain_fm_data = chain_fm_response.json()
                #     if chain_fm_data.get('success'):
                #         data = chain_fm_data.get('response', {}).get('data', [])
                #         if data and len(data) > 0:
                #             result = data[0].get('result', {})
                #             transactions = result.get('data', {}).get('json', {}).get('data', {}).get('parsedTransactions', [])
                #             address_labels = result['data']['json']['data']['data'][0]['renderContext']['addressLabelsMap']
                #             self.update_smart_money_info(transactions, address_labels)
                #     else:
                #         self.add_log("获取Chain.fm数据", f"失败 - {chain_fm_data.get('error')}")
                # else:
                #     self.add_log("获取Chain.fm数据", f"失败 - 状态码: {chain_fm_response.status_code}")
            else:
                self.add_log("获取GMGN数据失败", "所有API请求均失败")
        except Exception as e:
            self.add_log("获取数据失败", f"错误: {str(e)}")

        self.btnQueryTradeInfo.setEnabled(True)
        self.btnQueryTradeInfo.setText("查询GMGN")

    def display_gmgn_results(self, results):
        """显示GMGN数据结果"""
        try:
            # 显示holder数据
            if 'holder' in results:
                holder_data = results['holder'].get('data', {})
                holder_count = holder_data.get('data')['holder_count']
                blue_chip_count = holder_data.get('data')['bluechip_owner_count']
                # bluechip_owner_percentage = holder_data.get('data')['bluechip_owner_percentage']
                # top_rat_trader_percentage = holder_data.get('data')['top_rat_trader_percentage']

                bluechip_owner_percentage = float(holder_data.get('data', {}).get('bluechip_owner_percentage', 0))
                top_rat_trader_percentage = float(holder_data.get('data', {}).get('top_rat_trader_percentage', 0))

                holder_html = f"""
                <html>
                <head>
                <style>
                    .container {{ font-family: Arial, sans-serif; padding: 10px; }}
                    .title {{ color: #1976D2; font-size: 14px; font-weight: bold; margin-bottom: 5px; }}
                    .stat {{ margin: 5px 0; }}
                    .label {{ color: #666; }}
                    .value {{ color: #2196F3; font-weight: bold; }}
                    .highlight {{ color: #4CAF50; font-weight: bold; }}
                </style>
                </head>
                <body>
                <div class="container">
                    <div class="title">持有者统计：</div>
                        <span class="label">Holder：</span>
                        <span class="value">{holder_count:,}</span>

                        <span class="label">蓝筹持有人：</span>
                        <span class="value">{blue_chip_count:,}</span>

                        <span class="label">蓝筹比例：</span>
                        <span class="value">{bluechip_owner_percentage:.2%}</span>

                        <span class="label">老鼠仓比例：</span>
                        <span class="value">{top_rat_trader_percentage:.2%}</span>
                    </div>
                </div>
                </body>
                </html>
                """
                self.labelHolderInfo.setText(holder_html)

            # 显示钱包分类统计
            if 'wallet_tags' in results:
                wallet_data = results['wallet_tags'].get('data').get('data')
                wallet_tags_smart_wallets=wallet_data['smart_wallets']
                wallet_fresh_wallets=wallet_data['fresh_wallets']
                wallet_tags_renowned_wallets=wallet_data['renowned_wallets']
                wallet_tags_sniper_wallets=wallet_data['sniper_wallets']
                wallet_tags_rat_trader_wallets=wallet_data['rat_trader_wallets']
                wallet_tags_whale_wallets=wallet_data['whale_wallets']
                wallet_tags_top_wallets=wallet_data['top_wallets']
                wallet_tags_following_wallets=wallet_data['following_wallets']

                tags_html = f"""
                <html>
                <head>
                <style>
                    .container {{ font-family: Arial, sans-serif; padding: 10px; }}
                    .title {{ color: #1976D2; font-size: 14px; font-weight: bold; margin-bottom: 5px; }}
                    .stat {{ margin: 5px 0; }}
                    .label {{ color: #666; }}
                    .value {{ color: #2196F3; font-weight: bold; }}
                    .highlight {{ color: #4CAF50; font-weight: bold; }}
                </style>
                </head>
                <body>
                    <div class="container">
                        <div class="title">地址分类：</div>
                            <span class="label">聪明钱：</span>
                            <span class="value">{wallet_tags_smart_wallets:,}</span>
                            <span class="label">新地址：</span>
                            <span class="value">{wallet_fresh_wallets:,}</span>
    
                            <span class="label">Renowned：</span>
                            <span class="value">{wallet_tags_renowned_wallets:,}</span>
                            <span class="label">阻击地址：</span>
                            <span class="value">{wallet_tags_sniper_wallets:,}</span>
    
                            <span class="label">老鼠仓地址：</span>
                            <span class="value">{wallet_tags_rat_trader_wallets:,}</span>
                            <span class="label">大户地址：</span>
                            <span class="value">{wallet_tags_whale_wallets:,}</span>
    
                            <span class="label">Top Wallet：</span>
                            <span class="value">{wallet_tags_top_wallets:,}</span>
                            <span class="label">关注地址：</span>
                            <span class="value">{wallet_tags_following_wallets:,}</span>
                        </div>
                    </div>
                </body>
                </html>
                """
                self.labelWalletTag.setText(tags_html)

            # 显示Top 10持有量
            if 'top_holders' in results:
                holders_data = results['top_holders'].get('data').get('data').get('security')
                top_10_holder_rate = float(holders_data.get('top_10_holder_rate'))
                burn_status=holders_data.get('burn_status')

                holders_html = f"""
                <html>
                <head>
                <style>
                    .container {{ font-family: Arial, sans-serif; padding: 10px; }}
                    .title {{ color: #1976D2; font-size: 14px; font-weight: bold; margin-bottom: 5px; }}
                    .stat {{ margin: 5px 0; }}
                    .label {{ color: #666; }}
                    .value {{ color: #2196F3; font-weight: bold; }}
                    .highlight {{ color: #4CAF50; font-weight: bold; }}
                </style>
                </head>
                <body>
                <div class="container">
                    <div class="title">Top 10持有者：</div>
                        <span class="label">Top 10比例：</span>
                        <span class="value">{top_10_holder_rate:.2%}</span>
                        <span class="label">燃烧状态：</span>
                        <span class="value">{burn_status}</span>
                </div>
                </body>
                </html>
                """
                self.labelTop10.setText(holders_html)

        except Exception as e:
            self.add_log("显示数据时出错", f"错误: {str(e)}")

def main():
    """程序入口函数"""
    try:
        # 创建应用
        app = QApplication(sys.argv)

        # 应用Material主题
        apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)

        # 创建窗口
        window = MainWindow()

        # 设置窗口标题和图标
        window.ui.setWindowTitle("MEME通 - Material Style")

        sys.exit(app.exec())
    except Exception as e:
        print(f"程序启动时出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
