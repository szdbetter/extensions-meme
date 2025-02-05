// 代币信息缓存
const tokenInfoCache = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5分钟缓存

// 实现fetchTokenInfo函数
async function fetchTokenInfo(address) {
  // 检查缓存
  const cacheKey = `token_${address}`;
  const cachedData = tokenInfoCache.get(cacheKey);
  if (cachedData && (Date.now() - cachedData.timestamp) < CACHE_DURATION) {
    console.log('使用缓存的代币数据');
    return cachedData.data;
  }

  try {
    const requests = [
      fetch('https://www.pump.news/api/trpc/utils.getCannyList?input=' + 
        encodeURIComponent(JSON.stringify({"json": null, "meta": {"values": ["undefined"]}})), {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      }),
      fetch('https://www.pump.news/api/trpc/service.getServiceCallCount?input=' + 
        encodeURIComponent(JSON.stringify({"json": {"service": "optimize"}})), {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      }),
      fetch('https://www.pump.news/api/trpc/tweets.getTweetsByTokenAddress?input=' + 
        encodeURIComponent(JSON.stringify({
          "json": {
            "tokenAddress": address,
            "type": "filter",
            "category": "top"
          }
        })), {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      })
    ];

    const responses = await Promise.all(requests);
    const results = await Promise.all(responses.map(response => response.json()));

    const data = {
      "0": results[0],
      "1": results[1],
      "2": results[2]
    };

    // 更新缓存
    tokenInfoCache.set(cacheKey, {
      data: data,
      timestamp: Date.now()
    });

    return data;
  } catch (error) {
    console.error('获取代币信息失败:', error);
    throw error;
  }
}

// 从pump.fun获取数据
async function fetchPumpFunData(address) {
  try {
    const url = `https://frontend-api-v3.pump.fun/coins/search?offset=0&limit=50&sort=market_cap&includeNsfw=false&order=DESC&searchTerm=${address}&type=exact`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.pump.fun',
        'Referer': 'https://www.pump.fun/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      }
    });

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('从pump.fun获取数据失败:', error);
    throw error;
  }
}

// 从pump.fun获取DEV信息
async function fetchDevInfo(address) {
  try {
    const url = `https://frontend-api-v3.pump.fun/coins/user-created-coins/${address}?offset=0&limit=10&includeNsfw=false`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.pump.fun',
        'Referer': 'https://www.pump.fun/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      }
    });

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('从pump.fun获取DEV信息失败:', error);
    throw error;
  }
}

// 修改 GMGN 数据获取函数
async function fetchGMGNData(url) {
  try {
    // 从 URL 中提取代币地址
    const address = url.split('/sol/')[1].split('?')[0];
    console.log('正在通过本地服务器获取 GMGN 数据，地址:', address);

    // 构造 GMGN API 的参数
    const params = {
      device_id: '520cc162-92cd-4ee6-9add-25e40e359805',
      client_id: 'gmgn_web_2025.0128.214338',
      from_app: 'gmgn',
      app_ver: '2025.0128.214338',
      tz_name: 'Asia/Shanghai',
      tz_offset: '28800',
      app_lang: 'en'
    };

    // 定义所有需要获取的 GMGN API
    const apis = {
      'Holder统计': `https://gmgn.ai/api/v1/token_stat/sol/${address}`,
      '钱包分类': `https://gmgn.ai/api/v1/token_wallet_tags_stat/sol/${address}`,
      'Top10持有': `https://gmgn.ai/api/v1/mutil_window_token_security_launchpad/sol/${address}`,
      'Dev交易': `https://gmgn.ai/api/v1/token_trades/sol/${address}`
    };

    // 通过本地服务器获取所有数据
    const results = {};
    for (const [name, apiUrl] of Object.entries(apis)) {
      console.log(`正在获取${name}数据...`);
      const response = await fetch('http://localhost:3000', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: apiUrl,
          dataType: `gmgn_${name}`,
          params: name === 'Dev交易' ? { ...params, limit: 100, tag: 'creator' } : params
        })
      });

      if (!response.ok) {
        throw new Error(`获取${name}数据失败: ${response.status}`);
      }

      const data = await response.json();
      if (!data.success) {
        throw new Error(`获取${name}数据失败: ${data.error}`);
      }

      results[name.toLowerCase()] = data.response.data;
    }

    return results;
  } catch (error) {
    console.error('获取 GMGN 数据失败:', error);
    throw error;
  }
}

// 从chain.fm获取数据
async function fetchChainFMData(url, params) {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://chain.fm',
        'Referer': 'https://chain.fm/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      }
    });

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('从chain.fm获取数据失败:', error);
    throw error;
  }
}

