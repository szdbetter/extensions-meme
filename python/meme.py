"""
Solana代币信息查询工具
作者: Your Name
版本: 1.0.0
描述: 该工具用于查询Solana链上代币信息，支持图片显示和基本信息展示
"""

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLineEdit,
                             QTextEdit, QLabel, QTableView, QStyledItemDelegate, QStyle, QHeaderView,
                             QListView, QStyleOptionViewItem)
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

class TweetModel(QAbstractListModel):
    """推文数据模型"""
    def __init__(self, tweets=None):
        super().__init__()
        self._tweets = tweets or []
        print(f"TweetModel initialized with {len(self._tweets)} tweets")  # 调试信息

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tweets)):
            return None
            
        tweet = self._tweets[index.row()]
        
        if role == Qt.DisplayRole:
            return tweet
        elif role == Qt.UserRole:
            return tweet
            
        return None
            
    def rowCount(self, parent=QModelIndex()):
        count = len(self._tweets)
        print(f"rowCount called, returning {count}")  # 调试信息
        return count

    def addTweets(self, tweets):
        if not tweets:
            print("Warning: Attempting to add empty tweets list")  # 调试信息
            return
            
        print(f"Adding {len(tweets)} tweets to model")  # 调试信息
        self.beginInsertRows(QModelIndex(), 0, len(tweets)-1)
        self._tweets = tweets
        self.endInsertRows()
        print(f"Model now has {len(self._tweets)} tweets")  # 调试信息

