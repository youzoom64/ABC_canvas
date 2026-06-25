# ABC Canvas

ABC Canvas は、意味をポワンとして置き、その中にさらに意味を入れていくためのローカルWebアプリです。

## 起動

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8790 --no-access-log
```

Windows では `start_abc_canvas.bat` からも起動できます。

## サンプル

`powan_work/APIから作ったプロジェクト_20260624_072755/project.powan` に、国家ポワンのサンプルを入れています。

## 公開対象外

DB、ログ、個人設定、作業中の他プロジェクト、キャッシュ、一時テスト結果は公開対象から外しています。