// 修改智能钱包数据获取函数
async function fetchSmartMoneyData(contractAddress) {
  try {
    console.log('尝试获取智能钱包数据，地址:', contractAddress);
    
    // 构造请求参数
    const params = {
      "0": {
        "json": {
          "page": 1,
          "pageSize": 30,
          "dateRange": null,
          "token": contractAddress,
          "address": [],
          "useFollowing": true,
          "includeChannels": [],
          "lastUpdateTime": null,
          "events": []
        },
        "meta": {
          "values": {
            "dateRange": ["undefined"],
            "lastUpdateTime": ["undefined"]
          }
        }
      }
    };

    // 尝试通过本地服务器获取数据
    const localResponse = await fetch('http://localhost:3000', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: 'https://chain.fm/api/trpc/parsedTransaction.list?batch=1',
        dataType: 'smartMoney',
        params: params
      })
    });

    if (!localResponse.ok) {
      throw new Error(`本地服务器请求失败: ${localResponse.status}`);
    }

    const localData = await localResponse.json();
    if (!localData.success) {
      throw new Error(localData.error || '本地服务器返回错误');
    }

    return {
      success: true,
      data: localData.response.data,
      source: 'local_server'
    };

  } catch (error) {
    console.error('获取智能钱包数据失败:', error);
    return {
      success: false,
      error: error.message,
      errorType: error.constructor.name
    };
  }
}

// 添加处理交易信息的函数
async function fetchTradeInfo(address) {
  try {
    // 从pump.fun获取代币信息
    const pumpFunData = await fetchPumpFunData(address);
    
    if (!pumpFunData || pumpFunData.length === 0) {
      throw new Error('未找到代币信息');
    }

    return { 
      success: true, 
      data: pumpFunData[0]
    };
  } catch (error) {
    console.error('获取交易信息失败:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// 监听来自content script的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('收到消息:', request.type, request);

  const handleAsyncOperation = async () => {
    try {
      switch (request.type) {
        case 'FETCH_PUMP_FUN':
          const pumpFunData = await fetchPumpFunData(request.address);
          console.log('pump.fun数据:', pumpFunData);
          return { success: true, data: pumpFunData };

        case 'FETCH_SMART_MONEY':
          const smartMoneyResult = await fetchSmartMoneyData(request.address);
          console.log('智能钱包数据:', smartMoneyResult);
          return smartMoneyResult;

        case 'FETCH_TRADE_INFO':
          const tradeResult = await fetchTradeInfo(request.address);
          console.log('交易信息:', tradeResult);
          return tradeResult;

        case 'FETCH_DEV_INFO':
          const devData = await fetchDevInfo(request.address);
          console.log('开发者信息:', devData);
          return { success: true, data: devData };

        case 'FETCH_CHAIN_FM':
          const chainFMData = await fetchChainFMData(request.url, request.params);
          console.log('chain.fm数据:', chainFMData);
          return { success: true, data: chainFMData };

        case 'FETCH_GMGN_DATA':
          try {
            console.log('开始获取GMGN数据:', request.url);
            const gmgnData = await fetchGMGNData(request.url);
            console.log('GMGN数据获取成功:', gmgnData);
            return { success: true, data: gmgnData };
          } catch (error) {
            console.error('GMGN数据获取失败:', error);
            return { 
              success: false, 
              error: error.message,
              errorType: error.constructor.name
            };
          }

        default:
          console.warn('未知的消息类型:', request.type);
          return { success: false, error: '未知的消息类型' };
      }
    } catch (error) {
      console.error(`${request.type}错误:`, error);
      return { 
        success: false, 
        error: error.message,
        errorType: error.constructor.name
      };
    }
  };

  // 执行异步操作并发送响应
  handleAsyncOperation()
    .then(response => {
      console.log(`${request.type}响应:`, response);
      sendResponse(response);
    })
    .catch(error => {
      console.error(`${request.type}处理失败:`, error);
      sendResponse({ 
        success: false, 
        error: error.message,
        errorType: error.constructor.name
      });
    });

  return true; // 保持消息通道开放
});

// 定期清理缓存
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of tokenInfoCache.entries()) {
    if (now - value.timestamp > CACHE_DURATION) {
      tokenInfoCache.delete(key);
    }
  }
}, CACHE_DURATION);

// 创建右键菜单
function createContextMenu() {
  if (chrome.contextMenus) {
    // 先移除所有现有菜单
    chrome.contextMenus.removeAll(() => {
      // 创建新菜单
      chrome.contextMenus.create({
        id: 'searchToken',
        title: '查询Token信息',
        contexts: ['selection']
      });
    });
  }
}

// 处理菜单点击事件
function handleContextMenuClick(info, tab) {
  if (info.menuItemId === 'searchToken' && info.selectionText) {
    // 保存选中的文本
    chrome.storage.local.set({ lastAddress: info.selectionText }, () => {
      // 打开popup
      chrome.windows.create({
        url: 'src/popup.html',
        type: 'popup',
        width: 800,
        height: 600
      });
    });
  }
}

// 等待扩展安装完成后初始化
chrome.runtime.onInstalled.addListener(() => {
  // 创建右键菜单
  createContextMenu();
  
  // 添加菜单点击事件监听器
  if (chrome.contextMenus) {
    chrome.contextMenus.onClicked.addListener(handleContextMenuClick);
  }
}); 