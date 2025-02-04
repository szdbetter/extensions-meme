// 简化版图表库
const LightweightCharts = {
  createChart: function(container, options) {
    const chartContainer = document.createElement('div');
    chartContainer.style.width = options.width + 'px';
    chartContainer.style.height = options.height + 'px';
    chartContainer.style.position = 'relative';
    chartContainer.style.background = '#f5f5f5';
    chartContainer.style.border = '1px solid #ddd';
    chartContainer.style.borderRadius = '4px';
    container.appendChild(chartContainer);

    return {
      addCandlestickSeries: function() {
        return {
          setData: function() {
            // 移除价格显示逻辑
          }
        };
      },
      applyOptions: function(newOptions) {
        chartContainer.style.width = newOptions.width + 'px';
        chartContainer.style.height = newOptions.height + 'px';
      },
      remove: function() {
        container.removeChild(chartContainer);
      }
    };
  }
};
