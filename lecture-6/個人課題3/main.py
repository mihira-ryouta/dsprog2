import flet as ft
import requests
from datetime import datetime, timezone, timedelta
from weather_code import CODE_TO_TEXT, WEATHER_COLORS
from db import WeatherDB

# ヘルパー関数で、天気文を短く整形するし、わかりやすくする
def format_short_weather_text(text):
    remove_words = ["所により", "を伴う", "山沿いでは", "平地では", "付近", "から", "にかけて"]
    cleaned_text = text
    for word in remove_words: 
        #不要な語句を削除
        cleaned_text = cleaned_text.replace(word, "") 
    # 全角スペースを半角に変換し、連続スペースを単一スペースに
    cleaned_text = cleaned_text.replace("　", " ")
    cleaned_text = " ".join(cleaned_text.split())
    return cleaned_text

# 天気テキストからアイコンと色を決定し、表示用のコントロールを作成するヘルパー関数
def create_weather_display_from_text(weather_text):
    weather_keywords = {
        "雪": (ft.Icons.SNOWING, ft.Colors.CYAN),
        "雷": (ft.Icons.THUNDERSTORM, ft.Colors.YELLOW_900),
        "雨": (ft.Icons.WATER_DROP, ft.Colors.BLUE),
        "晴": (ft.Icons.SUNNY, ft.Colors.ORANGE),
        "曇": (ft.Icons.CLOUD, ft.Colors.GREY),
        "くもり": (ft.Icons.CLOUD, ft.Colors.GREY)
    }
    found_items = []
    # テキスト内のキーワードを検索
    for word, (icon, color) in weather_keywords.items():
        # キーワードがテキストに含まれているかチェック
        index = weather_text.find(word)
        if index != -1:
            found_items.append({"index": index, "icon": icon, "color": color})
    # キーワードの出現順にソート
    found_items.sort(key=lambda x: x["index"])

    # 複数キーワードが見つかった場合の処理
    if len(found_items) >= 2:
        first, second = found_items[0], found_items[1]
        # 「のち」があれば矢印、それ以外（時々など）は区切り線
        separator = ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.GREY_400, size=24) if "のち" in weather_text else ft.Text("|", size=30, color=ft.Colors.GREY_300)
        # 2つのアイコンを横並びで表示
        return ft.Row([ft.Icon(first["icon"], color=first["color"], size=40), separator, ft.Icon(second["icon"], color=second["color"], size=40)], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
    elif len(found_items) == 1:
        item = found_items[0]
        # 単一アイコンを表示
        return ft.Icon(item["icon"], color=item["color"], size=70)
    else:
        return ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.GREY_300, size=50)


