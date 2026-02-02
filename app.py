# [1-4 冒頭と関数定義は維持：Tab 2 の中身を以下に差し替え]

    with tab2:
        st.markdown("##### 収支影響シミュレーション")
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
        
        if st.session_state.simulation_result is not None:
            sr = st.session_state.simulation_result
            total_curr = sr['現行料金'].sum()
            
            # --- 【強化】サマリーメトリクス ---
            summ_cols = st.columns(len(new_plans) + 1)
            summ_cols[0].metric("現行 売上総額", f"¥{total_curr:,.0f}")
            
            summ_data = [{"プラン名": "現行", "売上": total_curr, "差額": 0, "増減率": 0.0}]
            for idx, (pn, pdf) in enumerate(new_plans.items()):
                t_new = sr[pn].sum()
                diff = t_new - total_curr
                ratio = (diff / total_curr * 100) if total_curr != 0 else 0
                summ_data.append({"プラン名": pn, "売上": t_new, "差額": diff, "増減率": ratio})
                # メトリクス表示
                summ_cols[idx+1].metric(f"{pn} 売上", f"¥{t_new:,.0f}", f"{ratio:+.2f}%")

            st.markdown("---")
            
            # --- 【強化】ビジュアル分析 ---
            c_graph1, c_graph2 = st.columns(2)
            sel_p = c_graph1.selectbox("可視化するプランを選択", list(new_plans.keys()))
            
            with c_graph1:
                # 差額の分布（ヒストグラム）
                fig_hist = px.histogram(sr, x=f"{sel_p}_差額", nbins=50, title=f"{sel_p}: 顧客別影響額分布",
                                       color_discrete_sequence=[COLOR_NEW])
                fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_hist, use_container_width=True, key="sim_hist")

            with c_graph2:
                # 新旧価格プロット（散布図）
                # データ量が多い場合は1000件サンプリングして軽量化
                sample_n = min(len(sr), 1000)
                df_smp = sr.sample(sample_n)
                fig_scatter = go.Figure()
                fig_scatter.add_trace(go.Scatter(x=df_smp['使用量'], y=df_smp['現行料金'], mode='markers', name='現行', marker=dict(color=COLOR_CURRENT, opacity=0.5)))
                fig_scatter.add_trace(go.Scatter(x=df_smp['使用量'], y=df_smp[sel_p], mode='markers', name=sel_p, marker=dict(color=COLOR_NEW, opacity=0.5)))
                fig_scatter.update_layout(title=f"使用量 vs 料金 (n={sample_n})", xaxis_title="使用量 (m³)", yaxis_title="料金 (円)")
                st.plotly_chart(fig_scatter, use_container_width=True, key="sim_scatter")

            st.markdown("### 集計一覧")
            st.dataframe(pd.DataFrame(summ_data).style.format({
                "売上": "¥{:,.0f}", "差額": "¥{:,.0f}", "増減率": "{:+.2f}%"
            }), hide_index=True, use_container_width=True)
