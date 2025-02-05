const puppeteer = require('puppeteer-core');
const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

const app = express();
const port = 3000;

// 定义颜色代码
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    reset: '\x1b[0m'
};

// 检查端口是否被占用并释放
async function checkAndKillPort() {
    try {
        // 对于 macOS 和 Linux
        const { stdout } = await execAsync(`lsof -i :${port} -t`);
        if (stdout) {
            const pid = stdout.trim();
            console.log(`${colors.yellow}端口 ${port} 被进程 ${pid} 占用${colors.reset}`);
            
            // 终止占用端口的进程
            await execAsync(`kill -9 ${pid}`);
            console.log(`${colors.green}已终止占用端口的进程${colors.reset}`);
            
            // 等待端口完全释放
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    } catch (error) {
        // 如果 lsof 命令没有输出，说明端口没有被占用，这是正常的
        if (!error.stdout && !error.stderr) {
            console.log(`${colors.green}端口 ${port} 未被占用${colors.reset}`);
            return;
        }
        console.error(`${colors.red}检查端口时出错:${colors.reset}`, error);
    }
}

// 启用 CORS
app.use(cors());
app.use(express.json());

// 将 fetchGMGN 函数改造成接受参数的版本
async function fetchGMGNData(tokenAddress) {
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
        
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        await page.setExtraHTTPHeaders({
            'Accept': 'application/json',
            'Origin': 'https://gmgn.ai',
            'Referer': 'https://gmgn.ai/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        });

        // 定义所有API
        const apis = {
            'Holder统计': `https://gmgn.ai/api/v1/token_stat/sol/${tokenAddress}`,
            '钱包分类': `https://gmgn.ai/api/v1/token_wallet_tags_stat/sol/${tokenAddress}`,
            'Top10持有': `https://gmgn.ai/api/v1/mutil_window_token_security_launchpad/sol/${tokenAddress}`,
            'Dev交易': `https://gmgn.ai/api/v1/token_trades/sol/${tokenAddress}`
        };

        const params = '?device_id=520cc162-92cd-4ee6-9add-25e40e359805&client_id=gmgn_web_2025.0128.214338&from_app=gmgn&app_ver=2025.0128.214338&tz_name=Asia%2FShanghai&tz_offset=28800&app_lang=en';

        const results = {};

        // 监听所有响应
        page.on('response', async response => {
            const url = response.url();
            if (url.includes('gmgn.ai/api/v1/')) {
                try {
                    const data = await response.json();
                    if (url.includes('token_stat')) {
                        results.holderStats = data;
                    } else if (url.includes('token_wallet_tags_stat')) {
                        results.walletTags = data;
                    } else if (url.includes('mutil_window_token_security_launchpad')) {
                        results.top10Holders = data;
                    } else if (url.includes('token_trades')) {
                        results.devTrades = data;
                    }
                } catch (e) {
                    console.error('Response not JSON:', e);
                }
            }
        });

        // 依次访问所有API
        for (const [name, url] of Object.entries(apis)) {
            console.log(`${colors.red}正在访问 ${url} 获取${name}数据...${colors.reset}`);
            
            await page.goto(url + params + (name === 'Dev交易' ? '&limit=100&tag=creator' : ''), {
                waitUntil: 'networkidle0',
                timeout: 10000
            });
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            console.log(`${colors.green}${name}数据获取完成${colors.reset}\n`);
        }

        return results;

    } catch (error) {
        console.error(`${colors.red}Error:${colors.reset}`, error);
        throw error;
    } finally {
        await browser.close();
    }
}

// API 路由
app.post('/api/gmgn', async (req, res) => {
    try {
        const { address } = req.body;
        if (!address) {
            return res.status(400).json({ error: '缺少代币地址' });
        }

        console.log(`${colors.green}收到请求，代币地址: ${address}${colors.reset}`);
        const data = await fetchGMGNData(address);
        res.json({ success: true, data });
    } catch (error) {
        console.error(`${colors.red}服务器错误:${colors.reset}`, error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// 修改启动服务器的代码
async function startServer() {
    try {
        // 先检查并释放端口
        await checkAndKillPort();

        // 启动服务器
        app.listen(port, () => {
            console.log(`${colors.green}GMGN 本地服务器运行在 http://localhost:${port}${colors.reset}`);
        }).on('error', (error) => {
            console.error(`${colors.red}启动服务器失败:${colors.reset}`, error);
            process.exit(1);
        });
    } catch (error) {
        console.error(`${colors.red}启动服务器时出错:${colors.reset}`, error);
        process.exit(1);
    }
}

// 启动服务器
startServer();