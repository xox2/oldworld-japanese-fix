# README

1. まずオリジナルのファイルを手動でoriginalに置く
2. sync_fixja.pyを実行してoriginal-fixjaフォルダを更新する
3. AIに読み込ませるために、sync_for_ai.pyを実行してoriginal-ai-fixjaフォルダを更新する（このファイルはサイズが軽くなるように最適化されます）
4. original-fixjaフォルダの内容を確認し、必要に応じて修正する
5. extract_diff.pyを実行して、ビルドする