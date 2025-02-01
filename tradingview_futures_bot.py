import time
import requests
import ccxt
import tradingview_ta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plyer import notification

# Default parameters
exchange = "BITGET"
default_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
default_timeframe = "15m"

# Initialize ccxt exchange for live price fetching
bitget = ccxt.bitget()
previous_signals = {}  # Track previous signals

# Symbol options
symbol_options = sorted([
    {'label': 'Algorand (ALGOUSDT)', 'value': 'ALGOUSDT'},
    {'label': 'Avalanche (AVAXUSDT)', 'value': 'AVAXUSDT'},
    {'label': 'Binance Coin (BNBUSDT)', 'value': 'BNBUSDT'},
    {'label': 'Bitcoin (BTCUSDT)', 'value': 'BTCUSDT'},
    {'label': 'Brett (BRETTUSDT)', 'value': 'BRETTUSDT'},
    {'label': 'Cardano (ADAUSDT)', 'value': 'ADAUSDT'},
    {'label': 'Chainlink (LINKUSDT)', 'value': 'LINKUSDT'},
    {'label': 'Cosmos (ATOMUSDT)', 'value': 'ATOMUSDT'},
    {'label': 'Dogecoin (DOGEUSDT)', 'value': 'DOGEUSDT'},
    {'label': 'Ethereum (ETHUSDT)', 'value': 'ETHUSDT'},
    {'label': 'Ethereum Classic (ETCUSDT)', 'value': 'ETCUSDT'},
    {'label': 'Fetch.ai (FETUSDT)', 'value': 'FETUSDT'},
    {'label': 'Filecoin (FILUSDT)', 'value': 'FILUSDT'},
    {'label': 'Hedera (HBARUSDT)', 'value': 'HBARUSDT'},
    {'label': 'Injective Protocol (INJUSDT)', 'value': 'INJUSDT'},
    {'label': 'Jupiter (JUPUSDT)', 'value': 'JUPUSDT'},
    {'label': 'Kaspa (KASUSDT)', 'value': 'KASUSDT'},
    {'label': 'Lido DAO (LDOUSDT)', 'value': 'LDOUSDT'},
    {'label': 'Litecoin (LTCUSDT)', 'value': 'LTCUSDT'},
    {'label': 'Mocaverse (MOCAUSDT)', 'value': 'MOCAUSDT'},
    {'label': 'NEAR Protocol (NEARUSDT)', 'value': 'NEARUSDT'},
    {'label': 'Polygon (MATICUSDT)', 'value': 'MATICUSDT'},
    {'label': 'Polkadot (DOTUSDT)', 'value': 'DOTUSDT'},
    {'label': 'Qtum (QTUMUSDT)', 'value': 'QTUMUSDT'},
    {'label': 'Ripple (XRPUSDT)', 'value': 'XRPUSDT'},
    {'label': 'Shiba Inu (SHIBUSDT)', 'value': 'SHIBUSDT'},
    {'label': 'Solana (SOLUSDT)', 'value': 'SOLUSDT'},
    {'label': 'Stellar (XLMUSDT)', 'value': 'XLMUSDT'},
    {'label': 'Sui (SUIUSDT)', 'value': 'SUIUSDT'},
    {'label': 'Tao (TAOUSDT)', 'value': 'TAOUSDT'},
    {'label': 'Tezos (XTZUSDT)', 'value': 'XTZUSDT'},
    {'label': 'Theta Network (THETAUSDT)', 'value': 'THETAUSDT'},
    {'label': 'Tron (TRXUSDT)', 'value': 'TRXUSDT'},
    {'label': 'TrumpCoin (TRUMPUSDT)', 'value': 'TRUMPUSDT'},
    {'label': 'VeChain (VETUSDT)', 'value': 'VETUSDT'}
], key=lambda x: x['label'])

def fetch_tradingview_analysis(symbol, timeframe):
    """Fetch TradingView analysis with more indicators, including market trend."""
    try:
        analysis = tradingview_ta.TA_Handler(
            symbol=symbol, exchange=exchange, screener="crypto", interval=timeframe
        )
        full_analysis = analysis.get_analysis()
        
        market_trend = "UPTREND" if full_analysis.summary['BUY'] > full_analysis.summary['SELL'] else "DOWNTREND"
        
        return {
            "summary": full_analysis.summary,
            "moving_averages": full_analysis.moving_averages,
            "oscillators": full_analysis.oscillators,
            "market_trend": market_trend
        }
    except Exception as e:
        print(f"Error fetching TradingView data for {symbol}: {e}")
        return None

