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

// 从GMGN获取数据
async function fetchGMGNData(url, params, headers) {
  try {
    const fullUrl = `${url}?${params}`;
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('从GMGN获取数据失败:', error);
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

// 备用的智能钱包数据获取函数
async function fetchAlternativeSmartMoneyData(contractAddress) {
  try {
    console.log('尝试使用备用方案获取智能钱包数据，地址:', contractAddress);
    
    // 使用Solscan的API作为备选方案
    const apiUrl = `https://public-api.solscan.io/token/meta?token=${contractAddress}`;

    console.log('备用请求URL:', apiUrl);

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      },
      timeout: 10000  // 10秒超时
    });

    console.log('备用方案响应状态:', response.status, response.statusText);

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    
    console.log('备用方案返回的数据:', JSON.stringify(data, null, 2));

    // 检查数据结构
    if (!data || !data.address) {
      console.warn('备用方案数据结构不正确:', data);
      throw new Error('备用方案数据结构不正确');
    }

    return { 
      success: true, 
      data: data,
      transactions: []  // Solscan API可能不直接提供交易数据
    };
  } catch (error) {
    console.error('获取备用智能钱包数据失败:', error);
    return { 
      success: false, 
      error: error.message,
      errorType: error.constructor.name
    };
  }
}

// 修改原有的fetchSmartMoneyData函数，添加备用方案
async function fetchSmartMoneyData(contractAddress) {
  try {
    console.log('尝试获取智能钱包数据，地址:', contractAddress);
    
    const apiUrl = `https://chain.fm/api/trpc/parsedTransaction.list?batch=1&input=${encodeURIComponent(
      JSON.stringify({
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
      })
    )}`;

    console.log('请求URL:', apiUrl);

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://chain.fm',
        'Referer': 'https://chain.fm/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      },
      timeout: 10000  // 10秒超时
    });

    console.log('响应状态:', response.status, response.statusText);

    if (!response.ok) {
      // 如果主API失败，尝试备用方案
      console.warn('主API请求失败，尝试备用方案');
      return await fetchAlternativeSmartMoneyData(contractAddress);
    }

    const data = await response.json();
    
    console.log('返回的数据:', JSON.stringify(data, null, 2));

    // 检查数据结构
    if (!data || !data[0]?.result?.data?.json?.data) {
      console.warn('数据结构不正确，尝试备用方案');
      return await fetchAlternativeSmartMoneyData(contractAddress);
    }

    const transactions = data[0].result.data.json.data.parsedTransactions || [];
    console.log('交易数量:', transactions.length);

    return { 
      success: true, 
      data: data,
      transactions: transactions
    };
  } catch (error) {
    console.error('获取聪明钱数据失败:', error);
    
    // 如果主API调用失败，尝试备用方案
    console.warn('主API调用失败，尝试备用方案');
    return await fetchAlternativeSmartMoneyData(contractAddress);
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