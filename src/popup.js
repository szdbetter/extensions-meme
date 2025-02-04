async function fetchTradeInfo(address) {
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'FETCH_TRADE_INFO',
      address: address
    });

    if (!response || !response.data) {
      throw new Error('获取交易信息失败: 无响应数据');
    }

    if (!response.data.success) {
      throw new Error(`获取交易信息失败: ${response.data.message || '未知错误'}`);
    }

    return response.data;
  } catch (error) {
    console.error('获取交易信息失败:', error);
    throw error;
  }
} 