def fetch_live_price(symbol):
    """Fetch live price from Bitget."""
    formatted_symbol = symbol.replace("USDT", "/USDT")
    try:
        ticker = bitget.fetch_ticker(formatted_symbol)
        return ticker['last']
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None

def calculate_stop_loss_take_profit(entry_price, trade_signal, atr=0.03):
    """Use ATR-based SL/TP for adaptive risk management."""
    if trade_signal in ["LONG", "STRONG LONG"]:
        return entry_price * (1 - atr), entry_price * (1 + atr)
    elif trade_signal in ["SHORT", "STRONG SHORT"]:
        return entry_price * (1 + atr), entry_price * (1 - atr)
    return None, None

def generate_trade_signal(symbol, timeframe):
    """Enhanced signal processing using more TradingView indicators, including market trend."""
    analysis = fetch_tradingview_analysis(symbol, timeframe)
    if not analysis:
        return None
    
    summary = analysis["summary"]
    buy, sell, neutral = summary['BUY'], summary['SELL'], summary['NEUTRAL']
    
    moving_avg = analysis["moving_averages"]["RECOMMENDATION"]
    oscillators = analysis["oscillators"]["RECOMMENDATION"]
    market_trend = analysis["market_trend"]

    if moving_avg == "STRONG_BUY" and oscillators == "STRONG_BUY":
        trade_signal = "STRONG LONG"
    elif buy > sell and buy >= 10:
        trade_signal = "LONG"
    elif moving_avg == "STRONG_SELL" and oscillators == "STRONG_SELL":
        trade_signal = "STRONG SHORT"
    elif sell > buy and sell >= 10:
        trade_signal = "SHORT"
    else:
        trade_signal = "HOLD"
    
    entry_price = fetch_live_price(symbol)
    stop_loss, take_profit = (calculate_stop_loss_take_profit(entry_price, trade_signal) 
                              if entry_price else (None, None))
    
    if symbol in previous_signals and previous_signals[symbol] != trade_signal:
        notification.notify(
            title=f"Trade Signal Update: {symbol}",
            message=f"New Signal: {trade_signal}",
            timeout=5
        )
    previous_signals[symbol] = trade_signal
    
    return {
        "Symbol": symbol, "Trade Signal": trade_signal,
        "Buy Pressure": buy, "Sell Pressure": sell, "Neutral": neutral,
        "Moving Averages": moving_avg, "Oscillators": oscillators,
        "Market Trend": market_trend,
        "Current Price": entry_price,
        "Stop Loss": stop_loss, "Take Profit": take_profit
    }
    
    summary = analysis["summary"]
    buy, sell, neutral = summary['BUY'], summary['SELL'], summary['NEUTRAL']
    
    moving_avg = analysis["moving_averages"]["RECOMMENDATION"]
    oscillators = analysis["oscillators"]["RECOMMENDATION"]

    if moving_avg == "STRONG_BUY" and oscillators == "STRONG_BUY":
        trade_signal = "STRONG LONG"
    elif buy > sell and buy >= 10:
        trade_signal = "LONG"
    elif moving_avg == "STRONG_SELL" and oscillators == "STRONG_SELL":
        trade_signal = "STRONG SHORT"
    elif sell > buy and sell >= 10:
        trade_signal = "SHORT"
    else:
        trade_signal = "HOLD"
    
    entry_price = fetch_live_price(symbol)
    stop_loss, take_profit = (calculate_stop_loss_take_profit(entry_price, trade_signal) 
                              if entry_price else (None, None))
    
    if symbol in previous_signals and previous_signals[symbol] != trade_signal:
        notification.notify(
            title=f"Trade Signal Update: {symbol}",
            message=f"New Signal: {trade_signal}",
            timeout=5
        )
    previous_signals[symbol] = trade_signal
    
    return {
        "Symbol": symbol, "Trade Signal": trade_signal,
        "Buy Pressure": buy, "Sell Pressure": sell, "Neutral": neutral,
        "Moving Averages": moving_avg, "Oscillators": oscillators,
        "Current Price": entry_price,
        "Stop Loss": stop_loss, "Take Profit": take_profit
    }
    
    buy, sell = analysis['BUY'], analysis['SELL']
    if buy > sell and buy >= 10:
        trade_signal = "STRONG LONG"
    elif buy > sell:
        trade_signal = "LONG"
    elif sell > buy and sell >= 10:
        trade_signal = "STRONG SHORT"
    elif sell > buy:
        trade_signal = "SHORT"
    else:
        trade_signal = "HOLD"
    
    entry_price = fetch_live_price(symbol)
    stop_loss, take_profit = (calculate_stop_loss_take_profit(entry_price, trade_signal) 
                              if entry_price else (None, None))
    
    if symbol in previous_signals and previous_signals[symbol] != trade_signal:
        notification.notify(
            title=f"Trade Signal Update: {symbol}",
            message=f"New Signal: {trade_signal}",
            timeout=5
        )
    previous_signals[symbol] = trade_signal
    
    return {
        "Symbol": symbol, "Trade Signal": trade_signal,
        "Buy Pressure": buy, "Sell Pressure": sell,
        "Current Price": entry_price,
        "Stop Loss": stop_loss, "Take Profit": take_profit
    }

