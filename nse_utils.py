import nsepython as nse
import pandas as pd
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available indices for trading
INDICES = {
    'NIFTY': 'NIFTY 50',
    'BANKNIFTY': 'Bank Nifty',
    'FINNIFTY': 'Fin Nifty',
    'MIDCPNIFTY': 'Nifty Midcap 50'
}

INDICES_LIST = list(INDICES.keys())


def get_expiries(symbol: str, option_type: str = 'indices') -> List[str]:
    """
    Fetch available expiry dates for a symbol.
    
    Args:
        symbol: Stock/Index symbol (e.g., 'NIFTY', 'RELIANCE')
        option_type: 'indices' or 'equities'
    
    Returns:
        List of expiry date strings (e.g., ['27-Jan-2025', '03-Feb-2025'])
    """
    try:
        url = f'https://www.nseindia.com/api/option-chain-contract-info?symbol={symbol}'
        payload = nse.nsefetch(url)
        
        if 'expiryDates' in payload:
            return payload['expiryDates']
        else:
            logger.warning(f"No expiry dates found for {symbol}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching expiries for {symbol}: {str(e)}")
        return []


def get_option_chain(
    symbol: str, 
    expiry: str, 
    option_type: str = 'indices'
) -> Dict:
    """
    Fetch full option chain data for a symbol and expiry.
    
    Args:
        symbol: Stock/Index symbol
        expiry: Expiry date string (e.g., '27-Jan-2025')
        option_type: 'indices' or 'equities'
    
    Returns:
        Dictionary with option chain records
    """
    try:
        url = (
            f'https://www.nseindia.com/api/option-chain-v3?type={option_type}'
            f'&symbol={symbol}&expiry={expiry}'
        )
        payload = nse.nsefetch(url)
        
        if 'records' in payload and 'data' in payload['records']:
            return payload['records']
        else:
            logger.warning(f"No option chain data found for {symbol} {expiry}")
            return {'data': []}
    
    except Exception as e:
        logger.error(f"Error fetching option chain: {str(e)}")
        return {'data': []}


def calculate_activity_score(row: Dict) -> float:
    """
    Calculate activity score for a strike based on volume and OI.
    Higher score = more active.
    
    Args:
        row: Single strike row from option chain
    
    Returns:
        Activity score (float)
    """
    score = 0
    
    # CE activity
    if 'CE' in row:
        ce = row['CE']
        ce_oi = ce.get('openInterest', 0) or 0
        ce_volume = ce.get('totalTradedVolume', 0) or 0
        ce_qty = (ce.get('totalBuyQuantity', 0) or 0) + (ce.get('totalSellQuantity', 0) or 0)
        score += (ce_oi * 0.5) + (ce_volume * 0.3) + (ce_qty * 0.2)
    
    # PE activity
    if 'PE' in row:
        pe = row['PE']
        pe_oi = pe.get('openInterest', 0) or 0
        pe_volume = pe.get('totalTradedVolume', 0) or 0
        pe_qty = (pe.get('totalBuyQuantity', 0) or 0) + (pe.get('totalSellQuantity', 0) or 0)
        score += (pe_oi * 0.5) + (pe_volume * 0.3) + (pe_qty * 0.2)
    
    return score


def get_top5_active_strikes(
    option_chain_data: Dict,
    symbol: str,
    option_type: str = 'indices'
) -> List[Dict]:
    """
    Get top 5 most active strikes from option chain data.
    
    Args:
        option_chain_data: Dict from get_option_chain()
        symbol: Symbol name (for getting underlying value)
        option_type: 'indices' or 'equities'
    
    Returns:
        List of top 5 strike dicts with CE/PE data
    """
    if not option_chain_data or 'data' not in option_chain_data:
        return []
    
    try:
        # Calculate activity for each strike
        strikes_with_score = []
        
        for row in option_chain_data['data']:
            score = calculate_activity_score(row)
            strikes_with_score.append((row, score))
        
        # Sort by score descending
        strikes_with_score.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 5
        top5 = [row for row, score in strikes_with_score[:5]]
        
        return top5
    
    except Exception as e:
        logger.error(f"Error getting top 5 strikes: {str(e)}")
        return []


