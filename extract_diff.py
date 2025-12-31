import os
import glob
import re

# --- 設定 ---
SOURCE_DIR = 'original-fixja'
OUTPUT_DIR = '.'  # カレントディレクトリに出力

def extract_tag_content(tag, block):
    """指定されたタグの中身を抽出する（見つからない場合はNone）"""
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, block, re.DOTALL)
    return match.group(1) if match else None

def process_files():
    # ソースディレクトリの確認
    if not os.path.exists(SOURCE_DIR):
        print(f"エラー: ソースディレクトリ '{SOURCE_DIR}' が見つかりません。")
        return

    # XMLファイルを取得
    files = glob.glob(os.path.join(SOURCE_DIR, '*.xml'))
    print(f"{len(files)} 個のファイルをチェックして、修正適用版を作成します...")

    # Entryブロック抽出用正規表現
    entry_pattern = re.compile(r"(<Entry>.*?</Entry>)", re.DOTALL)
    
    diff_files_count = 0
    total_diff_entries = 0

    for file_path in files:
        filename = os.path.basename(file_path)
        output_path = os.path.join(OUTPUT_DIR, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            entries = entry_pattern.findall(content)
            
            # 処理済み（修正適用済み）のEntryを格納するリスト
            processed_entries = []

            for block in entries:
                ja = extract_tag_content('ja', block)
                fixja = extract_tag_content('fixja', block)

                # jaとfixjaが両方存在し、かつ内容が異なる場合のみ対象
                if ja is not None and fixja is not None:
                    if ja.strip() != fixja.strip():
                        # --- 変換処理 ---
                        
                        # 1. <ja>の中身を<fixja>の中身に置き換える
                        # lambdaを使って、fixjaの中身をそのまま置換文字列として使う
                        new_block = re.sub(
                            r"<ja>.*?</ja>", 
                            lambda m: f"<ja>{fixja}</ja>", 
                            block, 
                            flags=re.DOTALL
                        )
                        
                        # 2. <fixja>タグを除去する（直前の改行とインデントも含む）
                        # これで空行ができるのを防ぐ
                        new_block = re.sub(r"\n?[ \t]*<fixja>.*?</fixja>", "", new_block, flags=re.DOTALL)
                        
                        # 3. インデントの修正
                        # 正規表現で抽出したブロックは先頭のインデントが含まれていないため、
                        # リストに追加する際にタブ(\t)を付与する。
                        processed_entries.append("\t" + new_block)

            # 差異があった場合のみファイル生成
            if processed_entries:
                # 元のファイルのヘッダーとフッターを再利用
                first_entry_match = entry_pattern.search(content)
                
                if first_entry_match:
                    header = content[:first_entry_match.start()]
                    
                    last_entry_end = 0
                    for m in entry_pattern.finditer(content):
                        last_entry_end = m.end()
                    footer = content[last_entry_end:]

                    # ヘッダー・フッターの余分な空白・改行を整理
                    clean_header = header.rstrip()
                    # footerは通常 </Root> で終わるが、その前の改行を確保したい
                    clean_footer = footer.lstrip('\n')

                    # 結合
                    # ヘッダー + 改行 + (タブ付きEntryブロック + 改行 + タブ付きEntryブロック...) + 改行 + フッター
                    body = "\n".join(processed_entries)
                    final_content = f"{clean_header}\n{body}\n{clean_footer}"

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    
                    print(f"生成: {filename} ({len(processed_entries)} 件の修正)")
                    diff_files_count += 1
                    total_diff_entries += len(processed_entries)

        except Exception as e:
            print(f"エラー {filename}: {e}")

    print("-" * 30)
    if diff_files_count == 0:
        print("差異のあるファイルは見つかりませんでした。")
    else:
        print(f"完了: 計 {diff_files_count} ファイルを作成しました。")

if __name__ == '__main__':
    process_files()