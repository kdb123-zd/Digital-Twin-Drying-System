import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime
import CoolProp.CoolProp as CP
import plotly.graph_objects as go

# ==========================================
# 1. 页面基本配置
# ==========================================
st.set_page_config(page_title="Bertram Digital Twin", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 2. 纯手写高级数字孪生 CSS 引擎 + LED 呼吸灯
# ==========================================
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center top, #0A1428 0%, #030712 100%);
        font-family: 'Segoe UI', sans-serif;
    }
    header {visibility: hidden;}

    .main-title {
        text-align: center; color: #E2E8F0; font-size: 34px; font-weight: 800;
        letter-spacing: 4px; text-shadow: 0 0 15px rgba(0, 216, 255, 0.6);
        margin-top: -40px; margin-bottom: 25px;
    }

    .dual-card {
        background: linear-gradient(180deg, rgba(16, 33, 65, 0.6) 0%, rgba(5, 12, 25, 0.8) 100%);
        border: 1px solid rgba(0, 216, 255, 0.25);
        border-radius: 10px;
        padding: 10px 8px;
        margin-bottom: 12px;
        box-shadow: inset 0 0 15px rgba(0, 216, 255, 0.03), 0 4px 10px rgba(0,0,0,0.5);
        transition: transform 0.2s;
    }
    .dual-card:hover {
        transform: scale(1.02); border-color: rgba(0, 216, 255, 0.8);
        box-shadow: 0 0 20px rgba(0, 216, 255, 0.15);
    }
    .dc-title {
        color: #3399FF; font-size: 13px; font-weight: bold;
        margin-bottom: 5px; margin-left: 5px; text-transform: uppercase;
        text-shadow: 0 0 5px rgba(51, 153, 255, 0.4);
    }
    .dc-row { display: flex; justify-content: space-evenly; align-items: center; }
    .dc-item { text-align: center; flex: 1; }
    .dc-divider { width: 1px; height: 35px; background: rgba(0, 216, 255, 0.2); }
    .dc-label { color: #94A3B8; font-size: 11px; margin-bottom: 2px; }
    .dc-value { color: #00D8FF; font-size: 24px; font-weight: bold; text-shadow: 0 0 8px rgba(0, 216, 255, 0.4); }
    .dc-unit { font-size: 11px; color: #64748B; font-weight: normal; }

    .alert-matrix { display: flex; justify-content: space-between; gap: 10px; margin-top: 10px; }
    .alert-box {
        flex: 1; padding: 12px 5px; border-radius: 8px; text-align: center;
        background: rgba(10, 20, 40, 0.8); border: 1px solid;
        display: flex; flex-direction: column; align-items: center;
    }
    .alert-safe { border-color: rgba(16, 185, 129, 0.3); }
    .alert-danger { border-color: rgba(239, 68, 68, 0.8); background: rgba(239, 68, 68, 0.1); }
    .alert-warn { border-color: rgba(245, 158, 11, 0.8); }

    .led-bulb { width: 16px; height: 16px; border-radius: 50%; margin-bottom: 8px; }
    .led-green { background-color: #10B981; box-shadow: 0 0 10px #10B981, inset 0 0 5px rgba(255,255,255,0.5); }
    .led-yellow { background-color: #F59E0B; box-shadow: 0 0 15px #F59E0B; animation: pulse-yellow 1.5s infinite; }
    .led-red { background-color: #EF4444; box-shadow: 0 0 15px #EF4444; animation: pulse-red 0.8s infinite; }

    @keyframes pulse-red { 0% { box-shadow: 0 0 10px #EF4444; } 50% { box-shadow: 0 0 25px #EF4444; } 100% { box-shadow: 0 0 10px #EF4444; } }
    @keyframes pulse-yellow { 0% { box-shadow: 0 0 10px #F59E0B; } 50% { box-shadow: 0 0 20px #F59E0B; } 100% { box-shadow: 0 0 10px #F59E0B; } }

    .control-panel {
        background: rgba(10, 20, 40, 0.6); border: 1px solid rgba(0, 216, 255, 0.3);
        border-radius: 10px; padding: 15px; margin-top: 10px;
    }

    hr { border-top: 1px solid rgba(0, 216, 255, 0.15); margin: 15px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚡ BERTRAM 数字化孪生控制大屏</div>", unsafe_allow_html=True)

# ==========================================
# ⚙️ 3. 系统核心物理参数与能耗配置
# ==========================================
REFRIGERANT = 'R134a'
VOLTAGE = 220.0
POWER_FACTOR = 0.85

HIGH_POUT_LIMIT, LOW_PIN_LIMIT, LOW_SH_LIMIT, HIGH_TCOMO_LIMIT = 16.0, 0.5, 2.0, 95.0

current_date = datetime.now().strftime("%Y-%m-%d")
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(current_dir, f"Dymola_Data_Log_{current_date}.csv")


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                df.columns = df.columns.str.upper().str.strip()
                if 'TIME_STAMP' in df.columns:
                    df['TIME_STAMP'] = pd.to_datetime(df['TIME_STAMP'])
                    df.set_index('TIME_STAMP', inplace=True)
                return df
        except:
            pass
    return pd.DataFrame()


df = load_data()


# 核心热力学解算引擎
def calculate_thermodynamics(row):
    try:
        pin_abs = (float(row.get('PIN', 0)) + 1.01325) * 100000.0
        pout_abs = (float(row.get('POUT', 0)) + 1.01325) * 100000.0
        tcomi_k = float(row.get('TCOMI', 0)) + 273.15
        tcomo_k = float(row.get('TCOMO', 0)) + 273.15
        outcono_k = float(row.get('OUTCONO', 0)) + 273.15

        tsat_in_k = CP.PropsSI('T', 'P', pin_abs, 'Q', 1, REFRIGERANT)
        tsat_out_k = CP.PropsSI('T', 'P', pout_abs, 'Q', 1, REFRIGERANT)
        sh = (tcomi_k - 273.15) - (tsat_in_k - 273.15)
        dsh = (tcomo_k - 273.15) - (tsat_out_k - 273.15)

        h1 = CP.PropsSI('H', 'P', pin_abs, 'T', tcomi_k, REFRIGERANT)
        h2 = CP.PropsSI('H', 'P', pout_abs, 'T', tcomo_k, REFRIGERANT)
        h3 = CP.PropsSI('H', 'P', pout_abs, 'T', outcono_k, REFRIGERANT)

        cop = (h2 - h3) / (h2 - h1)*0.65 if (h2 - h1) > 0 else 0.0
        return pd.Series({'SH': sh, 'DSH': dsh, 'COP': cop})
    except:
        return pd.Series({'SH': 0.0, 'DSH': 0.0, 'COP': 0.0})


# 动态生成双子星卡片的辅助函数
def dual_card(title, l1, v1, u1, l2, v2, u2):
    return f"""
    <div class="dual-card">
        <div class="dc-title">◈ {title}</div>
        <div class="dc-row">
            <div class="dc-item"><div class="dc-label">{l1}</div><div class="dc-value">{v1} <span class="dc-unit">{u1}</span></div></div>
            <div class="dc-divider"></div>
            <div class="dc-item"><div class="dc-label">{l2}</div><div class="dc-value">{v2} <span class="dc-unit">{u2}</span></div></div>
        </div>
    </div>
    """


def create_gauge(value, title, max_val, color, suffix=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={'suffix': suffix, 'font': {'color': color, 'size': 24}},
        title={'text': title, 'font': {'color': '#3399FF', 'size': 13}},
        gauge={
            'axis': {'range': [None, max_val], 'tickwidth': 1, 'tickcolor': "#3399FF",
                     'tickfont': {'color': '#94A3B8'}},
            'bar': {'color': color}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 1,
            'bordercolor': "rgba(0, 216, 255, 0.2)",
            'steps': [{'range': [0, max_val], 'color': "rgba(10, 20, 40, 0.6)"}],
        }
    ))
    fig.update_layout(height=170, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      font={'color': "#00D8FF"})
    return fig


# 高级发光波形图引擎
def create_tech_line_chart(plot_df, title, y_title=""):
    fig = go.Figure()
    colors = ['#00D8FF', '#F59E0B', '#10B981', '#C084FC', '#FB7185']
    fills = ['rgba(0,216,255,0.1)', 'rgba(245,158,11,0.1)', 'rgba(16,185,129,0.1)', 'rgba(192,132,252,0.1)',
             'rgba(251,113,133,0.1)']

    for i, col in enumerate(plot_df.columns):
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[col], mode='lines', name=col,
            line=dict(width=2.5, color=colors[i % len(colors)], shape='spline'),
            fill='tozeroy', fillcolor=fills[i % len(fills)],
            hoverinfo='x+y+name'
        ))

    fig.update_layout(
        title=dict(text=f"◈ {title}", font=dict(color='#E2E8F0', size=15)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10,20,40,0.5)',
        font=dict(color='#94A3B8', size=11),
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 216, 255, 0.1)', zeroline=False, tickformat="%H:%M:%S"),
        yaxis=dict(title=y_title, showgrid=True, gridcolor='rgba(0, 216, 255, 0.1)', zeroline=False),
        margin=dict(l=30, r=20, t=40, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(color='#E2E8F0')),
        hovermode="x unified", height=280
    )
    return fig


if df.empty:
    st.error("🚨 无法建立通信：未检测到今日数据流。")
else:
    latest = df.iloc[-1]

    # 提取基础数据
    pout, pin, tcomo, ysjdl = latest.get('POUT', 0), latest.get('PIN', 0), latest.get('TCOMO', 0), latest.get('YSJDL',
                                                                                                              0)
    zkbdl = latest.get('ZKBDL', 0)

    # 电气能耗换算
    w_comp = ysjdl * VOLTAGE * POWER_FACTOR / 1000.0
    w_vp = zkbdl * VOLTAGE * POWER_FACTOR / 1000.0
    w_total = w_comp + w_vp

    # 热力学解算
    thermo_data = calculate_thermodynamics(latest)
    sh, dsh, cop = thermo_data['SH'], thermo_data['DSH'], thermo_data['COP']

    # 🌟 核心提炼：计算多点温度均值(T1,T2,T3) 与 多点湿度均值(W1,W2,W3)
    t_avg = (float(latest.get('T1', 0)) + float(latest.get('T2', 0)) + float(latest.get('T3', 0))) / 3.0
    w_avg = (float(latest.get('W1', 0)) + float(latest.get('W2', 0)) + float(latest.get('W3', 0))) / 3.0

    # ==========================================
    # 🎛 *完美 6v6 满血中轴对称布局*
    # ==========================================
    col_left, col_center, col_right = st.columns([1.1, 2.5, 1.1])

    # ------------------ 左栏：功耗、能效、物料与环境 (6块) ------------------
    with col_left:
        st.markdown(
            dual_card("压缩机吸排气压力", "吸气 (PIN)", f"{pin:.2f}", "bar", "排气 (POUT)", f"{pout:.2f}", "bar"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("运行回路监测电流", "压缩机 (YSJDL)", f"{ysjdl:.2f}", "A", "真空泵 (ZKBDL)", f"{zkbdl:.2f}", "A"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("设备实时运行能耗", "压缩机能耗", f"{w_comp:.2f}", "kW", "真空泵能耗", f"{w_vp:.2f}", "kW"),
            unsafe_allow_html=True)
        st.markdown(dual_card("系统综合能效评估", "系统总功耗", f"{w_total:.2f}", "kW", "热力学 COP", f"{cop:.2f}", ""),
                    unsafe_allow_html=True)
        st.markdown(
            dual_card("系统进排气过热度", "吸气过热 (SH)", f"{sh:.1f}", "℃", "排气过热 (DSH)", f"{dsh:.1f}", "℃"),
            unsafe_allow_html=True)
        st.markdown(
            dual_card("物料与环境状态", "当前重量 (ZL)", f"{latest.get('ZL', 0):.1f}", "g", "平均湿度 (W_AVG)",
                      f"{w_avg:.1f}", "%"), unsafe_allow_html=True)

    # ------------------ 中栏：孪生主图 + 仪表盘 + 警报矩阵 ------------------
    with col_center:
        st.markdown("""
        <div style="background: rgba(10, 20, 40, 0.4); border: 1px solid rgba(0, 216, 255, 0.15); border-radius: 12px; height: 380px; padding: 20px; text-align: center; display: flex; flex-direction: column; justify-content: center; position: relative; margin-bottom: 5px;">
            <h3 style="color: rgba(51, 153, 255, 0.3);">[ 3D 设 备 孪生 图 纸 预 留 区 ]</h3>
        </div>
        """, unsafe_allow_html=True)

        cg1, cg2 = st.columns(2)
        with cg1: st.plotly_chart(create_gauge(latest.get('ZKD', 0), "绝对真空度 (ZKD)", 120000, "#00D8FF", " Pa"),
                                  width="stretch")
        with cg2: st.plotly_chart(create_gauge(latest.get('PZFKD', 0), "EEV 开度 (PZFKD)", 100, "#22D3EE", " %"),
                                  width="stretch")

        pout_cls, pout_led = ("alert-danger", "led-red") if pout > HIGH_POUT_LIMIT else ("alert-safe", "led-green")
        pin_cls, pin_led = ("alert-danger", "led-red") if pin < LOW_PIN_LIMIT else ("alert-safe", "led-green")
        sh_cls, sh_led = ("alert-warn", "led-yellow") if (sh < LOW_SH_LIMIT and ysjdl > 1.0) else (
        "alert-safe", "led-green")
        tcomo_cls, tcomo_led = ("alert-danger", "led-red") if tcomo > HIGH_TCOMO_LIMIT else ("alert-safe", "led-green")

        st.markdown(f"""
        <div class="alert-matrix">
            <div class="alert-box {pout_cls}"><div class="led-bulb {pout_led}"></div><div class="alert-title">高压排气</div><div class="alert-val" style="color: {'#EF4444' if pout > HIGH_POUT_LIMIT else '#10B981'};">{pout:.2f} bar</div></div>
            <div class="alert-box {pin_cls}"><div class="led-bulb {pin_led}"></div><div class="alert-title">低压吸气</div><div class="alert-val" style="color: {'#EF4444' if pin < LOW_PIN_LIMIT else '#10B981'};">{pin:.2f} bar</div></div>
            <div class="alert-box {sh_cls}"><div class="led-bulb {sh_led}"></div><div class="alert-title">液击风险(SH)</div><div class="alert-val" style="color: {'#F59E0B' if (sh < LOW_SH_LIMIT and ysjdl > 1.0) else '#10B981'};">{sh:.1f} ℃</div></div>
            <div class="alert-box {tcomo_cls}"><div class="led-bulb {tcomo_led}"></div><div class="alert-title">排气超温</div><div class="alert-val" style="color: {'#EF4444' if tcomo > HIGH_TCOMO_LIMIT else '#10B981'};">{tcomo:.1f} ℃</div></div>
        </div>
        """, unsafe_allow_html=True)

    # ------------------ 右栏：全系统各节点热场网络 (6块) ------------------
    with col_right:
        st.markdown(dual_card("压缩机进出口温度", "进口 (TCOMI)", f"{latest.get('TCOMI', 0):.1f}", "℃", "出口 (TCOMO)",
                              f"{tcomo:.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(
            dual_card("蒸发器进出口温度", "进口 (EVPINT)", f"{latest.get('EVPINT', 0):.1f}", "℃", "出口 (EVPOUT)",
                      f"{latest.get('EVPOUT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("冷凝器进出口温度", "进口 (CONIN)", f"{latest.get('CONIN', 0):.1f}", "℃", "出口 (CONOUT)",
                              f"{latest.get('CONOUT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("外冷出与靶材核心", "外冷出 (OUTCONO)", f"{latest.get('OUTCONO', 0):.1f}", "℃",
                              "物料温度 (WULIAOT)", f"{latest.get('WULIAOT', 0):.1f}", "℃"), unsafe_allow_html=True)
        st.markdown(dual_card("腔体多点平均温度", "平均测温 (T_AVG)", f"{t_avg:.1f}", "℃", "系统工质", REFRIGERANT, ""),
                    unsafe_allow_html=True)
        st.markdown(dual_card("数字孪生通信网络", "刷新频率", "0.5", "Hz", "网络延时", "< 10", "ms"),
                    unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ==========================================
    # 📉 底部高级赛博朋克图表区
    # ==========================================
    st.markdown("<h4 style='color: #00D8FF;'>📉 深度时序波形诊断与滤波网络</h4>", unsafe_allow_html=True)

    c_set1, c_set2 = st.columns([1, 4])
    with c_set1:
        st.markdown("""<div class='control-panel'>""", unsafe_allow_html=True)
        window_option = st.selectbox("⏳ 数据视窗", ["最近 200 条", "最近 500 条", "显示全部"])
        filter_window = st.slider("⚡ 电流降噪滤波强度", 1, 50, 10)
        st.markdown("""</div>""", unsafe_allow_html=True)

    plot_df = df.tail(200).copy() if window_option == "最近 200 条" else (
        df.tail(500).copy() if window_option == "最近 500 条" else df.copy())

    if 'YSJDL' in plot_df.columns and filter_window > 1: plot_df['YSJDL'] = plot_df['YSJDL'].rolling(
        window=filter_window, min_periods=1).mean().round(2)
    if 'ZKBDL' in plot_df.columns and filter_window > 1: plot_df['ZKBDL'] = plot_df['ZKBDL'].rolling(
        window=filter_window, min_periods=1).mean().round(2)

    plot_df['系统总功耗(kW)'] = (plot_df['YSJDL'] + plot_df['ZKBDL']) * VOLTAGE * POWER_FACTOR / 1000.0

    thermo_history = plot_df.apply(calculate_thermodynamics, axis=1)
    plot_df['系统COP'] = thermo_history['COP']

    with c_set2:
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            keys = [k for k in ['POUT', 'PIN'] if k in plot_df.columns]
            if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "系统高低压动态极值", "压力 (bar)"),
                                     width="stretch")
        with col_c2:
            keys = [k for k in ['CONIN', 'CONOUT', 'WULIAOT'] if k in plot_df.columns]
            if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "换热侧与物料温升逼近", "温度 (℃)"),
                                     width="stretch")
        with col_c3:
            keys = [k for k in ['系统总功耗(kW)', '系统COP'] if k in plot_df.columns]
            if keys: st.plotly_chart(create_tech_line_chart(plot_df[keys], "能效与功耗动态时序交叉", "数值"),
                                     width="stretch")

# 心跳刷新
time.sleep(2)
st.rerun()