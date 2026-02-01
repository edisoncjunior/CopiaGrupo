# VERSAO 2 Main CopiaGrupo BINANCE 
# Com LOG e envio diário as 00h funcionando
# T
# Bruno Aguiar - MEXC com Taxa Zero

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

TZ_BRASILIA = timezone(timedelta(hours=-3))
last_sent_date = None

# -------------------------------------------------
# Moedas permitidas para alerta
# -------------------------------------------------
ALLOWED_SYMBOLS = {
#Lista dos ativos do Bruno Aguiar na MEXC com taxa zero:
#    "BCHUSDT", "BNBUSDT", "CHZUSDT", "DOGEUSDT", "ENAUSDT", "ETHUSDT",
#    "JASMYUSDT", "SOLUSDT", "UNIUSDT", "XMRUSDT", 
    "XRPUSDT"
}
 
# -------------------------------------------------
# Ambiente local → carrega .env (se existir)
# Ambiente web  → ignora .env e usa env vars
# -------------------------------------------------
try:
    from dotenv import load_dotenv
    if os.path.exists(".env"):
        load_dotenv()
        print("[ENV] .env carregado (execução local)")
    else:
        print("[ENV] execução web (Railway)")
except ImportError:
    # python-dotenv não instalado (Railway/GitHub)
    print("[ENV] python-dotenv ausente (execução web)")

# -------------------------------------------------
# Variáveis de ambiente (obrigatórias)
# -------------------------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SOURCE_CHAT_ID = int(os.environ["SOURCE_CHAT_ID"])
TARGET_CHAT_ID = int(os.environ["TARGET_CHAT_ID"])
SESSION_STRING = os.environ["TELEGRAM_SESSION_STRING"]

BINANCE_API_KEY = os.environ["BINANCE_API_KEY"]
BINANCE_API_SECRET = os.environ["BINANCE_API_SECRET"]

# -------------------------------------------------
# Cliente Telegram
# -------------------------------------------------
client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)

# -------------------------------------------------
# Cliente Binance
# -------------------------------------------------
def get_binance_client():
    return Client(
        BINANCE_API_KEY,
        BINANCE_API_SECRET
    )

