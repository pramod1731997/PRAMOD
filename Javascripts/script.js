// Dummy Data for Stock Sentiment
const stockData = {
    activeStocks: [
      "AAPL", "GOOGL", "AMZN", "MSFT", "TSLA"
    ],
    topGainers: [
      "TSLA +5.3%", "AMZN +3.9%", "GOOGL +2.4%", "NVDA +1.8%", "AAPL +1.6%"
    ],
    topLosers: [
      "META -4.2%", "NFLX -3.8%", "BABA -2.5%", "AMD -2.2%", "PFE -1.8%"
    ],
    optionsBuyers: [
      "AAPL (100k)", "GOOGL (95k)", "MSFT (85k)", "AMZN (80k)", "TSLA (75k)"
    ],
    optionsSellers: [
      "AAPL (70k)", "GOOGL (60k)", "AMZN (55k)", "MSFT (50k)", "TSLA (45k)"
    ],
    marketDepthBuyers: [
      "AAPL (2500)", "GOOGL (2300)", "AMZN (2200)", "TSLA (2100)", "MSFT (2000)"
    ],
    marketDepthSellers: [
      "META (2400)", "NFLX (2200)", "BABA (2000)", "AMD (1900)", "PFE (1800)"
    ]
  };
  
  function displayData() {
    // Active Stocks
    const activeStocksList = document.getElementById("active-stocks-list");
    stockData.activeStocks.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      activeStocksList.appendChild(li);
    });
  
    // Top Gainers
    const topGainersList = document.getElementById("top-gainers-list");
    stockData.topGainers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      topGainersList.appendChild(li);
    });
  
    // Top Losers
    const topLosersList = document.getElementById("top-losers-list");
    stockData.topLosers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      topLosersList.appendChild(li);
    });
  
    // Most Options Buyers
    const optionsBuyersList = document.getElementById("options-buyers-list");
    stockData.optionsBuyers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      optionsBuyersList.appendChild(li);
    });
  
    // Most Options Sellers
    const optionsSellersList = document.getElementById("options-sellers-list");
    stockData.optionsSellers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      optionsSellersList.appendChild(li);
    });
  
    // Stocks with Most Buyers in Market Depth
    const marketDepthBuyersList = document.getElementById("market-depth-buyers-list");
    stockData.marketDepthBuyers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      marketDepthBuyersList.appendChild(li);
    });
  
    // Stocks with Most Sellers in Market Depth
    const marketDepthSellersList = document.getElementById("market-depth-sellers-list");
    stockData.marketDepthSellers.forEach(stock => {
      let li = document.createElement("li");
      li.textContent = stock;
      marketDepthSellersList.appendChild(li);
    });
  }
  
  window.onload = displayData;
  