def get_signal_color(signal):
    """Assign colors to trade signals."""
    return {"STRONG LONG": "green", "LONG": "blue", "SHORT": "orange", "STRONG SHORT": "red"}.get(signal, "black")

# Dash Dashboard
app = dash.Dash(__name__)
app.layout = html.Div(style={'backgroundColor': 'white', 'color': 'black', 'fontFamily': 'Arial, sans-serif'}, children=[
    html.H1("TradingView Futures Analysis Dashboard"),
    html.P("Click on a ticker to view its chart on TradingView.", style={'font-size': '14px', 'color': 'gray'}),
    html.Label("Select Symbols:"),
    dcc.Dropdown(id='symbols_dropdown', options=symbol_options, value=default_symbols, multi=True),
    html.Label("Select Timeframe:"),
    dcc.Dropdown(id='timeframe_dropdown', options=[
        {'label': '1 Minute', 'value': '1m'},
        {'label': '15 Minutes', 'value': '15m'},
        {'label': '1 Hour', 'value': '1h'},
        {'label': '4 Hours', 'value': '4h'},
        {'label': '1 Day', 'value': '1d'}
    ], value=default_timeframe),
    dcc.Interval(id='interval', interval=60000, n_intervals=0),
    html.Div(id='trade_signal_output', style={'display': 'flex', 'flex-wrap': 'wrap', 'justify-content': 'space-around'})
])

@app.callback(
    Output('trade_signal_output', 'children'),
    [Input('interval', 'n_intervals'), Input('symbols_dropdown', 'value'), Input('timeframe_dropdown', 'value')]
)
def update_dashboard(n, symbols, timeframe):
    trade_signals = []
    sorted_signals = []
    for symbol in symbols:
        signal_data = generate_trade_signal(symbol, timeframe)
        if signal_data:
            sorted_signals.append(signal_data)
    
    sorted_signals.sort(key=lambda x: ['STRONG LONG', 'STRONG SHORT', 'LONG', 'SHORT'].index(x['Trade Signal']) if x['Trade Signal'] in ['STRONG LONG', 'STRONG SHORT', 'LONG', 'SHORT'] else 4)
    
    for signal_data in sorted_signals:
        trade_signals.append(html.Div([
                html.A(signal_data['Symbol'], href=f'https://www.tradingview.com/chart/?symbol=BITGET:{signal_data["Symbol"]}', target='_blank', style={'text-decoration': 'none', 'color': 'black'}),
                html.P(f"Trade Signal: {signal_data['Trade Signal']}", style={'color': get_signal_color(signal_data['Trade Signal'])}),
                html.P(f"Buy Pressure: {signal_data['Buy Pressure']}"),
                html.P(f"Sell Pressure: {signal_data['Sell Pressure']}"),
                html.P(f"Current Price: {signal_data['Current Price']}", style={'color': 'blue'}),
                html.P(f"Moving Averages: {signal_data['Moving Averages']}"),
                html.P(f"Oscillators: {signal_data['Oscillators']}"),
                html.P(f"Market Trend: {signal_data['Market Trend']}", style={'font-weight': 'bold'}),
                html.P(f"Stop Loss: {signal_data['Stop Loss']}", style={'color': 'red'}),
                html.P(f"Take Profit: {signal_data['Take Profit']}", style={'color': 'green'})
            ], style={'border': '2px solid #333', 'border-radius': '10px', 'background-color': '#f9f9f9', 'padding': '10px', 'margin-bottom': '10px'}))
    return trade_signals

if __name__ == "__main__":
    app.run_server(debug=True)
