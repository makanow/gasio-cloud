# [1-4 冒頭と関数定義は完全に維持：Tab 2 の中身を以下に差し替え]

    with tab2:
        st.markdown("##### 収支影響シミュレーション")
        
        # 計算実行ボタン
        if st.button("🚀 シミュレーション計算実行", type="primary"):
            with st.spinner("計算中..."):
                res = df_target_usage.copy()
                # 現行料金の計算
                res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']], r['調定数']), axis=1)
                # 新プランの計算
                for pn, pdf in new_plans.items():
                    res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf, r['調定数']), axis=1)
                    res[f"{pn}_差額"] = res[pn] - res['現行料金']
                st.session_state.simulation_result = res

        # 結果表示エリア
        if st.session_state.simulation_result is not None:
            sr = st.session_state.simulation_result
            total_curr = sr['現行料金'].sum()

            # --- 1. サマリーメトリクス (視覚化) ---
            st.markdown("### 📊 収支インパクト")
            m_cols = st.columns(len(new_plans) + 1)
            m_cols[0].metric("現行 売上総額", f"¥{total_curr:,.0f}")
            
            summ_list = []
            for idx, (pn, pdf) in enumerate(new_plans.items()):
                t_new = sr[pn].sum()
                diff = t_new - total_curr
                ratio = (diff / total_curr * 100) if total_curr != 0 else 0
                
                # プランごとにメトリクスを表示
                m_cols[idx+1].metric(f"{pn}", f"¥{t_new:,.0f}", f"{ratio:+.2f}%")
                summ_list.append({"プラン名": pn, "売上総額": t_new, "増減額": diff, "増減率": ratio})

            st.markdown("---")

            # --- 2. グラフ分析 ---
            g_col1, g_col2 = st.columns(2)
            sel_p = g_col1.selectbox("分析対象プランを選択", list(new_plans.keys()), key="sel_p_graph")

            with g_col1:
                # 影響額の分布 (ヒストグラム)
                fig_h = px.histogram(sr, x=f"{sel_p}_差額", nbins=50, 
                                   title=f"顧客別影響額の分布 ({sel_p})",
                                   color_discrete_sequence=['#e67e22'])
                fig_h.add_vline(x=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_h, use_container_width=True)

            with g_col2:
                # 新旧価格の比較 (散布図) - 1000件サンプリング
                s_size = min(len(sr), 1000)
                s_df = sr.sample(s_size)
                fig_s = px.scatter(s_df, x='使用量', y=['現行料金', sel_p],
                                 title=f"使用量 vs 料金プロット (n={s_size})",
                                 labels={'value': '料金 (円)', 'variable': 'プラン'},
                                 color_discrete_sequence=['#95a5a6', '#3498db'],
                                 opacity=0.6)
                st.plotly_chart(fig_s, use_container_width=True)

            # --- 3. データテーブル ---
            st.markdown("### 📋 集計データ")
            st.dataframe(pd.DataFrame(summ_list).style.format({
                "売上総額": "¥{:,.0f}", "増減額": "¥{:,.0f}", "増減率": "{:+.2f}%"
            }), hide_index=True, use_container_width=True)
