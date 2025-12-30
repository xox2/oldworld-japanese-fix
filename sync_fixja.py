import os
import glob
import re

# --- 設定 ---
SOURCE_DIR = 'original'
TARGET_DIR = 'original-fixja'

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

    # --- 3. ファイル内容の同期・再構築フェーズ ---
    all_source_files = glob.glob(os.path.join(SOURCE_DIR, '*.xml'))
    print(f"\n--- {len(all_source_files)} 個のファイルの同期とクリーニングを開始 ---")

    # Regex: Entryブロックの抽出
    entry_pattern = re.compile(r"(<Entry>.*?</Entry>)", re.DOTALL)

    for src_path in all_source_files:
        filename = os.path.basename(src_path)
        dest_path = os.path.join(TARGET_DIR, filename)
        
        try:
            # Source (Original) の読み込み
            with open(src_path, 'r', encoding='utf-8') as f:
                src_content = f.read()

            # Source内の全Entryを取得
            src_entries = entry_pattern.findall(src_content)
            
            # ヘッダーとフッターの抽出（Originalの構造を維持するため）
            # 最初のEntryの前までをヘッダー、最後のEntryの後ろをフッターとする
            first_entry_match = entry_pattern.search(src_content)
            if not first_entry_match:
                # Entryがないファイル（特殊なファイルやエラー）はそのままコピーして終了
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(src_content)
                print(f"コピー（Entryなし）: {filename}")
                continue

            header = src_content[:first_entry_match.start()]
            
            # 最後のEntryを探すための処理
            # findallだと位置が分からないので、finditerを使う
            last_entry_end = 0
            for m in entry_pattern.finditer(src_content):
                last_entry_end = m.end()
            footer = src_content[last_entry_end:]

            # Target (既存の作業ファイル) から fixja を回収するマップを作成
            target_fixja_map = {} # { zType: fixja_content }
            if os.path.exists(dest_path):
                with open(dest_path, 'r', encoding='utf-8') as f:
                    dest_content = f.read()
                dest_entries = entry_pattern.findall(dest_content)
                for block in dest_entries:
                    ztype = extract_tag_content('zType', block)
                    fixja = extract_tag_content('fixja', block)
                    if ztype and fixja:
                        target_fixja_map[ztype] = fixja

            # 新しいブロックリストの構築
            new_blocks = []
            
            for block in src_entries:
                ztype = extract_tag_content('zType', block)
                if not ztype:
                    continue # zTypeがない不正なブロックはスキップ

                en_us = extract_tag_content('en-US', block)
                ja = extract_tag_content('ja', block)
                
                # fixjaの決定（既存があればそれ、なければjaをコピー、jaもなければ空）
                fixja = target_fixja_map.get(ztype)
                if fixja is None:
                    fixja = ja if ja else ""

                # ブロックの再構築（指定されたタグのみを含める）
                # インデントは \t で統一
                new_block_lines = [
                    "\t<Entry>",
                    f"\t\t<zType>{ztype}</zType>"
                ]
                
                if en_us is not None:
                    new_block_lines.append(f"\t\t<en-US>{en_us}</en-US>")
                
                if ja is not None:
                    new_block_lines.append(f"\t\t<ja>{ja}</ja>")
                
                # fixjaは必ず追加
                new_block_lines.append(f"\t\t<fixja>{fixja}</fixja>")
                
                new_block_lines.append("\t</Entry>")
                
                new_blocks.append("\n".join(new_block_lines))

            # ファイル全体の結合
            # ヘッダー + (改行) + ブロック結合 + フッター
            # ブロック間は改行1つ (\n) で結合（空行を作らない）
            
            # ヘッダーの末尾が改行かどうかで調整
            clean_header = header.rstrip()
            clean_footer = footer.lstrip('\n') # footerの先頭の改行は調整する

            if not new_blocks:
                # Entryがすべて消えた場合（ありえないが）
                final_content = clean_header + "\n" + clean_footer
            else:
                body = "\n".join(new_blocks)
                final_content = f"{clean_header}\n{body}\n{clean_footer}"

            # 書き出し
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            print(f"処理完了: {filename} (Entry数: {len(new_blocks)})")

        except Exception as e:
            print(f"エラー発生 {filename}: {e}")

    print("-" * 30)
    print("全処理終了")

if __name__ == '__main__':
    process_files()