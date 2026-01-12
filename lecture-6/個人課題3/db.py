import sqlite3
from datetime import datetime

# 天気予報アプリ用のSQLiteデータベース管理
class WeatherDB:
    def __init__(self, db_name="weather_app.db"):
        self.db_name = db_name
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    
    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS areas (
                    area_id TEXT PRIMARY KEY,
                    area_name TEXT NOT NULL,
                    center_id TEXT NOT NULL,
                    center_name TEXT NOT NULL
                )
            """)# 地域マスターテーブル

            cur.execute("""
                CREATE TABLE IF NOT EXISTS weather_codes (
                    weather_code TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    icon TEXT NOT NULL,
                    color_code TEXT NOT NULL,
                    memo TEXT,
                    bg_color_code TEXT
                )
            """)# 天気コードマスターテーブル

            cur.execute("""
                CREATE TABLE IF NOT EXISTS forecasts (
                    forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    office_code TEXT NOT NULL,
                    area_id TEXT NOT NULL,
                    FOREIGN KEY (area_id) REFERENCES areas(area_id)
                )
            """)# 天気予報テーブル

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_forecasts (
                    daily_forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    temp_min REAL,
                    temp_max REAL,
                    forecast_id INTEGER NOT NULL,
                    weather_code TEXT NOT NULL,
                    FOREIGN KEY (forecast_id) REFERENCES forecasts(forecast_id),
                    FOREIGN KEY (weather_code) REFERENCES weather_codes(weather_code)
                )
            """)# 日別天気予報テーブル
            # インデックス作成
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_forecasts_area_id
                ON forecasts(area_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_forecasts_forecast_id
                ON daily_forecasts(forecast_id)
            """)
            conn.commit()

    # 天気コードマスターデータ登録
    def seed_weather_master(self, code_to_text, weather_colors):
        with self._get_conn() as conn: 
            cur = conn.cursor()
            for code, desc in code_to_text.items(): # 天気コードと説明文を登録
                color = "#808080"
                for kw, c in weather_colors.items(): # 説明文に基づき色を決定
                    if kw in desc: # 部分一致で判定
                        color = c
                        break
                # 登録・更新処理
                cur.execute("""
                    INSERT OR REPLACE INTO weather_codes
                    (weather_code, description, icon, color_code, memo, bg_color_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, desc, "help_outline", color, "", "#FFFFFF"))
            conn.commit()

    # 天気予報データ保存
    def save_weather_report(self, area_info, daily_data_list):
        with self._get_conn() as conn: 
            cur = conn.cursor()

            # 地域情報登録・更新
            cur.execute("""
                INSERT OR REPLACE INTO areas (area_id, area_name, center_id, center_name)
                VALUES (?, ?, ?, ?)
            """, (area_info['id'], area_info['name'],
                  area_info['c_id'], area_info['c_name']))

            # 天気予報登録
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 予報ヘッダ登録
            cur.execute("""
                INSERT INTO forecasts (datetime, office_code, area_id)
                VALUES (?, ?, ?)
            """, (now, area_info['id'], area_info['id']))
            f_id = cur.lastrowid

            # 日別天気予報登録
            cur.executemany("""
                INSERT INTO daily_forecasts
                (date, temp_min, temp_max, forecast_id, weather_code)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (d['date'], d['min_t'], d['max_t'], f_id, d['w_code'])
                for d in daily_data_list
            ])
            conn.commit()

    # 最新の天気予報取得
    def get_latest_forecast(self, area_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT df.*, wc.description, wc.color_code
                FROM daily_forecasts df
                JOIN weather_codes wc
                  ON df.weather_code = wc.weather_code
                WHERE df.forecast_id = (
                    SELECT MAX(forecast_id)
                    FROM forecasts
                    WHERE area_id = ?
                )
                ORDER BY df.date ASC
            """, (area_id,))
            return cur.fetchall()