def format_strike_data(strike_row: Dict, strike_price: float) -> str:
    output = f"\n<b>Strike: {strike_price:.2f}</b>\n"

    # CE Data
    if 'CE' in strike_row:
        ce = strike_row['CE']
        ce_ltp = ce.get('lastPrice', 0.0) or 0.0
        ce_oi = ce.get('openInterest', 0.0) or 0.0
        ce_iv = ce.get('impliedVolatility', 0.0) or 0.0

        output += (
            f"📈 <b>CE:</b> "
            f"LTP <code>{ce_ltp:.2f}</code> | "
            f"OI <code>{ce_oi:.2f}</code> | "
            f"IV <code>{ce_iv:.2f}%</code>\n"
        )
    else:
        output += "📈 CE: No data\n"

    # PE Data
    if 'PE' in strike_row:
        pe = strike_row['PE']
        pe_ltp = pe.get('lastPrice', 0.0) or 0.0
        pe_oi = pe.get('openInterest', 0.0) or 0.0
        pe_iv = pe.get('impliedVolatility', 0.0) or 0.0

        output += (
            f"📉 <b>PE:</b> "
            f"LTP <code>{pe_ltp:.2f}</code> | "
            f"OI <code>{pe_oi:.2f}</code> | "
            f"IV <code>{pe_iv:.2f}%</code>\n"
        )
    else:
        output += "📉 PE: No data\n"

    return output


def format_option_chain_message(option_chain_data: Dict, symbol: str, expiry: str, option_type: str = 'indices') -> str:
    top5_strikes = get_top5_active_strikes(option_chain_data, symbol, option_type)
    if not top5_strikes:
        return f"❌ No active strikes found for {symbol} {expiry}"

    total_ce_oi = 0.0
    total_pe_oi = 0.0
    for row in option_chain_data.get('data', []):
        if 'CE' in row:
            total_ce_oi += row['CE'].get('openInterest', 0.0) or 0.0
        if 'PE' in row:
            total_pe_oi += row['PE'].get('openInterest', 0.0) or 0.0

    pcr = (total_pe_oi / total_ce_oi) if total_ce_oi else 0.0

    symbol_name = INDICES.get(symbol, symbol)
    message = (
        f"<b>🎯 {symbol_name}</b> | Expiry: <b>{expiry}</b>\n"
        f"PCR: <code>{pcr:.2f}</code> | "
        f"Total CE OI: <code>{total_ce_oi:.2f}</code> | "
        f"Total PE OI: <code>{total_pe_oi:.2f}</code>\n"
        + "=" * 50 + "\n"
        "<b>Top 5 Most Active Strikes:</b>\n"
    )

    for strike_row in top5_strikes:
        strike_price = strike_row.get('strikePrice', 0.0)
        message += format_strike_data(strike_row, strike_price)

    return message

def format_most_active() -> str:
    df = nse.nse_most_active()  # usually returns DataFrame[web:62]
    df = df.head(10)
    lines = ["🔥 <b>Most Active (By Value)</b>\n"]
    for i, row in df.iterrows():
        symbol = row.get("symbol")
        ltp = row.get("lastPrice")
        trn = row.get("totalTradedValue")
        vol = row.get("quantityTraded")
        lines.append(
            f"{i+1} <b>{symbol}</b> | LTP <code>{ltp:.2f}</code> | Turnover <code>{trn:.2f}</code> | Vol <code>{vol:.2f}</code>"
        )
    return "\n".join(lines)


def format_preopen_movers() -> str:
    df = nse.nse_preopen_movers()  # preopen gainers/losers[web:62]
    df = df.head(10)
    lines = ["🕒 <b>Preopen Movers</b>\n"]
    for i, row in df.iterrows():
        symbol = row.get("symbol")
        prev = row.get("previousClose")
        open_ = row.get("lastPrice")
        chg = row.get("pChange")
        lines.append(
            f"{i+1} <b>{symbol}</b> | Prev <code>{prev:.2f}</code> | "
            f"Open <code>{open_:.2f}</code> | Chg <code>{chg:.2f}%</code>"
        )
    return "\n".join(lines)


def format_fiidii() -> str:
    df = nse.nse_fiidii()  # FII/DII flows table[web:62]
    lines = ["🏦 <b>FII / DII Activity</b>\n"]
    for _, row in df.iterrows():
        cat = row.get("category")
        buy = row.get("buyValue")
        sell = row.get("sellValue")
        net = row.get("netValue")
        lines.append(
            f"<b>{cat}</b> | Buy <code>{buy}</code> | Sell <code>{sell}</code> | Net <code>{net}</code>"
        )
    return "\n".join(lines)


def format_block_deals() -> str:
    df = nse.get_blockdeals()  # recent block deals[web:62]
    df = df.head(10)
    lines = ["📦 <b>Recent Block Deals (Top 10)</b>\n"]
    for _, row in df.iterrows():
        symbol = row.get("Symbol")
        qty = row.get("Quantity Traded")
        price = row.get("Trade Price / Wght. Avg. Price")
        buyer = row.get("Client Name")
        seller = row.get("Client Name")
        lines.append(
            f"<b>{symbol}</b> | Qty <code>{qty:.2f}</code> | "
            f"Price <code>{price:.2f}</code>\n"
            f"   B: {buyer} | S: {seller}"
        )
    return "\n".join(lines)


