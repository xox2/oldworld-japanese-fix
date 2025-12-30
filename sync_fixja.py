import os
import glob
import re

# --- 設定 ---
SOURCE_DIR = 'original'
TARGET_DIR = 'original-fixja'

def get_ztype(block):
    """EntryブロックからzTypeの中身を抽出する"""
    match = re.search(r"<zType>(.*?)</zType>", block)
    return match.group(1) if match else None

def add_fixja_to_block(block, indent_str="\t"):
    """
    Entryブロックを受け取り、<fixja>がなければ<ja>からコピーして挿入する。
    """
    if "<fixja>" in block:
        return block

    ja_match = re.search(r"<ja>(.*?)</ja>", block, re.DOTALL)
    if not ja_match:
        return block

    ja_content = ja_match.group(1)
    
    indent_match = re.search(r"(^[ \t]*)<ja>", block, re.MULTILINE)
    current_indent = indent_match.group(1) if indent_match else indent_str

    tail_match = re.search(r"(\s*</Entry>)$", block)
    if tail_match:
        tail_part = tail_match.group(1)
        if tail_part.startswith('\n'):
            insertion = f"\n{current_indent}<fixja>{ja_content}</fixja>"
            return block[:tail_match.start()] + insertion + tail_part
        else:
            return block[:tail_match.start()] + f"{current_indent}<fixja>{ja_content}</fixja>" + tail_part
    
    return block

def process_files():
    # 1. ディレクトリの準備
    if not os.path.exists(SOURCE_DIR):
        print(f"エラー: ソースディレクトリ '{SOURCE_DIR}' が見つかりません。")
        return

    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"ディレクトリ作成: '{TARGET_DIR}'")

    # --- 2. ファイル削除フェーズ (TARGET_DIR内の text-*.xml のみ) ---
    print(f"'{TARGET_DIR}' 内の不要ファイル削除チェック...")
    
    target_files_paths = glob.glob(os.path.join(TARGET_DIR, 'text-*.xml'))
    target_files_map = {os.path.basename(p): p for p in target_files_paths}
    
    source_files_paths = glob.glob(os.path.join(SOURCE_DIR, 'text-*.xml'))
    source_files_names = set(os.path.basename(p) for p in source_files_paths)
    
    deleted_files_count = 0
    for filename, filepath in target_files_map.items():
        if filename not in source_files_names:
            try:
                os.remove(filepath)
                print(f"ファイル削除: {filename}")
                deleted_files_count += 1
            except Exception as e:
                print(f"削除エラー {filename}: {e}")

    # --- 3. ファイル内容の同期フェーズ ---
    # 同期対象は original 内の全ての .xml
    all_source_files = glob.glob(os.path.join(SOURCE_DIR, '*.xml'))
    print(f"{len(all_source_files)} 個のファイルを対象に同期を開始します...")

    # Regex設定
    entry_pattern_with_indent = re.compile(r"(\n?[ \t]*<Entry>.*?</Entry>)", re.DOTALL)
    simple_entry_pattern = re.compile(r"(<Entry>.*?</Entry>)", re.DOTALL)

    total_added_entries = 0
    total_deleted_entries = 0
    total_new_files = 0

    for src_path in all_source_files:
        filename = os.path.basename(src_path)
        dest_path = os.path.join(TARGET_DIR, filename)
        
        try:
            # Originalデータの読み込み
            with open(src_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            original_entries = simple_entry_pattern.findall(original_content)
            original_map = {}
            for block in original_entries:
                ztype = get_ztype(block)
                if ztype:
                    original_map[ztype] = block
            
            valid_ztypes = set(original_map.keys())

            # ターゲットディレクトリのファイルを処理
            if os.path.exists(dest_path):
                with open(dest_path, 'r', encoding='utf-8') as f:
                    target_content = f.read()

                deleted_count = 0
                
                # A. 削除ロジック (Entry単位) - target_contentから不要なEntryを消す
                def deletion_callback(match):
                    full_block = match.group(1)
                    ztype = get_ztype(full_block)
                    # originalに存在しないzTypeは削除
                    if ztype and ztype not in valid_ztypes:
                        nonlocal deleted_count
                        deleted_count += 1
                        return "" # 削除
                    return full_block

                target_content = entry_pattern_with_indent.sub(deletion_callback, target_content)

                # B. 追加ロジック (Entry単位)
                current_blocks = simple_entry_pattern.findall(target_content)
                current_ztypes = set()
                for block in current_blocks:
                    zt = get_ztype(block)
                    if zt:
                        current_ztypes.add(zt)

                blocks_to_add = []
                for block in original_entries:
                    ztype = get_ztype(block)
                    # originalにあってtargetにない場合
                    if ztype and ztype not in current_ztypes:
                        processed_block = add_fixja_to_block(block)
                        blocks_to_add.append(processed_block)

                # 書き込み判定
                if deleted_count > 0 or len(blocks_to_add) > 0:
                    if blocks_to_add:
                        last_tag_match = re.search(r"(\s*)(</[^>]+>)\s*$", target_content, re.DOTALL)
                        if last_tag_match:
                            start_pos = last_tag_match.start()
                            closing_tag = last_tag_match.group(2)
                            
                            formatted_blocks = "\n".join(["\t" + b for b in blocks_to_add])
                            new_tail = "\n" + formatted_blocks + "\n" + closing_tag
                            target_content = target_content[:start_pos] + new_tail

                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(target_content)
                    
                    print(f"同期完了: {filename} (削除: {deleted_count}件, 追加: {len(blocks_to_add)}件)")
                    total_deleted_entries += deleted_count
                    total_added_entries += len(blocks_to_add)
                else:
                    # 変更なし
                    pass 

            else:
                # 新規作成モード (original -> original-fixja へ新規作成)
                def replace_callback(match):
                    return add_fixja_to_block(match.group(1))
                
                new_content = simple_entry_pattern.sub(replace_callback, original_content)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"新規作成: {filename}")
                total_new_files += 1

        except Exception as e:
            print(f"エラー {filename}: {e}")

    print("-" * 30)
    print(f"全処理終了")
    print(f"  - 出力先: {TARGET_DIR}")
    print(f"  - ファイル削除: {deleted_files_count} ファイル")
    print(f"  - 新規ファイル作成: {total_new_files} ファイル")
    print(f"  - Entry削除: {total_deleted_entries} 箇所")
    print(f"  - Entry追加: {total_added_entries} 箇所")

if __name__ == '__main__':
    process_files()