// 监听页面上的合约地址
document.addEventListener('mouseover', function(event) {
  // 检查是否是文本节点
  if (event.target.nodeType === Node.TEXT_NODE || 
      event.target.tagName === 'INPUT' || 
      event.target.tagName === 'TEXTAREA') {
    
    const text = event.target.textContent || event.target.value;
    // 简单的Solana地址格式检查（这里可以根据需要调整正则表达式）
    if (text && text.match(/^[1-9A-HJ-NP-Za-km-z]{32,44}$/)) {
      // 向background script发送消息
      chrome.runtime.sendMessage({
        type: 'GET_TOKEN_INFO',
        address: text
      }, response => {
        if (response && response.success) {
          // 这里可以添加显示tooltip的逻辑
          showTooltip(event.target, response.data);
        }
      });
    }
  }
});

// 创建和显示tooltip的函数
function showTooltip(element, data) {
  // 移除已存在的tooltip
  const existingTooltip = document.getElementById('meme-token-tooltip');
  if (existingTooltip) {
    existingTooltip.remove();
  }

  // 创建tooltip元素
  const tooltip = document.createElement('div');
  tooltip.id = 'meme-token-tooltip';
  tooltip.style.cssText = `
    position: absolute;
    z-index: 10000;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    max-width: 300px;
    font-size: 12px;
  `;

  // 添加数据到tooltip
  if (data[0]?.result?.data) {
    const smartMoneyInfo = data[0].result.data[0];
    tooltip.innerHTML = `
      <div style="margin-bottom: 8px;">
        <strong>最新智能资金动向:</strong><br>
        地址: ${smartMoneyInfo.address}<br>
        数量: ${smartMoneyInfo.amount}<br>
        时间: ${new Date(smartMoneyInfo.timestamp).toLocaleString()}
      </div>
    `;
  }

  // 定位tooltip
  const rect = element.getBoundingClientRect();
  tooltip.style.left = `${rect.left + window.scrollX}px`;
  tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;

  // 添加到页面
  document.body.appendChild(tooltip);

  // 监听鼠标离开事件
  element.addEventListener('mouseout', function() {
    tooltip.remove();
  });
} 