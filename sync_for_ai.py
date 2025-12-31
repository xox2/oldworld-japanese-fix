import os
import glob
import re

# --- 設定 ---
SOURCE_DIR = 'original'
TARGET_DIR = 'original-for-AI'

def extract_tag_content(tag, block):
    """指定されたタグの中身を抽出する（見つからない場合はNone）"""
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, block, re.DOTALL)
    return match.group(1) if match else None

def process_files():
    # 1. ディレクトリの準備
    if not os.path.exists(SOURCE_DIR):
        print(f"エラー: ソースディレクトリ '{SOURCE_DIR}' が見つかりません。")
        return

    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"ディレクトリ作成: '{TARGET_DIR}'")

    # --- 2. ファイル削除フェーズ (TARGET_DIR内の text-*.xml のみ) ---
    print(f"--- 不要ファイルの削除チェック ({TARGET_DIR}) ---")
    
    target_files_paths = glob.glob(os.path.join(TARGET_DIR, 'text-*.xml'))
    target_files_map = {os.path.basename(p): p for p in target_files_paths}
    
    source_files_paths = glob.glob(os.path.join(SOURCE_DIR, 'text-*.xml'))
    source_files_names = set(os.path.basename(p) for p in source_files_paths)
    
    deleted_files_count = 0
    for filename, filepath in target_files_map.items():
        if filename not in source_files_names:
            try:
                os.remove(filepath)
                print(f"削除: {filename}")
                deleted_files_count += 1
            except Exception as e:
                print(f"削除エラー {filename}: {e}")
    
    if deleted_files_count == 0:
        print("削除対象なし")

    # --- 3. ファイル生成・同期フェーズ ---
    all_source_files = glob.glob(os.path.join(SOURCE_DIR, '*.xml'))
    print(f"\n--- {len(all_source_files)} 個のファイルの抽出処理を開始 ---")

    # Regex: Entryブロックの抽出
    entry_pattern = re.compile(r"(<Entry>.*?</Entry>)", re.DOTALL)

    for src_path in all_source_files:
        filename = os.path.basename(src_path)
        dest_path = os.path.join(TARGET_DIR, filename)
        
        try:
            # Source (Original) の読み込み
            with open(src_path, 'r', encoding='utf-8') as f:
                src_content = f.read()

            src_entries = entry_pattern.findall(src_content)
            
            # ヘッダーとフッターの抽出
            first_entry_match = entry_pattern.search(src_content)
            if not first_entry_match:
                # Entryがないファイルはそのままコピー
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(src_content)
                print(f"コピー（Entryなし）: {filename}")
                continue

            header = src_content[:first_entry_match.start()]
            
            last_entry_end = 0
            for m in entry_pattern.finditer(src_content):
                last_entry_end = m.end()
            footer = src_content[last_entry_end:]

            # 新しいブロックリストの構築
            new_blocks = []
            
            for block in src_entries:
                ztype = extract_tag_content('zType', block)
                if not ztype:
                    continue 

                en_us = extract_tag_content('en-US', block)
                ja = extract_tag_content('ja', block)
                
                # ブロックの再構築
                # AI用なので、zType, en-US, ja 以外は含めない
                new_block_lines = [
                    "\t<Entry>",
                    f"\t\t<zType>{ztype}</zType>"
                ]
                
                if en_us is not None:
                    new_block_lines.append(f"\t\t<en-US>{en_us}</en-US>")
                
                if ja is not None:
                    new_block_lines.append(f"\t\t<ja>{ja}</ja>")
                
                new_block_lines.append("\t</Entry>")
                
                new_blocks.append("\n".join(new_block_lines))

            # ファイル結合
            clean_header = header.rstrip()
            clean_footer = footer.lstrip('\n') 

            if not new_blocks:
                final_content = clean_header + "\n" + clean_footer
            else:
                body = "\n".join(new_blocks)
                final_content = f"{clean_header}\n{body}\n{clean_footer}"

            # 書き出し
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            print(f"生成: {filename}")

        except Exception as e:
            print(f"エラー発生 {filename}: {e}")

    print("-" * 30)
    print(f"全処理終了: {TARGET_DIR} に出力しました")

if __name__ == '__main__':
    process_files()