def format_bulk_deals() -> str:
    df = nse.get_bulkdeals()
    df = df.head(20)
    lines = ["📊 <b>Recent Bulk Deals (Top 10)</b>\n"]
    
    for _, row in df.iterrows():
        symbol = row.get("Symbol") or row.get("SYMBOL") or ""
        qty = row.get("Quantity Traded") or row.get("QUANTITY") or 0.0
        price = row.get("Trade Price / Wght. Avg. Price") or row.get("PRICE") or 0.0
        
        client_name = row.get("Client Name") or row.get("CLIENT_NAME") or ""
        client_type = row.get("Buy/Sell") or row.get("TRADE_TYPE") or ""
        
        # Build buyer/seller strings
        buyer_str = ""
        seller_str = ""
        
        if "BUY" in str(client_type).upper():
            buyer_str = f"🟢 BUYER: {client_name}"
        elif "SELL" in str(client_type).upper():
            seller_str = f"🔴 SELLER: {client_name}"
        
        # Combine on same line
        if buyer_str and seller_str:
            lines.append(
                f"<b>{symbol}</b> | Qty <code>{qty:.2f}</code> | "
                f"Price <code>{price:.2f}</code>\n"
                f"   {buyer_str} {seller_str}"
            )
        elif buyer_str:
            lines.append(
                f"<b>{symbol}</b> | Qty <code>{qty:.2f}</code> | "
                f"Price <code>{price:.2f}</code>\n"
                f"   {buyer_str}"
            )
        elif seller_str:
            lines.append(
                f"<b>{symbol}</b> | Qty <code>{qty:.2f}</code> | "
                f"Price <code>{price:.2f}</code>\n"
                f"   {seller_str}"
            )
        else:
            lines.append(
                f"<b>{symbol}</b> | Qty <code>{qty:.2f}</code> | "
                f"Price <code>{price:.2f}</code>\n"
                f"   👤 Client: {client_name}"
            )
    
    return "\n".join(lines)




def format_indiavix() -> str:
    vix = nse.indiavix()  # dict with index data[web:62]
    ltp = vix.get("last") or vix.get("lastPrice") or 0.0
    chg = vix.get("variation") or vix.get("change") or 0.0
    pchg = vix.get("percentChange") or 0.0
    open_ = vix.get("open") or 0.0
    high = vix.get("high") or 0.0
    low = vix.get("low") or 0.0
    prev = vix.get("previousClose") or 0.0

    return (
        "⚡ <b>India VIX</b>\n\n"
        f"LTP: <code>{ltp:.2f}</code> | Chg <code>{chg:.2f}</code> "
        f"(<code>{pchg:.2f}%</code>)\n"
        f"Open <code>{open_:.2f}</code> | High <code>{high:.2f}</code> | "
        f"Low <code>{low:.2f}</code> | Prev <code>{prev:.2f}</code>"
    )


def format_top_gainers() -> str:
    df = nse.nse_get_top_gainers()  # top gainers list[web:6]
    df = df.head(10)
    lines = ["📈 <b>Top Gainers</b>\n"]
    for i, row in df.iterrows():
        symbol = row.get("symbol") or row.get("SYMBOL") or ""
        ltp = row.get("ltp") or row.get("LTP") or 0.0
        pchg = row.get("netPrice") or row.get("%CHNG") or 0.0
        vol = row.get("tradedQuantity") or row.get("VOLUME") or 0.0
        lines.append(
            f"{i+1} <b>{symbol}</b> | LTP <code>{ltp:.2f}</code> | "
            f"Chg <code>{pchg:.2f}%</code> | Vol <code>{vol:.2f}</code>"
        )
    return "\n".join(lines)


def format_top_losers() -> str:
    df = nse.nse_get_top_losers()  # top losers list[web:6]
    df = df.head(10)
    lines = ["📉 <b>Top Losers</b>\n"]
    for i, row in df.iterrows():
        symbol = row.get("symbol") or row.get("SYMBOL") or ""
        ltp = row.get("ltp") or row.get("LTP") or 0.0
        pchg = row.get("netPrice") or row.get("%CHNG") or 0.0
        vol = row.get("tradedQuantity") or row.get("VOLUME") or 0.0
        lines.append(
            f"{i+1} <b>{symbol}</b> | LTP <code>{ltp:.2f}</code> | "
            f"Chg <code>{pchg:.2f}%</code> | Vol <code>{vol:.2f}</code>"
            )
    return "\n".join(lines)
