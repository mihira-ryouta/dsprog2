import flet as ft
import requests
from datetime import datetime, timezone, timedelta
from weather_code import CODE_TO_TEXT, WEATHER_COLORS


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

        # 天気予報データ取得
        office_code = e.control.data
        weather_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{office_code}.json"
        
        # データ取得と表示更新
        try:
            response_data = requests.get(weather_url).json() #スライドで指定されたやつにした
            
            if len(response_data) <= 1:
                # 週間予報がない場合はエラーを表示
                raise Exception("週間予報データがありません")

            daily_data = response_data[0]   # 発表日時など
            weekly_data = response_data[1]  # ループのメインに使用

            # 今日の天気で背景色を更新
            first_day_code = weekly_data['timeSeries'][0]['areas'][0]['weatherCodes'][0]
            update_background_theme(CODE_TO_TEXT.get(first_day_code, "晴れ"))

            cards_grid.controls.clear()
            page.open(ft.SnackBar(ft.Text(f"{daily_data['publishingOffice']} 発表")))

            # データ展開
            weather_area = weekly_data['timeSeries'][0]['areas'][0] 
            temp_area = weekly_data['timeSeries'][1]['areas'][0]
            time_defines = weekly_data['timeSeries'][0]['timeDefines']
            
            # 各日のデータをカードとして表示
            for i in range(len(time_defines)):
                date_label = datetime.fromisoformat(time_defines[i].replace('Z', '+00:00')).astimezone(JST).strftime('%Y-%m-%d') # 日付フォーマット
                weather_text = CODE_TO_TEXT.get(weather_area['weatherCodes'][i], "晴れ") # 天気コードをテキストに変換
                
                min_t = temp_area['tempsMin'][i] if i < len(temp_area['tempsMin']) and temp_area['tempsMin'][i] != "" else "--" # 最低気温
                max_t = temp_area['tempsMax'][i] if i < len(temp_area['tempsMax']) and temp_area['tempsMax'][i] != "" else "--" # 最高気温

                # カードを作成してグリッドに追加
                cards_grid.controls.append(
                    ft.Container(
                        padding=20, bgcolor=ft.Colors.WHITE, border_radius=15, 
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLUE_GREY_100),
                        content=ft.Column([
                            ft.Text(date_label, weight="bold"),
                            ft.Container(content=create_weather_display_from_text(weather_text), height=80, alignment=ft.alignment.center),
                            ft.Text(format_short_weather_text(weather_text), size=13, weight="bold", text_align=ft.TextAlign.CENTER),
                            ft.Row([
                                ft.Text(f"{min_t}℃", color=ft.Colors.BLUE, weight="bold"),
                                ft.Text("/", color=ft.Colors.GREY),
                                ft.Text(f"{max_t}℃", color=ft.Colors.RED, weight="bold"),
                            ], alignment=ft.MainAxisAlignment.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
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