class TweetItemDelegate(QStyledItemDelegate):
    """推文项代理"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.last_clicked_link = None

    def editorEvent(self, event, model, option, index):
        """处理鼠标事件"""
        if event.type() == QEvent.MouseButtonRelease:
            tweet = index.data(Qt.UserRole)
            if not tweet:
                return False

            # 获取点击位置
            pos = event.pos()
            
            # 计算链接图标的位置（右上角）
            link_rect = QRect(option.rect.right() - 20, option.rect.top() + 10, 15, 15)
            
            # 检查是否点击了链接图标
            if link_rect.contains(pos):
                tweet_id = tweet.get("tweet_id", "")
                user_screen_name = tweet.get("user", {}).get("screen_name", "")
                if tweet_id and user_screen_name:
                    url = QUrl(f"https://twitter.com/{user_screen_name}/status/{tweet_id}")
                    QDesktopServices.openUrl(url)
                    return True
                    
        return False  # 不再调用父类方法，禁止其他区域的点击事件

    def paint(self, painter, option, index):
        if not index.isValid():
            return
            
        try:
            tweet = index.data(Qt.UserRole)
            if not tweet:
                return
                
            # 设置背景
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            elif option.state & QStyle.State_MouseOver:
                painter.fillRect(option.rect, QColor("#f8f9fa"))
            else:
                painter.fillRect(option.rect, QColor("#ffffff"))
                
            # 创建文档
            doc = QTextDocument()
            
            # 获取发推时间
            created_at = tweet.get("created_at", "0")
            try:
                timestamp = int(float(created_at)) * 1000
                time_diff = TimeUtil.get_time_diff(timestamp)
            except:
                time_diff = ""
            
            # 构建HTML内容
            html = f"""
            <div style='margin: 10px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;'>
                <div style='margin-bottom: 5px;'>
                    <div style='display: flex; align-items: center; justify-content: space-between;'>
                        <div style='display: flex; align-items: center;'>
                            <span style='font-weight: bold; font-size: 15px;'>{tweet.get("user", {}).get("name", "")}</span>
                            <span style='color: #657786; font-size: 15px; margin-left: 4px;'>
                                @{tweet.get("user", {}).get("screen_name", "")}
                                {' <span style="color: #1DA1F2; font-weight: bold;">✓</span>' if tweet.get("user", {}).get("is_blue_verified") else ""}
                            </span>
                            <span style='color: #657786; font-size: 13px; margin-left: 8px;'>
                                · {time_diff}
                            </span>
                        </div>
                        <span style='color: #1DA1F2; font-size: 12px; cursor: pointer;'>🔗</span>
                    </div>
                    <div style='color: #657786; font-size: 14px; display: flex; align-items: center;'>
                        <span>{tweet.get("user", {}).get("followers_count", 0):,} 关注者</span>
                        <span style='margin-left: 15px;'>🔄 {tweet.get("retweet_count", 0):,}</span>
                        <span style='margin-left: 15px;'>❤️ {tweet.get("favorite_count", 0):,}</span>
                        <span style='margin-left: 15px;'>👁️ {tweet.get("views", 0):,}</span>
                    </div>
                </div>
                <div style='color: #14171a; font-size: 15px; line-height: 1.4; margin: 8px 0;'>{tweet.get("text", "")}</div>
                {"<div style='margin: 8px 0;'><img src='" + tweet["medias"][0]["image_url"] + "' width='100%' style='border-radius: 8px; margin: 5px 0;'/></div>" 
                 if tweet.get("medias") and tweet["medias"][0].get("image_url") else ""}
            </div>
            """
            doc.setHtml(html)
            
            # 设置文档宽度
            doc.setTextWidth(option.rect.width())
            
            # 绘制内容
            painter.save()
            painter.translate(option.rect.topLeft())
            doc.drawContents(painter)
            painter.restore()
            
        except Exception as e:
            print(f"Error painting tweet: {str(e)}")

    def sizeHint(self, option, index):
        try:
            tweet = index.data(Qt.UserRole)
            if not tweet:
                return QSize(0, 0)
                
            doc = QTextDocument()
            
            # 获取发推时间
            created_at = tweet.get("created_at", "0")
            try:
                timestamp = int(float(created_at)) * 1000
                time_diff = TimeUtil.get_time_diff(timestamp)
            except:
                time_diff = ""
            
            html = f"""
            <div style='margin: 10px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;'>
                <div style='margin-bottom: 5px;'>
                    <div style='display: flex; align-items: center; justify-content: space-between;'>
                        <div style='display: flex; align-items: center;'>
                            <span style='font-weight: bold; font-size: 15px;'>{tweet.get("user", {}).get("name", "")}</span>
                            <span style='color: #657786; font-size: 15px; margin-left: 4px;'>
                                @{tweet.get("user", {}).get("screen_name", "")}
                                {' <span style="color: #1DA1F2; font-weight: bold;">✓</span>' if tweet.get("user", {}).get("is_blue_verified") else ""}
                            </span>
                            <span style='color: #657786; font-size: 13px; margin-left: 8px;'>
                                · {time_diff}
                            </span>
                        </div>
                        <span style='color: #1DA1F2; font-size: 12px; cursor: pointer;'>🔗</span>
                    </div>
                    <div style='color: #657786; font-size: 14px; display: flex; align-items: center;'>
                        <span>{tweet.get("user", {}).get("followers_count", 0):,} 关注者</span>
                        <span style='margin-left: 15px;'>🔄 {tweet.get("retweet_count", 0):,}</span>
                        <span style='margin-left: 15px;'>❤️ {tweet.get("favorite_count", 0):,}</span>
                        <span style='margin-left: 15px;'>👁️ {tweet.get("views", 0):,}</span>
                    </div>
                </div>
                <div style='color: #14171a; font-size: 15px; line-height: 1.4; margin: 8px 0;'>{tweet.get("text", "")}</div>
                {"<div style='margin: 8px 0;'><img src='" + tweet["medias"][0]["image_url"] + "' width='100%' style='border-radius: 8px; margin: 5px 0;'/></div>" 
                 if tweet.get("medias") and tweet["medias"][0].get("image_url") else ""}
            </div>
            """
            doc.setHtml(html)
            doc.setTextWidth(option.rect.width())
            
            # 计算高度（基础高度 + 图片高度）
            height = doc.size().height()
            if tweet.get("medias") and tweet["medias"][0].get("image_url"):
                height += 200  # 图片固定高度
                
            return QSize(option.rect.width(), int(height) + 20)
            
        except Exception as e:
            print(f"Error calculating size hint: {str(e)}")
            return QSize(option.rect.width(), 100)  # 返回默认大小

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

class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        """初始化主窗口"""
        super(MainWindow, self).__init__()
        self.clipboard = QApplication.clipboard()  # 初始化剪贴板
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
        # 定义所有需要的控件及其名称
        controls = {
            'btnQuery': (QPushButton, '查询按钮'),
            'leCA': (QLineEdit, '合约地址输入框'),
            'labelDevInfo': (QLabel, '开发者信息标签'),
            'labelDevHistory': (QLabel, '开发者历史标签'),
            'labelDevTrade': (QLabel, '开发者交易标签'),
            'tableDevHistory': (QTableView, '开发者历史表格'),
            'tableDevTrade': (QTableView, '开发者交易表格'),
            'tableSmartMoney': (QTableView, '聪明钱交易表格'),
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
            'listViewSocial': (QListView, '推文列表'),
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

        # 设置表格样式，与Material主题配合
        table_delegate = TableStyleDelegate()
        for table in [self.tableDevHistory, self.tableDevTrade]:
            table.setItemDelegate(table_delegate)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            # 移除之前的表格样式，使用Material主题样式

        # 设置列表视图样式，与Material主题配合
        self.listViewLog.setProperty('class', 'dense')  # 使用Material主题的紧凑列表样式

        # 设置默认CA地址
        default_ca = "9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump"
        self.leCA.setText(default_ca)

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

    def query_coin_info(self):
        """查询代币信息"""
        contract_address = self.leCA.text().strip()
        if not contract_address:
            self.show_error_message("请输入代币合约地址")
            return

        # 禁用查询按钮
        self.btnQuery.setEnabled(False)
        self.btnQuery.setText("查询中...")

        # 添加日志
        self.add_log("开始查询代币信息", f"合约地址: {contract_address}", f"https://gmgn.ai/sol/token/{contract_address}")

        # 创建异步工作线程获取代币数据
        self.coin_worker = ApiWorker(CoinDataFetcher.fetch_coin_data, contract_address)
        self.coin_worker.finished.connect(self.on_coin_data_received)
        self.coin_worker.error.connect(self.on_api_error)
        self.coin_worker.start()

    def on_coin_data_received(self, coin_data):
        """处理代币数据"""
        if coin_data:
            # 添加日志
            self.add_log("获取代币信息",
                        f"成功 - {coin_data.get('name', '')} ({coin_data.get('symbol', '')})",
                        f"https://gmgn.ai/sol/token/{coin_data.get('mint', '')}")

            # 更新代币相关标签
            self.update_coin_labels(coin_data)

            # 获取社交媒体信息
            contract = coin_data.get('mint', '')
            if contract:
                # 获取社交统计信息
                url = f"https://www.pump.news/api/trpc/analyze.getBatchTokenDataByTokenAddress,watchlist.batchTokenWatchState?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22tokenAddresses%22%3A%5B%22{contract}%22%5D%7D%7D%2C%221%22%3A%7B%22json%22%3A%7B%22tokenAddresses%22%3A%5B%22{contract}%22%5D%7D%7D%7D"
                
                self.social_worker = ApiWorker(requests.get, url)
                self.social_worker.finished.connect(lambda response: self.update_social_info(response.json()))
                self.social_worker.error.connect(self.on_api_error)
                self.social_worker.start()
                
                # 获取推文列表
                tweets_url = f"https://www.pump.news/api/trpc/utils.getCannyList,service.getServiceCallCount,tweets.getTweetsByTokenAddress?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%2C%22meta%22%3A%7B%22values%22%3A%5B%22undefined%22%5D%7D%7D%2C%221%22%3A%7B%22json%22%3A%7B%22service%22%3A%22optimize%22%7D%7D%2C%222%22%3A%7B%22json%22%3A%7B%22tokenAddress%22%3A%22{contract}%22%2C%22type%22%3A%22filter%22%2C%22category%22%3A%22top%22%7D%7D%7D"
                
                self.tweets_worker = ApiWorker(requests.get, tweets_url)
                self.tweets_worker.finished.connect(lambda response: self.update_tweets(response.json()))
                self.tweets_worker.error.connect(self.on_api_error)
                self.tweets_worker.start()

            # 异步获取开发者信息
            creator = coin_data.get('creator')
            if creator:
                # 先获取交易记录
                self.add_log("请求开发者交易记录", "正在获取...", f"https://gmgn.ai/sol/address/{creator}")
                self.trade_worker = ApiWorker(DevDataFetcher.fetch_dev_trades, coin_data.get('mint', ''))
                self.trade_worker.finished.connect(lambda data: self.on_trade_data_received(data, creator))
                self.trade_worker.error.connect(self.on_api_error)
                self.trade_worker.start()
        else:
            self.add_log("获取代币信息", "失败 - 未找到代币信息或发生错误")

        # 恢复查询按钮
        self.btnQuery.setEnabled(True)
        self.btnQuery.setText("查询")

    def on_trade_data_received(self, trade_data, creator):
        """处理交易数据"""
        if trade_data:
            self.labelDevTrade.setText(f"交易信息（{DevDataFetcher.format_dev_trade_status(trade_data)}）")

            if 'transactions' in trade_data:
                self.add_log("获取开发者交易记录", f"成功 - {len(trade_data['transactions'])}条交易")
                trade_model = DevTradeTableModel(trade_data['transactions'], creator)
                self.tableDevTrade.setModel(trade_model)

                # 获取历史记录
                self.add_log("请求开发者历史记录", "正在获取...", f"https://gmgn.ai/sol/address/{creator}")
                self.history_worker = ApiWorker(DevDataFetcher.fetch_dev_history, creator)
                self.history_worker.finished.connect(lambda data: self.on_history_data_received(data, creator))
                self.history_worker.error.connect(self.on_api_error)
                self.history_worker.start()

    def on_history_data_received(self, history_data, creator):
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

            # 开始获取聪明钱数据
            self.add_log("请求聪明钱信息", "正在获取...", "https://chain.fm")
            contract_address = self.leCA.text().strip()

            try:
                # 使用Node.js服务获取数据
                data = NodeService.fetch_chain_fm_data(contract_address)
                
                if data and len(data) > 0:
                    result = data[0].get('result', {})
                    transactions = result.get('data', {}).get('json', {}).get('data', {}).get('parsedTransactions', [])
                    address_labels = result['data']['json']['data']['renderContext']['addressLabelsMap']

                    self.add_log("获取聪明钱数据", f"成功 - 获取到{len(transactions)}条交易记录，{len(address_labels)}个地址标签")
                    self.update_smart_money_info(transactions, address_labels)
                else:
                    self.add_log("获取聪明钱数据", "失败 - 返回数据为空")
                    
            except Exception as e:
                self.add_log("获取聪明钱数据", f"错误 - {str(e)}")
                self.show_error_message(f"获取聪明钱数据失败：{str(e)}")

    def on_api_error(self, error_msg):
        """处理API错误"""
        self.add_log("API请求错误", f"错误 - {error_msg}")
        self.btnQuery.setEnabled(True)
        self.btnQuery.setText("查询")

    def show_error_message(self, message: str):
        """显示错误信息"""
        error_html = f"""
        <html>
        <head>
        <style type="text/css">
            .error-message {{
                color: #e74c3c;
                font-family: Arial, sans-serif;
                padding: 10px;
                font-size: 14px;
            }}
        </style>
        </head>
        <body>
            <div class='error-message'>
                {message}
            </div>
        </body>
        </html>
        """
        # 移除 self.txtCoinInfo.setHtml(error_html)

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

    def update_smart_money_info(self, transactions_data: List[Dict[str, Any]], address_labels_map: Dict[str, List[Dict[str, str]]]):
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

    def update_social_info(self, data):
        """更新社交信息"""
        try:
            # 更新统计数据
            stats = data[0]["result"]["data"]["json"]["data"]["data"][0]["stats"]
            self.labelFilterTweets.setText(f"推文数：{stats['filter_tweets']}")
            self.labelFollowers.setText(f"关注者：{stats['followers']:,}")
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
        """更新推文列表"""
        try:
            # 检查tweets_data是否有效
            if not tweets_data or not isinstance(tweets_data, list) or len(tweets_data) < 3:
                self.add_log("更新推文列表", f"错误 - 无效的推文数据格式")
                return

            # 获取推文数据 - 修改数据访问路径
            tweets = tweets_data[2]["result"]["data"]["json"]["data"]["data"]["tweets"]
            if not tweets:
                self.add_log("更新推文列表", "警告 - 没有找到推文数据")
                return
            self.add_log("推文列表", f"成功获取 {len(tweets)} 条推文")

            # 设置代理和模型
            try:
                if not hasattr(self, 'tweet_model'):
                    self.tweet_model = TweetModel()
                    self.listViewSocial.setModel(self.tweet_model)
                    self.listViewSocial.setItemDelegate(TweetItemDelegate())
                    self.listViewSocial.clicked.connect(self.on_tweet_clicked)
                    self.add_log("推文列表", "初始化模型和代理成功")
            except Exception as model_error:
                self.add_log("更新推文列表", f"错误 - 设置模型和代理失败: {str(model_error)}")
                return

            # 更新模型数据
            try:
                self.tweet_model.addTweets(tweets)
                self.add_log("推文列表", "成功更新推文数据到模型")
            except Exception as update_error:
                self.add_log("更新推文列表", f"错误 - 更新模型数据失败: {str(update_error)}")
                return

            # 设置样式
            try:
                self.listViewSocial.setStyleSheet("""
                    QListView {
                        background-color: white;
                        border: 1px solid #dcdcdc;
                        border-radius: 4px;
                        padding: 5px;
                    }
                    QListView::item {
                        border-bottom: 1px solid #f0f0f0;
                        padding: 5px;
                        margin: 2px 0;
                    }
                    QListView::item:hover {
                        background-color: #f8f9fa;
                    }
                    QListView::item:selected {
                        background-color: #e3f2fd;
                        color: black;
                    }
                """)
                self.add_log("推文列表", "成功设置样式")
            except Exception as style_error:
                self.add_log("更新推文列表", f"错误 - 设置样式失败: {str(style_error)}")
                return

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.add_log("更新推文列表", f"错误 - {str(e)}\n{error_details}")

    def on_tweet_clicked(self, index):
        """处理推文点击事件"""
        tweet = index.data(Qt.UserRole)
        if tweet:
            tweet_id = tweet.get("tweet_id")
            user_screen_name = tweet.get("user", {}).get("screen_name")
            if tweet_id and user_screen_name:
                url = f"https://twitter.com/{user_screen_name}/status/{tweet_id}"
                QDesktopServices.openUrl(QUrl(url))

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
