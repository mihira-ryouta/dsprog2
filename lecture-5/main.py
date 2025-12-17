import flet as ft
import requests
from datetime import datetime, timezone, timedelta


# ヘルパー: 天気コードを日本語テキストに変換する辞書
# これによって、週間予報の数字データ(101など)をテキスト解析ロジック("晴時々曇")に渡せる
# 参考に https://www.t3a.jp/blog/web-develop/weather-code-list/　を使用
CODE_TO_TEXT = {
    "100": "晴れ",
    "101": "晴時々曇",
    "102": "晴一時雨",
    "103": "晴時々雨",
    "104": "晴時々雪",
    "105": "晴時々雪",
    "106": "晴一時雨",
    "107": "晴一時雨",
    "108": "晴一時雨",
    "110": "晴のち曇",
    "111": "晴のち曇",
    "112": "晴のち雨",
    "113": "晴のち雨",
    "114": "晴のち雨",
    "115": "晴のち雪",
    "116": "晴のち雪",
    "117": "晴のち雪",
    "118": "晴のち雨",
    "119": "晴のち雨",
    "120": "晴一時雨",
    "121": "晴一時雨",
    "122": "晴一時雨",
    "123": "晴一時雨",
    "124": "晴一時雪", 
    "132": "晴のち曇",
    "140": "晴時々雨",
    "160": "晴一時雪",
    "170": "晴時々雪",
    "181": "晴のち雪",
    
    "200": "くもり",
    "201": "くもり時々晴",
    "202": "くもり一時雨",
    "203": "くもり時々雨",
    "204": "くもり時々雪",
    "205": "くもり時々雪",
    "206": "くもり一時雨",
    "207": "くもり一時雨",
    "208": "くもり一時雨",
    "209": "くもり一時雪",
    "210": "くもりのち晴",
    "211": "くもりのち晴",
    "212": "くもりのち雨",
    "213": "くもりのち雨",
    "214": "くもりのち雨",
    "215": "くもりのち雪",
    "216": "くもりのち雪",
    "217": "くもりのち雪",
    "218": "くもりのち雨",
    "219": "くもりのち雨",
    "220": "くもり一時雨",
    "221": "くもり一時雨",
    "222": "くもり一時雨",
    "223": "くもり一時雨",
    "224": "くもり一時雪",
    "225": "くもり一時雪",
    "226": "くもり一時雪",
    "228": "くもり一時雪",
    "229": "くもり一時雪",
    "231": "くもり一時晴",
    "240": "くもり時々雨",
    "250": "くもり時々雪",
    "260": "くもり一時雪",
    "270": "くもり時々雪",
    "281": "くもりのち雪",
    
    "300": "雨",
    "301": "雨時々晴",
    "302": "雨時々止む",
    "303": "雨時々雪",
    "304": "雨",
    "306": "大雨",
    "308": "雨",
    "309": "雨一時雪",
    "311": "雨のち晴",
    "313": "雨のちくもり",
    "314": "雨のち雪",
    "315": "雨のち雪",
    "316": "雨のち晴",
    "317": "雨のちくもり",
    "320": "雨一時晴",
    "321": "雨一時晴",
    "322": "雨時々雪",
    "323": "雨一時雪",
    "324": "雨一時雪",
    "325": "雨一時雪",
    "326": "雨一時雪",
    "327": "雨一時雪",
    "328": "雨一時雪",
    "329": "雨一時雪",
    "340": "雪",
    "350": "雨",
    "361": "雪",
    "371": "雪",
    
    "400": "雪",
    "401": "雪時々晴",
    "402": "雪時々止む",
    "403": "雪時々雨",
    "405": "大雪",
    "406": "風雪",
    "407": "暴風雪",
    "409": "雪一時雨",
    "411": "雪のち晴",
    "413": "雪のちくもり",
    "414": "雪のち雨",
    "420": "雪一時晴",
    "421": "雪一時晴",
    "422": "雪一時雨",
    "423": "雪一時雨",
    "425": "雪一時雨",
    "426": "雪一時雨",
    "427": "雪一時雨",
    "450": "雪",
}

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

