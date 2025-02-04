// 检查是否在扩展环境中运行
const isExtensionEnvironment = typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage;

document.addEventListener('DOMContentLoaded', function() {
  console.log('插件已加载');

  // 首先创建必要的容器结构
  function createContainers() {
    // 创建主结果容器（如果不存在）
    let resultsContainer = document.querySelector('.results-container');
    if (!resultsContainer) {
      resultsContainer = document.createElement('div');
      resultsContainer.className = 'results-container';
      document.body.appendChild(resultsContainer);
    }

    // 创建代币信息区域（如果不存在）
    let tokenSection = document.querySelector('.token-info-section');
    if (!tokenSection) {
      tokenSection = document.createElement('div');
      tokenSection.className = 'section token-info-section';
      
      const tokenInfoTitle = document.createElement('div');
      tokenInfoTitle.className = 'section-header';
      tokenInfoTitle.innerHTML = '<h2>代币信息</h2>';
      
      const tokenInfoContainer = document.createElement('div');
      tokenInfoContainer.id = 'tokenInfoContainer';
      tokenInfoContainer.className = 'info-box';
      
      tokenSection.appendChild(tokenInfoTitle);
      tokenSection.appendChild(tokenInfoContainer);
      
      resultsContainer.appendChild(tokenSection);
    }

    // 创建智能钱包区域（如果不存在）
    let smartMoneySection = document.querySelector('.smart-money-section');
    if (!smartMoneySection) {
      smartMoneySection = document.createElement('div');
      smartMoneySection.className = 'section smart-money-section';
      
      const smartMoneyTitle = document.createElement('div');
      smartMoneyTitle.className = 'section-header';
      smartMoneyTitle.innerHTML = '<h2 id="smartMoneyTitle">聪明钱</h2>';
      
      const smartMoneyContainer = document.createElement('div');
      smartMoneyContainer.id = 'smartMoneyInfo';
      smartMoneyContainer.className = 'info-box';
      
      smartMoneySection.appendChild(smartMoneyTitle);
      smartMoneySection.appendChild(smartMoneyContainer);
      
      resultsContainer.appendChild(smartMoneySection);
    }

    // 创建社交媒体区域（如果不存在）
    let socialSection = document.querySelector('.social-info-section');
    if (!socialSection) {
      socialSection = document.createElement('div');
      socialSection.className = 'section social-info-section';
      
      const socialTitle = document.createElement('div');
      socialTitle.className = 'section-header';
      socialTitle.innerHTML = '<h2>社交媒体信息</h2><span class="count" id="socialCount"></span>';
      
      const socialContainer = document.createElement('div');
      socialContainer.id = 'socialInfo';
      socialContainer.className = 'info-box';
      
      socialSection.appendChild(socialTitle);
      socialSection.appendChild(socialContainer);
      
      resultsContainer.appendChild(socialSection);
    }
  }

  // 在初始化时创建容器
  createContainers();

  // 获取所有需要的DOM元素
  const contractInput = document.getElementById('contractAddress');
  const searchBtn = document.getElementById('searchBtn');
  const smartMoneyInfo = document.getElementById('smartMoneyInfo');
  const socialInfo = document.getElementById('socialInfo');
  const loading = document.getElementById('loading');
  const error = document.getElementById('error');
  const errorText = error.querySelector('.error-text');
  const retryBtn = document.getElementById('retryBtn');
  const smartMoneyCount = document.getElementById('smartMoneyCount');
  const socialCount = document.getElementById('socialCount');
  const tokenInfoContainer = document.getElementById('tokenInfoContainer');
  const tradeInfoContainer = document.getElementById('tradeInfoContainer');

  // 添加loading相关函数
  function showLoading() {
    if (loading) {
      loading.style.display = 'flex';
    }
  }

  function hideLoading() {
    if (loading) {
      loading.style.display = 'none';
    }
  }

  // 清除结果的函数
  function clearResults() {
    if (tokenInfoContainer) tokenInfoContainer.innerHTML = '';
    if (tradeInfoContainer) tradeInfoContainer.innerHTML = '';
    if (smartMoneyInfo) smartMoneyInfo.innerHTML = '';
    if (socialInfo) socialInfo.innerHTML = '';
    if (smartMoneyCount) smartMoneyCount.textContent = '0';
    if (socialCount) socialCount.textContent = '0';
  }

  // 检查所有必要的DOM元素是否存在
  const requiredElements = {
    contractInput,
    searchBtn,
    smartMoneyInfo,
    socialInfo,
    loading,
    error,
    errorText,
    retryBtn,
    smartMoneyCount,
    socialCount,
    tokenInfoContainer,
    tradeInfoContainer
  };

  for (const [name, element] of Object.entries(requiredElements)) {
    if (!element) {
      console.error(`缺少必要的DOM元素: ${name}`);
    }
  }

  // 添加样式
  const style = document.createElement('style');
  style.textContent = `
    body {
      min-height: auto;
    }

    .token-section {
      margin-bottom: 0;
    }

    .section {
      margin-bottom: 0;
    }

    .loading-container {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(26, 26, 26, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      z-index: 10;
    }

    .loading-text {
      color: rgba(255, 255, 255, 0.8);
      font-size: 14px;
      margin-left: 10px;
    }

    .loading-spinner {
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }

    #tokenInfoContainer {
      padding: 15px;
      background: #1a1a1a;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      position: relative;
    }

    .token-info {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .token-header {
      display: flex;
      align-items: center;
      gap: 15px;
    }

    .token-image {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      object-fit: cover;
    }

    .token-basic-info {
      flex: 1;
      min-width: 0;
    }

    .token-basic-info h2 {
      margin: 0;
      font-size: 16px;
      color: #fff;
      line-height: 1.4;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .token-narrative {
      margin: 6px 0 0;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.8);
      line-height: 1.4;
    }

    .token-headline {
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 8px;
      padding: 4px 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }

    .token-narrative-text {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.8);
      line-height: 1.6;
      padding: 0 4px;
    }

    .token-stats {
      display: flex;
      gap: 8px;
      flex-wrap: nowrap;
      align-items: center;
      width: 100%;
      overflow-x: auto;
      padding-bottom: 4px;
    }

    .stat-item {
      font-size: 13px;
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
      padding: 6px 10px;
      border-radius: 6px;
      transition: background-color 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      flex: 0 0 auto;
      min-width: auto;
      white-space: nowrap;
    }

    .stat-item a {
      width: 100%;
      display: flex;
      justify-content: center;
      text-align: center;
      text-decoration: none;
      color: inherit;
    }

    .stat-item:hover {
      background: rgba(255, 255, 255, 0.2);
    }

    .platform-icon {
      width: 16px;
      height: 16px;
      vertical-align: middle;
    }

    .platform-text {
      font-size: 13px;
      font-weight: 500;
      color: #fff;
    }

    .section-header .count {
      font-size: 16px;
      font-weight: 600;
    }

    .smart-money-table {
      max-height: 800px;
      overflow-y: auto;
    }
    
    .tweet-item {
      background: rgba(255, 255, 255, 0.9);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 10px;
    }
    
    #smartMoneyInfo, #socialInfo {
      max-height: 800px;
      overflow-y: auto;
      padding-right: 10px;
    }

    .analytics-section {
      margin-bottom: 20px;
      color: #fff;
      background: #1a1a1a;
      border-radius: 12px;
      padding: 15px;
    }

    .analytics-title {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 15px;
    }

    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 15px;
    }

    .analytics-item {
      display: flex;
      flex-direction: column;
      gap: 5px;
      background: rgba(255, 255, 255, 0.1);
      padding: 10px;
      border-radius: 8px;
    }

    .analytics-label {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.6);
    }

    .analytics-value {
      font-size: 20px;
      font-weight: 600;
      color: #fff;
    }

    .tweet-avatar {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .tweet-header {
      gap: 10px;
    }

    .trade-info-section {
      margin-bottom: 0;
    }

    .trade-info-container {
      padding: 15px;
      background: #1a1a1a;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      margin-bottom: 15px;
      max-height: 600px;
      overflow-y: auto;
    }

    .dev-info {
      margin-bottom: 20px;
    }

    .dev-info-title {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .dev-info-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 15px;
    }

    .dev-tokens-list {
      margin-top: 15px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }

    .dev-token-item {
      padding: 12px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      margin-bottom: 8px;
      transition: background-color 0.2s;
    }

    .dev-token-item:last-child {
      margin-bottom: 0;
    }

    .dev-token-item:hover {
      background: rgba(255, 255, 255, 0.08);
    }

    /* 添加滚动条样式 */
    .trade-info-container::-webkit-scrollbar {
      width: 8px;
    }

    .trade-info-container::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.05);
      border-radius: 4px;
    }

    .trade-info-container::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 4px;
    }

    .trade-info-container::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    .dev-token-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }

    .dev-token-index {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.5);
      min-width: 30px;
    }

    .dev-token-name {
      flex: 1;
      font-weight: 500;
      color: #fff;
    }

    .dev-token-marketcap {
      color: #00ff9d;
      font-weight: 500;
    }

    .dev-token-details {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }

    .dev-token-time {
      color: rgba(255, 255, 255, 0.5);
    }

    .dev-token-status {
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.1);
    }

    .dev-token-link {
      color: #3b82f6;
      text-decoration: none;
      margin-left: auto;
    }

    .dev-token-link:hover {
      text-decoration: underline;
    }

    .market-info {
      margin-top: 20px;
      padding-top: 15px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }

    .market-info-title {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 12px;
    }

    .market-info-content {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .market-info-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 6px;
    }

    .market-info-label {
      color: rgba(255, 255, 255, 0.6);
      font-size: 14px;
    }

    .market-info-value {
      color: #fff;
      font-size: 14px;
      font-weight: 500;
    }
  `;
  document.head.appendChild(style);

  // 添加自定义样式
  const styleElement = document.createElement('style');
  styleElement.textContent = `
    .trade-info-container {
      max-height: 800px !important;
      overflow-y: auto;
    }
    
    .dev-info-value, 
    .dev-token-name,
    .dev-token-status,
    .dev-token-time,
    .dev-token-index {
      color: #fff !important;
    }
    
    .dev-token-marketcap {
      color: #00ff9d !important;
    }
    
    .dev-tokens-list {
      max-height: 600px !important;
      overflow-y: auto;
    }
    
    .dev-token-link {
      color: #3b82f6 !important;
    }
    
    .dev-token-link:hover {
      color: #60a5fa !important;
    }
    
    /* 滚动条样式 */
    .trade-info-container::-webkit-scrollbar,
    .dev-tokens-list::-webkit-scrollbar {
      width: 8px;
    }
    
    .trade-info-container::-webkit-scrollbar-track,
    .dev-tokens-list::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.05);
      border-radius: 4px;
    }
    
    .trade-info-container::-webkit-scrollbar-thumb,
    .dev-tokens-list::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 4px;
    }
    
    .trade-info-container::-webkit-scrollbar-thumb:hover,
    .dev-tokens-list::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    .smart-money-stats {
      display: flex;
      gap: 20px;
      margin-bottom: 15px;
      padding: 10px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 6px;
    }

    .stat-group {
      flex: 1;
    }

    .stat-group h4 {
      margin: 0 0 5px 0;
      font-size: 0.9em;
      color: #888;
    }

    .stat-value {
      font-size: 1.1em;
      font-weight: bold;
    }

    .stat-value.positive {
      color: #22c55e;
    }

    .stat-value.negative {
      color: #ef4444;
    }

    .transactions-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      table-layout: fixed;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .transactions-table th,
    .transactions-table td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #eee;
      color: #000;
    }

    .transactions-table th {
      background: #f8f9fa;
      font-weight: 600;
      color: #000;
      border-bottom: 2px solid #eee;
    }

    .transactions-table tr:hover {
      background: #f8f9fa;
    }

    .transactions-table tr:last-child td {
      border-bottom: none;
    }

    .tx-type-cell {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.9em;
      font-weight: 500;
    }

    .tx-type-cell.buy {
      background: rgba(34, 197, 94, 0.1);
      color: #22c55e;
    }

    .tx-type-cell.sell {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }

    .smart-money-title-buy {
      color: #22c55e;
    }

    .smart-money-title-sell {
      color: #ef4444;
    }
  `;
  document.head.appendChild(styleElement);

  // 修改图片错误处理方式
  function handleImageError(img) {
    img.src = 'images/default-avatar.png';
  }

  // 测试所有DOM元素是否正确获取
  console.log('DOM元素检查:', {
    contractInput: !!contractInput,
    searchBtn: !!searchBtn,
    smartMoneyInfo: !!smartMoneyInfo,
    socialInfo: !!socialInfo,
    loading: !!loading,
    error: !!error,
    errorText: !!errorText,
    retryBtn: !!retryBtn,
    smartMoneyCount: !!smartMoneyCount,
    socialCount: !!socialCount
  });

  let lastSearchAddress = '';

  // 从storage中获取上次搜索的地址（仅在扩展环境中）
  if (isExtensionEnvironment) {
    chrome.storage.local.get(['lastAddress'], function(result) {
      if (result.lastAddress) {
        contractInput.value = result.lastAddress;
      }
    });
  } else {
    // 在非扩展环境中，尝试从localStorage获取上次搜索的地址
    const lastAddress = localStorage.getItem('lastAddress');
    if (lastAddress) {
      contractInput.value = lastAddress;
    }
  }

  // 添加格式化数字的函数
  function formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toFixed(1);
  }

  // 添加相对时间计算函数
  function getRelativeTimeString(timestamp) {
    const now = new Date();
    const past = new Date(timestamp * 1000);
    const diffInSeconds = Math.floor((now - past) / 1000);

    if (diffInSeconds < 60) {
      return '刚刚';
    }

    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
      return `${diffInMinutes}分钟前`;
    }

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
      return `${diffInHours}小时前`;
    }

    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}天前`;
  }

  // 显示代币信息
  function displayTokenInfo(tokenInfo) {
    const container = document.getElementById('tokenInfoContainer');
    if (!container) return;

    // 获取代币基本信息
    const token = tokenInfo.pumpfun;
    if (!token) {
      container.innerHTML = '<p class="no-data">未找到代币信息</p>';
      return;
    }

    // 计算相对时间
    const relativeTime = getRelativeTimeString(token.deploy_timestamp);

    // 构建HTML
    const html = `
      <div class="token-info">
        <div class="token-header">
          <img src="${token.image_uri || 'images/default-token.png'}" alt="${token.name}" class="token-image" onerror="this.src='images/default-token.png'">
          <div class="token-basic-info">
            <h2>${token.name} (${token.symbol})，${relativeTime}</h2>
            <div class="token-narrative">${token.description || ''}</div>
          </div>
        </div>
        
        <div class="token-stats">
          <div class="stat-item">
            <a href="https://gmgn.ai/sol/token/${token.mint}" target="_blank">
              🔍 <span class="platform-text">GMGN</span>
            </a>
          </div>
          <div class="stat-item">
            <a href="https://www.pump.news/token/${token.mint}" target="_blank">
              📊 <span class="platform-text">PUMPNEWS</span>
            </a>
          </div>
          <div class="stat-item">
            <a href="https://twitter.com/search?q=${token.mint}" target="_blank">
              🐦 <span class="platform-text">搜推特</span>
            </a>
          </div>
          ${token.twitter ? `
            <div class="stat-item">
              <a href="https://twitter.com/${token.twitter}" target="_blank">
                📱 <span class="platform-text">官推</span>
              </a>
            </div>
          ` : ''}
          ${token.website ? `
            <div class="stat-item">
              <a href="${token.website}" target="_blank">
                🌐 <span class="platform-text">官网</span>
              </a>
            </div>
          ` : ''}
        </div>
      </div>
    `;

    container.innerHTML = html;
  }

  // 修改CORS代理设置
  const CORS_PROXIES = [
    'https://corsproxy.io/?',
    'https://api.allorigins.win/raw?url=',
    'https://api.codetabs.com/v1/proxy?quest='
  ];

  // 添加重试逻辑的函数
  async function fetchWithRetry(url, options = {}, proxyIndex = 0) {
    try {
      // 首先尝试直接请求
      try {
        const headers = {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        };

        // 如果是chain.fm的API，添加特定的请求头
        if (url.includes('chain.fm')) {
          Object.assign(headers, {
            'authority': 'chain.fm',
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://chain.fm',
            'referer': 'https://chain.fm/',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
          });
        }

        const response = await fetch(url, { 
          ...options,
          mode: 'cors',
          headers,
          credentials: url.includes('chain.fm') ? 'include' : 'omit'
        });
        
        if (!response.ok) {
          console.log('直接请求失败，状态码:', response.status);
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
      } catch (directError) {
        console.log('直接请求失败，尝试使用代理', directError);
      }

      // 如果直接请求失败，尝试使用代理
      if (proxyIndex >= CORS_PROXIES.length) {
        throw new Error('所有代理都已尝试失败');
      }

      const proxy = CORS_PROXIES[proxyIndex];
      console.log(`尝试使用代理 ${proxyIndex + 1}/${CORS_PROXIES.length}: ${proxy}`);
      
      const proxyUrl = proxy + encodeURIComponent(url);
      console.log('代理URL:', proxyUrl);

      const response = await fetch(proxyUrl, {
        ...options,
        headers: url.includes('chain.fm') ? {
          'authority': 'chain.fm',
          'accept': '*/*',
          'accept-language': 'zh-CN,zh;q=0.9',
          'content-type': 'application/json',
          'origin': 'https://chain.fm',
          'referer': 'https://chain.fm/',
          'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"macOS"',
          'sec-fetch-dest': 'empty',
          'sec-fetch-mode': 'cors',
          'sec-fetch-site': 'same-origin',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        } : {
          'Content-Type': 'application/json',
          'Accept': '*/*'
        }
      });
      
      if (!response.ok) {
        console.log(`代理 ${proxy} 请求失败，状态码:`, response.status);
        // 如果当前代理失败，尝试下一个代理
        return await fetchWithRetry(url, options, proxyIndex + 1);
      }
      
      const data = await response.json();
      console.log('代理请求成功，返回数据:', data);
      return data;
    } catch (error) {
      console.error(`代理 ${CORS_PROXIES[proxyIndex]} 请求失败:`, error);
      if (proxyIndex < CORS_PROXIES.length - 1) {
        // 如果还有其他代理可用，继续尝试
        return await fetchWithRetry(url, options, proxyIndex + 1);
      }
      throw error;
    }
  }

  // 修改mockExtensionRequest函数
  async function mockExtensionRequest(type, data) {
    try {
      switch (type) {
        case 'FETCH_PUMP_FUN': {
          const url = `https://frontend-api-v3.pump.fun/coins/search?offset=0&limit=50&sort=market_cap&includeNsfw=false&order=DESC&searchTerm=${data.address}&type=exact`;
          const pumpFunData = await fetchWithRetry(url);
          return { success: true, data: pumpFunData };
        }

        case 'FETCH_SMART_MONEY': {
          // 构建chain.fm的请求参数
          const params = {
            "0": {
              "json": {
                "page": 1,
                "pageSize": 30,
                "dateRange": null,
                "token": data.address,
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

          // 直接使用fetch请求，不使用代理
          const response = await fetch('https://chain.fm/api/trpc/parsedTransaction.list?batch=1', {
            method: 'POST',
            headers: {
              'accept': '*/*',
              'accept-language': 'zh-CN,zh;q=0.9',
              'content-type': 'application/json',
              'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
              'sec-ch-ua-mobile': '?0',
              'sec-ch-ua-platform': '"macOS"',
              'sec-fetch-dest': 'empty',
              'sec-fetch-mode': 'cors',
              'sec-fetch-site': 'same-origin',
              'Referer': 'https://chain.fm/',
              'Referrer-Policy': 'strict-origin-when-cross-origin'
            },
            body: JSON.stringify(params)
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const smartMoneyData = await response.json();
          return { success: true, data: smartMoneyData };
        }

        default:
          throw new Error('未知的请求类型');
      }
    } catch (error) {
      console.error('请求失败:', error);
      return { success: false, error: error.message };
    }
  }

  // 修改fetchPumpFunData函数
  async function fetchPumpFunData(address) {
    console.log('尝试从pump.fun获取数据');
    try {
      let response;
      
      if (isExtensionEnvironment) {
        // 在扩展环境中使用chrome.runtime.sendMessage
        response = await new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error('请求超时'));
          }, 30000);

          chrome.runtime.sendMessage({
            type: 'FETCH_PUMP_FUN',
            address: address
          }, (response) => {
            clearTimeout(timeoutId);
            if (chrome.runtime.lastError) {
              console.error('消息发送错误:', chrome.runtime.lastError);
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        });
      } else {
        // 在本地调试模式下直接调用API
        response = await mockExtensionRequest('FETCH_PUMP_FUN', { address });
      }

      if (!response.success) {
        throw new Error(response.error);
      }

      const pumpFunData = response.data;
      console.log('pump.fun返回数据:', pumpFunData);

      if (Array.isArray(pumpFunData) && pumpFunData.length > 0) {
        const tokenData = pumpFunData[0];
        return {
          pumpfun: {
            mint: tokenData.mint,
            name: tokenData.name,
            symbol: tokenData.symbol,
            image_uri: tokenData.image_uri,
            description: tokenData.description,
            twitter: tokenData.twitter,
            telegram: tokenData.telegram,
            website: tokenData.website,
            deploy_timestamp: tokenData.created_timestamp,
            deployer: tokenData.creator
          },
          analysis: {
            'lang-zh-CN': {
              summary: tokenData.description
            }
          }
        };
      }
      return null;
    } catch (error) {
      console.error('从pump.fun获取数据失败:', error);
      throw error;
    }
  }

  // 修改fetchSmartMoneyData函数
  async function fetchSmartMoneyData(address) {
    try {
      let response;
      
      if (isExtensionEnvironment) {
        // 在扩展环境中使用chrome.runtime.sendMessage
        response = await new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error('请求超时'));
          }, 30000);

          chrome.runtime.sendMessage({
            type: 'FETCH_SMART_MONEY',
            address: address
          }, (response) => {
            clearTimeout(timeoutId);
            if (chrome.runtime.lastError) {
              console.error('消息发送错误:', chrome.runtime.lastError);
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        });
      } else {
        // 在本地调试模式下直接调用API
        response = await mockExtensionRequest('FETCH_SMART_MONEY', { address });
      }

      // 调试日志
      console.log('智能钱包数据响应:', response);

      // 检查响应是否存在
      if (!response) {
        throw new Error('获取聪明钱数据失败: 无响应');
      }

      // 检查响应是否成功
      if (!response.success) {
        throw new Error(`获取聪明钱数据失败: ${response.error || '请求失败'}`);
      }

      return response;
    } catch (error) {
      console.error('获取聪明钱数据失败:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  // 搜索代币信息
  async function performSearch(address) {
    try {
      // 显示加载状态
      document.getElementById('loading').classList.remove('hidden');
      
      // 重置所有区域
      document.getElementById('tokenInfoContainer').innerHTML = '';
      document.getElementById('smartMoneyInfo').innerHTML = '';
      document.getElementById('smartMoneyCount').textContent = '';
      
      // 显示各个区域的加载动画
      document.getElementById('tokenInfoLoading').classList.add('active');
      document.getElementById('smartMoneyLoading').classList.add('active');
      
      // 首先获取代币基本信息
      const pumpFunData = await fetchPumpFunData(address);
      
      // 隐藏代币信息加载动画
      document.getElementById('tokenInfoLoading').classList.remove('active');
      
      // 显示代币基本信息
      if (pumpFunData) {
        console.log('显示代币基本信息:', pumpFunData);
        await displayTokenInfo(pumpFunData);
      } else {
        console.warn('获取代币信息失败');
        document.getElementById('tokenInfoContainer').innerHTML = `
          <div class="error-message">
            <p>获取代币信息失败</p>
          </div>
        `;
      }

      // 然后获取智能钱包数据
      const smartMoneyData = await fetchSmartMoneyData(address);
      
      // 隐藏智能钱包加载动画
      document.getElementById('smartMoneyLoading').classList.remove('active');
      
      // 处理智能钱包数据
      if (smartMoneyData && smartMoneyData.success) {
        await displaySmartMoneyData(smartMoneyData.data);
      } else {
        console.warn('获取聪明钱数据失败:', smartMoneyData?.error);
        document.getElementById('smartMoneyInfo').innerHTML = `
          <div class="error-message">
            <p>获取聪明钱数据失败: ${smartMoneyData?.error || '未知错误'}</p>
          </div>
        `;
      }

      // 调试信息
      const debugInfo = document.getElementById('debugInfo');
      debugInfo.textContent = JSON.stringify({
        pumpFunData,
        smartMoneyData
      }, null, 2);

      // 隐藏加载状态
      document.getElementById('loading').classList.add('hidden');

    } catch (error) {
      console.error('搜索处理失败:', error);
      
      // 显示错误信息
      showError(`搜索失败: ${error.message}`);
      
      // 隐藏所有加载动画
      document.getElementById('tokenInfoLoading').classList.remove('active');
      document.getElementById('smartMoneyLoading').classList.remove('active');
      document.getElementById('loading').classList.add('hidden');
    }
  }

  // 搜索按钮点击事件
  searchBtn.addEventListener('click', async function() {
    console.log('搜索按钮被点击');
    const address = contractInput.value.trim();
    if (!address) {
      showError('请输入合约地址');
      return;
    }

    try {
      lastSearchAddress = address;
      // 保存搜索地址
      if (isExtensionEnvironment) {
        await new Promise((resolve) => {
          chrome.storage.local.set({ lastAddress: address }, resolve);
        });
      } else {
        // 在非扩展环境中使用localStorage
        localStorage.setItem('lastAddress', address);
      }
      await performSearch(address);
    } catch (error) {
      console.error('搜索处理失败:', error);
      showError(`搜索失败: ${error.message}`);
    }
  });

  // 重试按钮点击事件
  retryBtn.addEventListener('click', async function() {
    if (lastSearchAddress) {
      await performSearch(lastSearchAddress);
    }
  });

  // 修改fetchTradeInfo函数支持本地环境
  async function fetchTradeInfo(address) {
    try {
      let response;
      
      if (isExtensionEnvironment) {
        response = await new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => {
            reject(new Error('请求超时'));
          }, 30000);

          chrome.runtime.sendMessage({
            type: 'FETCH_TRADE_INFO',
            address: address
          }, (response) => {
            clearTimeout(timeoutId);
            if (chrome.runtime.lastError) {
              console.error('消息发送错误:', chrome.runtime.lastError);
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        });
      } else {
        // 在本地环境中直接返回null，因为这个API目前不需要
        response = { success: true, data: null };
      }

      console.log('交易信息响应:', response);

      if (!response || !response.success) {
        throw new Error(`获取交易信息失败: ${response?.error || '未知错误'}`);
      }

      return response;
    } catch (error) {
      console.error('获取交易信息失败:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  function showError(message) {
    error.classList.remove('hidden');
    errorText.textContent = message;
    setTimeout(() => {
      error.classList.add('hidden');
    }, 3000);
  }

  // 修改displaySmartMoneyData函数
  async function displaySmartMoneyData(data) {
    try {
      console.log('开始显示智能钱包数据', data);
      
      // 检查数据结构
      if (!Array.isArray(data) || !data[0] || !data[0].result) {
        throw new Error('数据格式不正确');
      }

      // 修改数据访问路径
      const transactions = data[0].result.data.json.data.parsedTransactions || [];
      const addressLabelsMap = data[0].result.data.json.data.renderContext.addressLabelsMap || {};
      
      // 更新交易计数
      document.getElementById('smartMoneyCount').textContent = transactions.length.toString();

      if (transactions.length === 0) {
        document.getElementById('smartMoneyInfo').innerHTML = '<p class="no-data">暂无聪明钱数据</p>';
        return;
      }

      // 计算统计数据
      const stats = transactions.reduce((acc, tx) => {
        if (!tx.events || !tx.events[0] || !tx.events[0].data) return acc;
        const event = tx.events[0];
        const native_sol = event.data.order?.volume_native || 0;

        if (event.kind === 'token:buy') {
          acc.uniqueBuyers.add(event.address);
          acc.buyVolumeSol += native_sol;
        } else if (event.kind === 'token:sell') {
          acc.uniqueSellers.add(event.address);
          acc.sellVolumeSol += native_sol;
        }
        return acc;
      }, {
        uniqueBuyers: new Set(),
        uniqueSellers: new Set(),
        buyVolumeSol: 0,
        sellVolumeSol: 0
      });

      // 添加新的样式
      const styleElement = document.createElement('style');
      styleElement.textContent += `
        .transactions-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
          table-layout: fixed;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .transactions-table th,
        .transactions-table td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid #eee;
          color: #000;
        }

        .transactions-table th {
          background: #f8f9fa;
          font-weight: 600;
          color: #000;
          border-bottom: 2px solid #eee;
        }

        .transactions-table tr.buy-row {
          transition: background-color 0.3s;
        }

        .transactions-table tr.sell-row {
          transition: background-color 0.3s;
        }

        .transactions-table tr:last-child td {
          border-bottom: none;
        }

        .tx-type-cell {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-weight: 500;
        }

        .tx-type-cell.buy {
          background: rgba(34, 197, 94, 0.1);
          color: #22c55e;
        }

        .tx-type-cell.sell {
          background: rgba(239, 68, 68, 0.1);
          color: #ef4444;
        }

        .smart-money-title-buy {
          color: #22c55e;
        }

        .smart-money-title-sell {
          color: #ef4444;
        }
      `;
      document.head.appendChild(styleElement);

      // 更新标题显示统计信息
      const buyText = `买:${stats.uniqueBuyers.size} 人 ${Math.round(stats.buyVolumeSol).toLocaleString()} SOL`;
      const sellText = `卖：${stats.uniqueSellers.size} 人 ${Math.round(stats.sellVolumeSol).toLocaleString()} SOL`;
      
      // 查找标题元素并更新
      let smartMoneyTitle = document.getElementById('smartMoneyTitle');
      if (!smartMoneyTitle) {
        // 如果找不到标题元素，创建一个新的
        smartMoneyTitle = document.createElement('h2');
        smartMoneyTitle.id = 'smartMoneyTitle';
        const header = document.querySelector('.smart-money-section .section-header');
        if (header) {
          header.innerHTML = ''; // 清空现有内容
          header.appendChild(smartMoneyTitle);
        }
      }
      smartMoneyTitle.innerHTML = `聪明钱（<span class="smart-money-title-buy">${buyText}</span>,<span class="smart-money-title-sell">${sellText}</span>)`;

      // 找出最大交易量，用于计算颜色深度
      const maxVolume = Math.max(...transactions.map(tx => {
        if (!tx || !tx.events || !tx.events[0] || !tx.events[0].data) return 0;
        return tx.events[0].data.order?.volume_native || 0;
      }));

      // 构建表格HTML
      let html = `
        <table class="transactions-table">
          <colgroup>
            <col style="width: 15%">
            <col style="width: 10%">
            <col style="width: 45%">
            <col style="width: 15%">
            <col style="width: 15%">
          </colgroup>
          <thead>
            <tr>
              <th>时间</th>
              <th>类型</th>
              <th>聪明钱</th>
              <th>价格</th>
              <th>SOL</th>
            </tr>
          </thead>
          <tbody>
      `;
      
      for (const tx of transactions) {
        if (!tx || !tx.block_time || !tx.events || !tx.events[0]) continue;

        const timeString = getRelativeTimeString(tx.block_time);
        
        const event = tx.events[0];
        if (!event || !event.data) continue;

        const type = event.kind === 'token:buy' ? 'B' : 
                    event.kind === 'token:sell' ? 'S' : '交易';
        const typeClass = event.kind === 'token:buy' ? 'buy' : 
                         event.kind === 'token:sell' ? 'sell' : 'trade';
        
        const price = event.data.order?.price_usd?.toFixed(4) || '未知';
        const volume_native = event.data.order?.volume_native || 0;
        
        // 计算颜色深度（0.1到0.3之间）
        const opacity = 0.1 + (volume_native / maxVolume) * 0.2;
        const bgColor = event.kind === 'token:buy' ? 
          `rgba(34, 197, 94, ${opacity})` : 
          `rgba(239, 68, 68, ${opacity})`;
        
        // 获取地址标签
        let addressLabel = '未知';
        if (event.address && addressLabelsMap[event.address] && addressLabelsMap[event.address][0]) {
          addressLabel = addressLabelsMap[event.address][0].label;
        }
        
        html += `
          <tr class="${typeClass}-row" style="background-color: ${bgColor}">
            <td>${timeString}</td>
            <td><span class="tx-type-cell ${typeClass}">${type}</span></td>
            <td class="address-cell">
              <span class="address-text" style="color: #000;">${addressLabel}</span>
            </td>
            <td class="price-cell" style="color: #000;">$${price}</td>
            <td class="volume-cell" style="color: #000;">${Math.round(volume_native)}</td>
          </tr>
        `;
      }
      
      html += `
          </tbody>
        </table>
      `;
      document.getElementById('smartMoneyInfo').innerHTML = html;
      
    } catch (error) {
      console.error('显示智能钱包数据失败:', error);
      document.getElementById('smartMoneyInfo').innerHTML = `
        <div class="error-message">
          <p>显示智能钱包数据失败: ${error.message}</p>
        </div>
      `;
    }
  }

  async function displayTradeInfo(data) {
    try {
      console.log('开始显示交易信息');
      const tokenInfoContainer = document.getElementById('tokenInfoContainer');
      if (!tokenInfoContainer) {
        console.warn('未找到代币信息容器');
        return;
      }

      const {
        pumpfun: {
          name,
          symbol,
          image_uri,
          description,
          twitter,
          telegram,
          website,
          deploy_timestamp
        }
      } = data;

      // 计算部署时间
      const deployTime = new Date(deploy_timestamp);
      const now = new Date();
      const timeDiff = now - deployTime;
      const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
      let timeAgo;
      if (days > 0) {
        timeAgo = `${days}天前`;
      } else if (hours > 0) {
        timeAgo = `${hours}小时前`;
      } else {
        timeAgo = `${minutes}分钟前`;
      }

      const html = `
        <div class="trade-info">
          <div class="trade-info-header">
            <img src="${image_uri}" alt="${name}" class="token-icon" onerror="this.src='images/default-token.png'">
            <div class="token-info">
              <h3>${name} (${symbol})</h3>
              <p class="token-description">${description || '暂无描述'}</p>
              <p class="token-deploy-time">部署时间: ${timeAgo}</p>
            </div>
          </div>
          <div class="trade-info-links">
            ${website ? `<a href="${website}" target="_blank" class="link-item website-link">
              <img src="images/website.svg" class="link-icon">
              <span>网站</span>
            </a>` : ''}
            ${twitter ? `<a href="${twitter}" target="_blank" class="link-item twitter-link">
              <img src="images/twitter.svg" class="link-icon">
              <span>Twitter</span>
            </a>` : ''}
            ${telegram ? `<a href="${telegram}" target="_blank" class="link-item telegram-link">
              <img src="images/telegram.svg" class="link-icon">
              <span>Telegram</span>
            </a>` : ''}
          </div>
        </div>
      `;

      tokenInfoContainer.innerHTML = html;
    } catch (error) {
      console.error('显示交易信息失败:', error);
      const tokenInfoContainer = document.getElementById('tokenInfoContainer');
      if (tokenInfoContainer) {
        tokenInfoContainer.innerHTML = `
          <div class="error-message">
            <p>显示交易信息失败: ${error.message}</p>
          </div>
        `;
      }
    }
  }
});