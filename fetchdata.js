const puppeteer = require('puppeteer-core');
const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

// 定义颜色代码
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    reset: '\x1b[0m'
};

// 打印使用说明
function printUsageGuide() {
    console.log(`
${colors.cyan}==========================================================
    通用数据获取服务 - 使用说明
==========================================================${colors.reset}

${colors.green}功能说明：${colors.reset}
- 这是一个基于Puppeteer的通用数据获取服务
- 可以绕过CORS限制获取任意URL的数据
- 支持自动处理动态加载的内容
- 提供详细的日志输出和错误处理

${colors.yellow}使用方法：${colors.reset}
1. 启动服务：
   - 运行 node fetchdata.js
   - 服务将在 http://localhost:3000 上启动

2. API接口：
   POST http://localhost:3000
   请求体格式：
   {
     "url": "要获取数据的URL",
     "dataType": "数据类型标识（可选）"
   }

${colors.blue}输出信息说明：${colors.reset}
- 时间戳：[HH:MM:SS.mmm]
- URL信息：访问的目标地址
- 数据类型：请求的数据类型
- 响应状态：请求的结果状态
- 错误信息：如果发生错误，会显示详细的错误信息

${colors.magenta}示例请求：${colors.reset}
curl -X POST http://localhost:3000 \\
     -H "Content-Type: application/json" \\
     -d '{"url": "https://example.com/api/data"}'

${colors.cyan}===========================================================${colors.reset}
`);
}

// 在服务启动时打印使用说明
printUsageGuide();

// 格式化时间的函数
function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3 
    });
}

// 检查端口是否被占用并释放
async function checkAndKillPort() {
    try {
        const { stdout } = await execAsync(`lsof -i :${port} -t`);
        if (stdout) {
            const pid = stdout.trim();
            console.log(`${colors.yellow}[${getFormattedTime()}] 端口 ${port} 被进程 ${pid} 占用${colors.reset}`);
            
            await execAsync(`kill -9 ${pid}`);
            console.log(`${colors.green}[${getFormattedTime()}] 已终止占用端口的进程${colors.reset}`);
            
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    } catch (error) {
        if (!error.stdout && !error.stderr) {
            console.log(`${colors.green}[${getFormattedTime()}] 端口 ${port} 未被占用${colors.reset}`);
            return;
        }
        console.error(`${colors.red}[${getFormattedTime()}] 检查端口时出错:${colors.reset}`, error);
    }
}

const app = express();
const port = 3000;

// 启用 CORS
app.use(cors());
app.use(express.json());

// 修改为通用的数据获取函数
async function fetchData(url, dataType = '') {
    console.log(`${colors.cyan}[${getFormattedTime()}] 开始通过 Puppeteer 获取数据${colors.reset}`);
    console.log(`${colors.blue}URL: ${url}${colors.reset}`);
    console.log(`${colors.yellow}数据类型: ${dataType}${colors.reset}`);
    
    const browser = await puppeteer.launch({
        headless: true,
        executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    });
    
    try {
        const page = await browser.newPage();
        
        // 设置通用请求头
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        await page.setExtraHTTPHeaders({
            'Accept': 'application/json',
            'Origin': 'https://gmgn.ai',
            'Referer': 'https://gmgn.ai/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        });

        // 监听所有响应
        let targetResponse = null;
        let responseError = null;
        
        page.on('response', async response => {
            const responseUrl = response.url();
            try {
                if (responseUrl === url || responseUrl.includes(new URL(url).pathname)) {
                    const contentType = response.headers()['content-type'];
                    if (contentType?.includes('application/json')) {
                        console.log(`${colors.green}[${getFormattedTime()}] 成功捕获目标响应${colors.reset}`);
                        const data = await response.json();
                        targetResponse = {
                            url: responseUrl,
                            status: response.status(),
                            headers: response.headers(),
                            data: data
                        };
                    }
                }
            } catch (e) {
                responseError = e;
                console.error(`${colors.red}[${getFormattedTime()}] 处理响应时出错:${colors.reset}`, e);
            }
        });

        // 访问页面
        console.log(`${colors.yellow}[${getFormattedTime()}] 正在加载页面...${colors.reset}`);
        const response = await page.goto(url, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        // 等待数据加载
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        if (!targetResponse && response.headers()['content-type']?.includes('application/json')) {
            try {
                const data = await response.json();
                targetResponse = {
                    url: url,
                    status: response.status(),
                    headers: response.headers(),
                    data: data
                };
            } catch (e) {
                console.error(`${colors.red}[${getFormattedTime()}] 解析主响应失败:${colors.reset}`, e);
            }
        }

        if (!targetResponse) {
            throw new Error('未能获取到目标数据');
        }

        console.log(`${colors.green}[${getFormattedTime()}] 数据获取成功${colors.reset}`);
        console.log(`${colors.cyan}响应状态: ${targetResponse.status}${colors.reset}`);
        
        return {
            success: true,
            source: 'puppeteer',
            url: url,
            timestamp: new Date().toISOString(),
            dataType: dataType,
            response: targetResponse
        };

    } catch (error) {
        console.error(`${colors.red}[${getFormattedTime()}] 错误:${colors.reset}`, error);
        return {
            success: false,
            source: 'puppeteer',
            url: url,
            timestamp: new Date().toISOString(),
            dataType: dataType,
            error: error.message,
            stack: error.stack
        };
    } finally {
        await browser.close();
        console.log(`${colors.green}[${getFormattedTime()}] 浏览器已关闭${colors.reset}`);
    }
}

// API 路由
app.post('/', async (req, res) => {
    try {
        const { url, dataType } = req.body;
        if (!url) {
            return res.status(400).json({ 
                success: false, 
                error: '缺少URL参数',
                timestamp: new Date().toISOString()
            });
        }

        console.log(`${colors.green}[${getFormattedTime()}] 收到请求${colors.reset}`);
        console.log(`${colors.blue}URL: ${url}${colors.reset}`);
        console.log(`${colors.yellow}数据类型: ${dataType || '未指定'}${colors.reset}`);
        
        const data = await fetchData(url, dataType);
        res.json(data);
    } catch (error) {
        console.error(`${colors.red}[${getFormattedTime()}] 服务器错误:${colors.reset}`, error);
        res.status(500).json({ 
            success: false, 
            error: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString()
        });
    }
});

// 修改启动服务器的代码
async function startServer() {
    try {
        await checkAndKillPort();

        app.listen(port, () => {
            console.log(`${colors.green}[${getFormattedTime()}] 本地服务器运行在 http://localhost:${port}${colors.reset}`);
            console.log(`${colors.cyan}[${getFormattedTime()}] 等待请求中...${colors.reset}`);
        }).on('error', (error) => {
            console.error(`${colors.red}[${getFormattedTime()}] 启动服务器失败:${colors.reset}`, error);
            process.exit(1);
        });
    } catch (error) {
        console.error(`${colors.red}[${getFormattedTime()}] 启动服务器时出错:${colors.reset}`, error);
        process.exit(1);
    }
}

// 启动服务器
startServer(); 