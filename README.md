# PyMacro
PythonでC++等のマクロやテンプレートを再現しようというやつです
使い方
```py
@def_macro(mode="s")
def chmax(a, b):
    a = max(a, b)
    

@def_macro
def chmin(a, b):
    [a>b, a := min(a, b)][0]


@macro(chmax | chmin)
def main():
    a = 0
    print(a)
    chmax(a, 2)
    print(a)
    if chmin(a, -1):
        print(a)

```
```
0
2
-1
```
という感じです
def_macroデコレータでマクロを定義します。デフォルトだと1行目の式として展開、mode="s"とすると関数全体の文として展開します。
定義したマクロは|演算子でまとめれます(|=も使えます)。
そして、@macroデコレータでマクロを関数に適応させます。適応させるマクロを引数で指定します。
@macroデコレータをprint_code=Trueで呼び出すと、関数ではなく展開後のコードが返されます。これはPython3.9以降でしか使えません。