# メイン
def main(page: ft.Page):
    # ページの基本設定
    page.title = "天気予報アプリ (週間予報)"
    page.theme_mode = ft.ThemeMode.LIGHT # ダークモードは未対応
    page.scroll = None # スクロール無効

    db = WeatherDB()

    # アプリ起動時に天気の定義（晴れ、曇りなど）をDBに登録する
    db.seed_weather_master(CODE_TO_TEXT, WEATHER_COLORS)

    def update_background_theme(weather_text):
            target_color = ft.Colors.BLUE_GREY_50
            for keyword, color in WEATHER_COLORS.items():
                if keyword in weather_text:
                    target_color = color
                    break
            page.bgcolor = target_color
            page.update()

    JST = timezone(timedelta(hours=9))

    # 地域リストの準備
    # APIで地域リストを取得し、地域名とコードの辞書を作成
    region_data = {}
    try:
        area_url = "http://www.jma.go.jp/bosai/common/const/area.json"
        area_json = requests.get(area_url).json()
        center_data = area_json.get('centers', {}) 
        office_data = area_json.get('offices', {}) 
        
        # 地域ごとのリスト作成
        for center_code, center_info in center_data.items():
            center_name = center_info['name']
            office_codes = center_info.get('children', [])
            office_list = []
            for office_code in office_codes:
                office_info = office_data.get(office_code, {})
                office_list.append({"name": office_info.get('name', '不明'), "code": office_code})
            region_data[center_name] = office_list
    except Exception as e:
        page.add(ft.Text(f"地域リスト取得エラー: {e}"))
        return
    
    # 天気表示エリア　
    cards_grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=220,
        child_aspect_ratio=0.75,
        spacing=15,
        run_spacing=15,
        padding=20,
    ) 

    # 取得・表示処理
    def get_and_show_weather(e):
        cards_grid.controls.clear()
        cards_grid.controls.append(ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center, expand=True))
        page.update()

        # 1. 選択された地域コードを取得
        office_code = e.control.data
        
        #「十勝・奄美」の例外を判定
        mapping = {
            "014030": "014100",  # 十勝 -> 釧路・根室・十勝セットのファイルを指定
            "460040": "460100",  # 奄美 -> 鹿児島県セットのファイルを指定
        }
        fetch_code = mapping.get(office_code, office_code)
        
        # 実際に読みに行くURLを修正
        weather_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{fetch_code}.json"
        
        try:
            response_data = requests.get(weather_url).json()
            if len(response_data) <= 1:
                raise Exception("週間予報データがありません")

            # 週間予報データ(index 1)を解析
            weekly_data = response_data[1]
            time_series = weekly_data['timeSeries']
            
            # 複数の地域が入っている中から、選んだ地域の「インデックス」を探す
            area_index = 0
            for i, area in enumerate(time_series[0]['areas']):
                if area['area']['code'] == office_code:
                    area_index = i
                    break
            
            # 探し出したarea_indexを使ってデータを取得。[0] ではなく [area_index] を使う
            dates = time_series[0]['timeDefines']
            weather_codes = time_series[0]['areas'][area_index]['weatherCodes']
            
            # 気温データ側（timeSeries[1]）でも同じarea_indexを使用
            temps_min = time_series[1]['areas'][area_index].get('tempsMin', [None] * len(dates))
            temps_max = time_series[1]['areas'][area_index].get('tempsMax', [None] * len(dates))

            # DB保存用の地域情報を作成
            area_info = {
                'id': office_code,
                'name': e.control.title.value,
                'c_id': "center_id_sample",
                'c_name': "center_name_sample"
            }

            # DB保存と表示の処理
            daily_list = []
            for i in range(len(dates)):
                daily_list.append({
                    'date': dates[i][:10], 
                    'w_code': weather_codes[i],
                    'min_t': temps_min[i],
                    'max_t': temps_max[i]
                })
            
            db.save_weather_report(area_info, daily_list)
            db_rows = db.get_latest_forecast(office_code)

            cards_grid.controls.clear()
            for row in db_rows:
                weather_desc = row['description']
                min_t = f"{row['temp_min']}℃" if row['temp_min'] is not None else "--"
                max_t = f"{row['temp_max']}℃" if row['temp_max'] is not None else "--"

                cards_grid.controls.append(
                    ft.Container(
                        padding=20, bgcolor=ft.Colors.WHITE, border_radius=15, 
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLUE_GREY_100),
                        content=ft.Column([
                            ft.Text(row['date'], weight="bold"),
                            ft.Container(content=create_weather_display_from_text(weather_desc), height=80, alignment=ft.alignment.center),
                            ft.Text(format_short_weather_text(weather_desc), size=13, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Row([
                                ft.Text(min_t, color=ft.Colors.BLUE, weight="bold"),
                                ft.Text("/", color=ft.Colors.GREY),
                                ft.Text(max_t, color=ft.Colors.RED, weight="bold"),
                            ], alignment=ft.MainAxisAlignment.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
            if db_rows:
                update_background_theme(db_rows[0]['description'])

        except Exception as err:
            cards_grid.controls.clear()
            cards_grid.controls.append(ft.Text(f"エラー: {err}", color=ft.Colors.RED))
        page.update()
            

    # サイドバーとレイアウト
    sidebar_controls = []
    sidebar_controls.append(ft.Container(padding=15, bgcolor=ft.Colors.BLUE_GREY_700, content=ft.Text("地域を選択", weight="bold", color=ft.Colors.WHITE, size=16)))
    
     # 地域ごとに展開タイルを作成
    for center_name, office_list in region_data.items():
        office_tiles = []
        for office in office_list:
            office_tiles.append(
                ft.ListTile(title=ft.Text(office["name"], color=ft.Colors.WHITE70), data=office["code"], on_click=get_and_show_weather, bgcolor=ft.Colors.BLUE_GREY_800)
            )
        # 展開タイルをサイドバーに追加
        sidebar_controls.append(
            ft.ExpansionTile(title=ft.Text(center_name, size=14, color=ft.Colors.WHITE), controls=office_tiles, collapsed_text_color=ft.Colors.WHITE, icon_color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_GREY_900, dense=True)
        )
    # レイアウト構築
    sidebar = ft.Container(width=250, bgcolor=ft.Colors.BLUE_GREY_900, content=ft.ListView(controls=sidebar_controls, padding=0, spacing=0)) 
    weather_display_container = ft.Container(content=cards_grid, expand=True) 
    layout = ft.Row(controls=[sidebar, weather_display_container], expand=True, spacing=0)
    page.add(layout)

if __name__ == "__main__":
    ft.app(target=main)