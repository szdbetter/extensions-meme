"""
Solana代币信息查询工具
作者: Your Name
版本: 1.0.0
描述: 该工具用于查询Solana链上代币信息，支持图片显示和基本信息展示
"""

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLineEdit, 
                             QTextEdit, QLabel, QTableView, QStyledItemDelegate, QStyle, QHeaderView,
                             QListView)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QCoreApplication, QAbstractTableModel, QModelIndex, QThread, Signal, QDateTime
from PySide6.QtGui import (QPixmap, QColor, QBrush, QFont, QPalette, 
                          QStandardItemModel, QStandardItem)
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
        dev_info = f"""{original_text} 
                  <a href='https://gmgn.ai/sol/address/{creator}' style='color: #3498db; text-decoration: none;'>{creator}</a>
                  <span style='cursor: pointer;' onclick='navigator.clipboard.writeText("{creator}")'>📋</span>"""
        return f"""
        <html>
        <head>
        <style>
            a:hover {{ text-decoration: underline; }}
        </style>
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
        # 定义所有需要的控件及其名称
        controls = {
            'btnQuery': (QPushButton, '查询按钮'),
            'leCA': (QLineEdit, '合约地址输入框'),
            'txtCoinInfo': (QTextEdit, '代币信息显示区'),
            'labelDevInfo': (QLabel, '开发者信息标签'),
            'labelDevHistory': (QLabel, '开发者历史标签'),
            'labelDevTrade': (QLabel, '开发者交易标签'),
            'tableDevHistory': (QTableView, '开发者历史表格'),
            'tableDevTrade': (QTableView, '开发者交易表格'),
            'listViewLog': (QListView, '日志列表'),
            'labelCoinPic': (QLabel, '代币图片'),
            'labelCoinSymbol': (QLabel, '代币名称'),
            'labelCoinDescription': (QLabel, '代币描述')
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
            QListView::item:nth-child(odd) {
                background-color: #f8f9fa;
            }
            QListView::item:nth-child(even) {
                background-color: white;
            }
        """)

        # 设置按钮样式
        self.btnQuery.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2472a4;
            }
        """)

        # 设置表格样式
        table_delegate = TableStyleDelegate()
        for table in [self.tableDevHistory, self.tableDevTrade]:
            table.setItemDelegate(table_delegate)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setStyleSheet("""
                QTableView {
                    border: 1px solid #dcdcdc;
                    gridline-color: #f0f0f0;
                    background-color: white;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    padding: 4px;
                    border: none;
                    border-bottom: 1px solid #dcdcdc;
                }
                QTableView::item {
                    padding: 4px;
                }
                QTableView::item:selected {
                    background-color: #e8f0fe;
                }
            """)

        # 设置默认CA地址
        default_ca = "9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump"
        self.leCA.setText(default_ca)

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

        # 获取base64编码的图片
        image_data = ImageHandler.get_image_base64(image_uri) if image_uri else ''

        # 使用HTML格式化信息
        html = f"""
        <html>
        <head>
        <style type="text/css">
            .container {{
                font-family: Arial, sans-serif;
                padding: 10px;
                max-width: 800px;
            }}
            .header {{
                display: flex;
                align-items: flex-start;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .coin-image {{
                width: 32px;
                height: 32px;
                object-fit: cover;
                border-radius: 4px;
                flex-shrink: 0;
                vertical-align: middle;
                margin-top: 4px;
            }}
            .info {{
                flex: 1;
                min-width: 0;
            }}
            .title {{
                font-size: 16px;
                margin-bottom: 8px;
                color: #333;
            }}
            .description {{
                font-size: 14px;
                line-height: 1.5;
                color: #666;
            }}
            .buttons {{
                margin-top: 15px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }}
            .button {{
                display: inline-block;
                padding: 5px 12px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 12px;
            }}
        </style>
        </head>
        <body>
        <div class='container'>
            <div class='header'>
                <img src='{image_data}' class='coin-image' onerror="this.style.display='none'"/>
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

    def update_dev_info(self, coin_data: Dict[str, Any]):
        """更新开发者信息"""
        creator = coin_data.get('creator')
        if not creator:
            return

        # 获取开发者历史记录
        history_data = DevDataFetcher.fetch_dev_history(creator)
        if history_data:
            # 更新开发者信息标签
            self.labelDevInfo.setText(DevDataFetcher.format_dev_info(creator))
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

    def add_log(self, operation: str, status: str = ""):
        """添加日志到列表视图"""
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        log_text = f"{current_time} - {operation}"
        if status:
            log_text += f" - {status}"
        
        item = QStandardItem(log_text)
        # 设置交替颜色
        row = self.log_model.rowCount()
        if row % 2 == 0:
            item.setBackground(QBrush(QColor("#f8f9fa")))
        else:
            item.setBackground(QBrush(QColor("#ffffff")))
            
        self.log_model.insertRow(0, item)  # 在顶部插入
        self.listViewLog.scrollToTop()  # 滚动到顶部

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
        self.add_log(f"开始查询代币信息", f"合约地址: {contract_address}")
            
        # 创建异步工作线程获取代币数据
        self.coin_worker = ApiWorker(CoinDataFetcher.fetch_coin_data, contract_address)
        self.coin_worker.finished.connect(self.on_coin_data_received)
        self.coin_worker.error.connect(self.on_api_error)
        self.coin_worker.start()

    def on_coin_data_received(self, coin_data):
        """处理代币数据"""
        if coin_data:
            # 添加日志
            self.add_log("获取代币信息成功", f"代币: {coin_data.get('name', '')} ({coin_data.get('symbol', '')})")
            
            # 显示代币信息
            self.txtCoinInfo.setHtml(self.format_coin_info(coin_data))
            self.txtCoinInfo.setOpenExternalLinks(True)

            # 更新代币相关标签
            self.update_coin_labels(coin_data)
            
            # 异步获取开发者信息
            creator = coin_data.get('creator')
            if creator:
                self.add_log("开始获取开发者信息", f"开发者地址: {creator}")
                
                self.history_worker = ApiWorker(DevDataFetcher.fetch_dev_history, creator)
                self.history_worker.finished.connect(lambda data: self.on_history_data_received(data, creator))
                self.history_worker.error.connect(self.on_api_error)
                self.history_worker.start()

                self.trade_worker = ApiWorker(DevDataFetcher.fetch_dev_trades, coin_data.get('mint', ''))
                self.trade_worker.finished.connect(lambda data: self.on_trade_data_received(data, creator))
                self.trade_worker.error.connect(self.on_api_error)
                self.trade_worker.start()
        else:
            self.show_error_message("未找到代币信息或发生错误")
            self.add_log("获取代币信息失败")
        
        # 恢复查询按钮
        self.btnQuery.setEnabled(True)
        self.btnQuery.setText("查询")

    def on_history_data_received(self, history_data, creator):
        """处理历史数据"""
        if history_data:
            self.add_log("获取开发者历史记录成功", f"历史发币数: {len(history_data)}")
            
            # 更新开发者信息标签，保留原有文本
            original_text = self.labelDevInfo.text()
            self.labelDevInfo.setText(DevDataFetcher.format_dev_info(creator, original_text))
            self.labelDevInfo.setOpenExternalLinks(True)  # 允许打开外部链接
            
            self.labelDevHistory.setText(DevDataFetcher.format_dev_history(history_data))
            
            # 按市值排序
            sorted_history = sorted(history_data, 
                                  key=lambda x: (x.get('usd_market_cap', 0), x.get('created_timestamp', 0)), 
                                  reverse=True)
            
            history_model = DevHistoryTableModel(sorted_history)
            self.tableDevHistory.setModel(history_model)

    def on_trade_data_received(self, trade_data, creator):
        """处理交易数据"""
        if trade_data:
            self.labelDevTrade.setText(f"交易信息（{DevDataFetcher.format_dev_trade_status(trade_data)}）")
            
            if 'transactions' in trade_data:
                self.add_log("获取交易记录成功", f"交易数: {len(trade_data['transactions'])}")
                trade_model = DevTradeTableModel(trade_data['transactions'], creator)
                self.tableDevTrade.setModel(trade_model)

    def on_api_error(self, error_msg):
        """处理API错误"""
        self.add_log("API请求错误", error_msg)
        self.show_error_message(f"API请求错误: {error_msg}")
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
        self.txtCoinInfo.setHtml(error_html)

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