# ---------------------------------------------------
# Extrai dados estruturados da mensagem do Telegram.
# Retorna dict ou None se não casar com o padrão.
# ---------------------------------------------------
def parse_signal_message(text: str):
    # Normaliza texto
    text = text.strip().replace("\r", "")

    # Regex principal
    pattern = re.compile(
        r'^(?P<exchange>\w+):(?P<symbol>\w+)\s+deu\s+'
        r'(?P<signal>.+?)\s+nos?\s+'
        r'(?P<time>\d+)\s+minutos?.*?\n+'
        r'Preço:\s*(?P<price>[\d\.]+)',
        re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(text)
    if not match:
        return None

    exchange = match.group("exchange").upper()
    symbol = match.group("symbol").upper()
    signal = match.group("signal").strip().lower()
    timeframe = f'{match.group("time")} minutos'
    price = match.group("price").replace(".", ",")

    return {
        "exchange": exchange,
        "symbol": symbol,
        "signal": signal,
        "timeframe": timeframe,
        "price": price
    }
# -------------------------------------------------------------------------
# Função que verifica se já possui uma posição na Binance
# -------------------------------------------------------------------------
def has_open_position(symbol: str, position_side: str) -> bool:
    """
    Retorna True se já existir posição aberta (qty != 0)
    """
    binance = get_binance_client()

    try:
        positions = binance.futures_position_information(symbol=symbol)

        for pos in positions:
            if (
                pos["symbol"] == symbol
                and pos["positionSide"] == position_side
                and float(pos["positionAmt"]) != 0.0
            ):
                return True

        return False

    except BinanceAPIException as e:
        print(f"[BINANCE][POSITION][ERRO] {e}")
        return True  # segurança: assume que existe

# -------------------------------------------------------------------------
# Função cria ordem Binance
# -------------------------------------------------------------------------
def create_binance_order(signal: dict):
    binance = get_binance_client()
    symbol = signal["symbol"]
    signal_type = signal["signal"]

    # ---- MAPEAMENTO DO SINAL ----
    if "compra" in signal_type:
        side = SIDE_BUY
        position_side = "LONG"
    elif "venda" in signal_type:
        side = SIDE_SELL
        position_side = "SHORT"
    else:
        print("[BINANCE] Sinal não reconhecido")
        return
    # ---------------------------------
    # BLOQUEIO: posição já aberta
    # ---------------------------------
    if has_open_position(symbol, position_side):
        print(
            "[BINANCE][SKIP] Posição já aberta | "
            f"Symbol={symbol} | Position={position_side}"
        )
        return


    # ---- CONFIGURAÇÕES FIXAS (AJUSTE SE QUISER) ----
    quantity = 10  # contratos
    leverage = 10  # alavancagem

    try:
        # Setar alavancagem
        binance.futures_change_leverage(
            symbol=symbol,
            leverage=leverage
        )

        order = binance.futures_create_order(
            symbol=symbol,
            side=side,
            positionSide=position_side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )

        # ------------------------------
        # CONFIRMA EXECUÇÃO
        # ------------------------------
        if not order_filled(order):
            print("[BINANCE] Ordem criada mas não executada ainda")
            return

        entry_price = float(order.get("avgPrice"))
        executed_qty = float(order.get("executedQty"))

        print(
            "[BINANCE] ORDEM CONFIRMADA | "
            f"Symbol={symbol} | "
            f"Entry={entry_price} | "
            f"Qty={executed_qty}"
        )

        # ------------------------------
        # CRIA TAKE PROFIT 50%
        # ------------------------------
        create_take_profit_50(
            symbol=symbol,
            position_side=position_side,
            entry_price=entry_price,
            qty=executed_qty,
            leverage=leverage
        )


        order_price = order.get("avgPrice") or order.get("price") or "market"
        executed_qty = order.get("executedQty")
        order_id = order.get("orderId")
        client_order_id = order.get("clientOrderId")
        status = order.get("status")

        print(
            "[BINANCE] ORDEM EXECUTADA | "
            f"Symbol={symbol} | "
            f"Side={side} | "
            f"Position={position_side} | "
            f"Qty={executed_qty} | "
            f"Preço={order_price} | "
            f"Status={status} | "
            f"OrderID={order_id}"
        )

        return order

    except BinanceAPIException as e:
        print(f"[BINANCE][ERRO] {e}")

# -------------------------------------------------------------------------
# Função que confirma se ordem foi criada na Binance
# -------------------------------------------------------------------------
def order_filled(order: dict) -> bool:
    binance = get_binance_client()
    return order.get("status") in ("FILLED", "PARTIALLY_FILLED")

# -------------------------------------------------------------------------
# Função que cria TP 50%
# -------------------------------------------------------------------------
def create_take_profit_50(symbol, position_side, entry_price, qty, leverage):
    binance = get_binance_client()
    TP_PERCENT = 0.50  / leverage # 50%

    if position_side == "LONG":
        tp_price = round(entry_price * (1 + TP_PERCENT), 6)
        side = SIDE_SELL
    else:  # SHORT
        tp_price = round(entry_price * (1 - TP_PERCENT), 6)
        side = SIDE_BUY

    try:
        tp_order = binance.futures_create_order(
            symbol=symbol,
            side=side,
            positionSide=position_side,
            type=ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=tp_price,
            closePosition=False,
            quantity=qty,
            workingType="MARK_PRICE"
        )

        print(
            "[BINANCE][TP] Criado | "
            f"Symbol={symbol} | "
            f"Position={position_side} | "
            f"Qty={qty} | "
            f"TP_Price={tp_price}"
        )

        return tp_order

    except BinanceAPIException as e:
        print(f"[BINANCE][TP][ERRO] {e}")

# -------------------------------------------------------------------------
# Função que retorna a data
# -------------------------------------------------------------------------

def get_operational_date(now):
    return now.date()

# -------------------------------------------------
# Função para gravar o log tabulado
# -------------------------------------------------
def write_log(data: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    now = datetime.now(TZ_BRASILIA)

    operational_date = get_operational_date(now)
    file_name = f"log_{operational_date.isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    header = "Data\tHora\tExchange\tMoeda\tSinal\tGrafico\tPreco\n"
    file_exists = os.path.exists(log_path)

    data_str = now.strftime("%d/%m/%Y")
    hora_str = now.strftime("%H:%M:%S")

    with open(log_path, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(header)

        f.write(
            f"{data_str}\t"
            f"{hora_str}\t"
            f"{data['exchange']}\t"
            f"{data['symbol']}\t"
            f"{data['signal']}\t"
            f"{data['timeframe']}\t"
            f"{data['price']}\n"
        )

# -------------------------------------------------
# Listener de mensagens
# -------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def forward_message(event):
    try:
        text = event.message.text or ""

        # -------- LOG --------
        parsed = parse_signal_message(text)
        if parsed:
            write_log(parsed)
            print(f"[LOG] Registrado: {parsed}")

            # -------- FILTRO DE MOEDAS --------
            if parsed["symbol"] not in ALLOWED_SYMBOLS:
                print(f"[SKIP] Moeda ignorada: {parsed['symbol']}")
                return  # não envia para o Telegram

        else:
            # mensagem não é sinal → ignora encaminhamento
            return

        # -------- FORWARD --------
        if event.message.media:
            await client.send_file(
                TARGET_CHAT_ID,
                event.message.media,
                caption=text
            )
        else:
            await client.send_message(
                TARGET_CHAT_ID,
                text
            )

        print(f"[FORWARD] Enviado: {parsed['symbol']}")

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# -------------------------------------------------
# Função para enviar o log para o Telegram
# -------------------------------------------------
async def send_daily_log():
    now = datetime.now(TZ_BRASILIA)

    log_date = now.date() - timedelta(days=1)

    file_name = f"log_{log_date.isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    if not os.path.exists(log_path):
        print(f"[LOG] Nenhum arquivo para enviar ({file_name})")
        return

    caption = (
        f"📊 Log diário\n"
        f"Data: {log_date.strftime('%d/%m/%Y')}\n"
        f"Horário envio: {now.strftime('%H:%M')}"
    )

    await client.send_file(
        TARGET_CHAT_ID,
        log_path,
        caption=caption
    )

    print("[LOG] Arquivo enviado ao Telegram")


# -------------------------------------------------
# Scheduler assíncrono (00h)
# -------------------------------------------------
async def scheduler():
    global last_sent_date

    while True:
        now = datetime.now(TZ_BRASILIA)
# and last_sent_date != now.date():
        if now.hour == 00 and now.minute == 0:
            print(f"[SCHEDULER] Envio enviado {now}")
            await send_daily_log()
            last_sent_date = now.date()
            await asyncio.sleep(70)  # evita envio duplicado no mesmo minuto

        await asyncio.sleep(15)

# -------------------------------------------------
# Execução principal (versão final)
# -------------------------------------------------
async def main():
    print("Modo BOT: iniciado...")
    await client.start()
    asyncio.create_task(scheduler())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
