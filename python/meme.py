from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLineEdit, QTextEdit, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QPixmap
import sys
import os
import requests
from datetime import datetime, timezone

# 设置Qt属性
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        # 获取当前脚本的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # UI文件应该在同一目录下
        ui_file = os.path.join(current_dir, "Main.ui")
        
        # 检查UI文件是否存在
        if not os.path.exists(ui_file):
            print(f"错误: UI文件不存在: {ui_file}")
            sys.exit(1)
            
        loader = QUiLoader()
        try:
            self.ui = loader.load(ui_file)
            if self.ui is None:
                print("错误: 无法加载UI文件")
                sys.exit(1)
        except Exception as e:
            print(f"加载UI文件时出错: {str(e)}")
            sys.exit(1)

        # 获取控件
        self.btnQuery = self.ui.findChild(QPushButton, 'btnQuery')
        self.leCA = self.ui.findChild(QLineEdit, 'leCA')
        self.txtCoinInfo = self.ui.findChild(QTextEdit, 'txtCoinInfo')
        self.labelCoinPic = self.ui.findChild(QLabel, 'labelCoinPic')  # 更新为新的标签名

        # 检查控件是否成功获取
        if not all([self.btnQuery, self.leCA, self.txtCoinInfo, self.labelCoinPic]):
            print("错误: 无法找到所有必需的UI控件")
            print(f"btnQuery: {self.btnQuery}")
            print(f"leCA: {self.leCA}")
            print(f"txtCoinInfo: {self.txtCoinInfo}")
            print(f"labelCoinPic: {self.labelCoinPic}")
            sys.exit(1)

        # 连接按钮点击事件
        self.btnQuery.clicked.connect(self.query_data)
        
        # 显示主窗口
        self.ui.show()

    def get_time_diff(self, timestamp_ms):
        """计算时间差"""
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

    def set_image(self, image_url):
        """设置图片"""
        try:
            # 下载图片
            response = requests.get(image_url)
            if response.status_code == 200:
                # 创建临时文件保存图片
                temp_file = "temp_image.png"
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                
                # 加载并显示图片
                pixmap = QPixmap(temp_file)
                self.labelCoinPic.setPixmap(pixmap.scaled(
                    self.labelCoinPic.width(), 
                    self.labelCoinPic.height(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
                
                # 删除临时文件
                os.remove(temp_file)
            else:
                print(f"下载图片失败: {response.status_code}")
        except Exception as e:
            print(f"设置图片时出错: {e}")

    def format_coin_info(self, coin_data):
        """格式化代币信息"""
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', '')
        created_time = self.get_time_diff(coin_data.get('created_timestamp', 0))
        description = coin_data.get('description', '暂无描述')

        info = f"代币名称: {name} ({symbol})\n"
        info += f"创建时间: {created_time}\n"
        info += f"代币介绍: {description}"
        
        return info

    def query_data(self):
        ca = self.leCA.text()
        url = f"https://frontend-api-v3.pump.fun/coins/search?offset=0&limit=50&sort=market_cap&includeNsfw=false&order=DESC&searchTerm={ca}&type=exact"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    coin_data = data[0]
                    # 显示格式化的代币信息
                    self.txtCoinInfo.setText(self.format_coin_info(coin_data))
                    
                    # 如果有图片，显示图片
                    if 'image_uri' in coin_data:
                        self.set_image(coin_data['image_uri'])
                else:
                    self.txtCoinInfo.setText("未找到代币信息")
            else:
                self.txtCoinInfo.setText(f"获取数据失败: 状态码 {response.status_code}")
        except Exception as e:
            self.txtCoinInfo.setText(f"发生错误: {e}")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        sys.exit(app.exec())
    except Exception as e:
        print(f"程序启动时出错: {str(e)}")
        sys.exit(1)
