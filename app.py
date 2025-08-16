# app.py
import os
import streamlit as st
from scoring import UnitInput, compute_scores, STATS

# ---- ユーティリティ ----
def pow_label(role: str):
    return "力（POW）" if role == "physical" else "魔力（POW）"

# ---- 基本設定 ----
st.set_page_config(page_title="FE6 キャラ評価（試作）", page_icon="🛡️", layout="centered")
st.title("ファイアーエムブレム封印の剣｜キャラ性能評価（試作）")

# ---- サイドバー：基本情報 ----
with st.sidebar:
    st.header("基本情報")
    name = st.text_input("キャラクター名", value="ロイ")
    class_name = st.text_input("クラス", value="ロード")  # ← 追加：クラス名
    level = st.number_input("レベル", min_value=1, max_value=20, value=10, step=1)
    role  = st.radio("職種", options=["physical","magical"], index=0,
                     format_func=lambda x: "物理職" if x=="physical" else "魔法職")
    st.caption("初期→現在→上限の関係から“成長度合い”も加点します。")

# ---- パラメータ入力（整数） ----
st.subheader("パラメータ入力")
colA, colB, colC = st.columns(3)
with colA: st.markdown("**初期値**")
with colB: st.markdown("**現在値**")
with colC: st.markdown("**上限値**")

def draw_rows_int(label_jp, key, default_cap=20):
    c1, c2, c3 = st.columns(3)
    with c1:
        init = st.number_input(f"{label_jp} 初期", key=f"init_{key}",
                               value=0, step=1, min_value=0)
    with c2:
        cur = st.number_input(f"{label_jp} 現在", key=f"cur_{key}",
                              value=0, step=1, min_value=0)
    with c3:
        cap = st.number_input(f"{label_jp} 上限", key=f"cap_{key}",
                              value=default_cap, step=1, min_value=0)
    return int(init), int(cur), int(cap)

labels = {
    "HP":"HP", "POW":"力（魔力）", "SKL":"技", "SPD":"速さ",
    "LCK":"幸運", "DEF":"守備", "RES":"魔防"
}

init_vals, cur_vals, cap_vals = {}, {}, {}
for stat_key in STATS:
    default_cap = 60 if stat_key == "HP" else 30
    i, c, p = draw_rows_int(labels[stat_key], stat_key, default_cap=default_cap)
    # scoring側はfloatでもOKだが、ここでは入力をintとして受け取り、floatへ変換
    init_vals[stat_key] = float(i)
    cur_vals[stat_key]  = float(c)
    cap_vals[stat_key]  = float(p)

# ---- 入力チェック ----
def validate(init_d, cur_d, cap_d) -> list:
    errs = []
    for k in STATS:
        if cap_d[k] < 0:
            errs.append(f"{k}: 上限は0以上にしてください。")
        if init_d[k] > cap_d[k]:
            errs.append(f"{k}: 初期値が上限を超えています。")
        if cur_d[k] > cap_d[k]:
            errs.append(f"{k}: 現在値が上限を超えています。")
    return errs

errs = validate(init_vals, cur_vals, cap_vals)
if errs:
    st.error("入力エラー:\n- " + "\n- ".join(errs))

st.divider()
if st.button("評価する", disabled=bool(errs)):
    u = UnitInput(
        name=name, level=int(level), role=role,
        init=init_vals, cur=cur_vals, cap=cap_vals
    )
    scores, rank = compute_scores(u)

    st.success(
        f"**{name}（{class_name}, Lv{level}, {'物理' if role=='physical' else '魔法'}）の評価結果：{rank} ランク**"
    )
    st.metric("総合スコア（0-100）", scores["TOTAL_100"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("攻撃面（0〜1）", f"{scores['O_offense']:.3f}")
        st.caption(f"達成度：{scores['O_offense']*100:.1f}% "
                   "（力/技/速さ/幸運を上限に対する比で加重。1.0に近いほど高火力）")
    with c2:
        st.metric("防御面（0〜1）", f"{scores['D_defense']:.3f}")
        st.caption(f"達成度：{scores['D_defense']*100:.1f}% "
                   "（HP/守備/魔防/速さを上限比で加重。1.0に近いほど倒されにくい）")
    with c3:
        st.metric("成長度合い（0〜1）", f"{scores['G_growth']:.3f}")
        st.caption(f"達成度：{scores['G_growth']*100:.1f}% "
                   "（初期→現在の伸びを上限制約で割った比。1.0は“ほぼ伸び切り”）")

    # ---- 任意：LLM解説（クラス＋現在パラメータも参照） ----
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # 現在パラメータ（整数表示に戻す）
            cur_int_view = {k: int(cur_vals[k]) for k in cur_vals}

            prompt = f"""
あなたは任天堂のゲーム「ファイアーエムブレム」の育成アドバイザーです。次のユニット情報を踏まえ、簡潔に助言してください。
ユニット: {name}
クラス: {class_name}
レベル: {level}
職種: {"物理職" if role=="physical" else "魔法職"}
現在パラメータ（整数）: {cur_int_view}

スコア:
- 総合評価: {scores["TOTAL_100"]} / ランク: {rank}
- 攻撃面(0-1): {scores["O_offense"]}
- 防御面(0-1): {scores["D_defense"]}
- 成長度合い(0-1): {scores["G_growth"]}

出力フォーマット（日本語・箇条書き）:
1) 強み（3点以内）
2) 弱み（3点以内）
3) 役割（クラスの特性を踏まえ簡潔に）
            """.strip()

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.3,
            )
            st.subheader("解説（LLM）")
            st.write(resp.choices[0].message.content)
        except Exception as e:
            st.info(f"LLM解説はスキップしました（{e}）")
    else:
        st.caption("LLM解説を有効にするには OPENAI_API_KEY を環境変数に設定してください。")

