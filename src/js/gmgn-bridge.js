// 等待页面完全加载
window.addEventListener('load', () => {
  // 等待Cloudflare验证完成
  const checkReady = setInterval(() => {
    // 检查是否存在特定的DOM元素或Cookie来确认验证完成
    if (document.cookie.includes('cf_clearance')) {
      clearInterval(checkReady);
      console.log('页面已准备就绪');
      
      // 通知background.js页面已准备好
      chrome.runtime.sendMessage({ type: 'gmgnBridgeReady' });
      
      // 监听请求
      chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.type === 'gmgnRequest') {
          console.log('Bridge收到请求:', request);
          
          // 使用页面的fetch函数发送请求
          window.fetch(request.url + '?' + request.params, {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'Referer': window.location.href,
              // 使用页面当前的cookie
              'Cookie': document.cookie
            },
            credentials: 'include'
          })
          .then(response => {
            console.log('Bridge响应状态:', response.status);
            if (!response.ok) {
              throw new Error(`请求失败: ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            console.log('Bridge获取数据成功:', data);
            sendResponse({ success: true, data: data });
          })
          .catch(error => {
            console.error('Bridge请求失败:', error);
            sendResponse({ success: false, error: error.message });
          });
          
          return true; // 保持消息通道开放
        }
      });
    }
  }, 1000); // 每秒检查一次
  
  // 30秒后如果还没准备好，就停止检查
  setTimeout(() => {
    clearInterval(checkReady);
    console.log('页面准备超时');
  }, 30000);
}); 