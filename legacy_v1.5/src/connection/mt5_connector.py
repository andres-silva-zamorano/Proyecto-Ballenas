import MetaTrader5 as mt5
import polars as pl
from datetime import datetime, timedelta
import sys

class MT5Connector:
    def __init__(self, login=None, password=None, server=None):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False

    def conectar(self):
        if not mt5.initialize():
            print(f"Error al inicializar MT5: {mt5.last_error()}", file=sys.stderr)
            self.connected = False
            return False
        
        self.connected = True
        return True

    def desconectar(self):
        mt5.shutdown()
        self.connected = False

    def obtener_ticks_recientes(self, symbol: str, num_ticks: int = 1000) -> pl.DataFrame:
        if not self.connected:
            if not self.conectar():
                return pl.DataFrame()

        # 1. Obtener la hora del servidor (último tick conocido)
        last_tick = mt5.symbol_info_tick(symbol)
        if last_tick is None:
            # Si no hay datos, retornamos vacío
            return pl.DataFrame()
            
        server_time = datetime.fromtimestamp(last_tick.time)
        
        # 2. Definir rango de búsqueda: Desde hace 30 minutos hasta AHORA MISMO (server time)
        # Esto garantiza que traemos los tics más frescos.
        date_to = server_time + timedelta(seconds=10) # Un poco en el futuro por si acaso
        date_from = server_time - timedelta(minutes=30) 
        
        # Usamos copy_ticks_range que es más seguro para "atrás hacia adelante"
        ticks = mt5.copy_ticks_range(symbol, date_from, date_to, mt5.COPY_TICKS_ALL)

        if ticks is None or len(ticks) == 0:
            return pl.DataFrame()

        # 3. Convertir a Polars y tomar solo los últimos N pedidos
        df = pl.from_numpy(ticks)
        
        # Ordenar y cortar
        df = df.tail(num_ticks)

        # Selección de columnas
        df_clean = df.select([
            pl.col("time").alias("timestamp_sec"),
            pl.col("time_msc").alias("timestamp_ms"),
            pl.col("bid"),
            pl.col("ask")
        ])

        return df_clean

    def obtener_velas_recientes(self, symbol: str, timeframe=mt5.TIMEFRAME_M1, num_velas: int = 500) -> pl.DataFrame:
        if not self.connected:
            if not self.conectar():
                return pl.DataFrame()

        # copy_rates_from_pos trae las últimas N velas desde la posición 0 (actual) hacia atrás
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_velas)
        
        if rates is None:
            return pl.DataFrame()

        df = pl.from_numpy(rates)
        
        df = df.select([
            pl.col("time").alias("timestamp"),
            pl.col("open"),
            pl.col("high"),
            pl.col("low"),
            pl.col("close"),
            pl.col("tick_volume"),
        ])
        
        return df