# ヘルパー関数: アイコン、色、テキスト解析から天気表示を作成
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
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.BLUE_GREY_50
    page.scroll = None

    JST = timezone(timedelta(hours=9))

    # 地域リストの準備
    # APIで地域リストを取得し、地域名とコードの辞書を作成
    URL = "http://www.jma.go.jp/bosai/common/const/area.json"
    # データ取得
    try:
        date_json = requests.get(URL).json() #スライドで指定された形になっているはず、、、
    except:
        page.add(ft.Text("データ取得エラー"))
        return

    # 地域データの解析
    center_data = date_json.get('centers', {})
    office_data = date_json.get('offices', {})
    region_data = {}
    
    # 1. 地域ごとのリスト作成
    for center_code, center_info in center_data.items():
        center_name = center_info['name']
        office_codes = center_info.get('children', [])
        office_list = []
        for office_code in office_codes:
            office_info = office_data.get(office_code, {})
            name = office_info.get('name', '不明')
            office_list.append({"name": name, "code": office_code})
        region_data[center_name] = office_list

    # UI
    cards_grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=220,
        child_aspect_ratio=0.75,
        spacing=15,
        run_spacing=15,
        padding=20,
    )
    # 天気表示エリア
    weather_display_container = ft.Container(content=cards_grid, expand=True, padding=10)

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
            response_data = requests.get(weather_url).json() #スライドで指定されたやつした
            
            
            if len(response_data) <= 1:
                # 週間予報がない場合はエラーを表示
                raise Exception("週間予報データがありません")

            daily_data = response_data[0]   # 発表日時など
            weekly_data = response_data[1]  # ループのメインに使用

            # 基本情報取得
            publishing_office = daily_data['publishingOffice'] # 発表官署
            report_time_utc = datetime.fromisoformat(daily_data['reportDatetime'].replace('Z', '+00:00')) # 発表日時(UTC)
            report_time_jst = report_time_utc.astimezone(JST).strftime('%Y年%m月%d日 %H時%M分') # 発表日時(JST)

            cards_grid.controls.clear() # 進捗表示クリア
            page.open(ft.SnackBar(ft.Text(f"{publishing_office} 発表 (週間予報)"), duration=2000)) 

            # 週間予報のデータを取得
            # timeSeries[0] -> 天気コード (weatherCodes) ・　timeSeries[1] -> 気温 (tempsMin, tempsMax)ととして扱う
            
            weekly_weather_series = weekly_data['timeSeries'][0]
            weekly_temp_series = weekly_data['timeSeries'][1]

            # 日付リスト（天気予報側）
            time_defines = weekly_weather_series['timeDefines']
            
            # エリアごとのデータ（ループで該当地域のものを探す）
            weather_area = weekly_weather_series['areas'][0] 
            temp_area = weekly_temp_series['areas'][0]

            weather_codes = weather_area.get('weatherCodes', []) 
            temps_min = temp_area.get('tempsMin', [])
            temps_max = temp_area.get('tempsMax', [])

            # 7日分ループする
            loop_count = len(time_defines)

            for i in range(loop_count):
                # 日付処理
                time_str = time_defines[i]
                # UTC -> JST 変換
                start_time_utc = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                start_time_jst = start_time_utc.astimezone(JST)
                date_label = start_time_jst.strftime('%Y-%m-%d')
                
                # 天気コード取得
                code = weather_codes[i] if i < len(weather_codes) else "100"
                
                # ★ここでコードをテキストに変換（例: "101" -> "晴時々曇"）
                # マップにない場合は "晴れ" などを仮置きする
                weather_text = CODE_TO_TEXT.get(code, "晴れ")

                # 天気表示作成
                weather_icon_display = create_weather_display_from_text(weather_text)
                
                # 短縮テキスト作成（念のため）
                short_text = format_short_weather_text(weather_text)

                # 気温取得
                # 配列の長さチェック
                min_temp = temps_min[i] if i < len(temps_min) and temps_min[i] != "" else "--"
                max_temp = temps_max[i] if i < len(temps_max) and temps_max[i] != "" else "--"

                # カード作成
                card = ft.Container(
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=15,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLUE_GREY_100, offset=ft.Offset(2, 5)),
                    content=ft.Column(
                        [
                            ft.Text(date_label, weight="bold", color=ft.Colors.BLACK87),
                            ft.Container(height=10),
                            ft.Container(content=weather_icon_display, height=80, alignment=ft.alignment.center),
                            ft.Container(height=5),
                            
                            ft.Text(
                                short_text,
                                size=13,
                                weight="bold",
                                color=ft.Colors.BLACK87,
                                text_align=ft.TextAlign.CENTER,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            ft.Container(height=15),
                            
                            ft.Row(
                                [
                                    ft.Text(f"{min_temp}℃", color=ft.Colors.BLUE, weight="bold", size=16),
                                    ft.Text(" / ", color=ft.Colors.GREY),
                                    ft.Text(f"{max_temp}℃", color=ft.Colors.RED, weight="bold", size=16),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0
                    )
                )
                cards_grid.controls.append(card)

        except Exception as err:
            cards_grid.controls.clear()
            cards_grid.controls.append(ft.Text(f"エラー: {err}", color=ft.Colors.RED))
            print(err)
        
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
        sidebar_controls.append(
            ft.ExpansionTile(title=ft.Text(center_name, size=14, color=ft.Colors.WHITE), controls=office_tiles, collapsed_text_color=ft.Colors.WHITE, icon_color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_GREY_900, dense=True)
        )

    sidebar = ft.Container(width=250, bgcolor=ft.Colors.BLUE_GREY_900, content=ft.ListView(controls=sidebar_controls, padding=0, spacing=0))
    layout = ft.Row(controls=[sidebar, weather_display_container], expand=True, spacing=0)
    page.add(layout)

ft.app(target=main)