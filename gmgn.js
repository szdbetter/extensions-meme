const puppeteer = require('puppeteer-core');

// 定义颜色代码
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    reset: '\x1b[0m'
};

async function fetchGMGN() {
    const browser = await puppeteer.launch({
        headless: true,  // 无头模式
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
        
        // 设置请求头
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
            'Holder统计': 'https://gmgn.ai/api/v1/token_stat/sol/9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump',
            '钱包分类': 'https://gmgn.ai/api/v1/token_wallet_tags_stat/sol/9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump',
            'Top10持有': 'https://gmgn.ai/api/v1/mutil_window_token_security_launchpad/sol/9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump',
            'Dev交易': 'https://gmgn.ai/api/v1/token_trades/sol/Gg6AkMeFsQsNqBiNNbEeymcxjF49kZjBQrwGE3md9x1b'
        };

        // 添加通用参数
        const params = '?device_id=520cc162-92cd-4ee6-9add-25e40e359805&client_id=gmgn_web_2025.0128.214338&from_app=gmgn&app_ver=2025.0128.214338&tz_name=Asia%2FShanghai&tz_offset=28800&app_lang=en';

        // 监听所有响应
        page.on('response', async response => {
            const url = response.url();
            if (url.includes('gmgn.ai/api/v1/')) {
                try {
                    const data = await response.json();
                    // 确定API类型并格式化输出
                    if (url.includes('token_stat')) {
                        console.log('\n=== Holder统计 ===');
                        console.log(JSON.stringify(data, null, 2));
                    } else if (url.includes('token_wallet_tags_stat')) {
                        console.log('\n=== 钱包分类统计 ===');
                        console.log(JSON.stringify(data, null, 2));
                    } else if (url.includes('mutil_window_token_security_launchpad')) {
                        console.log('\n=== Top 10持有量 ===');
                        console.log(JSON.stringify(data, null, 2));
                    } else if (url.includes('token_trades')) {
                        console.log('\n=== Dev交易记录 ===');
                        console.log(JSON.stringify(data, null, 2));
                    }
                } catch (e) {
                    console.log('Response not JSON:', await response.text());
                }
            }
        });

        // 依次访问所有API
        for (const [name, url] of Object.entries(apis)) {
            // 红色提示正在访问的 API
            console.log(`${colors.red}正在访问 ${url} 获取${name}数据...${colors.reset}`);
            
            await page.goto(url + params + (name === 'Dev交易' ? '&limit=100&tag=creator' : ''), {
                waitUntil: 'networkidle0',
                timeout: 10000
            });
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // 绿色提示完成获取
            console.log(`${colors.green}${name}数据获取完成${colors.reset}\n`);
        }

    } catch (error) {
        console.error(`${colors.red}Error:${colors.reset}`, error);
    } finally {
        await browser.close();
    }
}

// 运行函数
fetchGMGN().catch(console.error);