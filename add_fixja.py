import os
import glob
import re

def process_files():
    source_dir = 'original'
    
    # originalディレクトリの確認
    if not os.path.exists(source_dir):
        print(f"エラー: '{source_dir}' ディレクトリが見つかりません。")
        return

    files = glob.glob(os.path.join(source_dir, '*.xml'))
    if not files:
        print(f"'{source_dir}' 内にXMLファイルが見つかりません。")
        return

    print(f"{len(files)} 個のファイルを処理します...")

    # <Entry>...</Entry> ブロックを抽出する正規表現（改行含む）
    entry_pattern = re.compile(r"(<Entry>.*?</Entry>)", re.DOTALL)
    
    # <ja>の中身を抽出する正規表現
    ja_pattern = re.compile(r"<ja>(.*?)</ja>", re.DOTALL)
    
    # <fixja>が既に存在するかチェックする正規表現
    fixja_check_pattern = re.compile(r"<fixja>.*?</fixja>", re.DOTALL)

    for file_path in files:
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 置換処理を行う関数
            def replace_entry_block(match):
                block = match.group(1)
                
                # 既に <fixja> がある場合は何もしない
                if fixja_check_pattern.search(block):
                    return block
                
                # <ja> タグを探す
                ja_match = ja_pattern.search(block)
                if not ja_match:
                    return block # <ja>がない場合も何もしない
                
                ja_content = ja_match.group(1) # 中身をそのまま取得（タグなども含む）

                # <ja>タグのインデントレベルを推測（行頭の空白を取得）
                # block内での検索だと行頭マッチが難しいので、再検索
                ja_indent_match = re.search(r"(^[ \t]*)<ja>", block, re.MULTILINE)
                if ja_indent_match:
                    indent_str = ja_indent_match.group(1)
                else:
                    indent_str = "\t" # デフォルト

                # ブロック末尾の </Entry> とその前の空白を検出
                tail_match = re.search(r"(\s*</Entry>)$", block)
                if tail_match:
                    tail_part = tail_match.group(1)
                    # 挿入する文字列を作成（前に改行、インデント、タグ）
                    # 末尾の空白(tail_part)の前に挿入することで、前後の改行を維持
                    
                    # tail_part が "\n\t</Entry>" のように改行で始まっている場合、
                    # 挿入文字列の先頭にも改行をつけると "\n\n" になる可能性があるが、
                    # tail_part は「前のタグの後ろの改行」を含んでいるので、
                    # ここでは「前のタグの後ろ」に「改行+インデント+fixja」を追加する形にする。
                    
                    if tail_part.startswith('\n'):
                        # tail_part = "\n\t</Entry>"
                        # 挿入 = "\n\t\t<fixja>...</fixja>"
                        # 結果 = "\n\t\t<fixja>...</fixja>" + "\n\t</Entry>"
                        # これで、前のタグ </xx> の後に改行して fixja が来て、その後に改行して </Entry> が来る
                        insertion = f"\n{indent_str}<fixja>{ja_content}</fixja>"
                        
                        # blockの末尾(tail_part)を (insertion + tail_part) に置き換える
                        return block[:tail_match.start()] + insertion + tail_part
                    else:
                        # 改行がない場合（1行XMLなど）、強制的に改行を入れるかそのまま繋げる
                        return block[:tail_match.start()] + f"{indent_str}<fixja>{ja_content}</fixja>" + tail_part
                
                # 万が一末尾マッチが失敗した場合（通常ありえない）
                return block

            # ファイル全体に対して置換を実行
            new_content = entry_pattern.sub(replace_entry_block, content)

            # ファイル書き出し
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            print(f"処理完了: {filename}")

        except Exception as e:
            print(f"エラー {filename}: {e}")

if __name__ == '__main__':
    process_files()