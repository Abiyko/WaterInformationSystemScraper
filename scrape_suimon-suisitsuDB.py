from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import WebDriverException
import time
import os
import sys


# 観測所と期間の指定（ここを変更）
observatoy_id = "1368041150050" # 観測所記号
year_start = "2002" # YYYY
month_start = "01" # MM
day_start = "01" # DD
year_end = "2022" # YYYY
month_end = "12" # MM
day_end = "31" # DD

url = f"https://www1.river.go.jp/cgi-bin/SrchDamData.exe?ID={observatoy_id}&KIND=1&PAGE=0" # 任意期間雨量
# url = f"https://www1.river.go.jp/cgi-bin/SrchRainData.exe?ID={observatoy_id}&KIND=1&PAGE=0" # 任意ダム諸量



def validate_date_range():
    # 期間の指定が不適切かチェック
    start_date_str = year_start + month_start + day_start
    end_date_str = year_end + month_end + day_end
    start_date = datetime.strptime(start_date_str, "%Y%m%d")
    end_date = datetime.strptime(end_date_str, "%Y%m%d")
    if start_date > end_date:
        print("期間の指定が不適切です。開始日が終了日より後になっています。")
        sys.exit()
    return start_date, end_date


def setup_webdriver():
    # ChromeDriverの初期設定
    options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    # Chromeを開く
    driver.execute_script("window.open('https://www.google.com', 'new_window')")
    driver.switch_to.window(driver.window_handles[1])
    return driver


def input_period(driver, start_of_month, end_of_month):
    # 期間を入力
    print(f"処理期間: {start_of_month.strftime('%Y%m%d')} から {end_of_month.strftime('%Y%m%d')}")
    year_first = start_of_month.strftime("%Y")
    month_first = start_of_month.strftime("%m")
    day_first = start_of_month.strftime("%d")
    year_last = end_of_month.strftime("%Y")
    month_last = end_of_month.strftime("%m")
    day_last = end_of_month.strftime("%d")
    input_elements = driver.find_elements(By.TAG_NAME, "input")
    new_values = [str(year_first), str(month_first), str(day_first), str(year_last), str(month_last), str(day_last)]
    for i, element in enumerate(input_elements[:6]):
        try:
            driver.execute_script("arguments[0].setAttribute('value', arguments[1])", element, new_values[i])
        except IndexError:
            print(f"要素 {i+1} の変更中にエラーが発生しました。")
            sys.exit()


def split_period_into_months(start_date, end_date):
    # 処理する期間の分割
    date_ranges = []
    current_start = start_date
    while current_start <= end_date:
        next_month_start = current_start + relativedelta(months=1) # 現在の月の終わりを計算
        current_end = min(next_month_start - relativedelta(days=1), end_date) # 期間の終了日を、現在の月の末日または全体の終了日のどちらか早い方にする
        date_ranges.append((current_start, current_end)) # 日付のタプルをリストに追加
        current_start = next_month_start # 次の処理期間の開始日を更新
    return date_ranges


def open_website(driver):
    # 水質水門データベースの任意期間時間雨量検索を開く
    try:
        driver.get(url)
    except WebDriverException as e:
        print(f"ウェブサイトを開けませんでした。URL: {url}")
        driver.quit()
        sys.exit()
    
    # 最新の（最後に開かれた）ウィンドウハンドルに切り替える
    all_handles = driver.window_handles
    new_tab_handle = all_handles[-1]
    driver.switch_to.window(new_tab_handle)
    return driver


def reset_page(driver):
    # 任意期間時間雨量検索に戻る
    all_handles = driver.window_handles
    first_two_handles = all_handles[:2]
    for handle in all_handles[2:]:
        driver.switch_to.window(handle)
        driver.close()
    driver.switch_to.window(first_two_handles[1])


def write_data(place, pre_text):
    # グローバル変数に依存しないように引数を利用
    filename = f"{place}{year_start}{month_start}{day_start}-{year_end}{month_end}{day_end}.txt"

    if not os.path.exists(filename): # ディレクトリが存在しない場合は作成
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(pre_text)
            f.write('\n')
            print(f"'{filename}' を作成しました。")
    else: # ファイルに追記モードで書き込み
        with open(filename, 'a', encoding='utf-8') as f: # pre_textを改行で分割して行のリストにする
            lines = pre_text.splitlines() # 先頭9行を削除する（インデックス9から最後までを取得）
            cleaned_lines = lines[9:] # 再び一つの文字列に戻す
            pre_text = '\n'.join(cleaned_lines)
            f.write(pre_text)
            f.write('\n')


def get_observation_data(driver):
    # 観測データを取得
    pre_elements = driver.find_elements(By.TAG_NAME, "pre")
    pre_text = pre_elements[0].text
    lines = pre_text.split('\n')
    if len(lines) > 3:
        fourth_line = lines[3]
        columns = fourth_line.split(',')
        if len(columns) > 1:
            place = columns[1]
            write_data(place, pre_text)
        else:
            print("観測所名がありません。")
            sys.exit()
    else:
        print("ヘッダーがありません。")
        sys.exit()


def process_data(driver, date_ranges):
    # ここから各期間をループで処理
    for start_of_month, end_of_month in date_ranges:
        input_period(driver, start_of_month, end_of_month)

        # ボタンを押して最新のウィンドウハンドルに切り替える
        input_elements = driver.find_elements(By.TAG_NAME, "input")
        last_input = input_elements[7]
        last_input.click()
        all_handles = driver.window_handles
        new_tab_handle = all_handles[-1]
        driver.switch_to.window(new_tab_handle)

        #データの読み込み待ち
        time.sleep(1)

        # ボタンを押して最新のウィンドウハンドルに切り替える
        a_elements = driver.find_elements(By.TAG_NAME, "a")
        first_a_element = a_elements[0]
        first_a_element.click()
        all_handles = driver.window_handles
        new_tab_handle = all_handles[-1]
        driver.switch_to.window(new_tab_handle)

        get_observation_data(driver)
        reset_page(driver)


def main():
    start_date, end_date = validate_date_range()

    date_ranges = split_period_into_months(start_date, end_date)
    driver = setup_webdriver()
    driver = open_website(driver)

    process_data(driver, date_ranges)

    driver.quit()


if __name__ == "__main__":
    main()